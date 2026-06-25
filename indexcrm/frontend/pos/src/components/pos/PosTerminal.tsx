"use client";

import { AlertTriangle } from "lucide-react";
import { useMemo, useState } from "react";

import { PosShell } from "@/components/layout/PosShell";
import { useOfflineSalesQueue } from "@/hooks/useOfflineSalesQueue";
import { usePosConnectivity } from "@/hooks/usePosConnectivity";
import { useCompleteSaleFlow } from "@/hooks/useSales";
import { findProductByBarcode } from "@/services/api/products";
import { ApiError } from "@/services/api/client";
import {
  createSaleIdempotencyKey,
  enqueuePendingSale,
} from "@/services/offlineSalesQueue";
import {
  Product,
  Sale,
  SalePaymentMethod,
  SalePayload,
} from "@/services/api/types";
import { useCartStore, getCartLineTotal } from "@/stores/cartStore";
import { useCashierStore } from "@/stores/cashierStore";
import { useCustomerStore } from "@/stores/customerStore";
import { toApiMoney, toApiQuantity } from "@/lib/format";

import { BarcodeInput } from "./BarcodeInput";
import { CartSummary } from "./CartSummary";
import { CartTable } from "./CartTable";
import { CashierSessionPanel } from "./CashierSessionPanel";
import { CustomerPicker } from "./CustomerPicker";
import { OfflineSyncStatus } from "./OfflineSyncStatus";
import { PaymentPanel } from "./PaymentPanel";
import { ProductSearch } from "./ProductSearch";
import { ReceiptPreview } from "./ReceiptPreview";

function stringifyDetail(detail: unknown): string {
  if (!detail) {
    return "";
  }
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    return detail.map((item) => stringifyDetail(item)).filter(Boolean).join(" ");
  }
  if (typeof detail === "object") {
    return Object.entries(detail as Record<string, unknown>)
      .filter(([key]) => !["code", "message"].includes(key))
      .map(([key, value]) => `${key}: ${stringifyDetail(value)}`)
      .filter((message) => !message.endsWith(": "))
      .join(" ");
  }
  return String(detail);
}

function getApiErrorCode(detail: unknown) {
  if (detail && typeof detail === "object" && "code" in detail) {
    return String((detail as { code?: unknown }).code);
  }
  return "";
}

function formatError(error: unknown) {
  if (error instanceof ApiError) {
    const code = getApiErrorCode(error.detail);
    if (code === "shift_closed_missing") {
      return "Faol kassir smenasi yo'q. Chekoutdan oldin Sessiya panelida smenani oching.";
    }
    if (code === "stock_conflict") {
      return "Savatdagi ayrim mahsulotlar uchun qoldiq yetarli emas. Miqdor va ombor qoldig'ini tekshiring.";
    }
    if (code === "idempotency_conflict") {
      return "Bu checkout boshqa savat ma'lumotlari bilan yuborilgan. Yangi savdo boshlang va qayta urinib ko'ring.";
    }
    if (code === "scope_denied") {
      return "Bu filial yoki ombor akkauntingiz uchun mavjud emas. Admin filial huquqlarini tekshirsin.";
    }
    if (error.status === 401 || error.status === 403) {
      return "Sessiyangiz endi amal qilmaydi. Qayta kiring.";
    }
    if (error.status >= 500) {
      return "Server checkoutni yakunlay olmadi. Bir marta qayta urinib ko'ring, davom etsa yordamga murojaat qiling.";
    }
    if (error.status === 400) {
      const detailMessage = stringifyDetail(error.detail);
      return detailMessage
        ? `Checkoutni tekshirish kerak. ${detailMessage}`
        : "Checkoutni tekshirish kerak. Filial, ombor, qoldiq, to'lov va mijoz ma'lumotlarini tekshiring.";
    }
    return "So'rov bajarilmadi. Aloqani tekshirib, qayta urinib ko'ring.";
  }
  if (
    error instanceof TypeError ||
    (error instanceof Error &&
      ["Failed to fetch", "fetch failed"].includes(error.message))
  ) {
    return "Backend bilan aloqa yo'q. Filial, ombor va smena tayyor bo'lsa, savdo offline saqlanadi.";
  }
  if (error instanceof Error) {
    return "Xatolik yuz berdi. Qayta urinib ko'ring.";
  }
  return "Kutilmagan xatolik";
}

type CheckoutPayment = {
  payment_method: SalePaymentMethod;
  amount: number;
};

export function PosTerminal() {
  const items = useCartStore((state) => state.items);
  const addProduct = useCartStore((state) => state.addProduct);
  const setQuantity = useCartStore((state) => state.setQuantity);
  const removeItem = useCartStore((state) => state.removeItem);
  const clearCart = useCartStore((state) => state.clearCart);
  const { selectedCustomer, setSelectedCustomer } = useCustomerStore();
  const {
    activeShiftId,
    branchId,
    cashDeskId,
    cashierEmail,
    cashierName,
    warehouseId,
  } = useCashierStore();
  const connectivity = usePosConnectivity();
  const { lockState, summary: offlineSummary } = useOfflineSalesQueue();
  const completeSale = useCompleteSaleFlow();
  const [notice, setNotice] = useState("");
  const [scanLoading, setScanLoading] = useState(false);
  const [offlineSavePending, setOfflineSavePending] = useState(false);
  const [completedSale, setCompletedSale] = useState<Sale | null>(null);
  const [checkoutIdempotencyKey, setCheckoutIdempotencyKey] = useState("");

  const itemCount = useMemo(
    () => items.reduce((totalItems, item) => totalItems + item.quantity, 0),
    [items],
  );
  const subtotal = useMemo(
    () =>
      Math.round(
        items.reduce((total, item) => total + item.quantity * item.price, 0) * 100,
      ) / 100,
    [items],
  );
  const total = useMemo(
    () =>
      Math.round(
        items.reduce((sum, item) => sum + getCartLineTotal(item), 0) * 100,
      ) / 100,
    [items],
  );
  const missingSessionReason = !branchId && !warehouseId
    ? "Filial va ombor tanlanmagan. Checkoutdan oldin ularni Sessiya panelida tanlang."
    : !branchId
      ? "Filial tanlanmagan. Checkoutdan oldin Sessiya panelida filialni tanlang."
      : !warehouseId
        ? "Ombor tanlanmagan. Checkoutdan oldin Sessiya panelida omborni tanlang."
        : !activeShiftId
          ? "Faol kassir smenasi yo'q. Checkoutdan oldin Sessiya panelida smenani oching."
          : undefined;

  function addToCart(product: Product) {
    const existingItem = items.find((item) => item.product.id === product.id);
    addProduct(product);
    setCompletedSale(null);
    setCheckoutIdempotencyKey("");
    setNotice(
      existingItem
        ? `${product.name} miqdori oshirildi`
        : `${product.name} savatga qo'shildi`,
    );
  }

  async function handleScan(code: string) {
    setNotice("");
    setScanLoading(true);
    try {
      const product = await findProductByBarcode(code);

      if (!product) {
        setNotice(`"${code}" kodi bo'yicha mahsulot topilmadi. SKU/barcodeni tekshiring.`);
        return;
      }
      addToCart(product);
    } catch (error) {
      setNotice(
        error instanceof TypeError
          ? "Backend bilan aloqa yo'q. Skan qilingan mahsulot qo'shilmadi."
          : `"${code}" kodini qidirib bo'lmadi. Qayta urinib ko'ring.`,
      );
    } finally {
      setScanLoading(false);
    }
  }

  function buildSalePayload(payments: CheckoutPayment[], idempotencyKey: string) {
    return {
      branch: branchId,
      warehouse: warehouseId,
      idempotency_key: idempotencyKey,
      customer: selectedCustomer?.id ?? null,
      discount_amount: "0.00",
      tax_amount: "0.00",
      items: items.map((item) => ({
        product: item.product.id,
        quantity: toApiQuantity(item.quantity),
        price: toApiMoney(item.price),
        discount: toApiMoney(item.discount),
      })),
      payments: payments.map((payment) => ({
        payment_method: payment.payment_method,
        amount: toApiMoney(payment.amount),
      })),
    } satisfies SalePayload;
  }

  function getStableCheckoutKey() {
    const idempotencyKey = checkoutIdempotencyKey || createSaleIdempotencyKey();
    setCheckoutIdempotencyKey(idempotencyKey);
    return idempotencyKey;
  }

  async function handleOfflineSale(payments: CheckoutPayment[]) {
    if (missingSessionReason) {
      setNotice(`Offline savdo saqlanmadi. ${missingSessionReason}`);
      return;
    }
    if (items.length === 0) {
      setNotice("Savat bo'sh");
      return;
    }

    const idempotencyKey = getStableCheckoutKey();
    const payload = buildSalePayload(payments, idempotencyKey);

    setOfflineSavePending(true);
    try {
      const queuedSale = await enqueuePendingSale({
        payload,
        cartItems: items.map((item) => ({
          productId: item.product.id,
          productName: item.product.name,
          sku: item.product.sku,
          barcode: item.product.barcode,
          quantity: item.quantity,
          price: item.price,
          discount: item.discount,
          lineTotal: getCartLineTotal(item),
        })),
        payments,
        session: {
          branchId,
          warehouseId,
          cashDeskId,
          activeShiftId,
          cashierName,
          cashierEmail,
          customerId: selectedCustomer?.id ?? null,
          customerName: selectedCustomer?.full_name ?? null,
        },
        totals: {
          subtotal,
          total,
          paidAmount:
            Math.round(
              payments.reduce((sum, payment) => sum + payment.amount, 0) * 100,
            ) / 100,
        },
      });
      clearCart();
      setCompletedSale(null);
      setCheckoutIdempotencyKey("");
      setNotice(
        `Savdo ushbu qurilmada saqlandi (${queuedSale.receiptFallback.receiptNumber}). Hali serverga yuborilmagan.`,
      );
    } catch {
      setNotice(
        "Offline savdo ushbu qurilmada saqlanmadi. Savatni tozalashdan oldin brauzer xotirasini tekshirib, qayta urinib ko'ring.",
      );
    } finally {
      setOfflineSavePending(false);
    }
  }

  async function handleCompleteSale(payments: CheckoutPayment[]) {
    if (missingSessionReason) {
      setNotice(missingSessionReason);
      return;
    }
    if (items.length === 0) {
      setNotice("Savat bo'sh");
      return;
    }

    const idempotencyKey = getStableCheckoutKey();
    const payload = buildSalePayload(payments, idempotencyKey);

    try {
      const sale = await completeSale.mutateAsync(payload);
      setCompletedSale(sale);
      clearCart();
      setCheckoutIdempotencyKey("");
      setNotice(`Savdo ${sale.receipt_number} yakunlandi`);
    } catch (error) {
      setNotice(formatError(error));
    }
  }

  async function handlePaymentSubmit(payments: CheckoutPayment[]) {
    const latestConnectivity =
      connectivity.status === "online" && !connectivity.isStale
        ? connectivity
        : await connectivity.refresh({
            force:
              connectivity.status === "unknown" ||
              connectivity.status === "checking" ||
              connectivity.isStale,
          });

    if (latestConnectivity.status === "online") {
      await handleCompleteSale(payments);
      return;
    }

    if (
      latestConnectivity.status === "browser_offline" ||
      latestConnectivity.status === "backend_unreachable"
    ) {
      setNotice(
        latestConnectivity.status === "browser_offline"
          ? "Internet aloqasi yo'q. Bu savdo offline saqlanmoqda."
          : "Server mavjud emas. Savdo offline saqlanmoqda.",
      );
      await handleOfflineSale(payments);
      return;
    }

    setNotice("Backend holati tekshirilmoqda. Birozdan keyin qayta urinib ko'ring.");
  }

  const checkoutVariant = connectivity.status === "online" ? "online" : "offline";
  const connectivityBlockReason =
    connectivity.status === "unknown" || connectivity.status === "checking"
      ? "Checkoutdan oldin backend holati tekshirilmoqda"
      : undefined;

  const offlineSyncBusy = offlineSummary.syncing > 0 || lockState.locked;
  const checkoutDisabledReason =
    missingSessionReason
      ? missingSessionReason
      : items.length === 0
      ? "Checkoutdan oldin mahsulot qo'shing"
      : offlineSyncBusy
        ? "Offline navbat sinxronlash jarayonida"
        : connectivityBlockReason
          ? connectivityBlockReason
          : undefined;

  return (
    <PosShell>
      <div className="grid h-[calc(100vh-3.5rem)] grid-cols-1 overflow-hidden lg:grid-cols-[32%_1fr_360px]">
        <div className="no-print flex min-h-0 flex-col border-r border-white/20">
          <div className="glass grid gap-2 border-b border-white/20 p-3">
            <BarcodeInput busy={scanLoading} onScan={handleScan} />
            <OfflineSyncStatus />
          </div>
          <ProductSearch onSelectProduct={addToCart} />
        </div>

        <div className="flex min-h-0 flex-col border-r border-white/20">
          {notice ? (
            <div className="no-print flex min-h-11 items-center gap-2 border-b border-amber-200/40 bg-amber-50/60 px-4 text-sm font-bold text-amber-800 backdrop-blur-sm">
              <AlertTriangle aria-hidden="true" className="h-4 w-4" />
              <span className="truncate">{notice}</span>
            </div>
          ) : null}
          <CartTable
            items={items}
            onQuantityChange={(productId, quantity) => {
              setQuantity(productId, quantity);
              setCheckoutIdempotencyKey("");
            }}
            onRemove={(productId) => {
              removeItem(productId);
              setCheckoutIdempotencyKey("");
            }}
          />
          <CartSummary
            subtotal={subtotal}
            total={total}
            itemCount={itemCount}
            onClear={() => {
              clearCart();
              setCompletedSale(null);
              setCheckoutIdempotencyKey("");
              setNotice("");
            }}
          />
        </div>

        <aside className="flex min-h-0 flex-col">
          <CashierSessionPanel />
          <CustomerPicker
            selectedCustomer={selectedCustomer}
            onSelectCustomer={(customer) => {
              setSelectedCustomer(customer);
              setCheckoutIdempotencyKey("");
            }}
          />
          <PaymentPanel
            total={total}
            disabled={Boolean(checkoutDisabledReason)}
            disabledReason={checkoutDisabledReason}
            loading={completeSale.isPending || offlineSavePending}
            variant={checkoutVariant}
            onComplete={handlePaymentSubmit}
          />
          <ReceiptPreview
            sale={completedSale}
            onNewSale={() => {
              setCompletedSale(null);
              setCheckoutIdempotencyKey("");
              setNotice("");
            }}
          />
        </aside>
      </div>
    </PosShell>
  );
}

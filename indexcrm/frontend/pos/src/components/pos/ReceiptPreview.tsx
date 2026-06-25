"use client";

import {
  Loader2,
  Printer,
  ReceiptText,
  RotateCw,
  ShoppingCart,
} from "lucide-react";

import { useReceipt } from "@/hooks/useSales";
import { formatMoney } from "@/lib/format";
import { Sale } from "@/services/api/types";

import { IconButton } from "./IconButton";

type ReceiptPreviewProps = {
  sale: Sale | null;
  onNewSale?: () => void;
};

function pickText(source: unknown, keys: string[], fallback = "-") {
  if (source && typeof source === "object") {
    const record = source as Record<string, unknown>;
    for (const key of keys) {
      const value = record[key];
      if (value !== undefined && value !== null && String(value) !== "") {
        return String(value);
      }
    }
  }
  return fallback;
}

function formatDate(value?: string) {
  if (!value) {
    return "-";
  }
  return new Date(value).toLocaleString();
}

export function ReceiptPreview({ sale, onNewSale }: ReceiptPreviewProps) {
  const receiptQuery = useReceipt(sale?.id);
  const receipt = receiptQuery.data;
  const receiptItems = receipt?.items ?? sale?.items ?? [];
  const receiptPayments = receipt?.payments ?? sale?.payments ?? [];
  const totals = receipt?.totals ?? {};
  const branchName =
    pickText(receipt?.branch, ["store_name", "name"], "") ||
    sale?.branch_name ||
    "Index";
  const cashierName =
    pickText(receipt?.cashier, ["full_name", "email"], "") ||
    sale?.cashier_email ||
    "-";
  const customerName =
    pickText(receipt?.customer, ["full_name", "name"], "") ||
    sale?.customer_name ||
    "";
  const sessionLabel = pickText(
    receipt,
    ["shift_number", "shift_id", "session_id"],
    "",
  );
  const receiptNumber = receipt?.receipt_number ?? sale?.receipt_number ?? "-";
  const saleDate = receipt?.sale_date ?? sale?.sale_date;
  const subtotal = pickText(totals, ["subtotal"], sale?.subtotal ?? "0");
  const discount = pickText(
    totals,
    ["discount_amount"],
    sale?.discount_amount ?? "0",
  );
  const tax = pickText(totals, ["tax_amount"], sale?.tax_amount ?? "0");
  const total = pickText(totals, ["total_amount"], sale?.total_amount ?? "0");
  const paid = pickText(totals, ["paid_amount"], sale?.paid_amount ?? "0");
  const remaining = pickText(
    totals,
    ["remaining_amount"],
    sale?.remaining_amount ?? "0",
  );
  const canPrint = Boolean(sale) && !receiptQuery.isLoading;

  return (
    <section className="print-panel flex min-h-0 flex-1 flex-col bg-slate-50 p-3">
      <div className="no-print mb-2 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-slate-500">
          <ReceiptText aria-hidden="true" className="h-4 w-4" />
          Chek
        </div>
        <div className="flex gap-2">
          <IconButton
            icon={<ShoppingCart aria-hidden="true" className="h-4 w-4" />}
            label="Yangi savdo"
            onClick={onNewSale}
            disabled={!sale}
            className="min-h-9 px-2 py-1 text-xs"
          />
          <IconButton
            icon={<Printer aria-hidden="true" className="h-4 w-4" />}
            label="Chop etish"
            onClick={() => window.print()}
            disabled={!canPrint}
            className="min-h-9 px-2 py-1 text-xs"
          />
        </div>
      </div>
      <div className="receipt-paper min-h-0 flex-1 overflow-y-auto rounded-xl border border-slate-200 bg-white p-4 font-mono text-[13px] leading-tight shadow-sm">
        {!sale ? (
          <div className="flex h-full items-center justify-center text-center font-sans text-sm font-semibold text-slate-400">
            Chekni ko'rish uchun savdoni yakunlang.
          </div>
        ) : receiptQuery.isLoading ? (
          <div className="flex h-full items-center justify-center gap-2 text-center font-sans text-sm font-bold text-slate-500">
            <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin text-primary-500" />
            Chek yuklanmoqda
          </div>
        ) : (
          <>
            {receiptQuery.isError ? (
              <div className="no-print mb-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 font-sans text-xs font-bold text-amber-800">
                Chek ma'lumotlarini yangilab bo'lmadi. Savdo ma'lumotlari ko'rsatilmoqda.
                <button
                  type="button"
                  onClick={() => void receiptQuery.refetch()}
                  className="ml-2 inline-flex items-center gap-1 font-black text-amber-950 underline"
                >
                  <RotateCw aria-hidden="true" className="h-3 w-3" />
                  Qayta urinish
                </button>
              </div>
            ) : null}
            <div className="text-center">
              <div className="text-[15px] font-black uppercase tracking-tight">{branchName}</div>
              <div className="text-slate-500">{pickText(receipt?.branch, ["address"], "")}</div>
              <div className="text-slate-500">{pickText(receipt?.branch, ["phone"], "")}</div>
              <div className="mt-2 font-black">Chek #{receiptNumber}</div>
              <div className="text-slate-500">Sana: {formatDate(saleDate)}</div>
              <div className="text-slate-500">Kassir: {cashierName}</div>
              {sessionLabel ? <div className="text-slate-500">Sessiya: {sessionLabel}</div> : null}
              {customerName ? <div className="text-slate-500">Mijoz: {customerName}</div> : null}
            </div>

            <div className="my-3 border-t border-dashed border-slate-300" />
            {receiptItems.map((item, index) => {
              const row = item as Record<string, unknown>;
              const name = pickText(row, ["product_name", "name"], "Mahsulot");
              const sku = pickText(row, ["sku", "product_sku", "barcode"], "");
              const quantity = pickText(row, ["quantity"], "0");
              const price = pickText(row, ["price"], "0");
              const lineDiscount = pickText(row, ["discount"], "0");
              const lineTotal = pickText(row, ["total_price", "total"], "0");
              return (
                <div key={String(row.id ?? row.product_id ?? index)} className="mb-2">
                  <div className="font-bold text-slate-800">{name}</div>
                  {sku ? <div className="text-[11px] uppercase text-slate-400">SKU: {sku}</div> : null}
                  <div className="flex justify-between gap-3 text-slate-600">
                    <span>
                      {quantity} x {formatMoney(price)}
                    </span>
                    <span>{formatMoney(lineTotal)}</span>
                  </div>
                  {Number(lineDiscount) > 0 ? (
                    <div className="flex justify-between gap-3 text-xs text-rose-500">
                      <span>Chegirma</span>
                      <span>-{formatMoney(lineDiscount)}</span>
                    </div>
                  ) : null}
                </div>
              );
            })}

            <div className="my-3 border-t border-dashed border-slate-300" />
            <div className="flex justify-between text-slate-600">
              <span>Oraliq jami</span>
              <span>{formatMoney(subtotal)}</span>
            </div>
            {Number(discount) > 0 ? (
              <div className="flex justify-between text-rose-600">
                <span>Chegirma</span>
                <span>-{formatMoney(discount)}</span>
              </div>
            ) : null}
            {Number(tax) > 0 ? (
              <div className="flex justify-between text-slate-600">
                <span>Soliq</span>
                <span>{formatMoney(tax)}</span>
              </div>
            ) : null}
            <div className="mt-1 flex justify-between text-base font-black text-slate-900">
              <span>Yakuniy jami</span>
              <span>{formatMoney(total)}</span>
            </div>
            <div className="flex justify-between text-emerald-700">
              <span>To'langan summa</span>
              <span>{formatMoney(paid)}</span>
            </div>
            {Number(remaining) > 0 ? (
              <div className="flex justify-between text-rose-600">
                <span>Qarz</span>
                <span>{formatMoney(remaining)}</span>
              </div>
            ) : null}

            <div className="my-3 border-t border-dashed border-slate-300" />
            {receiptPayments.length > 0 ? (
              receiptPayments.map((payment, index) => {
                const row = payment as Record<string, unknown>;
                return (
                  <div
                    key={String(row.id ?? `${row.payment_method}-${index}`)}
                    className="flex justify-between text-slate-600"
                  >
                    <span>{pickText(row, ["payment_method"], "TO'LOV")}</span>
                    <span>{formatMoney(pickText(row, ["amount"], "0"))}</span>
                  </div>
                );
              })
            ) : (
              <div className="flex justify-between text-slate-600">
                <span>To'lov</span>
                <span>{formatMoney(sale.paid_amount)}</span>
              </div>
            )}

            <div className="mt-3 text-center text-xs uppercase tracking-wider text-slate-400">
              Xaridingiz uchun rahmat
            </div>
          </>
        )}
      </div>
    </section>
  );
}

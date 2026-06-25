"use client";

import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  Clipboard,
  Copy,
  Loader2,
  RotateCw,
  Trash2,
} from "lucide-react";
import { useMemo, useState } from "react";

import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { StatCard } from "@/components/dashboard/StatCard";
import { useOfflineSalesQueue } from "@/hooks/useOfflineSalesQueue";
import { usePosConnectivity } from "@/hooks/usePosConnectivity";
import { formatMoney } from "@/lib/format";
import { getStoredAuthToken } from "@/services/api/client";
import type {
  OfflineFailureClass,
  OfflineSaleStatus,
  OfflineSyncAuditEvent,
  PendingSaleRecord,
} from "@/services/offlineSalesQueue";
import { getOfflineFailureGuidance } from "@/services/offlineSalesQueue";

type QueueFilter = "all" | OfflineSaleStatus;
type QueueSort = "newest" | "oldest" | "failed";

const filters: Array<{ label: string; value: QueueFilter }> = [
  { label: "Hammasi", value: "all" },
  { label: "Lokal", value: "pending" },
  { label: "Xato", value: "failed" },
  { label: "Yuborilgan", value: "synced" },
  { label: "Yuborilmoqda", value: "syncing" },
];

const sortOptions: Array<{ label: string; value: QueueSort }> = [
  { label: "Avval yangilari", value: "newest" },
  { label: "Avval eskilari", value: "oldest" },
  { label: "Avval xatolar", value: "failed" },
];

const statusLabels: Record<OfflineSaleStatus, string> = {
  pending: "Lokal kutilmoqda",
  failed: "Xato",
  syncing: "Sinxronlanmoqda",
  synced: "Sinxronlangan",
};

const statusDescriptions: Record<OfflineSaleStatus, string> = {
  pending: "Ushbu qurilmada saqlangan, hali backendga yuborilmagan.",
  failed: "Oxirgi qayta urinish xato bo'ldi. Qayta urinishdan oldin xatoni ko'rib chiqing.",
  syncing: "Backendga yuborilmoqda. Boshqa oynadan qayta urinmang.",
  synced: "Backend bu savdoni qabul qildi. Lokal yozuv tarix sifatida saqlangan.",
};

function formatDateTime(value?: string) {
  if (!value) {
    return "-";
  }
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function shorten(value: string, visible = 10) {
  if (!value || value.length <= visible * 2) {
    return value || "-";
  }
  return `${value.slice(0, visible)}...${value.slice(-visible)}`;
}

function statusClassName(status: OfflineSaleStatus) {
  if (status === "synced") {
    return "border-emerald-200 bg-emerald-50 text-emerald-800";
  }
  if (status === "failed") {
    return "border-rose-200 bg-rose-50 text-rose-800";
  }
  if (status === "syncing") {
    return "border-blue-200 bg-blue-50 text-blue-800";
  }
  return "border-amber-200 bg-amber-50 text-amber-900";
}

function failureClassLabel(sale: PendingSaleRecord) {
  const failureClass =
    sale.failureClass ?? (sale.status === "failed" ? "unknown" : undefined);
  return failureClass ? getOfflineFailureGuidance(failureClass).label : "-";
}

function failureClassName(sale: PendingSaleRecord) {
  const failureClass =
    sale.failureClass ?? (sale.status === "failed" ? "unknown" : undefined);
  if (!failureClass) {
    return "border-slate-200 bg-slate-50 text-slate-500";
  }
  if (
    failureClass === "stock_conflict" ||
    failureClass === "shift_closed_missing" ||
    failureClass === "idempotency_conflict"
  ) {
    return "border-amber-200 bg-amber-50 text-amber-900";
  }
  if (
    failureClass === "product_missing" ||
    failureClass === "permission_store_scope"
  ) {
    return "border-rose-200 bg-rose-50 text-rose-800";
  }
  if (failureClass === "backend_unavailable") {
    return "border-blue-200 bg-blue-50 text-blue-800";
  }
  return "border-slate-200 bg-slate-50 text-slate-700";
}

function paymentSummary(sale: PendingSaleRecord) {
  if (sale.payments.length === 0) {
    return "-";
  }
  return sale.payments
    .map(
      (payment) =>
        `${payment.payment_method} ${formatMoney(payment.amount)}`,
    )
    .join(", ");
}

function saleFailureGuidance(sale: PendingSaleRecord) {
  const failureClass =
    sale.failureClass ?? sale.failureCategory ?? (sale.status === "failed" ? "unknown" : undefined);
  return failureClass ? getOfflineFailureGuidance(failureClass) : null;
}

function nextStepForSale(sale: PendingSaleRecord) {
  const guidance = saleFailureGuidance(sale);
  if (guidance) {
    return guidance.nextStep;
  }
  if (sale.status === "pending") {
    return "Backend ishlaganda bu savdoni yuboring.";
  }
  if (sale.status === "syncing") {
    return "Joriy sinxronlash tugashini kuting yoki eskirib qolsa tiklang.";
  }
  return "Bu qurilmadan yuborilgan tarixni tozalashni xohlamasangiz, amal kerak emas.";
}

function sortSales(sales: PendingSaleRecord[], sort: QueueSort) {
  return sales.slice().sort((first, second) => {
    if (sort === "failed") {
      const firstFailed = first.status === "failed" ? 0 : 1;
      const secondFailed = second.status === "failed" ? 0 : 1;
      if (firstFailed !== secondFailed) {
        return firstFailed - secondFailed;
      }
    }

    const firstTime = new Date(first.createdAt).getTime();
    const secondTime = new Date(second.createdAt).getTime();
    return sort === "oldest" ? firstTime - secondTime : secondTime - firstTime;
  });
}

function syncEventLabel(event: OfflineSyncAuditEvent) {
  if (event.type === "sync_started") {
    return "Sinxronlash boshlandi";
  }
  if (event.type === "sync_completed") {
    return "Sinxronlash tugadi";
  }
  if (event.type === "sync_skipped") {
    return "Sinxronlash o'tkazib yuborildi";
  }
  if (event.type === "sale_syncing") {
    return "Qayta urinish boshlandi";
  }
  if (event.type === "sale_synced") {
    return "Savdo sinxronlandi";
  }
  if (event.type === "sale_failed") {
    return "Savdo xato bo'ldi";
  }
  if (event.type === "stale_recovered") {
    return "Eskirgan yozuv tiklandi";
  }
  if (event.type === "lock_recovered") {
    return "Lock tiklandi";
  }
  return "Lock yo'qoldi";
}

function syncEventMeta(event: OfflineSyncAuditEvent) {
  const transition =
    event.fromStatus && event.toStatus
      ? `${event.fromStatus} -> ${event.toStatus}`
      : "";
  return [event.localReference, transition, event.errorCode]
    .filter(Boolean)
    .join(" | ");
}

export function OfflineQueueDashboardPage() {
  const connectivity = usePosConnectivity();
  const {
    clearSynced,
    isSyncing,
    lastResult,
    lockState,
    parseError,
    queue,
    recoverInterrupted,
    refresh,
    storageFallbackReason,
    storageInitialized,
    storageMode,
    migrationMessage,
    migrationStatus,
    summary,
    sync,
    syncEvents,
  } = useOfflineSalesQueue();
  const [filter, setFilter] = useState<QueueFilter>("all");
  const [sort, setSort] = useState<QueueSort>("newest");
  const [selectedId, setSelectedId] = useState("");
  const [actionNotice, setActionNotice] = useState("");

  const totals = useMemo(
    () =>
      queue.reduce(
        (values, sale) => ({
          queuedAmount: values.queuedAmount + sale.totals.total,
          failedAmount:
            values.failedAmount +
            (sale.status === "failed" ? sale.totals.total : 0),
        }),
        { queuedAmount: 0, failedAmount: 0 },
      ),
    [queue],
  );

  const visibleQueue = useMemo(() => {
    const filtered =
      filter === "all"
        ? queue
        : queue.filter((sale) => sale.status === filter);
    return sortSales(filtered, sort);
  }, [filter, queue, sort]);

  const selectedSale =
    queue.find((sale) => sale.id === selectedId) ?? visibleQueue[0] ?? null;
  const selectedCanRetry =
    selectedSale?.status === "pending" || selectedSale?.status === "failed";
  const hasAuthToken = Boolean(getStoredAuthToken());
  const syncBlockReason =
    connectivity.status === "browser_offline"
      ? "Brauzer offline. Navbatdagi savdolarni qayta yuborishdan oldin tarmoqqa ulang."
      : connectivity.status === "checking"
        ? "Qayta urinishdan oldin backend mavjudligi tekshirilmoqda."
        : connectivity.status === "unknown"
          ? "Aloqa holati noma'lum. Backend tekshiruvini kuting."
          : connectivity.status === "backend_unreachable"
            ? connectivity.message || "Backend API bilan aloqa yo'q."
        : !hasAuthToken
          ? "Lokal savdolarni yuborishdan oldin tizimga kiring."
        : isSyncing || summary.syncing > 0
          ? "Navbatdagi savdo sinxronlash allaqachon ishlayapti."
          : lockState.lockedByAnotherTab
            ? "Boshqa POS oynasi navbatdagi savdolarni sinxronlayapti."
            : "";
  const syncDisabled = Boolean(syncBlockReason);
  const retryAllDisabled = syncDisabled || summary.pending + summary.failed === 0;
  const retrySelectedDisabled = syncDisabled || !selectedCanRetry;
  const retryAllBlockReason =
    syncBlockReason ||
    (summary.pending + summary.failed === 0
      ? "Yuboriladigan lokal yoki xato savdolar yo'q."
      : "");
  const retrySelectedBlockReason =
    syncBlockReason ||
    (!selectedCanRetry
      ? "Faqat lokal yoki xato savdolarni yuborish mumkin."
      : "");
  const recoverDisabled =
    summary.staleSyncing === 0 || isSyncing || lockState.locked;
  const selectedGuidance = selectedSale ? saleFailureGuidance(selectedSale) : null;

  async function retryWithFreshHealth(saleIds?: string[]) {
    if (syncBlockReason && connectivity.status !== "online") {
      setActionNotice(syncBlockReason);
      return;
    }

    const health = await connectivity.refresh({ force: true });
    if (health.status !== "online") {
      setActionNotice(health.message);
      return;
    }

    const result = await sync({
      isOnline: true,
      backendReachable: true,
      saleIds,
    });
    if (result) {
      setActionNotice(result.reason);
    }
  }

  async function handleRetryAll() {
    setActionNotice("");
    if (retryAllDisabled) {
      setActionNotice(retryAllBlockReason);
      return;
    }
    await retryWithFreshHealth();
  }

  async function handleRetrySelected() {
    if (!selectedSale) {
      return;
    }
    setActionNotice("");
    if (retrySelectedDisabled) {
      setActionNotice(retrySelectedBlockReason);
      return;
    }
    await retryWithFreshHealth([selectedSale.id]);
  }

  async function handleRecover() {
    if (recoverDisabled) {
      setActionNotice(
        summary.staleSyncing === 0
          ? "No stale syncing sales are old enough to recover."
          : "Boshqa sinxronlash faol bo'lganda tiklash bloklangan.",
      );
      return;
    }

    const recovered = await recoverInterrupted();
    setActionNotice(
      recovered > 0
        ? `${recovered} uzilgan savdo tiklandi. Endi ular ko'rib chiqish va qo'lda qayta urinish uchun xato yozuvlar.`
        : "Eskirgan sinxronlashdagi savdo tiklanmadi.",
    );
  }

  async function handleClearSynced() {
    if (
      !window.confirm(
        "Sinxronlangan offline yozuvlarni ushbu qurilmadan tozalaysizmi? Kutilayotgan, xato va yuborilayotgan yozuvlar saqlanadi.",
      )
    ) {
      return;
    }
    const removed = await clearSynced();
    setActionNotice(`${removed} yuborilgan yozuv tozalandi.`);
  }

  async function handleCopy(value: string, label: string) {
    try {
      await navigator.clipboard.writeText(value);
      setActionNotice(`${label} nusxalandi.`);
    } catch {
      setActionNotice(`${label}ni bu brauzer nusxalay olmadi.`);
    }
  }

  if (parseError) {
    return (
      <ErrorState
        title="Offline navbatni o'qib bo'lmadi"
        description="Lokal offline navbat ma'lumoti yaroqli JSON emas. Hech bir navbatdagi savdo o'chirilmadi. Navbatni o'zgartirishdan oldin brauzer xotirasini tekshiring."
        onRetry={refresh}
      />
    );
  }

  return (
    <div className="grid gap-5">
      <SectionHeader
        title="Offline navbat"
        description="Lokal saqlangan POS savdolarni ko'ring, qo'lda sinxronlang va xato yozuvlarni tekshiring."
        actions={
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={retryAllDisabled}
              title={retryAllDisabled ? retryAllBlockReason : "Barcha lokal va xato savdolarni yuborish"}
              onClick={() => void handleRetryAll()}
              className="inline-flex min-h-10 items-center gap-2 rounded border border-blue-200 bg-blue-50 px-3 text-sm font-black text-blue-700 hover:bg-blue-100 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isSyncing ? (
                <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" />
              ) : (
                <RotateCw aria-hidden="true" className="h-4 w-4" />
              )}
              Hammasini yuborish
            </button>
            <button
              type="button"
              disabled={recoverDisabled}
              onClick={() => void handleRecover()}
              title={
                recoverDisabled
                  ? summary.staleSyncing === 0
                    ? "Tiklanadigan eskirgan sinxronlash yo'q"
                    : "Sinxronlash faol bo'lganda tiklash bloklangan"
                  : "Eskirgan sinxronlashlarni tiklash"
              }
              className="inline-flex min-h-10 items-center gap-2 rounded border border-slate-300 bg-white px-3 text-sm font-black text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Clock3 aria-hidden="true" className="h-4 w-4" />
              Tiklash {summary.staleSyncing > 0 ? `(${summary.staleSyncing})` : ""}
            </button>
            <button
              type="button"
              disabled={summary.synced === 0}
              onClick={() => void handleClearSynced()}
              className="inline-flex min-h-10 items-center gap-2 rounded border border-slate-300 bg-white px-3 text-sm font-black text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Trash2 aria-hidden="true" className="h-4 w-4" />
              Yuborilganlarni tozalash
            </button>
          </div>
        }
      />

      <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-7">
        <StatCard
          title="Jami navbat"
          value={String(summary.total)}
          icon={Clipboard}
          tone="slate"
        />
        <StatCard
          title="Lokal"
          value={String(summary.pending)}
          icon={Clock3}
          tone="amber"
        />
        <StatCard
          title="Xato"
          value={String(summary.failed)}
          icon={AlertTriangle}
          tone="rose"
        />
        <StatCard
          title="Yuborilgan"
          value={String(summary.synced)}
          icon={CheckCircle2}
          tone="green"
        />
        <StatCard
          title="Yuborilmoqda"
          value={String(summary.syncing)}
          icon={Loader2}
          tone="blue"
        />
        <StatCard
          title="Navbat summasi"
          value={formatMoney(totals.queuedAmount)}
          icon={Clipboard}
          tone="blue"
        />
        <StatCard
          title="Xato summasi"
          value={formatMoney(totals.failedAmount)}
          icon={AlertTriangle}
          tone="rose"
        />
      </div>

      {lockState.lockedByAnotherTab ? (
        <div className="rounded border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-bold text-amber-900">
          Boshqa POS oynasi navbatdagi savdolarni sinxronlayapti. Bu yerda qayta urinishlar bloklangan.
        </div>
      ) : null}
      {storageInitialized && storageMode === "localStorage" ? (
        <div className="rounded border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-bold text-amber-900">
          IndexedDB mavjud emas, shuning uchun bu POS offline navbat uchun
          localStorage zaxirasidan foydalanmoqda. {storageFallbackReason}
        </div>
      ) : null}
      {storageInitialized &&
      storageMode === "indexeddb" &&
      migrationStatus === "blocked" ? (
        <div className="rounded border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-bold text-amber-900">
          {migrationMessage}
        </div>
      ) : null}
      {retryAllBlockReason ? (
        <div className="rounded border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-bold text-amber-900">
          {retryAllBlockReason}
        </div>
      ) : null}
      {actionNotice || lastResult ? (
        <div className="rounded border border-slate-200 bg-white px-4 py-3 text-sm font-bold text-slate-700 shadow-panel">
          {actionNotice ||
            (lastResult
              ? `Oxirgi sinxronlash ${formatDateTime(lastResult.completedAt)}: ${lastResult.reason}`
              : "")}
        </div>
      ) : null}

      {syncEvents.length > 0 ? (
        <section className="rounded border border-slate-200 bg-white shadow-panel">
          <div className="border-b border-slate-200 px-4 py-3">
            <h2 className="text-base font-black text-slate-950">
              So'nggi sinxronlash faolligi
            </h2>
            <p className="text-sm font-semibold text-slate-500">
              Qo'lda qayta urinish va tiklash hodisalari uchun lokal audit tarixi.
            </p>
          </div>
          <div className="divide-y divide-slate-100">
            {syncEvents.slice(0, 8).map((event) => (
              <div
                key={event.id}
                className="grid gap-1 px-4 py-3 text-sm md:grid-cols-[180px_1fr]"
              >
                <div className="font-black text-slate-800">
                  {syncEventLabel(event)}
                </div>
                <div className="grid gap-1">
                  <div className="font-semibold text-slate-700">
                    {event.message}
                  </div>
                  <div className="text-xs font-semibold text-slate-500">
                    {formatDateTime(event.timestamp)}
                    {syncEventMeta(event) ? ` | ${syncEventMeta(event)}` : ""}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      <section className="rounded border border-slate-200 bg-white shadow-panel">
        <div className="flex flex-col gap-3 border-b border-slate-200 px-4 py-3 md:flex-row md:items-center md:justify-between">
          <div className="flex flex-wrap gap-2">
            {filters.map((item) => (
              <button
                key={item.value}
                type="button"
                onClick={() => setFilter(item.value)}
                className={`min-h-9 rounded border px-3 text-xs font-black uppercase ${
                  filter === item.value
                    ? "border-blue-600 bg-blue-50 text-blue-700"
                    : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
          <select
            value={sort}
            onChange={(event) => setSort(event.target.value as QueueSort)}
            className="h-10 rounded border border-slate-300 bg-white px-3 text-sm font-black text-slate-700"
          >
            {sortOptions.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </div>

        {visibleQueue.length === 0 ? (
          <EmptyState
            title="Navbatdagi savdolar yo'q"
            description="Ushbu qurilmada saqlangan offline savdolar shu yerda chiqadi."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
                  <th className="px-4 py-3 text-left font-black">Havola</th>
                  <th className="px-4 py-3 text-left font-black">Holat</th>
                  <th className="px-4 py-3 text-left font-black">Yaratildi</th>
                  <th className="px-4 py-3 text-left font-black">Turi</th>
                  <th className="px-4 py-3 text-left font-black">Keyingi qadam</th>
                  <th className="px-4 py-3 text-left font-black">To'lov</th>
                  <th className="px-4 py-3 text-right font-black">Jami</th>
                  <th className="px-4 py-3 text-left font-black">Urinishlar</th>
                  <th className="px-4 py-3 text-left font-black">Server</th>
                </tr>
              </thead>
              <tbody>
                {visibleQueue.map((sale) => (
                  <tr
                    key={sale.id}
                    onClick={() => setSelectedId(sale.id)}
                    className={`cursor-pointer border-b border-slate-100 last:border-0 hover:bg-slate-50 ${
                      selectedSale?.id === sale.id ? "bg-blue-50/70" : ""
                    }`}
                  >
                    <td className="px-4 py-3 font-black text-slate-800">
                      <div>{sale.receiptFallback.receiptNumber}</div>
                      <div className="text-xs font-semibold text-slate-500">
                        {shorten(sale.idempotencyKey, 8)}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex rounded border px-2 py-1 text-xs font-black uppercase ${statusClassName(
                          sale.status,
                        )}`}
                      >
                        {statusLabels[sale.status]}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-semibold text-slate-700">
                      {formatDateTime(sale.createdAt)}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex rounded border px-2 py-1 text-xs font-black ${failureClassName(
                          sale,
                        )}`}
                      >
                        {failureClassLabel(sale)}
                      </span>
                    </td>
                    <td className="max-w-72 px-4 py-3 text-xs font-bold text-slate-600">
                      <span className="line-clamp-2">{nextStepForSale(sale)}</span>
                    </td>
                    <td className="max-w-60 px-4 py-3 font-semibold text-slate-700">
                      <span className="line-clamp-2">{paymentSummary(sale)}</span>
                    </td>
                    <td className="px-4 py-3 text-right font-black text-slate-800">
                      {formatMoney(sale.totals.total)}
                    </td>
                    <td className="px-4 py-3 font-semibold text-slate-700">
                      {sale.retryCount}
                      {sale.lastAttemptAt ? (
                        <div className="text-xs text-slate-500">
                          Oxirgi urinish: {formatDateTime(sale.lastAttemptAt)}
                        </div>
                      ) : null}
                      {sale.lastError ? (
                        <div className="max-w-72 truncate text-xs text-rose-700">
                          {sale.lastErrorCode ? `${sale.lastErrorCode}: ` : ""}
                          {sale.lastError}
                        </div>
                      ) : null}
                    </td>
                    <td className="px-4 py-3 font-semibold text-slate-700">
                      {sale.serverReceiptNumber ?? sale.serverSaleId ?? "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {selectedSale ? (
        <section className="rounded border border-slate-200 bg-white shadow-panel">
          <div className="flex flex-col gap-3 border-b border-slate-200 px-4 py-3 md:flex-row md:items-center md:justify-between">
            <div>
              <h2 className="text-base font-black text-slate-950">
                Savdo tafsiloti
              </h2>
              <p className="text-sm font-semibold text-slate-500">
                Lokal savdoni tiklash uchun faqat ko'rish payload nusxasi.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                disabled={retrySelectedDisabled}
                title={
                  retrySelectedDisabled
                    ? retrySelectedBlockReason
                    : "Tanlangan lokal savdoni yuborish"
                }
                onClick={() => void handleRetrySelected()}
                className="inline-flex min-h-10 items-center gap-2 rounded border border-blue-200 bg-blue-50 px-3 text-sm font-black text-blue-700 hover:bg-blue-100 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <RotateCw aria-hidden="true" className="h-4 w-4" />
                Tanlanganni yuborish
              </button>
              <button
                type="button"
                onClick={() =>
                  void handleCopy(
                    selectedSale.receiptFallback.receiptNumber,
                    "Lokal havola",
                  )
                }
                className="inline-flex min-h-10 items-center gap-2 rounded border border-slate-300 bg-white px-3 text-sm font-black text-slate-700 hover:bg-slate-50"
              >
                <Copy aria-hidden="true" className="h-4 w-4" />
                Havolani nusxalash
              </button>
              <button
                type="button"
                onClick={() =>
                  void handleCopy(selectedSale.idempotencyKey, "Idempotency kaliti")
                }
                className="inline-flex min-h-10 items-center gap-2 rounded border border-slate-300 bg-white px-3 text-sm font-black text-slate-700 hover:bg-slate-50"
              >
                <Copy aria-hidden="true" className="h-4 w-4" />
                Kalitni nusxalash
              </button>
            </div>
          </div>

          <div className="grid gap-4 p-4 lg:grid-cols-[1fr_1fr]">
            {selectedGuidance ? (
              <div className="rounded border border-amber-200 bg-amber-50 p-4 lg:col-span-2">
                <div className="text-sm font-black text-amber-950">
                  {selectedGuidance.label}
                </div>
                <p className="mt-1 text-sm font-semibold text-amber-900">
                  {selectedGuidance.detail}
                </p>
                <p className="mt-2 text-sm font-black text-amber-950">
                  Keyingi qadam: {selectedGuidance.nextStep}
                </p>
              </div>
            ) : null}
            <div className="grid gap-3 rounded border border-slate-200 bg-slate-50 p-4">
              <DetailRow
                label="Lokal havola"
                value={selectedSale.receiptFallback.receiptNumber}
              />
              <DetailRow
                label="Idempotency kaliti"
                value={selectedSale.idempotencyKey}
              />
              <DetailRow label="Holat" value={statusLabels[selectedSale.status]} />
              <DetailRow
                label="Holat izohi"
                value={statusDescriptions[selectedSale.status]}
              />
              <DetailRow
                label="Yaratildi"
                value={formatDateTime(selectedSale.createdAt)}
              />
              <DetailRow
                label="Oxirgi lokal yangilanish"
                value={formatDateTime(selectedSale.updatedAt)}
              />
              <DetailRow
                label="Sinxronlandi"
                value={formatDateTime(selectedSale.syncedAt)}
              />
              <DetailRow
                label="Qayta urinishlar"
                value={String(selectedSale.retryCount)}
              />
              <DetailRow
                label="Oxirgi urinish"
                value={formatDateTime(selectedSale.lastAttemptAt)}
              />
              <DetailRow
                label="Xato kodi"
                value={selectedSale.lastErrorCode || "-"}
              />
              <DetailRow
                label="Xato sababi"
                value={selectedSale.lastError || "-"}
              />
              <DetailRow
                label="Keyingi qadam"
                value={nextStepForSale(selectedSale)}
              />
              <DetailRow
                label="Tasnif"
                value={failureClassLabel(selectedSale)}
              />
              <DetailRow
                label="Server savdosi"
                value={selectedSale.serverSaleId ?? "-"}
              />
              <DetailRow
                label="Server cheki"
                value={selectedSale.serverReceiptNumber ?? "-"}
              />
            </div>

            <div className="grid gap-3 rounded border border-slate-200 bg-slate-50 p-4">
              <DetailRow label="Oraliq jami" value={formatMoney(selectedSale.totals.subtotal)} />
              <DetailRow label="Jami" value={formatMoney(selectedSale.totals.total)} />
              <DetailRow
                label="To'langan"
                value={formatMoney(selectedSale.totals.paidAmount)}
              />
              <DetailRow
                label="Mijoz"
                value={selectedSale.session.customerName ?? selectedSale.session.customerId ?? "Mijozsiz"}
              />
              <DetailRow label="Kassir" value={selectedSale.session.cashierName || "-"} />
              <DetailRow label="Kassir email" value={selectedSale.session.cashierEmail || "-"} />
              <DetailRow label="Filial" value={selectedSale.session.branchId || "-"} />
              <DetailRow label="Ombor" value={selectedSale.session.warehouseId || "-"} />
              <DetailRow label="Kassa" value={selectedSale.session.cashDeskId || "-"} />
              <DetailRow label="Smena" value={selectedSale.session.activeShiftId || "-"} />
            </div>
          </div>

          <div className="grid gap-4 border-t border-slate-200 p-4 lg:grid-cols-2">
            <section>
              <h3 className="mb-2 text-sm font-black uppercase text-slate-500">
                Mahsulotlar
              </h3>
              <div className="grid gap-2">
                {selectedSale.cartItems.map((item) => (
                  <div
                    key={`${selectedSale.id}-${item.productId}`}
                    className="rounded border border-slate-200 bg-slate-50 p-3"
                  >
                    <div className="font-black text-slate-800">
                      {item.productName || item.productId}
                    </div>
                    <div className="mt-1 grid gap-1 text-sm font-semibold text-slate-600 sm:grid-cols-4">
                      <span>Miqdor: {item.quantity}</span>
                      <span>Narx: {formatMoney(item.price)}</span>
                      <span>Chegirma: {formatMoney(item.discount)}</span>
                      <span>Jami: {formatMoney(item.lineTotal)}</span>
                    </div>
                    <div className="mt-1 text-xs font-semibold text-slate-500">
                      Mahsulot ID: {item.productId}
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <section>
              <h3 className="mb-2 text-sm font-black uppercase text-slate-500">
                To'lovlar
              </h3>
              <div className="grid gap-2">
                {selectedSale.payments.map((payment, index) => (
                  <div
                    key={`${selectedSale.id}-${payment.payment_method}-${index}`}
                    className="flex items-center justify-between rounded border border-slate-200 bg-slate-50 p-3 text-sm font-bold"
                  >
                    <span>{payment.payment_method}</span>
                    <span>{formatMoney(payment.amount)}</span>
                  </div>
                ))}
              </div>
            </section>
          </div>
        </section>
      ) : null}
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-1 sm:grid-cols-[150px_1fr]">
      <div className="text-xs font-black uppercase text-slate-500">{label}</div>
      <div className="break-words text-sm font-bold text-slate-800">{value}</div>
    </div>
  );
}

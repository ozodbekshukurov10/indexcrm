import { ApiError, getStoredAuthToken } from "@/services/api/client";
import { completeSale, createSale } from "@/services/api/sales";
import { Sale, SalePayload, SalePaymentMethod } from "@/services/api/types";
import {
  OFFLINE_SALES_QUEUE_EVENT,
  OFFLINE_SALES_QUEUE_KEY,
  OFFLINE_SALES_SYNC_LOCK_KEY,
  addQueuedSaleToStorage,
  clearSyncedSalesFromStorage,
  getInitialOfflineSalesQueueState,
  readOfflineSalesQueueStorageState,
  saveOfflineSalesQueueToStorage,
  updateQueuedSaleInStorage,
} from "@/services/offlineSalesQueueStorage";
import type { OfflineSalesStorageMeta } from "@/services/offlineSalesQueueStorage";

export {
  OFFLINE_SALES_QUEUE_EVENT,
  OFFLINE_SALES_QUEUE_KEY,
  OFFLINE_SALES_QUEUE_PING_KEY,
  OFFLINE_SALES_SYNC_LOCK_KEY,
} from "@/services/offlineSalesQueueStorage";

export type OfflineSaleStatus = "pending" | "syncing" | "synced" | "failed";
export type OfflineFailureClass =
  | "backend_unavailable"
  | "idempotency_conflict"
  | "validation_error"
  | "stock_conflict"
  | "product_missing"
  | "shift_closed_missing"
  | "permission_store_scope"
  | "unknown";

export type OfflineFailureGuidance = {
  label: string;
  nextStep: string;
  detail: string;
};

export const OFFLINE_FAILURE_GUIDANCE: Record<
  OfflineFailureClass,
  OfflineFailureGuidance
> = {
  backend_unavailable: {
    label: "Backend mavjud emas",
    nextStep: "Django yoki tarmoqni tiklang, keyin qo'lda sinxronlashni qayta urining.",
    detail: "Backend qabul qila olmagani uchun savdo ushbu qurilmada qoldi.",
  },
  idempotency_conflict: {
    label: "Idempotency ziddiyati",
    nextStep: "Qayta-qayta urinmang. Lokal havola/kalitni nusxalab, qayta yaratishdan oldin serverdagi savdo bilan solishtiring.",
    detail: "Server bu checkout kalitini boshqa savdo ma'lumotlari bilan oldin ko'rgan.",
  },
  validation_error: {
    label: "Validatsiya",
    nextStep: "Qayta urinishdan oldin filial, ombor, mijoz, to'lovlar, jami va savatni tekshiring.",
    detail: "Backend saqlangan checkout payloadining bir qismini rad etdi.",
  },
  stock_conflict: {
    label: "Qoldiq ziddiyati",
    nextStep: "Mahsulot qoldig'ini tekshiring, kerak bo'lsa omborni tuzating yoki joriy miqdor bilan yangi savdo yarating.",
    detail: "Bu lokal savdo sinxronlanishidan oldin qoldiq o'zgargan.",
  },
  product_missing: {
    label: "Mahsulot yo'q",
    nextStep: "Mahsulot/barcodeni tiklang yoki joriy katalog mahsuloti bilan savdoni qayta yarating.",
    detail: "Mahsulotlardan biri yoki bog'liq checkout yozuvi backendda endi mavjud emas.",
  },
  shift_closed_missing: {
    label: "Smena yo'q",
    nextStep: "Filial uchun yaroqli kassir smenasini oching yoki tanlang, keyin savdo shu smenaga tegishli bo'lsa qayta urining.",
    detail: "Server bu checkout uchun faol kassir smenasini topa olmadi.",
  },
  permission_store_scope: {
    label: "Huquq yoki filial doirasi",
    nextStep: "Bu filial/omborga kirish huquqi bor akkaunt bilan kiring yoki admindan huquqni tuzatishni so'rang.",
    detail: "Joriy akkaunt bu savdo kontekstini sinxronlay olmaydi.",
  },
  unknown: {
    label: "Noma'lum",
    nextStep: "Backend holatini tekshirib bir marta qayta urining. Yana xato bo'lsa yozuvni developer ko'rib chiqishi uchun saqlang.",
    detail: "POS xavfsiz tasniflay olmagan sabab tufayli savdo xato bo'ldi.",
  },
};

export function getOfflineFailureGuidance(
  failureClass?: OfflineFailureClass,
) {
  return OFFLINE_FAILURE_GUIDANCE[failureClass ?? "unknown"];
}

export type PendingSaleCartItem = {
  productId: string;
  productName: string;
  sku: string;
  barcode: string;
  quantity: number;
  price: number;
  discount: number;
  lineTotal: number;
};

export type PendingSalePayment = {
  payment_method: SalePaymentMethod;
  amount: number;
  note?: string;
};

export type PendingSaleSession = {
  branchId: string;
  warehouseId: string;
  cashDeskId?: string;
  activeShiftId: string;
  cashierName: string;
  cashierEmail: string;
  customerId: string | null;
  customerName: string | null;
};

export type PendingSaleTotals = {
  subtotal: number;
  total: number;
  paidAmount: number;
};

export type PendingSaleReceiptFallback = {
  receiptNumber: string;
  createdAt: string;
  storeName: string;
};

export type PendingSaleRecord = {
  id: string;
  idempotencyKey: string;
  status: OfflineSaleStatus;
  createdAt: string;
  updatedAt: string;
  lastAttemptAt?: string;
  syncedAt?: string;
  serverSaleId?: string;
  serverReceiptNumber?: string;
  retryCount: number;
  lastError: string;
  lastErrorMessage?: string;
  lastErrorCode?: string;
  failureClass?: OfflineFailureClass;
  failureCategory?: OfflineFailureClass;
  payload: SalePayload;
  cartItems: PendingSaleCartItem[];
  payments: PendingSalePayment[];
  session: PendingSaleSession;
  totals: PendingSaleTotals;
  receiptFallback: PendingSaleReceiptFallback;
};

export type OfflineSyncEventType =
  | "sync_started"
  | "sync_completed"
  | "sync_skipped"
  | "sale_syncing"
  | "sale_synced"
  | "sale_failed"
  | "stale_recovered"
  | "lock_recovered"
  | "lock_lost";

export type OfflineSyncAuditEvent = {
  id: string;
  type: OfflineSyncEventType;
  timestamp: string;
  saleId?: string;
  localReference?: string;
  fromStatus?: OfflineSaleStatus;
  toStatus?: OfflineSaleStatus;
  errorCode?: string;
  failureClass?: OfflineFailureClass;
  message: string;
};

export type OfflineSalesSummary = {
  total: number;
  pending: number;
  syncing: number;
  staleSyncing: number;
  synced: number;
  failed: number;
};

export type CreatePendingSaleRecordInput = {
  payload: SalePayload;
  cartItems: PendingSaleCartItem[];
  payments: PendingSalePayment[];
  session: PendingSaleSession;
  totals: PendingSaleTotals;
};

export type OfflineSyncResult = {
  attempted: number;
  synced: number;
  failed: number;
  skipped: boolean;
  reason: string;
  completedAt: string;
};

export type OfflineSyncOptions = {
  isOnline?: boolean;
  backendReachable?: boolean;
  saleIds?: string[];
};

export type OfflineSyncLockState = {
  locked: boolean;
  lockedByCurrentTab: boolean;
  lockedByAnotherTab: boolean;
  ownerId: string;
  expiresAt: string;
};

export type OfflineSalesQueueReadState = OfflineSalesStorageMeta & {
  queue: PendingSaleRecord[];
  parseError: boolean;
  rawValue: string;
};

const SYNCING_STALE_MS = 3 * 60 * 1000;
const SYNC_LOCK_TTL_MS = 5 * 60 * 1000;
const SYNC_LOCK_HEARTBEAT_MS = 30 * 1000;
const MAX_SYNC_AUDIT_EVENTS = 80;
export const OFFLINE_SALES_SYNC_EVENTS_KEY =
  "index-pos-offline-sales-sync-events";
const STALE_SYNC_ERROR =
  "Sinxronlash savdo tugashidan oldin uzildi. Savdo o'chirilmadi; backend ishlaganda qayta urinib ko'ring.";

let syncInProgress = false;
let tabId = "";

function isBrowser() {
  return typeof window !== "undefined";
}

function nowIso() {
  return new Date().toISOString();
}

function isOnline(options?: OfflineSyncOptions) {
  if (typeof options?.isOnline === "boolean") {
    return options.isOnline;
  }
  if (typeof navigator === "undefined") {
    return true;
  }
  return navigator.onLine;
}

function getSyncBlockReason(options?: OfflineSyncOptions) {
  if (options?.isOnline === false) {
    return "Offline holatda navbatdagi savdolarni sinxronlab bo'lmaydi.";
  }
  if (options?.backendReachable === false) {
    return "Backend API bilan aloqa yo'qligi uchun navbatdagi savdolarni sinxronlab bo'lmaydi.";
  }
  if (!isOnline(options)) {
    return "Offline holatda navbatdagi savdolarni sinxronlab bo'lmaydi.";
  }
  if (isBrowser() && !getStoredAuthToken()) {
    return "Navbatdagi savdolarni sinxronlashdan oldin tizimga kiring.";
  }
  return "";
}

function generateLocalId(prefix: string) {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `${prefix}-${crypto.randomUUID()}`;
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function getTabId() {
  if (!tabId) {
    tabId = generateLocalId("sync-tab");
  }
  return tabId;
}

export function createSaleIdempotencyKey() {
  return generateLocalId("checkout");
}

function getSaleLocalReference(sale: PendingSaleRecord) {
  return (
    sale.serverReceiptNumber ||
    sale.receiptFallback?.receiptNumber ||
    sale.id
  );
}

function emitQueueChange() {
  if (isBrowser()) {
    window.dispatchEvent(new Event(OFFLINE_SALES_QUEUE_EVENT));
  }
}

type OfflineSyncAuditEventInput = Omit<
  OfflineSyncAuditEvent,
  "id" | "timestamp"
>;

function readSyncAuditEvents() {
  if (!isBrowser()) {
    return [];
  }
  try {
    const rawEvents = window.localStorage.getItem(OFFLINE_SALES_SYNC_EVENTS_KEY);
    if (!rawEvents) {
      return [];
    }
    const parsed = JSON.parse(rawEvents);
    return Array.isArray(parsed)
      ? (parsed as OfflineSyncAuditEvent[]).slice(0, MAX_SYNC_AUDIT_EVENTS)
      : [];
  } catch {
    return [];
  }
}

function appendSyncAuditEvent(input: OfflineSyncAuditEventInput) {
  if (!isBrowser()) {
    return null;
  }

  const event: OfflineSyncAuditEvent = {
    id: generateLocalId("sync-event"),
    timestamp: nowIso(),
    ...input,
    message: input.message.slice(0, 240),
  };
  const events = [event, ...readSyncAuditEvents()].slice(0, MAX_SYNC_AUDIT_EVENTS);
  try {
    window.localStorage.setItem(
      OFFLINE_SALES_SYNC_EVENTS_KEY,
      JSON.stringify(events),
    );
    emitQueueChange();
  } catch {
    // Audit events are helpful but must never block sale queue safety.
  }
  return event;
}

export function getOfflineSalesSyncEvents() {
  return readSyncAuditEvents();
}

function isStaleSyncingSale(sale: PendingSaleRecord, timestamp = Date.now()) {
  if (sale.status !== "syncing") {
    return false;
  }

  const updatedAt = new Date(sale.updatedAt).getTime();
  return Number.isFinite(updatedAt) && timestamp - updatedAt > SYNCING_STALE_MS;
}

function isOfflineSaleStatus(value: string): value is OfflineSaleStatus {
  return (
    value === "pending" ||
    value === "syncing" ||
    value === "synced" ||
    value === "failed"
  );
}

function normalizeQueuedSaleRecord(sale: PendingSaleRecord): PendingSaleRecord {
  const createdAt = sale.createdAt || sale.receiptFallback?.createdAt || nowIso();
  const payload = sale.payload ?? ({} as SalePayload);
  const id = sale.id || generateLocalId("local-sale");
  const idempotencyKey =
    sale.idempotencyKey || payload.idempotency_key || createSaleIdempotencyKey();
  const lastErrorMessage = sale.lastErrorMessage ?? sale.lastError ?? "";
  const failureCategory = sale.failureCategory ?? sale.failureClass;

  return {
    ...sale,
    id,
    idempotencyKey,
    status: isOfflineSaleStatus(sale.status) ? sale.status : "pending",
    createdAt,
    updatedAt:
      sale.updatedAt ||
      sale.syncedAt ||
      sale.lastAttemptAt ||
      createdAt,
    retryCount: Number.isFinite(sale.retryCount) ? sale.retryCount : 0,
    lastError: lastErrorMessage,
    lastErrorMessage,
    lastErrorCode: sale.lastErrorCode ?? "",
    failureClass: sale.failureClass ?? failureCategory,
    failureCategory,
    payload: {
      ...payload,
      idempotency_key: idempotencyKey,
    },
    receiptFallback: {
      receiptNumber: sale.receiptFallback?.receiptNumber || id,
      createdAt: sale.receiptFallback?.createdAt || createdAt,
      storeName: sale.receiptFallback?.storeName || "Index",
    },
  };
}

async function normalizeQueueState(
  state: OfflineSalesQueueReadState,
): Promise<OfflineSalesQueueReadState> {
  if (state.parseError || state.queue.length === 0) {
    return state;
  }

  const normalizedQueue = state.queue.map(normalizeQueuedSaleRecord);
  if (JSON.stringify(normalizedQueue) !== JSON.stringify(state.queue)) {
    await saveOfflineSalesQueueToStorage(normalizedQueue);
  }
  return {
    ...state,
    queue: normalizedQueue,
  };
}

function recoverStaleSyncingSales(queue: PendingSaleRecord[], timestamp = Date.now()) {
  let changed = false;
  let recoveredCount = 0;
  const recoveredSales: PendingSaleRecord[] = [];
  const recoveredQueue = queue.map((sale) => {
    if (!isStaleSyncingSale(sale, timestamp)) {
      return sale;
    }

    changed = true;
    recoveredCount += 1;
    const recoveredSale = {
      ...sale,
      status: "failed" as OfflineSaleStatus,
      updatedAt: nowIso(),
      lastError: STALE_SYNC_ERROR,
      lastErrorMessage: STALE_SYNC_ERROR,
      lastErrorCode: "stale_sync_recovered",
      failureClass: "backend_unavailable" as OfflineFailureClass,
      failureCategory: "backend_unavailable" as OfflineFailureClass,
    };
    recoveredSales.push(recoveredSale);
    return recoveredSale;
  });

  return { queue: recoveredQueue, changed, recoveredCount, recoveredSales };
}

export function getEmptyOfflineSalesQueueState() {
  return getInitialOfflineSalesQueueState();
}

export async function readOfflineSalesQueueState() {
  return normalizeQueueState(await readOfflineSalesQueueStorageState());
}

export async function getOfflineSalesQueue() {
  return (await readOfflineSalesQueueState()).queue;
}

export async function saveOfflineSalesQueue(queue: PendingSaleRecord[]) {
  await saveOfflineSalesQueueToStorage(queue.map(normalizeQueuedSaleRecord));
}

export async function recoverInterruptedSyncingSales() {
  const state = await readOfflineSalesQueueState();
  if (state.parseError || readLock().locked) {
    return 0;
  }

  const recovery = recoverStaleSyncingSales(state.queue);
  if (recovery.changed) {
    await saveOfflineSalesQueue(recovery.queue);
    recovery.recoveredSales.forEach((sale) => {
      appendSyncAuditEvent({
        type: "stale_recovered",
        saleId: sale.id,
        localReference: getSaleLocalReference(sale),
        fromStatus: "syncing",
        toStatus: "failed",
        errorCode: "stale_sync_recovered",
        failureClass: "backend_unavailable",
        message: "Uzilgan sinxronlashdagi savdo qo'lda qayta urinish uchun tiklandi.",
      });
    });
  }
  return recovery.recoveredCount;
}

async function updateQueuedSale(
  saleId: string,
  update: (sale: PendingSaleRecord) => PendingSaleRecord,
) {
  await updateQueuedSaleInStorage(saleId, update);
}

export async function getOfflineSalesSummary(): Promise<OfflineSalesSummary> {
  const queue = await getOfflineSalesQueue();
  return queue.reduce<OfflineSalesSummary>(
    (summary, sale) => ({
      total: summary.total + 1,
      pending: summary.pending + (sale.status === "pending" ? 1 : 0),
      syncing: summary.syncing + (sale.status === "syncing" ? 1 : 0),
      staleSyncing: summary.staleSyncing + (isStaleSyncingSale(sale) ? 1 : 0),
      synced: summary.synced + (sale.status === "synced" ? 1 : 0),
      failed: summary.failed + (sale.status === "failed" ? 1 : 0),
    }),
    { total: 0, pending: 0, syncing: 0, staleSyncing: 0, synced: 0, failed: 0 },
  );
}

export function createPendingSaleRecord(
  input: CreatePendingSaleRecordInput,
): PendingSaleRecord {
  const createdAt = nowIso();
  const id = generateLocalId("local-sale");
  const idempotencyKey = input.payload.idempotency_key ?? createSaleIdempotencyKey();
  return {
    id,
    idempotencyKey,
    status: "pending",
    createdAt,
    updatedAt: createdAt,
    retryCount: 0,
    lastError: "",
    lastErrorMessage: "",
    lastErrorCode: "",
    payload: { ...input.payload, idempotency_key: idempotencyKey },
    cartItems: input.cartItems,
    payments: input.payments,
    session: input.session,
    totals: input.totals,
    receiptFallback: {
      receiptNumber: id,
      createdAt,
      storeName: "Index",
    },
  };
}

export async function enqueuePendingSale(input: CreatePendingSaleRecordInput) {
  const sale = createPendingSaleRecord(input);
  const existingSale = (await getOfflineSalesQueue()).find(
    (queuedSale) =>
      queuedSale.idempotencyKey === sale.idempotencyKey &&
      queuedSale.status !== "synced",
  );
  if (existingSale) {
    appendSyncAuditEvent({
      type: "sync_skipped",
      saleId: existingSale.id,
      localReference: getSaleLocalReference(existingSale),
      message:
        "Takror offline saqlash o'tkazib yuborildi, chunki bu checkout allaqachon ushbu qurilma navbatida bor.",
    });
    return existingSale;
  }
  return addQueuedSaleToStorage(sale);
}

function readLock(): OfflineSyncLockState {
  if (!isBrowser()) {
    return {
      locked: false,
      lockedByCurrentTab: false,
      lockedByAnotherTab: false,
      ownerId: "",
      expiresAt: "",
    };
  }

  const rawLock = window.localStorage.getItem(OFFLINE_SALES_SYNC_LOCK_KEY);
  if (!rawLock) {
    return {
      locked: false,
      lockedByCurrentTab: false,
      lockedByAnotherTab: false,
      ownerId: "",
      expiresAt: "",
    };
  }

  try {
    const parsed = JSON.parse(rawLock) as {
      ownerId?: string;
      expiresAt?: string;
    };
    const expiresAtMs = new Date(parsed.expiresAt ?? "").getTime();
    if (!Number.isFinite(expiresAtMs) || expiresAtMs <= Date.now()) {
      window.localStorage.removeItem(OFFLINE_SALES_SYNC_LOCK_KEY);
      appendSyncAuditEvent({
        type: "lock_recovered",
        message: "Muddati o'tgan offline sinxronlash lock tiklandi.",
      });
      emitQueueChange();
      return {
        locked: false,
        lockedByCurrentTab: false,
        lockedByAnotherTab: false,
        ownerId: "",
        expiresAt: "",
      };
    }

    const ownerId = parsed.ownerId ?? "";
    return {
      locked: true,
      lockedByCurrentTab: ownerId === getTabId(),
      lockedByAnotherTab: ownerId !== getTabId(),
      ownerId,
      expiresAt: parsed.expiresAt ?? "",
    };
  } catch {
    window.localStorage.removeItem(OFFLINE_SALES_SYNC_LOCK_KEY);
    emitQueueChange();
    return {
      locked: false,
      lockedByCurrentTab: false,
      lockedByAnotherTab: false,
      ownerId: "",
      expiresAt: "",
    };
  }
}

export function getOfflineSalesSyncLockState() {
  return readLock();
}

export async function clearSyncedOfflineSales() {
  return clearSyncedSalesFromStorage();
}

function acquireSyncLock() {
  if (!isBrowser()) {
    return "";
  }

  const currentLock = readLock();
  if (currentLock.locked && !currentLock.lockedByCurrentTab) {
    return "";
  }

  const ownerId = getTabId();
  const expiresAt = new Date(Date.now() + SYNC_LOCK_TTL_MS).toISOString();
  window.localStorage.setItem(
    OFFLINE_SALES_SYNC_LOCK_KEY,
    JSON.stringify({ ownerId, expiresAt }),
  );
  emitQueueChange();

  const confirmedLock = readLock();
  return confirmedLock.lockedByCurrentTab ? ownerId : "";
}

function refreshSyncLock(ownerId: string) {
  if (!isBrowser() || !ownerId) {
    return false;
  }

  const currentLock = readLock();
  if (!currentLock.lockedByCurrentTab || currentLock.ownerId !== ownerId) {
    return false;
  }

  window.localStorage.setItem(
    OFFLINE_SALES_SYNC_LOCK_KEY,
    JSON.stringify({
      ownerId,
      expiresAt: new Date(Date.now() + SYNC_LOCK_TTL_MS).toISOString(),
    }),
  );
  emitQueueChange();
  return true;
}

function startSyncLockHeartbeat(ownerId: string) {
  if (!isBrowser() || !ownerId) {
    return () => undefined;
  }

  const intervalId = window.setInterval(() => {
    void refreshSyncLock(ownerId);
  }, SYNC_LOCK_HEARTBEAT_MS);

  return () => {
    window.clearInterval(intervalId);
  };
}

function releaseSyncLock(ownerId: string) {
  if (!isBrowser() || !ownerId) {
    return;
  }

  const currentLock = readLock();
  if (currentLock.lockedByCurrentTab && currentLock.ownerId === ownerId) {
    window.localStorage.removeItem(OFFLINE_SALES_SYNC_LOCK_KEY);
    emitQueueChange();
  }
}

function getReplayableSales(queue: PendingSaleRecord[], saleIds?: string[]) {
  const selectedIds = new Set(saleIds ?? []);
  return queue
    .filter(
      (sale) =>
        (sale.status === "pending" || sale.status === "failed") &&
        (selectedIds.size === 0 || selectedIds.has(sale.id)),
    )
    .sort(
      (first, second) =>
        new Date(first.createdAt).getTime() -
        new Date(second.createdAt).getTime(),
    );
}

function stringifyErrorDetail(detail: unknown): string {
  if (detail === null || detail === undefined) {
    return "";
  }
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    return detail.map((item) => stringifyErrorDetail(item)).join(" ");
  }
  if (typeof detail === "object") {
    const ignoredKeys = new Set(["code", "message", "status"]);

    return Object.entries(detail as Record<string, unknown>)
      .filter(([key]) => !ignoredKeys.has(key))
      .map(([key, value]) => {
        const message = stringifyErrorDetail(value);
        if (!message) {
          return "";
        }
        if (["detail", "non_field_errors"].includes(key)) {
          return message;
        }
        return `${key.replaceAll("_", " ")}: ${message}`;
      })
      .filter(Boolean)
      .join(" ");
  }
  return String(detail);
}

function includesAny(value: string, patterns: string[]) {
  return patterns.some((pattern) => value.includes(pattern));
}

function getBackendErrorCode(detail: unknown): string {
  if (detail === null || detail === undefined) {
    return "";
  }
  if (typeof detail === "string") {
    return "";
  }
  if (Array.isArray(detail)) {
    return detail.map(getBackendErrorCode).find(Boolean) ?? "";
  }
  if (typeof detail === "object") {
    const record = detail as Record<string, unknown>;
    if (typeof record.code === "string") {
      return record.code;
    }
    return Object.values(record).map(getBackendErrorCode).find(Boolean) ?? "";
  }
  return "";
}

export function classifyOfflineSaleFailure(error: unknown): {
  failureClass: OfflineFailureClass;
  message: string;
  errorCode: string;
} {
  if (error instanceof ApiError) {
    const backendCode = getBackendErrorCode(error.detail);
    const detailText = stringifyErrorDetail(error.detail).toLowerCase();
    const statusText = `${error.status} ${detailText}`;
    if (backendCode === "idempotency_conflict" || error.status === 409) {
      return {
        failureClass: "idempotency_conflict",
        errorCode: backendCode || "idempotency_conflict",
        message:
          "Idempotency kaliti ziddiyati. Navbatdagi savdo server nusxasiga mos emas va qo'lda ko'rib chiqilishi kerak.",
      };
    }
    if (error.status === 401 || error.status === 403) {
      return {
        failureClass: "permission_store_scope",
        errorCode: backendCode || `http_${error.status}`,
        message: "Huquq yoki do'kon doirasi bu savdoni blokladi. Tizimga kirib filial huquqini tekshiring.",
      };
    }
    if (
      backendCode === "shift_closed_missing" ||
      includesAny(statusText, [
        "shift",
        "cashier session",
        "active cashier",
        "open shift",
        "closed",
      ])
    ) {
      return {
        failureClass: "shift_closed_missing",
        errorCode: backendCode || "shift_closed_missing",
        message: "Kassir smenasi yo'q yoki yopilgan. Qayta urinishdan oldin yaroqli smena oching.",
      };
    }
    if (
      backendCode === "stock_conflict" ||
      includesAny(statusText, [
        "stock",
        "available",
        "quantity",
        "reserved",
        "negative",
        "insufficient",
      ])
    ) {
      return {
        failureClass: "stock_conflict",
        errorCode: backendCode || "stock_conflict",
        message: "Sinxronlashdan oldin qoldiq o'zgargan. Qayta urinishdan oldin miqdorlarni tekshiring.",
      };
    }
    if (
      error.status === 404 ||
      includesAny(statusText, ["product", "barcode", "not found", "does not exist"])
    ) {
      return {
        failureClass: "product_missing",
        errorCode: backendCode || "product_missing",
        message: "Mahsulot yoki bog'liq checkout yozuvi endi mavjud emas.",
      };
    }
    if (
      backendCode === "scope_denied" ||
      backendCode === "permission_denied" ||
      includesAny(statusText, [
        "permission",
        "forbidden",
        "scope",
        "branch",
        "warehouse",
        "access",
      ])
    ) {
      return {
        failureClass: "permission_store_scope",
        errorCode: backendCode || "scope_denied",
        message: "Filial, ombor yoki huquq doirasi bu savdoni blokladi.",
      };
    }
    if (backendCode === "validation_error" || error.status === 400) {
      return {
        failureClass: "validation_error",
        errorCode: backendCode || "validation_error",
        message: "Backend validatsiyasi bu savdoni rad etdi. To'lov, mijoz va jami summalarni tekshiring.",
      };
    }
    if (error.status >= 500) {
      return {
        failureClass: "backend_unavailable",
        errorCode: backendCode || `http_${error.status}`,
        message: "Bu savdoni sinxronlashda backend server xatosi. Keyinroq qayta urinib ko'ring.",
      };
    }
    return {
      failureClass: "unknown",
      errorCode: backendCode || `http_${error.status}`,
      message: "Navbatdagi savdoni sinxronlab bo'lmadi. Uni ko'rib chiqib, qayta urinib ko'ring.",
    };
  }
  if (error instanceof TypeError) {
    return {
      failureClass: "backend_unavailable",
      errorCode: "network_error",
      message: "Backend mavjud emas. Aloqani tekshirib, qayta urinib ko'ring.",
    };
  }
  return {
    failureClass: "unknown",
    errorCode: "unknown_error",
    message: "Kutilmagan sinxronlash xatosi. Qayta urinishdan oldin navbatdagi savdoni ko'rib chiqing.",
  };
}

async function markSyncing(saleId: string) {
  const attemptedAt = nowIso();
  let auditEvent: OfflineSyncAuditEventInput | null = null;
  await updateQueuedSale(saleId, (sale) => {
    auditEvent = {
      type: "sale_syncing",
      saleId: sale.id,
      localReference: getSaleLocalReference(sale),
      fromStatus: sale.status,
      toStatus: "syncing",
      message: "Navbatdagi savdoni qayta yuborish boshlandi.",
    };
    return {
      ...sale,
      status: "syncing",
      updatedAt: attemptedAt,
      lastAttemptAt: attemptedAt,
      lastError: "",
      lastErrorMessage: "",
      lastErrorCode: "",
      failureClass: undefined,
      failureCategory: undefined,
    };
  });
  if (auditEvent) {
    appendSyncAuditEvent(auditEvent);
  }
}

async function markSynced(saleId: string, sale: Sale) {
  const syncedAt = nowIso();
  let auditEvent: OfflineSyncAuditEventInput | null = null;
  await updateQueuedSale(saleId, (queuedSale) => {
    auditEvent = {
      type: "sale_synced",
      saleId: queuedSale.id,
      localReference: getSaleLocalReference(queuedSale),
      fromStatus: queuedSale.status,
      toStatus: "synced",
      message: "Navbatdagi savdo server tomonidan qabul qilindi.",
    };
    return {
      ...queuedSale,
      status: "synced",
      updatedAt: syncedAt,
      syncedAt,
      serverSaleId: sale.id,
      serverReceiptNumber: sale.receipt_number,
      lastError: "",
      lastErrorMessage: "",
      lastErrorCode: "",
      failureClass: undefined,
      failureCategory: undefined,
    };
  });
  if (auditEvent) {
    appendSyncAuditEvent(auditEvent);
  }
}

async function markFailed(
  saleId: string,
  failure: { failureClass: OfflineFailureClass; message: string; errorCode: string },
  serverSale?: Sale,
) {
  const failedAt = nowIso();
  let auditEvent: OfflineSyncAuditEventInput | null = null;
  await updateQueuedSale(saleId, (sale) => {
    auditEvent = {
      type: "sale_failed",
      saleId: sale.id,
      localReference: getSaleLocalReference(sale),
      fromStatus: sale.status,
      toStatus: "failed",
      errorCode: failure.errorCode,
      failureClass: failure.failureClass,
      message: failure.message,
    };
    return {
      ...sale,
      status: "failed",
      updatedAt: failedAt,
      lastAttemptAt: failedAt,
      retryCount: sale.retryCount + 1,
      lastError: failure.message,
      lastErrorMessage: failure.message,
      lastErrorCode: failure.errorCode,
      failureClass: failure.failureClass,
      failureCategory: failure.failureClass,
      serverSaleId: serverSale?.id ?? sale.serverSaleId,
      serverReceiptNumber: serverSale?.receipt_number ?? sale.serverReceiptNumber,
    };
  });
  if (auditEvent) {
    appendSyncAuditEvent(auditEvent);
  }
}

function createResult(
  result: Omit<OfflineSyncResult, "completedAt">,
): OfflineSyncResult {
  return {
    ...result,
    completedAt: nowIso(),
  };
}

function createSkippedSyncResult(reason: string) {
  const result = createResult({
    attempted: 0,
    synced: 0,
    failed: 0,
    skipped: true,
    reason,
  });
  appendSyncAuditEvent({
    type: "sync_skipped",
    message: reason,
  });
  return result;
}

function formatSaleCount(count: number) {
  return `${count} savdo`;
}

function createCompletedSyncReason({
  synced,
  failed,
  stoppedReason,
}: {
  synced: number;
  failed: number;
  stoppedReason: string;
}) {
  if (synced > 0 && failed === 0 && !stoppedReason) {
    return `Sinxronlash tugadi: ${formatSaleCount(synced)} serverga yuborildi.`;
  }
  if (synced === 0 && failed > 0 && !stoppedReason) {
    return `Sinxronlash tugadi: ${formatSaleCount(failed)} hali ko'rib chiqilishi kerak.`;
  }
  if (synced === 0 && failed === 0 && stoppedReason) {
    return stoppedReason;
  }
  return `Sinxronlash tugadi: ${formatSaleCount(synced)} yuborildi, ${formatSaleCount(
    failed,
  )} ko'rib chiqilishi kerak.${stoppedReason ? ` ${stoppedReason}` : ""}`;
}

export async function syncQueueOnce(
  options?: OfflineSyncOptions,
): Promise<OfflineSyncResult> {
  const blockReason = getSyncBlockReason(options);
  if (blockReason) {
    return createSkippedSyncResult(blockReason);
  }

  if (syncInProgress) {
    return createSkippedSyncResult("Savdo sinxronlash allaqachon ishlayapti.");
  }

  syncInProgress = true;
  const lockOwnerId = acquireSyncLock();
  if (!lockOwnerId) {
    syncInProgress = false;
    return createSkippedSyncResult(
      "Boshqa POS oynasi navbatdagi savdolarni sinxronlayapti.",
    );
  }

  const stopLockHeartbeat = startSyncLockHeartbeat(lockOwnerId);
  let synced = 0;
  let failed = 0;
  let attempted = 0;
  let stoppedReason = "";

  try {
    const replayableSales = getReplayableSales(
      await getOfflineSalesQueue(),
      options?.saleIds,
    );
    if (replayableSales.length === 0) {
      return createSkippedSyncResult(
        "Sinxronlanadigan kutilayotgan yoki xato savdolar yo'q.",
      );
    }

    appendSyncAuditEvent({
      type: "sync_started",
      message: `${replayableSales.length} navbatdagi savdo qo'lda sinxronlashga tayyor.`,
    });

    for (const queuedSale of replayableSales) {
      if (!refreshSyncLock(lockOwnerId)) {
        stoppedReason = "Lokal sinxronlash lock yo'qolgani uchun sinxronlash to'xtadi.";
        appendSyncAuditEvent({
          type: "lock_lost",
          message: stoppedReason,
        });
        break;
      }

      attempted += 1;
      const idempotencyKey =
        queuedSale.idempotencyKey || queuedSale.payload.idempotency_key;

      if (!idempotencyKey) {
        failed += 1;
        await markFailed(
          queuedSale.id,
          {
            failureClass: "validation_error",
            errorCode: "missing_idempotency_key",
            message: "Idempotency kaliti yo'q. Bu savdoni qo'lda ko'rib chiqish kerak.",
          },
        );
        continue;
      }

      await markSyncing(queuedSale.id);

      let draftSale: Sale | undefined;
      try {
        // Reuse the stored idempotency key so a replayed checkout cannot create
        // duplicate sale, stock, or finance effects after a partial retry.
        draftSale = await createSale({
          ...queuedSale.payload,
          idempotency_key: idempotencyKey,
        });
        const completedSale = await completeSale(draftSale.id);
        synced += 1;
        await markSynced(queuedSale.id, completedSale);
      } catch (error) {
        failed += 1;
        await markFailed(queuedSale.id, classifyOfflineSaleFailure(error), draftSale);
      }
    }

    const result = createResult({
      attempted,
      synced,
      failed,
      skipped: false,
      reason: createCompletedSyncReason({ synced, failed, stoppedReason }),
    });
    appendSyncAuditEvent({
      type: "sync_completed",
      message: result.reason,
    });
    return result;
  } finally {
    stopLockHeartbeat();
    syncInProgress = false;
    releaseSyncLock(lockOwnerId);
  }
}

export async function syncOfflineSalesQueue(
  options?: OfflineSyncOptions,
): Promise<OfflineSyncResult> {
  return syncQueueOnce(options);
}

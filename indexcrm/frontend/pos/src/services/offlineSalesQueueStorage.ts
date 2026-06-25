import type {
  OfflineSalesQueueReadState,
  PendingSaleRecord,
} from "@/services/offlineSalesQueue";

export type OfflineSalesStorageMode = "indexeddb" | "localStorage" | "unavailable";
export type OfflineSalesMigrationStatus =
  | "idle"
  | "already-migrated"
  | "migrated"
  | "blocked"
  | "fallback";

export type OfflineSalesStorageMeta = {
  storageInitialized: boolean;
  storageMode: OfflineSalesStorageMode;
  storageFallbackReason: string;
  migrationStatus: OfflineSalesMigrationStatus;
  migrationMessage: string;
};

export const OFFLINE_SALES_QUEUE_KEY = "index-pos-offline-sales";
export const OFFLINE_SALES_QUEUE_EVENT = "index-pos-offline-sales-change";
export const OFFLINE_SALES_SYNC_LOCK_KEY = "index-pos-offline-sales-sync-lock";
export const OFFLINE_SALES_QUEUE_PING_KEY =
  "index-pos-offline-sales-change-ping";

const DB_NAME = "index-pos-offline-sales-db";
const DB_VERSION = 1;
const STORE_NAME = "offline-sales";
const MIGRATION_VERSION = "1";
const MIGRATION_KEY = "index-pos-offline-sales-idb-migration-version";

const emptyMeta: OfflineSalesStorageMeta = {
  storageInitialized: false,
  storageMode: "indexeddb",
  storageFallbackReason: "",
  migrationStatus: "idle",
  migrationMessage: "",
};

let storageMeta: OfflineSalesStorageMeta = { ...emptyMeta };
let dbPromise: Promise<IDBDatabase> | null = null;
let initializationPromise: Promise<OfflineSalesStorageMeta> | null = null;

function isBrowser() {
  return typeof window !== "undefined";
}

function emitQueueChange() {
  if (!isBrowser()) {
    return;
  }
  window.dispatchEvent(new Event(OFFLINE_SALES_QUEUE_EVENT));
  try {
    window.localStorage.setItem(OFFLINE_SALES_QUEUE_PING_KEY, new Date().toISOString());
  } catch {
    // Storage events are best-effort; queue writes have already completed.
  }
}

function withMeta(
  state: Pick<OfflineSalesQueueReadState, "queue" | "parseError" | "rawValue">,
): OfflineSalesQueueReadState {
  return {
    ...state,
    ...storageMeta,
  };
}

function fallbackMeta(reason: string): OfflineSalesStorageMeta {
  return {
    storageInitialized: true,
    storageMode: "localStorage",
    storageFallbackReason: reason,
    migrationStatus: "fallback",
    migrationMessage: "IndexedDB is unavailable. Using localStorage fallback.",
  };
}

function parseLocalStorageQueue(value: string | null): OfflineSalesQueueReadState {
  if (!value) {
    return withMeta({ queue: [], parseError: false, rawValue: "" });
  }

  try {
    const parsed = JSON.parse(value);
    return withMeta({
      queue: Array.isArray(parsed) ? (parsed as PendingSaleRecord[]) : [],
      parseError: !Array.isArray(parsed),
      rawValue: value,
    });
  } catch {
    return withMeta({ queue: [], parseError: true, rawValue: value });
  }
}

function readLocalStorageQueueState(): OfflineSalesQueueReadState {
  if (!isBrowser()) {
    return withMeta({ queue: [], parseError: false, rawValue: "" });
  }
  try {
    return parseLocalStorageQueue(
      window.localStorage.getItem(OFFLINE_SALES_QUEUE_KEY),
    );
  } catch {
    return withMeta({ queue: [], parseError: true, rawValue: "" });
  }
}

function writeLocalStorageQueueSnapshot(queue: PendingSaleRecord[]) {
  if (!isBrowser()) {
    throw new Error("Offline queue storage is unavailable in this environment.");
  }
  window.localStorage.setItem(OFFLINE_SALES_QUEUE_KEY, JSON.stringify(queue));
}

function mirrorQueueToLocalStorage(queue: PendingSaleRecord[]) {
  try {
    writeLocalStorageQueueSnapshot(queue);
  } catch {
    // IndexedDB remains the primary queue; the localStorage mirror is best-effort.
  }
}

function saveLocalStorageQueue(queue: PendingSaleRecord[]) {
  writeLocalStorageQueueSnapshot(queue);
  emitQueueChange();
}

function requestToPromise<T>(request: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error ?? new Error("IndexedDB request failed."));
  });
}

function transactionDone(transaction: IDBTransaction): Promise<void> {
  return new Promise((resolve, reject) => {
    transaction.oncomplete = () => resolve();
    transaction.onerror = () =>
      reject(transaction.error ?? new Error("IndexedDB transaction failed."));
    transaction.onabort = () =>
      reject(transaction.error ?? new Error("IndexedDB transaction aborted."));
  });
}

function openIndexedDb() {
  if (!isBrowser() || !window.indexedDB) {
    return Promise.reject(new Error("IndexedDB is not available in this browser."));
  }

  if (dbPromise) {
    return dbPromise;
  }

  dbPromise = new Promise<IDBDatabase>((resolve, reject) => {
    const request = window.indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        const store = db.createObjectStore(STORE_NAME, { keyPath: "id" });
        store.createIndex("status", "status", { unique: false });
        store.createIndex("createdAt", "createdAt", { unique: false });
        store.createIndex("updatedAt", "updatedAt", { unique: false });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => {
      dbPromise = null;
      reject(request.error ?? new Error("IndexedDB open failed."));
    };
    request.onblocked = () => {
      dbPromise = null;
      reject(new Error("IndexedDB upgrade is blocked by another open POS tab."));
    };
  });

  return dbPromise;
}

async function listIndexedSales() {
  const db = await openIndexedDb();
  const transaction = db.transaction(STORE_NAME, "readonly");
  const request = transaction.objectStore(STORE_NAME).getAll();
  const sales = await requestToPromise<PendingSaleRecord[]>(request);
  return sales.sort(
    (first, second) =>
      new Date(second.createdAt).getTime() - new Date(first.createdAt).getTime(),
  );
}

async function putIndexedSales(sales: PendingSaleRecord[]) {
  const db = await openIndexedDb();
  const transaction = db.transaction(STORE_NAME, "readwrite");
  const store = transaction.objectStore(STORE_NAME);
  sales.forEach((sale) => store.put(sale));
  await transactionDone(transaction);
  emitQueueChange();
}

async function replaceIndexedSales(sales: PendingSaleRecord[]) {
  const db = await openIndexedDb();
  const transaction = db.transaction(STORE_NAME, "readwrite");
  const store = transaction.objectStore(STORE_NAME);
  store.clear();
  sales.forEach((sale) => store.put(sale));
  await transactionDone(transaction);
  emitQueueChange();
}

async function deleteIndexedSales(saleIds: string[]) {
  if (saleIds.length === 0) {
    return;
  }
  const db = await openIndexedDb();
  const transaction = db.transaction(STORE_NAME, "readwrite");
  const store = transaction.objectStore(STORE_NAME);
  saleIds.forEach((saleId) => store.delete(saleId));
  await transactionDone(transaction);
  emitQueueChange();
}

async function migrateLocalStorageQueueToIndexedDb() {
  if (!isBrowser()) {
    return { status: "idle" as OfflineSalesMigrationStatus, message: "" };
  }
  try {
    if (window.localStorage.getItem(MIGRATION_KEY) === MIGRATION_VERSION) {
      return {
        status: "already-migrated" as OfflineSalesMigrationStatus,
        message: "LocalStorage queue migration has already completed.",
      };
    }
  } catch {
    return {
      status: "blocked" as OfflineSalesMigrationStatus,
      message:
        "Existing localStorage queue could not be checked for migration in this browser.",
    };
  }

  const localState = readLocalStorageQueueState();
  if (localState.parseError) {
    return {
      status: "blocked" as OfflineSalesMigrationStatus,
      message:
        "Existing localStorage queue could not be migrated because it is not valid JSON.",
    };
  }

  const existingSales = await listIndexedSales();
  const existingIds = new Set(existingSales.map((sale) => sale.id));
  const missingSales = localState.queue.filter((sale) => !existingIds.has(sale.id));
  if (missingSales.length > 0) {
    await putIndexedSales(missingSales);
  }
  try {
    window.localStorage.setItem(MIGRATION_KEY, MIGRATION_VERSION);
  } catch {
    return {
      status: "blocked" as OfflineSalesMigrationStatus,
      message:
        "Local offline sales were copied into IndexedDB, but the migration marker could not be saved.",
    };
  }
  return {
    status: "migrated" as OfflineSalesMigrationStatus,
    message:
      missingSales.length > 0
        ? `Migrated ${missingSales.length} local offline sale(s) into IndexedDB.`
        : "No unmigrated local offline sales were found.",
  };
}

export function getInitialOfflineSalesQueueState(): OfflineSalesQueueReadState {
  return withMeta({ queue: [], parseError: false, rawValue: "" });
}

export function getOfflineSalesStorageMeta() {
  return storageMeta;
}

export async function initializeOfflineSalesStorage() {
  if (storageMeta.storageInitialized) {
    return storageMeta;
  }
  if (initializationPromise) {
    return initializationPromise;
  }

  initializationPromise = (async () => {
    if (!isBrowser()) {
      storageMeta = {
        storageInitialized: true,
        storageMode: "unavailable",
        storageFallbackReason: "Offline queue storage is unavailable outside the browser.",
        migrationStatus: "fallback",
        migrationMessage: "",
      };
      return storageMeta;
    }

    try {
      await openIndexedDb();
      const migration = await migrateLocalStorageQueueToIndexedDb();
      storageMeta = {
        storageInitialized: true,
        storageMode: "indexeddb",
        storageFallbackReason: "",
        migrationStatus: migration.status,
        migrationMessage: migration.message,
      };
      return storageMeta;
    } catch (error) {
      storageMeta = fallbackMeta(
        error instanceof Error
          ? error.message
          : "IndexedDB could not be opened.",
      );
      return storageMeta;
    }
  })();

  return initializationPromise;
}

export async function readOfflineSalesQueueStorageState() {
  await initializeOfflineSalesStorage();
  if (storageMeta.storageMode !== "indexeddb") {
    return readLocalStorageQueueState();
  }

  try {
    return withMeta({
      queue: await listIndexedSales(),
      parseError: false,
      rawValue: "",
    });
  } catch (error) {
    storageMeta = fallbackMeta(
      error instanceof Error
        ? error.message
        : "IndexedDB queue read failed.",
    );
    return readLocalStorageQueueState();
  }
}

export async function listOfflineSalesFromStorage() {
  return (await readOfflineSalesQueueStorageState()).queue;
}

export async function getQueuedSaleFromStorage(saleId: string) {
  return (await listOfflineSalesFromStorage()).find((sale) => sale.id === saleId) ?? null;
}

export async function saveOfflineSalesQueueToStorage(queue: PendingSaleRecord[]) {
  await initializeOfflineSalesStorage();
  if (storageMeta.storageMode === "indexeddb") {
    try {
      await replaceIndexedSales(queue);
      mirrorQueueToLocalStorage(queue);
    } catch (error) {
      storageMeta = fallbackMeta(
        error instanceof Error
          ? error.message
          : "IndexedDB queue write failed.",
      );
      saveLocalStorageQueue(queue);
    }
    return;
  }
  saveLocalStorageQueue(queue);
}

export async function addQueuedSaleToStorage(sale: PendingSaleRecord) {
  await initializeOfflineSalesStorage();
  if (storageMeta.storageMode === "indexeddb") {
    try {
      await putIndexedSales([sale]);
      mirrorQueueToLocalStorage(await listIndexedSales());
    } catch (error) {
      storageMeta = fallbackMeta(
        error instanceof Error
          ? error.message
          : "IndexedDB queue write failed.",
      );
      const state = readLocalStorageQueueState();
      if (state.parseError) {
        throw new Error("Offline queue is not valid JSON.");
      }
      saveLocalStorageQueue([
        sale,
        ...state.queue.filter((item) => item.id !== sale.id),
      ]);
    }
    return sale;
  }

  const state = readLocalStorageQueueState();
  if (state.parseError) {
    throw new Error("Offline queue is not valid JSON.");
  }
  saveLocalStorageQueue([sale, ...state.queue.filter((item) => item.id !== sale.id)]);
  return sale;
}

export async function updateQueuedSaleInStorage(
  saleId: string,
  update: (sale: PendingSaleRecord) => PendingSaleRecord,
) {
  const queue = await listOfflineSalesFromStorage();
  const nextQueue = queue.map((sale) => (sale.id === saleId ? update(sale) : sale));
  await saveOfflineSalesQueueToStorage(nextQueue);
}

export async function clearSyncedSalesFromStorage() {
  const queue = await listOfflineSalesFromStorage();
  const syncedIds = queue
    .filter((sale) => sale.status === "synced")
    .map((sale) => sale.id);

  if (syncedIds.length === 0) {
    return 0;
  }
  if (storageMeta.storageMode === "indexeddb") {
    try {
      await deleteIndexedSales(syncedIds);
      mirrorQueueToLocalStorage(queue.filter((sale) => sale.status !== "synced"));
    } catch (error) {
      storageMeta = fallbackMeta(
        error instanceof Error
          ? error.message
          : "IndexedDB queue delete failed.",
      );
      await saveOfflineSalesQueueToStorage(
        queue.filter((sale) => sale.status !== "synced"),
      );
    }
    return syncedIds.length;
  }

  await saveOfflineSalesQueueToStorage(
    queue.filter((sale) => sale.status !== "synced"),
  );
  return syncedIds.length;
}

"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import {
  OFFLINE_SALES_QUEUE_EVENT,
  OFFLINE_SALES_QUEUE_KEY,
  OFFLINE_SALES_QUEUE_PING_KEY,
  OFFLINE_SALES_SYNC_LOCK_KEY,
  OFFLINE_SALES_SYNC_EVENTS_KEY,
  OfflineSyncAuditEvent,
  OfflineSyncOptions,
  OfflineSyncResult,
  clearSyncedOfflineSales,
  getEmptyOfflineSalesQueueState,
  getOfflineSalesSummary,
  getOfflineSalesSyncLockState,
  getOfflineSalesSyncEvents,
  readOfflineSalesQueueState,
  recoverInterruptedSyncingSales,
  syncOfflineSalesQueue,
} from "@/services/offlineSalesQueue";

const emptySummary = {
  total: 0,
  pending: 0,
  syncing: 0,
  staleSyncing: 0,
  synced: 0,
  failed: 0,
};

export function useOfflineSalesQueue() {
  const [readState, setReadState] = useState(() => getEmptyOfflineSalesQueueState());
  const [queue, setQueue] = useState(readState.queue);
  const [summary, setSummary] = useState(emptySummary);
  const [lockState, setLockState] = useState(() => getOfflineSalesSyncLockState());
  const [syncEvents, setSyncEvents] = useState<OfflineSyncAuditEvent[]>([]);
  const [isSyncing, setIsSyncing] = useState(false);
  const [lastResult, setLastResult] = useState<OfflineSyncResult | null>(null);
  const syncInFlightRef = useRef(false);
  const refreshIdRef = useRef(0);

  const refresh = useCallback(async () => {
    const refreshId = refreshIdRef.current + 1;
    refreshIdRef.current = refreshId;

    await recoverInterruptedSyncingSales();
    const nextState = await readOfflineSalesQueueState();
    const nextSummary = await getOfflineSalesSummary();
    const nextSyncEvents = getOfflineSalesSyncEvents();
    if (refreshId !== refreshIdRef.current) {
      return;
    }
    setReadState(nextState);
    setQueue(nextState.queue);
    setSummary(nextSummary);
    setLockState(getOfflineSalesSyncLockState());
    setSyncEvents(nextSyncEvents);
  }, []);

  const sync = useCallback(
    async (options?: OfflineSyncOptions) => {
      if (syncInFlightRef.current) {
        const result: OfflineSyncResult = {
          attempted: 0,
          synced: 0,
          failed: 0,
          skipped: true,
          reason: "A queued sale sync is already running.",
          completedAt: new Date().toISOString(),
        };
        setLastResult(result);
        await refresh();
        return result;
      }

      syncInFlightRef.current = true;
      setIsSyncing(true);
      try {
        const result = await syncOfflineSalesQueue(options);
        setLastResult(result);
        await refresh();
        return result;
      } finally {
        syncInFlightRef.current = false;
        setIsSyncing(false);
      }
    },
    [refresh],
  );

  const clearSynced = useCallback(() => {
    return clearSyncedOfflineSales().then(async (removed) => {
      await refresh();
      return removed;
    });
  }, [refresh]);

  const recoverInterrupted = useCallback(() => {
    return recoverInterruptedSyncingSales().then(async (recovered) => {
      await refresh();
      return recovered;
    });
  }, [refresh]);

  useEffect(() => {
    const handleQueueChange = () => {
      void refresh();
    };
    const handleStorage = (event: StorageEvent) => {
      if (
        event.key === OFFLINE_SALES_QUEUE_KEY ||
        event.key === OFFLINE_SALES_QUEUE_PING_KEY ||
        event.key === OFFLINE_SALES_SYNC_LOCK_KEY ||
        event.key === OFFLINE_SALES_SYNC_EVENTS_KEY
      ) {
        void refresh();
      }
    };

    window.addEventListener("storage", handleStorage);
    window.addEventListener(OFFLINE_SALES_QUEUE_EVENT, handleQueueChange);
    void refresh();
    return () => {
      window.removeEventListener("storage", handleStorage);
      window.removeEventListener(OFFLINE_SALES_QUEUE_EVENT, handleQueueChange);
    };
  }, [refresh]);

  return {
    queue,
    parseError: readState.parseError,
    rawQueueValue: readState.rawValue,
    storageInitialized: readState.storageInitialized,
    storageMode: readState.storageMode,
    storageFallbackReason: readState.storageFallbackReason,
    migrationStatus: readState.migrationStatus,
    migrationMessage: readState.migrationMessage,
    summary,
    lockState,
    syncEvents,
    isSyncing,
    lastResult,
    refresh,
    sync,
    clearSynced,
    recoverInterrupted,
  };
}

"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { checkBackendHealth } from "@/services/api/health";

import { useNetworkStatus } from "./useNetworkStatus";

export type PosConnectivityStatus =
  | "online"
  | "browser_offline"
  | "backend_unreachable"
  | "checking"
  | "unknown";

export type PosConnectivitySnapshot = {
  status: PosConnectivityStatus;
  browserOnline: boolean;
  backendReachable: boolean;
  message: string;
  lastCheckedAt: string | null;
  lastReachableAt: string | null;
};

type RefreshOptions = {
  force?: boolean;
};

const HEALTH_STALE_MS = 30_000;
const HEALTH_COOLDOWN_MS = 5_000;

const subscribers = new Set<(snapshot: PosConnectivitySnapshot) => void>();
let cachedSnapshot: PosConnectivitySnapshot = {
  status: "unknown",
  browserOnline: true,
  backendReachable: false,
  message: "Connection has not been checked yet.",
  lastCheckedAt: null,
  lastReachableAt: null,
};
let inFlightCheck: Promise<PosConnectivitySnapshot> | null = null;

function nowIso() {
  return new Date().toISOString();
}

function isSnapshotStale(snapshot: PosConnectivitySnapshot) {
  if (!snapshot.lastCheckedAt) {
    return true;
  }
  const checkedAt = new Date(snapshot.lastCheckedAt).getTime();
  return !Number.isFinite(checkedAt) || Date.now() - checkedAt > HEALTH_STALE_MS;
}

function isInsideCooldown(snapshot: PosConnectivitySnapshot) {
  if (!snapshot.lastCheckedAt) {
    return false;
  }
  const checkedAt = new Date(snapshot.lastCheckedAt).getTime();
  return Number.isFinite(checkedAt) && Date.now() - checkedAt < HEALTH_COOLDOWN_MS;
}

function publish(snapshot: PosConnectivitySnapshot) {
  cachedSnapshot = snapshot;
  subscribers.forEach((subscriber) => subscriber(snapshot));
  return snapshot;
}

function offlineSnapshot(): PosConnectivitySnapshot {
  return {
    ...cachedSnapshot,
    status: "browser_offline",
    browserOnline: false,
    backendReachable: false,
    message: "Offline: no internet connection.",
    lastCheckedAt: nowIso(),
  };
}

async function refreshConnectivity({
  browserOnline,
  force,
}: {
  browserOnline: boolean;
  force?: boolean;
}) {
  if (!browserOnline) {
    return publish(offlineSnapshot());
  }

  if (
    !force &&
    cachedSnapshot.status !== "unknown" &&
    !isSnapshotStale(cachedSnapshot)
  ) {
    return cachedSnapshot;
  }
  if (!force && isInsideCooldown(cachedSnapshot)) {
    return cachedSnapshot;
  }
  if (inFlightCheck) {
    return inFlightCheck;
  }

  publish({
    ...cachedSnapshot,
    status: "checking",
    browserOnline: true,
    backendReachable: false,
    message: "Checking backend API.",
  });

  inFlightCheck = checkBackendHealth()
    .then((result) => {
      const nextSnapshot: PosConnectivitySnapshot = result.reachable
        ? {
            status: "online",
            browserOnline: true,
            backendReachable: true,
            message: result.message || "Online: API reachable.",
            lastCheckedAt: result.checkedAt,
            lastReachableAt: result.checkedAt,
          }
        : {
            ...cachedSnapshot,
            status: "backend_unreachable",
            browserOnline: true,
            backendReachable: false,
            message: result.message || "Server unavailable.",
            lastCheckedAt: result.checkedAt,
          };
      return publish(nextSnapshot);
    })
    .finally(() => {
      inFlightCheck = null;
    });

  return inFlightCheck;
}

export function usePosConnectivity() {
  const network = useNetworkStatus();
  const [snapshot, setSnapshot] = useState(cachedSnapshot);

  useEffect(() => {
    subscribers.add(setSnapshot);
    return () => {
      subscribers.delete(setSnapshot);
    };
  }, []);

  const refresh = useCallback(
    (options?: RefreshOptions) =>
      refreshConnectivity({
        browserOnline: network.isOnline,
        force: options?.force,
      }),
    [network.isOnline],
  );

  useEffect(() => {
    void refresh({ force: true });
  }, [network.isOnline, network.lastChangedAt, refresh]);

  useEffect(() => {
    if (!network.isOnline) {
      return undefined;
    }

    const intervalId = window.setInterval(() => {
      void refresh();
    }, HEALTH_STALE_MS);
    const handleFocus = () => {
      void refresh();
    };

    window.addEventListener("focus", handleFocus);
    return () => {
      window.clearInterval(intervalId);
      window.removeEventListener("focus", handleFocus);
    };
  }, [network.isOnline, refresh]);

  return useMemo(
    () => ({
      ...snapshot,
      isChecking: snapshot.status === "checking",
      isBackendReachable: snapshot.status === "online",
      isStale: isSnapshotStale(snapshot),
      shouldSaveOffline:
        snapshot.status === "browser_offline" ||
        snapshot.status === "backend_unreachable",
      refresh,
    }),
    [refresh, snapshot],
  );
}

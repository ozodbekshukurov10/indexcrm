"use client";

import { useCallback, useEffect, useState } from "react";

import { checkBackendHealth } from "@/services/api/health";

import { useNetworkStatus } from "./useNetworkStatus";

type BackendHealthState = {
  status: "checking" | "reachable" | "unreachable" | "offline";
  message: string;
  lastCheckedAt: string | null;
};

const CHECK_INTERVAL_MS = 30_000;

export function useBackendHealth() {
  const { isOnline } = useNetworkStatus();
  const [state, setState] = useState<BackendHealthState>({
    status: "checking",
    message: "Checking backend API.",
    lastCheckedAt: null,
  });

  const refresh = useCallback(async () => {
    if (!isOnline) {
      const offlineState: BackendHealthState = {
        status: "offline",
        message: "Browser is offline.",
        lastCheckedAt: new Date().toISOString(),
      };
      setState(offlineState);
      return offlineState;
    }

    setState((current) => ({
      ...current,
      status: current.status === "reachable" ? "reachable" : "checking",
      message:
        current.status === "reachable"
          ? current.message
          : "Checking backend API.",
    }));

    const result = await checkBackendHealth();
    const nextState: BackendHealthState = {
      status: result.reachable ? "reachable" : "unreachable",
      message: result.message,
      lastCheckedAt: result.checkedAt,
    };
    setState(nextState);
    return nextState;
  }, [isOnline]);

  useEffect(() => {
    void refresh();
    if (!isOnline) {
      return undefined;
    }

    const intervalId = window.setInterval(() => {
      void refresh();
    }, CHECK_INTERVAL_MS);

    window.addEventListener("focus", refresh);
    return () => {
      window.clearInterval(intervalId);
      window.removeEventListener("focus", refresh);
    };
  }, [isOnline, refresh]);

  return {
    ...state,
    isBackendReachable: state.status === "reachable",
    isChecking: state.status === "checking",
    refresh,
  };
}

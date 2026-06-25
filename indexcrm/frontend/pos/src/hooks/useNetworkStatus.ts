"use client";

import { useEffect, useState } from "react";

type NetworkStatus = {
  isOnline: boolean;
  lastChangedAt: string | null;
};

function readOnlineStatus() {
  if (typeof navigator === "undefined") {
    return true;
  }
  return navigator.onLine;
}

export function useNetworkStatus(): NetworkStatus {
  const [status, setStatus] = useState<NetworkStatus>({
    isOnline: true,
    lastChangedAt: null,
  });

  useEffect(() => {
    const updateStatus = () => {
      setStatus({
        isOnline: readOnlineStatus(),
        lastChangedAt: new Date().toISOString(),
      });
    };

    updateStatus();
    window.addEventListener("online", updateStatus);
    window.addEventListener("offline", updateStatus);
    return () => {
      window.removeEventListener("online", updateStatus);
      window.removeEventListener("offline", updateStatus);
    };
  }, []);

  return status;
}

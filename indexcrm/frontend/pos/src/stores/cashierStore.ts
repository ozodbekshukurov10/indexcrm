import { create } from "zustand";
import { persist } from "zustand/middleware";

import { clearStoredAuthToken, setStoredAuthToken } from "@/services/api/client";

type CashierState = {
  cashierName: string;
  cashierEmail: string;
  branchId: string;
  warehouseId: string;
  cashDeskId: string;
  activeShiftId: string;
  authToken: string;
  setSession: (session: {
    cashierName: string;
    cashierEmail: string;
    branchId: string;
    warehouseId: string;
    cashDeskId?: string;
    activeShiftId?: string;
    authToken?: string;
  }) => void;
  setAuthToken: (token: string) => void;
  clearAuthToken: () => void;
  setActiveShiftId: (shiftId: string) => void;
  clearSession: () => void;
};

const emptySession = {
  cashierName: "",
  cashierEmail: "",
  branchId: "",
  warehouseId: "",
  cashDeskId: "",
  activeShiftId: "",
  authToken: "",
};

function writeToken(token: string) {
  if (token) {
    setStoredAuthToken(token);
    return;
  }
  clearStoredAuthToken();
}

export const useCashierStore = create<CashierState>()(
  persist(
    (set) => ({
      ...emptySession,
      setSession: (session) => {
        if (session.authToken !== undefined) {
          writeToken(session.authToken);
        }
        set((state) => ({
          cashierName: session.cashierName,
          cashierEmail: session.cashierEmail,
          branchId: session.branchId,
          warehouseId: session.warehouseId,
          cashDeskId: session.cashDeskId ?? state.cashDeskId,
          activeShiftId: session.activeShiftId ?? state.activeShiftId,
          authToken: session.authToken ?? state.authToken,
        }));
      },
      setAuthToken: (token) =>
        set(() => {
          writeToken(token);
          return { authToken: token };
        }),
      clearAuthToken: () =>
        set(() => {
          writeToken("");
          return { authToken: "" };
        }),
      setActiveShiftId: (shiftId) => set({ activeShiftId: shiftId }),
      clearSession: () => {
        writeToken("");
        set(emptySession);
      },
    }),
    {
      name: "index-pos-cashier",
      onRehydrateStorage: () => (state) => {
        if (state?.authToken) {
          writeToken(state.authToken);
        }
      },
    },
  ),
);

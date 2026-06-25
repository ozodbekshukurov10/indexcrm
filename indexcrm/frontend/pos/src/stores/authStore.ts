import { create } from "zustand";

import { getCurrentUser } from "@/services/api/accounts";
import {
  clearStoredAuthToken,
  getStoredAuthToken,
  setStoredAuthToken,
} from "@/services/api/client";
import { UserAccount } from "@/services/api/types";
import { useCashierStore } from "@/stores/cashierStore";

export type AuthStatus = "checking" | "authenticated" | "unauthenticated";

type AuthState = {
  status: AuthStatus;
  token: string;
  user: UserAccount | null;
  initializeAuth: () => Promise<void>;
  signIn: (params: { token: string; user: UserAccount }) => void;
  signOut: () => void;
  setUser: (user: UserAccount | null) => void;
};

function getDisplayName(user: UserAccount) {
  return [user.first_name, user.last_name].filter(Boolean).join(" ") || user.email;
}

function hydrateCashierSession(user: UserAccount, token: string) {
  const cashierSession = useCashierStore.getState();
  cashierSession.setSession({
    cashierName: cashierSession.cashierName || getDisplayName(user),
    cashierEmail: cashierSession.cashierEmail || user.email,
    branchId: cashierSession.branchId || user.profile?.branch || "",
    warehouseId: cashierSession.warehouseId,
    cashDeskId: cashierSession.cashDeskId,
    activeShiftId: cashierSession.activeShiftId,
    authToken: token,
  });
}

export const useAuthStore = create<AuthState>()((set, get) => ({
  status: "checking",
  token: "",
  user: null,
  initializeAuth: async () => {
    if (get().status !== "checking") {
      return;
    }

    const token = getStoredAuthToken();
    if (!token) {
      set({ status: "unauthenticated", token: "", user: null });
      return;
    }

    try {
      const user = await getCurrentUser();
      hydrateCashierSession(user, token);
      set({ status: "authenticated", token, user });
    } catch {
      clearStoredAuthToken();
      useCashierStore.getState().clearAuthToken();
      set({ status: "unauthenticated", token: "", user: null });
    }
  },
  signIn: ({ token, user }) => {
    setStoredAuthToken(token);
    hydrateCashierSession(user, token);
    set({ status: "authenticated", token, user });
  },
  signOut: () => {
    clearStoredAuthToken();
    useCashierStore.getState().clearSession();
    set({ status: "unauthenticated", token: "", user: null });
  },
  setUser: (user) => set({ user }),
}));

import { apiRequest } from "./client";
import { CashierShift, PaginatedResponse } from "./types";

export function listCashierShifts(params: {
  cashier?: string;
  branch?: string;
  isOpen?: boolean;
}) {
  return apiRequest<PaginatedResponse<CashierShift>>(
    "/cashier-shifts/",
    {},
    {
      cashier: params.cashier,
      branch: params.branch,
      is_open:
        params.isOpen === undefined ? undefined : params.isOpen ? "true" : "false",
      ordering: "-opened_at",
    },
  );
}

export function openCashierShift(payload: {
  branch: string;
  opening_balance: string;
}) {
  return apiRequest<CashierShift>("/cashier-shifts/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getActiveCashierShift(params?: { branch?: string }) {
  return apiRequest<CashierShift | null>(
    "/cashier-shifts/active/",
    {},
    { branch: params?.branch },
  );
}

export function closeCashierShift(shiftId: string, closingBalance: string) {
  return apiRequest<CashierShift>(`/cashier-shifts/${shiftId}/close/`, {
    method: "POST",
    body: JSON.stringify({ closing_balance: closingBalance }),
  });
}

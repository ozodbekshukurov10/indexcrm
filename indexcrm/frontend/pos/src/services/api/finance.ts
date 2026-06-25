import { apiRequest } from "./client";
import { CashBox, Expense, PaginatedResponse } from "./types";

export type CashBoxPayload = {
  branch: string;
  name: string;
  is_active: boolean;
};

export function listCashBoxes() {
  return apiRequest<PaginatedResponse<CashBox>>(
    "/cashboxes/",
    {},
    { ordering: "branch__name,name" },
  );
}

export function createCashBox(payload: CashBoxPayload) {
  return apiRequest<CashBox>("/cashboxes/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateCashBox(cashboxId: string, payload: CashBoxPayload) {
  return apiRequest<CashBox>(`/cashboxes/${cashboxId}/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function listExpenses() {
  return apiRequest<PaginatedResponse<Expense>>(
    "/expenses/",
    {},
    { ordering: "-expense_date" },
  );
}

export function getCashflowSummary(params: { date_from?: string; date_to?: string }) {
  return apiRequest<Record<string, unknown>>(
    "/cash-transactions/cashflow-summary/",
    {},
    params,
  );
}

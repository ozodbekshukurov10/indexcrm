import { apiRequest } from "./client";
import { Branch, CashDesk, PaginatedResponse } from "./types";

export function listBranches(params: { store?: string; isActive?: boolean } = {}) {
  return apiRequest<PaginatedResponse<Branch>>(
    "/branches/",
    {},
    {
      store: params.store,
      is_active: params.isActive === false ? "false" : "true",
      ordering: "name",
    },
  );
}

export function listCashDesks(params: { branch?: string; isActive?: boolean } = {}) {
  return apiRequest<PaginatedResponse<CashDesk>>(
    "/cashdesks/",
    {},
    {
      branch: params.branch,
      is_active: params.isActive === false ? "false" : "true",
      ordering: "name",
    },
  );
}

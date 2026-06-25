import { apiRequest } from "./client";
import { PaginatedResponse, Stock, Warehouse } from "./types";

export type StockMovementPayload = {
  warehouse: string;
  product: string;
  movement_type: "IN" | "OUT" | "ADJUSTMENT";
  quantity: string;
  note?: string;
};

export function listWarehouses(params: {
  branch?: string;
  isActive?: boolean;
} = {}) {
  return apiRequest<PaginatedResponse<Warehouse>>(
    "/warehouses/",
    {},
    {
      branch: params.branch,
      is_active: params.isActive === false ? "false" : "true",
      ordering: "name",
    },
  );
}

export function listStocks(params: {
  search?: string;
  warehouse?: string;
  product?: string;
  lowStock?: boolean;
}) {
  const path = params.lowStock ? "/stocks/low-stock/" : "/stocks/";
  return apiRequest<PaginatedResponse<Stock>>(path, {}, {
    search: params.search,
    warehouse: params.warehouse,
    product: params.product,
  });
}

export function createStockMovement(payload: StockMovementPayload) {
  return apiRequest<Record<string, unknown>>("/stock-movements/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

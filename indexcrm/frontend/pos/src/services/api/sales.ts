import { apiRequest } from "./client";
import { PaginatedResponse, ReceiptData, Sale, SalePayload } from "./types";

export function listSales(params: {
  search?: string;
  status?: string;
  ordering?: string;
}) {
  return apiRequest<PaginatedResponse<Sale>>(
    "/sales/",
    {},
    {
      search: params.search,
      status: params.status,
      ordering: params.ordering ?? "-sale_date",
    },
  );
}

export function createSale(payload: SalePayload) {
  return apiRequest<Sale>("/sales/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function completeSale(saleId: string) {
  return apiRequest<Sale>(`/sales/${saleId}/complete/`, {
    method: "POST",
  });
}

export function getSaleReceipt(saleId: string) {
  return apiRequest<ReceiptData>(`/sales/${saleId}/receipt/`);
}

import { apiRequest } from "./client";
import { PaginatedResponse, Supplier } from "./types";

export type SupplierPayload = {
  company_name: string;
  full_name?: string;
  phone: string;
  extra_phone?: string;
  email?: string;
  address?: string;
  inn_or_tax_number?: string;
  notes?: string;
  is_active: boolean;
};

export function listSuppliers(search?: string) {
  return apiRequest<PaginatedResponse<Supplier>>(
    "/suppliers/",
    {},
    { search, ordering: "company_name" },
  );
}

export function createSupplier(payload: SupplierPayload) {
  return apiRequest<Supplier>("/suppliers/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateSupplier(supplierId: string, payload: SupplierPayload) {
  return apiRequest<Supplier>(`/suppliers/${supplierId}/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

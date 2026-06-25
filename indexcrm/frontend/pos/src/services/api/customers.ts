import { apiRequest } from "./client";
import { Customer, PaginatedResponse } from "./types";

export type CustomerPayload = {
  full_name: string;
  phone: string;
  extra_phone?: string;
  address?: string;
  notes?: string;
  is_active: boolean;
};

export function searchCustomers(search: string) {
  return apiRequest<PaginatedResponse<Customer>>(
    "/customers/",
    {},
    {
      search,
      is_active: "true",
      ordering: "full_name",
    },
  );
}

export function listCustomers(search?: string) {
  return apiRequest<PaginatedResponse<Customer>>(
    "/customers/",
    {},
    {
      search,
      ordering: "full_name",
    },
  );
}

export function createCustomer(payload: CustomerPayload) {
  return apiRequest<Customer>("/customers/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateCustomer(customerId: string, payload: CustomerPayload) {
  return apiRequest<Customer>(`/customers/${customerId}/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

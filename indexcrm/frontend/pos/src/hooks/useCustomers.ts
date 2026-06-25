import { useQuery } from "@tanstack/react-query";

import { searchCustomers } from "@/services/api/customers";

export function useCustomerSearch(search: string) {
  const normalized = search.trim();
  return useQuery({
    queryKey: ["customers", normalized],
    queryFn: () => searchCustomers(normalized),
    enabled: normalized.length >= 2,
  });
}

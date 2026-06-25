import { useQuery } from "@tanstack/react-query";

import { searchProducts } from "@/services/api/products";

export function useProductSearch(search: string) {
  const normalized = search.trim();
  return useQuery({
    queryKey: ["products", normalized],
    queryFn: () =>
      searchProducts({
        search: normalized.length > 0 ? normalized : undefined,
        isActive: true,
      }),
    enabled: normalized.length === 0 || normalized.length >= 2,
  });
}

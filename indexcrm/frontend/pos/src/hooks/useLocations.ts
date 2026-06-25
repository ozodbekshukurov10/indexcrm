import { useQuery } from "@tanstack/react-query";

import { listWarehouses } from "@/services/api/inventory";
import { listBranches, listCashDesks } from "@/services/api/stores";

export function useBranches() {
  return useQuery({
    queryKey: ["branches", "active"],
    queryFn: () => listBranches({ isActive: true }),
    staleTime: 60_000,
  });
}

export function useWarehouses(branchId?: string) {
  return useQuery({
    queryKey: ["warehouses", "active", branchId],
    queryFn: () => listWarehouses({ branch: branchId, isActive: true }),
    enabled: Boolean(branchId),
    staleTime: 60_000,
  });
}

export function useCashDesks(branchId?: string) {
  return useQuery({
    queryKey: ["cashdesks", "active", branchId],
    queryFn: () => listCashDesks({ branch: branchId, isActive: true }),
    enabled: Boolean(branchId),
    staleTime: 60_000,
  });
}

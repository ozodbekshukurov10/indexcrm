import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  closeCashierShift,
  getActiveCashierShift,
  listCashierShifts,
  openCashierShift,
} from "@/services/api/cashierShifts";

export function useOpenCashierShifts(branchId: string, cashierId?: string) {
  return useQuery({
    queryKey: ["cashier-shifts", branchId, cashierId, "open"],
    queryFn: () =>
      listCashierShifts({
        branch: branchId,
        cashier: cashierId,
        isOpen: true,
      }),
    enabled: Boolean(branchId),
  });
}

export function useOpenCashierShift() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: openCashierShift,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["cashier-shifts"] });
    },
  });
}

export function useActiveCashierShift(branchId?: string) {
  return useQuery({
    queryKey: ["cashier-shifts", "active", branchId],
    queryFn: () => getActiveCashierShift({ branch: branchId }),
    enabled: Boolean(branchId),
    staleTime: 30_000,
  });
}

export function useCloseCashierShift() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      shiftId,
      closingBalance,
    }: {
      shiftId: string;
      closingBalance: string;
    }) => closeCashierShift(shiftId, closingBalance),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["cashier-shifts"] });
    },
  });
}

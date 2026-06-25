import { useMutation, useQuery } from "@tanstack/react-query";

import { completeSale, createSale, getSaleReceipt } from "@/services/api/sales";
import { SalePayload } from "@/services/api/types";

export function useCompleteSaleFlow() {
  return useMutation({
    mutationFn: async (payload: SalePayload) => {
      const draft = await createSale(payload);
      return completeSale(draft.id);
    },
  });
}

export function useReceipt(saleId?: string) {
  return useQuery({
    queryKey: ["sale-receipt", saleId],
    queryFn: () => getSaleReceipt(saleId as string),
    enabled: Boolean(saleId),
  });
}

import { create } from "zustand";
import { persist } from "zustand/middleware";

import { Customer } from "@/services/api/types";

type CustomerState = {
  selectedCustomer: Customer | null;
  setSelectedCustomer: (customer: Customer | null) => void;
};

export const useCustomerStore = create<CustomerState>()(
  persist(
    (set) => ({
      selectedCustomer: null,
      setSelectedCustomer: (customer) => set({ selectedCustomer: customer }),
    }),
    {
      name: "index-pos-customer",
    },
  ),
);

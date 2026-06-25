"use client";

import { UserRound, X } from "lucide-react";
import { useState } from "react";

import { useCustomerSearch } from "@/hooks/useCustomers";
import { Customer } from "@/services/api/types";

import { IconButton } from "./IconButton";

type CustomerPickerProps = {
  selectedCustomer: Customer | null;
  onSelectCustomer: (customer: Customer | null) => void;
};

export function CustomerPicker({
  selectedCustomer,
  onSelectCustomer,
}: CustomerPickerProps) {
  const [search, setSearch] = useState("");
  const customersQuery = useCustomerSearch(search);
  const customers = customersQuery.data?.results ?? [];

  return (
    <section className="glass border-b border-white/20 p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-slate-500">
          <UserRound aria-hidden="true" className="h-4 w-4" />
          Mijoz
        </div>
        {selectedCustomer ? (
          <IconButton
            icon={<X aria-hidden="true" className="h-4 w-4" />}
            label="Mijozsiz"
            onClick={() => onSelectCustomer(null)}
            className="min-h-9 px-2 py-1 text-xs"
          />
        ) : null}
      </div>
      {selectedCustomer ? (
        <div className="glass-card rounded-xl border-emerald-200/60 p-3">
          <div className="font-bold text-emerald-900">
            {selectedCustomer.full_name}
          </div>
          <div className="mt-0.5 text-sm font-semibold text-emerald-600">
            {selectedCustomer.phone || "Mijozsiz"}
          </div>
        </div>
      ) : (
        <>
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Mijoz qidirish"
            className="glass-input h-11 w-full rounded-xl px-3 font-semibold transition focus:border-primary-400 focus:outline-none focus:ring-4 focus:ring-primary-100"
          />
          {customers.length > 0 ? (
            <div className="glass mt-2 max-h-36 overflow-y-auto rounded-xl shadow-glass">
              {customers.map((customer) => (
                <button
                  key={customer.id}
                  onClick={() => {
                    onSelectCustomer(customer);
                    setSearch("");
                  }}
                  className="block w-full border-b border-white/20 px-3 py-2 text-left last:border-0 transition hover:bg-white/30"
                >
                  <span className="block font-bold text-slate-800">{customer.full_name}</span>
                  <span className="text-sm text-slate-400">
                    {customer.phone || "-"}
                  </span>
                </button>
              ))}
            </div>
          ) : null}
        </>
      )}
    </section>
  );
}

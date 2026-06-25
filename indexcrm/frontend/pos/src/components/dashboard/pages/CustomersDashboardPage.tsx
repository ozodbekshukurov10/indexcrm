"use client";

import { Edit3, Save, UserPlus, UsersRound, WalletCards, X } from "lucide-react";
import { FormEvent, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { DataTable } from "@/components/dashboard/DataTable";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { LoadingState } from "@/components/dashboard/LoadingState";
import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { StatCard } from "@/components/dashboard/StatCard";
import { IconButton } from "@/components/pos/IconButton";
import { useCustomersDashboard } from "@/hooks/useDashboardData";
import { formatApiError } from "@/lib/apiErrors";
import { pickNumber, pickText } from "@/lib/dashboard";
import { formatMoney } from "@/lib/format";
import {
  createCustomer,
  CustomerPayload,
  updateCustomer,
} from "@/services/api/customers";
import { Customer } from "@/services/api/types";

type CustomerFormState = CustomerPayload & { id?: string };

const emptyCustomer: CustomerFormState = {
  full_name: "",
  phone: "",
  extra_phone: "",
  address: "",
  notes: "",
  is_active: true,
};

function formFromCustomer(customer: Customer): CustomerFormState {
  return {
    id: customer.id,
    full_name: customer.full_name,
    phone: customer.phone,
    extra_phone: customer.extra_phone,
    address: customer.address,
    notes: customer.notes,
    is_active: customer.is_active,
  };
}

export function CustomersDashboardPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [form, setForm] = useState<CustomerFormState | null>(null);
  const [formMessage, setFormMessage] = useState("");
  const customersQuery = useCustomersDashboard(search);
  const customers = customersQuery.data?.customers.results ?? [];
  const debts = customersQuery.data?.debts ?? [];

  const saveCustomer = useMutation({
    mutationFn: (nextForm: CustomerFormState) => {
      const payload: CustomerPayload = {
        full_name: nextForm.full_name.trim(),
        phone: nextForm.phone.trim(),
        extra_phone: nextForm.extra_phone?.trim(),
        address: nextForm.address?.trim(),
        notes: nextForm.notes?.trim(),
        is_active: nextForm.is_active,
      };
      return nextForm.id
        ? updateCustomer(nextForm.id, payload)
        : createCustomer(payload);
    },
    onSuccess: () => {
      setForm(null);
      setFormMessage("Mijoz saqlandi.");
      void queryClient.invalidateQueries({ queryKey: ["dashboard-customers"] });
      void queryClient.invalidateQueries({ queryKey: ["customers"] });
    },
    onError: (error) => {
      setFormMessage(formatApiError(error, "Mijozni saqlab bo'lmadi."));
    },
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormMessage("");
    if (!form) {
      return;
    }
    if (!form.full_name.trim() || !form.phone.trim()) {
      setFormMessage("Mijoz nomi va telefon majburiy.");
      return;
    }
    saveCustomer.mutate(form);
  }

  if (customersQuery.isLoading) {
    return (
      <LoadingState
        label="Mijozlar"
        description="Mijoz yozuvlari va qarz hisoblari yuklanmoqda."
      />
    );
  }

  if (customersQuery.isError) {
    return (
      <ErrorState
        title="Mijozlarni yuklab bo'lmadi"
        error={customersQuery.error}
        onRetry={() => void customersQuery.refetch()}
      />
    );
  }

  return (
    <div className="grid gap-5">
      <SectionHeader
        title="Mijozlar"
        description="Mijozlar yaratish, kontaktlarni yangilash va qarzni kuzatish."
        actions={
          <div className="flex flex-col gap-2 sm:flex-row">
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              aria-label="Mijozlarni qidirish"
              placeholder="Mijozlarni qidirish"
              className="h-11 rounded border border-slate-300 px-3 font-semibold shadow-panel"
            />
            <IconButton
              type="button"
              icon={<UserPlus aria-hidden="true" className="h-4 w-4" />}
              label="Yangi mijoz"
              tone="primary"
              onClick={() => {
                setForm({ ...emptyCustomer });
                setFormMessage("");
              }}
            />
          </div>
        }
      />
      <div className="grid gap-3 md:grid-cols-2">
        <StatCard
          title="Mijozlar"
          value={String(customersQuery.data?.customers.count ?? customers.length)}
          icon={UsersRound}
          tone="blue"
        />
        <StatCard
          title="Qarz hisoblari"
          value={String(debts.length)}
          icon={WalletCards}
          tone="amber"
        />
      </div>
      {form ? (
        <form
          onSubmit={handleSubmit}
          className="rounded border border-slate-200 bg-white p-4 shadow-panel"
        >
          <div className="mb-3 flex items-center justify-between gap-3">
            <h2 className="text-base font-black text-slate-950">
              {form.id ? "Mijozni tahrirlash" : "Mijoz yaratish"}
            </h2>
            <IconButton
              type="button"
              icon={<X aria-hidden="true" className="h-4 w-4" />}
              label="Bekor qilish"
              onClick={() => setForm(null)}
            />
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            <label className="grid gap-1 text-sm font-bold text-slate-700">
              Ism
              <input
                value={form.full_name}
                onChange={(event) =>
                  setForm({ ...form, full_name: event.target.value })
                }
                className="h-11 rounded border border-slate-300 px-3 shadow-panel"
              />
            </label>
            <label className="grid gap-1 text-sm font-bold text-slate-700">
              Telefon
              <input
                value={form.phone}
                onChange={(event) => setForm({ ...form, phone: event.target.value })}
                inputMode="tel"
                autoComplete="tel"
                className="h-11 rounded border border-slate-300 px-3 shadow-panel"
              />
            </label>
            <label className="grid gap-1 text-sm font-bold text-slate-700">
              Qo'shimcha telefon
              <input
                value={form.extra_phone}
                onChange={(event) =>
                  setForm({ ...form, extra_phone: event.target.value })
                }
                inputMode="tel"
                autoComplete="tel"
                className="h-11 rounded border border-slate-300 px-3 shadow-panel"
              />
            </label>
            <label className="grid gap-1 text-sm font-bold text-slate-700 md:col-span-2">
              Manzil
              <input
                value={form.address}
                onChange={(event) =>
                  setForm({ ...form, address: event.target.value })
                }
                className="h-11 rounded border border-slate-300 px-3 shadow-panel"
              />
            </label>
            <label className="flex items-center gap-2 self-end text-sm font-bold text-slate-700">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(event) =>
                  setForm({ ...form, is_active: event.target.checked })
                }
                className="h-5 w-5"
              />
              Faol
            </label>
          </div>
          {formMessage ? (
            <div className="mt-3 rounded border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-bold text-amber-900">
              {formMessage}
            </div>
          ) : null}
          <IconButton
            type="submit"
            icon={<Save aria-hidden="true" className="h-4 w-4" />}
            label={saveCustomer.isPending ? "Mijoz saqlanmoqda" : "Mijozni saqlash"}
            tone="success"
            disabled={saveCustomer.isPending}
            className="mt-3"
          />
        </form>
      ) : formMessage ? (
        <div className="rounded border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-bold text-emerald-900">
          {formMessage}
        </div>
      ) : null}
      <DataTable
        title="Mijozlar ro'yxati"
        rows={customers}
        rowKey={(row) => row.id}
        emptyTitle={search ? "Mos mijoz topilmadi" : "Mijoz topilmadi"}
        emptyDescription={
          search
            ? "Boshqa ism yoki telefon raqami bilan urinib ko'ring."
            : "Mijoz yozuvlari yaratilgandan keyin shu yerda chiqadi."
        }
        columns={[
          { key: "name", header: "Ism", render: (row) => row.full_name },
          { key: "phone", header: "Telefon", render: (row) => row.phone || "-" },
          {
            key: "balance",
            header: "Qarz",
            align: "right",
            render: (row) => formatMoney(row.balance),
          },
          {
            key: "status",
            header: "Holat",
            render: (row) => (row.is_active ? "Faol" : "Faol emas"),
          },
          {
            key: "actions",
            header: "Amallar",
            align: "right",
            render: (row) => (
              <IconButton
                type="button"
                icon={<Edit3 aria-hidden="true" className="h-4 w-4" />}
                label="Mijozni tahrirlash"
                hideLabel
                onClick={() => {
                  setForm(formFromCustomer(row));
                  setFormMessage("");
                }}
              />
            ),
          },
        ]}
      />
      <DataTable
        title="Mijoz qarzlari"
        rows={debts}
        rowKey={(row, index) =>
          pickText(row, ["id", "customer_id", "phone", "full_name"]) || index
        }
        emptyTitle="Mijoz qarzlari yo'q"
        emptyDescription="Balans bo'lsa mijoz qarz hisoblari shu yerda chiqadi."
        columns={[
          { key: "name", header: "Ism", render: (row) => pickText(row, ["full_name"]) },
          { key: "phone", header: "Telefon", render: (row) => pickText(row, ["phone"]) },
          {
            key: "balance",
            header: "Qarz",
            align: "right",
            render: (row) => formatMoney(pickNumber(row, ["balance"])),
          },
        ]}
      />
    </div>
  );
}

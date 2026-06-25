"use client";

import { Edit3, Save, Truck, TruckIcon, WalletCards, X } from "lucide-react";
import { FormEvent, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { DataTable } from "@/components/dashboard/DataTable";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { LoadingState } from "@/components/dashboard/LoadingState";
import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { StatCard } from "@/components/dashboard/StatCard";
import { IconButton } from "@/components/pos/IconButton";
import { useSuppliersDashboard } from "@/hooks/useDashboardData";
import { formatApiError } from "@/lib/apiErrors";
import { pickNumber, pickText } from "@/lib/dashboard";
import { formatMoney } from "@/lib/format";
import {
  createSupplier,
  SupplierPayload,
  updateSupplier,
} from "@/services/api/suppliers";
import { Supplier } from "@/services/api/types";

type SupplierFormState = SupplierPayload & { id?: string };

const emptySupplier: SupplierFormState = {
  company_name: "",
  full_name: "",
  phone: "",
  extra_phone: "",
  email: "",
  address: "",
  inn_or_tax_number: "",
  notes: "",
  is_active: true,
};

function formFromSupplier(supplier: Supplier): SupplierFormState {
  return {
    id: supplier.id,
    company_name: supplier.company_name,
    full_name: supplier.full_name,
    phone: supplier.phone,
    extra_phone: supplier.extra_phone,
    email: supplier.email,
    address: supplier.address,
    inn_or_tax_number: supplier.inn_or_tax_number,
    notes: supplier.notes,
    is_active: supplier.is_active,
  };
}

export function SuppliersDashboardPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [form, setForm] = useState<SupplierFormState | null>(null);
  const [formMessage, setFormMessage] = useState("");
  const suppliersQuery = useSuppliersDashboard(search);
  const suppliers = suppliersQuery.data?.suppliers.results ?? [];
  const debts = suppliersQuery.data?.debts ?? [];

  const saveSupplier = useMutation({
    mutationFn: (nextForm: SupplierFormState) => {
      const payload: SupplierPayload = {
        company_name: nextForm.company_name.trim(),
        full_name: nextForm.full_name?.trim(),
        phone: nextForm.phone.trim(),
        extra_phone: nextForm.extra_phone?.trim(),
        email: nextForm.email?.trim(),
        address: nextForm.address?.trim(),
        inn_or_tax_number: nextForm.inn_or_tax_number?.trim(),
        notes: nextForm.notes?.trim(),
        is_active: nextForm.is_active,
      };
      return nextForm.id
        ? updateSupplier(nextForm.id, payload)
        : createSupplier(payload);
    },
    onSuccess: () => {
      setForm(null);
      setFormMessage("Yetkazib beruvchi saqlandi.");
      void queryClient.invalidateQueries({ queryKey: ["dashboard-suppliers"] });
    },
    onError: (error) => {
      setFormMessage(formatApiError(error, "Yetkazib beruvchini saqlab bo'lmadi."));
    },
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormMessage("");
    if (!form) {
      return;
    }
    if (!form.company_name.trim() || !form.phone.trim()) {
      setFormMessage("Kompaniya nomi va telefon majburiy.");
      return;
    }
    saveSupplier.mutate(form);
  }

  if (suppliersQuery.isLoading) {
    return (
      <LoadingState
        label="Yetkazib beruvchilar"
        description="Yetkazib beruvchilar va to'lov qarzlari yuklanmoqda."
      />
    );
  }

  if (suppliersQuery.isError) {
    return (
      <ErrorState
        title="Yetkazib beruvchilarni yuklab bo'lmadi"
        error={suppliersQuery.error}
        onRetry={() => void suppliersQuery.refetch()}
      />
    );
  }

  return (
    <div className="grid gap-5">
      <SectionHeader
        title="Yetkazib beruvchilar"
        description="Yetkazib beruvchilar yaratish, kontaktlarni yangilash va qarzlarni kuzatish."
        actions={
          <div className="flex flex-col gap-2 sm:flex-row">
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              aria-label="Yetkazib beruvchilarni qidirish"
              placeholder="Yetkazib beruvchilarni qidirish"
              className="h-11 rounded border border-slate-300 px-3 font-semibold shadow-panel"
            />
            <IconButton
              type="button"
              icon={<TruckIcon aria-hidden="true" className="h-4 w-4" />}
              label="Yangi yetkazuvchi"
              tone="primary"
              onClick={() => {
                setForm({ ...emptySupplier });
                setFormMessage("");
              }}
            />
          </div>
        }
      />
      <div className="grid gap-3 md:grid-cols-2">
        <StatCard
          title="Yetkazuvchilar"
          value={String(suppliersQuery.data?.suppliers.count ?? suppliers.length)}
          icon={Truck}
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
              {form.id ? "Yetkazuvchini tahrirlash" : "Yetkazuvchi yaratish"}
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
              Kompaniya
              <input
                value={form.company_name}
                onChange={(event) =>
                  setForm({ ...form, company_name: event.target.value })
                }
                className="h-11 rounded border border-slate-300 px-3 shadow-panel"
              />
            </label>
            <label className="grid gap-1 text-sm font-bold text-slate-700">
              Kontakt
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
              Email
              <input
                value={form.email}
                onChange={(event) => setForm({ ...form, email: event.target.value })}
                type="email"
                autoComplete="email"
                className="h-11 rounded border border-slate-300 px-3 shadow-panel"
              />
            </label>
            <label className="grid gap-1 text-sm font-bold text-slate-700">
              Soliq raqami
              <input
                value={form.inn_or_tax_number}
                onChange={(event) =>
                  setForm({ ...form, inn_or_tax_number: event.target.value })
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
            label={saveSupplier.isPending ? "Yetkazuvchi saqlanmoqda" : "Yetkazuvchini saqlash"}
            tone="success"
            disabled={saveSupplier.isPending}
            className="mt-3"
          />
        </form>
      ) : formMessage ? (
        <div className="rounded border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-bold text-emerald-900">
          {formMessage}
        </div>
      ) : null}
      <DataTable
        title="Yetkazuvchilar ro'yxati"
        rows={suppliers}
        rowKey={(row) => row.id}
        emptyTitle={search ? "Mos yetkazuvchi topilmadi" : "Yetkazuvchi topilmadi"}
        emptyDescription={
          search
            ? "Boshqa kompaniya, kontakt yoki telefon raqami bilan urinib ko'ring."
            : "Yetkazuvchi yozuvlari yaratilgandan keyin shu yerda chiqadi."
        }
        columns={[
          { key: "company", header: "Kompaniya", render: (row) => row.company_name },
          { key: "contact", header: "Kontakt", render: (row) => row.full_name || "-" },
          { key: "phone", header: "Telefon", render: (row) => row.phone || "-" },
          {
            key: "balance",
            header: "Qarz",
            align: "right",
            render: (row) => formatMoney(row.balance),
          },
          {
            key: "actions",
            header: "Amallar",
            align: "right",
            render: (row) => (
              <IconButton
                type="button"
                icon={<Edit3 aria-hidden="true" className="h-4 w-4" />}
                label="Yetkazuvchini tahrirlash"
                hideLabel
                onClick={() => {
                  setForm(formFromSupplier(row));
                  setFormMessage("");
                }}
              />
            ),
          },
        ]}
      />
      <DataTable
        title="Yetkazuvchi qarzlari"
        rows={debts}
        rowKey={(row, index) =>
          pickText(row, ["id", "supplier_id", "phone", "company_name"]) || index
        }
        emptyTitle="Yetkazuvchi qarzlari yo'q"
        emptyDescription="Balans bo'lsa yetkazuvchi qarz hisoblari shu yerda chiqadi."
        columns={[
          {
            key: "company",
            header: "Kompaniya",
            render: (row) => pickText(row, ["company_name"]),
          },
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

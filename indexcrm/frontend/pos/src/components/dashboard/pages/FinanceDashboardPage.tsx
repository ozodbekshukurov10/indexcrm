"use client";

import {
  CircleDollarSign,
  CreditCard,
  Edit3,
  Landmark,
  Plus,
  Save,
  X,
} from "lucide-react";
import { FormEvent, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { DataTable } from "@/components/dashboard/DataTable";
import { DateFilter } from "@/components/dashboard/DateFilter";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { LoadingState } from "@/components/dashboard/LoadingState";
import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { StatCard } from "@/components/dashboard/StatCard";
import { IconButton } from "@/components/pos/IconButton";
import { useFinanceDashboard } from "@/hooks/useDashboardData";
import { useBranches } from "@/hooks/useLocations";
import { formatApiError } from "@/lib/apiErrors";
import { monthStartIsoDate, pickNumber, todayIsoDate } from "@/lib/dashboard";
import { formatMoney } from "@/lib/format";
import {
  CashBoxPayload,
  createCashBox,
  updateCashBox,
} from "@/services/api/finance";
import { CashBox } from "@/services/api/types";

type CashBoxFormState = CashBoxPayload & { id?: string };

function formFromCashBox(cashbox: CashBox): CashBoxFormState {
  return {
    id: cashbox.id,
    branch: cashbox.branch,
    name: cashbox.name,
    is_active: cashbox.is_active,
  };
}

export function FinanceDashboardPage() {
  const queryClient = useQueryClient();
  const [range, setRange] = useState({
    dateFrom: monthStartIsoDate(),
    dateTo: todayIsoDate(),
  });
  const [form, setForm] = useState<CashBoxFormState | null>(null);
  const [formMessage, setFormMessage] = useState("");
  const financeQuery = useFinanceDashboard(range.dateFrom, range.dateTo);
  const branchesQuery = useBranches();
  const branches = branchesQuery.data?.results ?? [];
  const branchesLoading = branchesQuery.isLoading || branchesQuery.isFetching;

  const saveCashBox = useMutation({
    mutationFn: (nextForm: CashBoxFormState) =>
      nextForm.id
        ? updateCashBox(nextForm.id, nextForm)
        : createCashBox(nextForm),
    onSuccess: () => {
      setForm(null);
      setFormMessage("Kassa saqlandi.");
      void queryClient.invalidateQueries({ queryKey: ["dashboard-finance"] });
    },
    onError: (error) => {
      setFormMessage(formatApiError(error, "Kassani saqlab bo'lmadi."));
    },
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormMessage("");
    if (!form) {
      return;
    }
    if (!form.branch || !form.name.trim()) {
      setFormMessage("Filial va kassa nomi majburiy.");
      return;
    }
    saveCashBox.mutate({ ...form, name: form.name.trim() });
  }

  if (financeQuery.isLoading) {
    return (
      <LoadingState
        label="Moliya"
        description="Foyda, xarajatlar va kassa balanslari yuklanmoqda."
      />
    );
  }

  if (financeQuery.isError) {
    return (
      <ErrorState
        title="Moliya panelini yuklab bo'lmadi"
        error={financeQuery.error}
        onRetry={() => void financeQuery.refetch()}
      />
    );
  }

  const profit = financeQuery.data?.profit ?? {};
  const cashboxes = financeQuery.data?.cashboxes.results ?? [];
  const expenses = financeQuery.data?.expenses.results ?? [];

  return (
    <div className="grid gap-5">
      <SectionHeader
        title="Moliya"
        description="Foyda, xarajatlar, kassalar va so'nggi pul oqimi holati."
        actions={
          <div className="flex flex-col gap-2 sm:flex-row">
            <DateFilter {...range} onChange={setRange} />
            <IconButton
              type="button"
              icon={<Plus aria-hidden="true" className="h-4 w-4" />}
              label="Yangi kassa"
              tone="primary"
              onClick={() => {
                if (branchesLoading) {
                  setFormMessage("Filiallar hali yuklanmoqda. Birozdan keyin urinib ko'ring.");
                  return;
                }
                if (branchesQuery.isError) {
                  setFormMessage("Filiallarni yuklab bo'lmadi. Backendni ishga tushirib, sahifani qayta sinang.");
                  return;
                }
                if (branches.length === 0) {
                  setFormMessage("Kassa qo'shishdan oldin filial yarating yoki seed qiling.");
                  return;
                }
                setForm({
                  branch: branches[0]?.id ?? "",
                  name: "",
                  is_active: true,
                });
                setFormMessage("");
              }}
            />
          </div>
        }
      />
      <div className="grid gap-3 md:grid-cols-3">
        <StatCard
          title="Foyda"
          value={formatMoney(pickNumber(profit, ["profit"]))}
          icon={CircleDollarSign}
          tone="green"
        />
        <StatCard
          title="Xarajatlar"
          value={formatMoney(pickNumber(profit, ["total_expenses"]))}
          icon={CreditCard}
          tone="amber"
        />
        <StatCard
          title="Kassalar"
          value={String(cashboxes.length)}
          icon={Landmark}
          tone="blue"
        />
      </div>
      {form ? (
        <form
          onSubmit={handleSubmit}
          className="rounded border border-slate-200 bg-white p-4 shadow-panel"
        >
          <div className="mb-3 flex items-center justify-between gap-3">
            <h2 className="text-base font-black text-slate-950">
              {form.id ? "Kassani tahrirlash" : "Kassa yaratish"}
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
              Filial
              <select
                value={form.branch}
                onChange={(event) => setForm({ ...form, branch: event.target.value })}
                className="h-11 rounded border border-slate-300 bg-white px-3 shadow-panel"
              >
                <option value="">
                  {branchesQuery.isFetching ? "Filiallar yuklanmoqda" : "Filialni tanlang"}
                </option>
                {branches.map((branch) => (
                  <option key={branch.id} value={branch.id}>
                    {branch.store_name ? `${branch.store_name} - ${branch.name}` : branch.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="grid gap-1 text-sm font-bold text-slate-700">
              Nomi
              <input
                value={form.name}
                onChange={(event) => setForm({ ...form, name: event.target.value })}
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
          <p className="mt-2 text-xs font-semibold text-slate-500">
            Kassa balansi savdo, xarajat, kirim va kassa tuzatish operatsiyalari orqali o'zgaradi.
          </p>
          {formMessage ? (
            <div className="mt-3 rounded border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-bold text-amber-900">
              {formMessage}
            </div>
          ) : null}
          <IconButton
            type="submit"
            icon={<Save aria-hidden="true" className="h-4 w-4" />}
            label={saveCashBox.isPending ? "Kassa saqlanmoqda" : "Kassani saqlash"}
            tone="success"
            disabled={saveCashBox.isPending}
            className="mt-3"
          />
        </form>
      ) : formMessage ? (
        <div className="rounded border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-bold text-emerald-900">
          {formMessage}
        </div>
      ) : null}
      <DataTable
        title="Kassalar"
        rows={cashboxes}
        rowKey={(row) => row.id}
        emptyTitle="Kassa topilmadi"
        emptyDescription="Moliya sozlamasidan keyin kassalar shu yerda chiqadi."
        columns={[
          { key: "name", header: "Nomi", render: (row) => row.name },
          { key: "branch", header: "Filial", render: (row) => row.branch_name },
          {
            key: "balance",
            header: "Balans",
            align: "right",
            render: (row) => formatMoney(row.current_balance),
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
                label="Kassani tahrirlash"
                hideLabel
                onClick={() => {
                  setForm(formFromCashBox(row));
                  setFormMessage("");
                }}
              />
            ),
          },
        ]}
      />
      <DataTable
        title="So'nggi xarajatlar"
        rows={expenses}
        rowKey={(row) => row.id}
        emptyTitle="Xarajat topilmadi"
        emptyDescription="Bu davr xarajatlari shu yerda chiqadi."
        columns={[
          { key: "category", header: "Kategoriya", render: (row) => row.category_name },
          { key: "cashbox", header: "Kassa", render: (row) => row.cashbox_name },
          {
            key: "amount",
            header: "Summa",
            align: "right",
            render: (row) => formatMoney(row.amount),
          },
        ]}
      />
    </div>
  );
}

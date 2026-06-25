"use client";

import { AlertTriangle, Boxes, Save, SlidersHorizontal, X } from "lucide-react";
import { FormEvent, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { DataTable } from "@/components/dashboard/DataTable";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { LoadingState } from "@/components/dashboard/LoadingState";
import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { StatCard } from "@/components/dashboard/StatCard";
import { IconButton } from "@/components/pos/IconButton";
import { useInventoryDashboard } from "@/hooks/useDashboardData";
import { formatApiError } from "@/lib/apiErrors";
import { pickNumber } from "@/lib/dashboard";
import { createStockMovement } from "@/services/api/inventory";
import { Stock } from "@/services/api/types";

type AdjustmentForm = {
  stock: Stock;
  movementType: "IN" | "OUT";
  quantity: string;
  note: string;
};

export function InventoryDashboardPage() {
  const queryClient = useQueryClient();
  const [adjustment, setAdjustment] = useState<AdjustmentForm | null>(null);
  const [formMessage, setFormMessage] = useState("");
  const inventoryQuery = useInventoryDashboard();

  const saveAdjustment = useMutation({
    mutationFn: (form: AdjustmentForm) =>
      createStockMovement({
        warehouse: form.stock.warehouse,
        product: form.stock.product,
        movement_type: form.movementType,
        quantity: form.quantity,
        note: form.note,
    }),
    onSuccess: () => {
      setAdjustment(null);
      setFormMessage("Qoldiq harakati saqlandi.");
      void queryClient.invalidateQueries({ queryKey: ["dashboard-inventory"] });
    },
    onError: (error) => {
      setFormMessage(formatApiError(error, "Qoldiq tuzatishini saqlab bo'lmadi."));
    },
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormMessage("");
    if (!adjustment) {
      return;
    }
    if (!adjustment.quantity || Number(adjustment.quantity) <= 0) {
      setFormMessage("Miqdor noldan katta bo'lishi kerak.");
      return;
    }
    if (!adjustment.note.trim()) {
      setFormMessage("Qoldiq harakati uchun qisqa sabab yoki izoh kiriting.");
      return;
    }
    saveAdjustment.mutate(adjustment);
  }

  if (inventoryQuery.isLoading) {
    return (
      <LoadingState
        label="Ombor"
        description="Qoldiq yozuvlari va kam qoldiq ogohlantirishlari yuklanmoqda."
      />
    );
  }

  if (inventoryQuery.isError) {
    return (
      <ErrorState
        title="Ombor panelini yuklab bo'lmadi"
        error={inventoryQuery.error}
        onRetry={() => void inventoryQuery.refetch()}
      />
    );
  }

  const stocks = inventoryQuery.data?.stocks.results ?? [];
  const report = inventoryQuery.data?.report ?? {};
  const lowStock = inventoryQuery.data?.lowStock ?? {};

  return (
    <div className="grid gap-5">
      <SectionHeader
        title="Ombor"
        description="Ombor qoldig'i va xavfsiz qoldiq harakatlari."
      />
      <div className="grid gap-3 md:grid-cols-3">
        <StatCard
          title="Ombordagi mahsulotlar"
          value={String(pickNumber(report, ["product_count"]))}
          icon={Boxes}
          tone="blue"
        />
        <StatCard
          title="Qoldiq yozuvlari"
          value={String(pickNumber(report, ["stock_record_count"]))}
          icon={Boxes}
        />
        <StatCard
          title="Kam qoldiq"
          value={String(pickNumber(lowStock, ["low_stock_count"]))}
          icon={AlertTriangle}
          tone="rose"
        />
      </div>
      {adjustment ? (
        <form
          onSubmit={handleSubmit}
          className="rounded border border-slate-200 bg-white p-4 shadow-panel"
        >
          <div className="mb-3 flex items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-black text-slate-950">
                Qoldiqni tuzatish
              </h2>
              <p className="text-sm font-semibold text-slate-500">
                {adjustment.stock.product_name} - {adjustment.stock.warehouse_name}.
                Joriy miqdor: {adjustment.stock.quantity}
              </p>
            </div>
            <IconButton
              type="button"
              icon={<X aria-hidden="true" className="h-4 w-4" />}
              label="Bekor qilish"
              onClick={() => setAdjustment(null)}
            />
          </div>
          <div className="grid gap-3 md:grid-cols-4">
            <label className="grid gap-1 text-sm font-bold text-slate-700">
              Harakat
              <select
                value={adjustment.movementType}
                onChange={(event) =>
                  setAdjustment({
                    ...adjustment,
                    movementType: event.target.value as "IN" | "OUT",
                  })
                }
                className="h-11 rounded border border-slate-300 bg-white px-3 shadow-panel"
              >
                <option value="IN">Qoldiqni oshirish</option>
                <option value="OUT">Qoldiqni kamaytirish</option>
              </select>
            </label>
            <label className="grid gap-1 text-sm font-bold text-slate-700">
              Miqdor
              <input
                value={adjustment.quantity}
                onChange={(event) =>
                  setAdjustment({ ...adjustment, quantity: event.target.value })
                }
                inputMode="decimal"
                className="h-11 rounded border border-slate-300 px-3 shadow-panel"
              />
            </label>
            <label className="grid gap-1 text-sm font-bold text-slate-700 md:col-span-2">
              Sabab
              <input
                value={adjustment.note}
                onChange={(event) =>
                  setAdjustment({ ...adjustment, note: event.target.value })
                }
                placeholder="Inventarizatsiya tuzatishi"
                className="h-11 rounded border border-slate-300 px-3 shadow-panel"
              />
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
            label={saveAdjustment.isPending ? "Harakat saqlanmoqda" : "Harakatni saqlash"}
            tone="success"
            disabled={saveAdjustment.isPending}
            className="mt-3"
          />
        </form>
      ) : formMessage ? (
        <div className="rounded border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-bold text-emerald-900">
          {formMessage}
        </div>
      ) : null}
      <DataTable
        title="Qoldiq ro'yxati"
        rows={stocks}
        rowKey={(row) => row.id}
        emptyTitle="Qoldiq yozuvlari yo'q"
        emptyDescription="Mahsulotlar omborga qo'shilgandan keyin qoldiq yozuvlari chiqadi."
        columns={[
          { key: "product", header: "Mahsulot", render: (row) => row.product_name },
          { key: "sku", header: "SKU", render: (row) => row.product_sku },
          {
            key: "warehouse",
            header: "Ombor",
            render: (row) => row.warehouse_name,
          },
          {
            key: "quantity",
            header: "Miqdor",
            align: "right",
            render: (row) => row.quantity,
          },
          {
            key: "low",
            header: "Kam",
            align: "center",
            render: (row) => (row.is_low_stock ? "Ha" : "Yo'q"),
          },
          {
            key: "actions",
            header: "Amallar",
            align: "right",
            render: (row) => (
              <IconButton
                type="button"
                icon={<SlidersHorizontal aria-hidden="true" className="h-4 w-4" />}
                label="Qoldiqni tuzatish"
                hideLabel
                onClick={() => {
                  setAdjustment({
                    stock: row,
                    movementType: "IN",
                    quantity: "1.000",
                    note: "",
                  });
                  setFormMessage("");
                }}
              />
            ),
          },
        ]}
      />
    </div>
  );
}

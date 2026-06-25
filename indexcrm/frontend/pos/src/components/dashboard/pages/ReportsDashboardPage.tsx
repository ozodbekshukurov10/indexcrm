"use client";

import { BarChart3, Download, FileSpreadsheet } from "lucide-react";
import { useState } from "react";

import { ChartPlaceholder } from "@/components/dashboard/ChartPlaceholder";
import { DataTable } from "@/components/dashboard/DataTable";
import { DateFilter } from "@/components/dashboard/DateFilter";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { LoadingState } from "@/components/dashboard/LoadingState";
import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { StatCard } from "@/components/dashboard/StatCard";
import { useReportsDashboard } from "@/hooks/useDashboardData";
import { monthStartIsoDate, pickNumber, pickText, todayIsoDate } from "@/lib/dashboard";
import { formatMoney } from "@/lib/format";
import { downloadApiFile } from "@/services/api/client";

const exportLinks = [
  {
    href: "/reports/export/monthly-sales/",
    label: "Oylik savdo",
    filename: "monthly-sales.xlsx",
  },
  {
    href: "/reports/export/monthly-profit/",
    label: "Oylik foyda",
    filename: "monthly-profit.xlsx",
  },
  {
    href: "/reports/export/inventory/",
    label: "Ombor",
    filename: "inventory.xlsx",
  },
  { href: "/reports/export/debts/", label: "Qarzlar", filename: "debts.xlsx" },
];

export function ReportsDashboardPage() {
  const [range, setRange] = useState({
    dateFrom: monthStartIsoDate(),
    dateTo: todayIsoDate(),
  });
  const [exporting, setExporting] = useState("");
  const [exportError, setExportError] = useState("");
  const reportsQuery = useReportsDashboard(range.dateFrom, range.dateTo);

  if (reportsQuery.isLoading) {
    return (
      <LoadingState
        label="Hisobotlar"
        description="Hisobot xulosalari va eksport havolalari yuklanmoqda."
      />
    );
  }

  if (reportsQuery.isError) {
    return (
      <ErrorState
        title="Hisobotlarni yuklab bo'lmadi"
        error={reportsQuery.error}
        onRetry={() => void reportsQuery.refetch()}
      />
    );
  }

  const profit = reportsQuery.data?.profit ?? {};
  const expenses = reportsQuery.data?.expenses ?? {};
  const bestSelling = reportsQuery.data?.bestSelling ?? [];
  const bestSellingValues = bestSelling
    .slice(0, 8)
    .map((row) => pickNumber(row, ["total_amount", "sold_amount", "quantity"]));

  async function handleExport(link: (typeof exportLinks)[number]) {
    setExporting(link.href);
    setExportError("");
    try {
      await downloadApiFile(link.href, link.filename, {
        date_from: range.dateFrom,
        date_to: range.dateTo,
      });
    } catch {
      setExportError("Eksportni yuklab bo'lmadi. Qayta urinib ko'ring.");
    } finally {
      setExporting("");
    }
  }

  return (
    <div className="grid gap-5">
      <SectionHeader
        title="Hisobotlar"
        description="Tahlil xulosalari va Excel eksportlari."
        actions={<DateFilter {...range} onChange={setRange} />}
      />
      <div className="grid gap-3 md:grid-cols-3">
        <StatCard
          title="Sof savdo"
          value={formatMoney(pickNumber(profit, ["net_sales"]))}
          icon={BarChart3}
          tone="blue"
        />
        <StatCard
          title="Foyda"
          value={formatMoney(pickNumber(profit, ["profit"]))}
          icon={FileSpreadsheet}
          tone="green"
        />
        <StatCard
          title="Xarajatlar"
          value={formatMoney(pickNumber(expenses, ["total_expenses"]))}
          icon={Download}
          tone="amber"
        />
      </div>
      <section className="grid gap-3 md:grid-cols-4">
        {exportLinks.map((link) => (
          <button
            type="button"
            key={link.href}
            onClick={() => void handleExport(link)}
            disabled={exporting === link.href}
            className="rounded border border-slate-200 bg-white p-4 text-left font-black text-slate-800 shadow-panel hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Download aria-hidden="true" className="mb-3 h-5 w-5 text-blue-700" />
            {exporting === link.href ? "Yuklab olinmoqda" : link.label}
          </button>
        ))}
      </section>
      {exportError ? (
        <div className="rounded border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-bold text-rose-800">
          {exportError}
        </div>
      ) : null}
      <ChartPlaceholder
        title="Eng ko'p sotilganlar faolligi"
        description="Hisobot jami ko'rsatkichlaridan yengil ko'rinish."
        values={bestSellingValues}
      />
      <DataTable
        title="Eng ko'p sotilgan mahsulotlar"
        rows={bestSelling}
        rowKey={(row, index) =>
          pickText(row, ["product", "product_id", "product__id", "product_name"]) ||
          index
        }
        emptyTitle="Eng ko'p sotilgan mahsulotlar yo'q"
        emptyDescription="Hisobot qatorlari yakunlangan savdolardan keyin chiqadi."
        columns={[
          {
            key: "product",
            header: "Mahsulot",
            render: (row) => pickText(row, ["product__name", "product_name"]),
          },
          {
            key: "qty",
            header: "Miqdor",
            align: "right",
            render: (row) => pickText(row, ["sold_quantity"]),
          },
          {
            key: "amount",
            header: "Summa",
            align: "right",
            render: (row) => formatMoney(pickNumber(row, ["total_amount"])),
          },
        ]}
      />
    </div>
  );
}

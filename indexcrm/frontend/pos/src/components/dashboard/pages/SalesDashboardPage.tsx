"use client";

import { ReceiptText, TrendingUp } from "lucide-react";
import { useState } from "react";

import { ChartPlaceholder } from "@/components/dashboard/ChartPlaceholder";
import { DataTable } from "@/components/dashboard/DataTable";
import { DateFilter } from "@/components/dashboard/DateFilter";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { LoadingState } from "@/components/dashboard/LoadingState";
import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { StatCard } from "@/components/dashboard/StatCard";
import { useSalesDashboard } from "@/hooks/useDashboardData";
import { monthStartIsoDate, pickNumber, pickText, todayIsoDate } from "@/lib/dashboard";
import { formatMoney } from "@/lib/format";

export function SalesDashboardPage() {
  const [range, setRange] = useState({
    dateFrom: monthStartIsoDate(),
    dateTo: todayIsoDate(),
  });
  const salesQuery = useSalesDashboard(range.dateFrom, range.dateTo);

  if (salesQuery.isLoading) {
    return (
      <LoadingState
        label="Savdolar"
        description="Cheklar, jami summalar va mahsulot harakati yuklanmoqda."
      />
    );
  }

  if (salesQuery.isError) {
    return (
      <ErrorState
        title="Savdolar panelini yuklab bo'lmadi"
        error={salesQuery.error}
        onRetry={() => void salesQuery.refetch()}
      />
    );
  }

  const report = salesQuery.data?.report ?? {};
  const rows = salesQuery.data?.sales.results ?? [];
  const bestSelling = salesQuery.data?.bestSelling ?? [];
  const bestSellingValues = bestSelling
    .slice(0, 8)
    .map((row) => pickNumber(row, ["total_amount", "sold_amount", "quantity"]));

  return (
    <div className="grid gap-5">
      <SectionHeader
        title="Savdolar"
        description="Cheklar faolligi, jami summalar va eng ko'p sotilgan mahsulotlar."
        actions={<DateFilter {...range} onChange={setRange} />}
      />
      <div className="grid gap-3 md:grid-cols-3">
        <StatCard
          title="Umumiy savdo"
          value={formatMoney(pickNumber(report, ["gross_sales", "net_sales"]))}
          icon={ReceiptText}
          tone="blue"
        />
        <StatCard
          title="To'langan"
          value={formatMoney(pickNumber(report, ["paid_amount"]))}
          icon={TrendingUp}
          tone="green"
        />
        <StatCard
          title="Qarz"
          value={formatMoney(pickNumber(report, ["debt_amount"]))}
          icon={ReceiptText}
          tone="amber"
        />
      </div>
      <ChartPlaceholder
        title="Eng ko'p sotilganlar faolligi"
        description="Sotilgan mahsulotlar jami bo'yicha tezkor ko'rinish."
        values={bestSellingValues}
      />
      <DataTable
        title="So'nggi savdolar"
        rows={rows}
        rowKey={(row) => row.id}
        emptyTitle="Savdo topilmadi"
        emptyDescription="Bu davrda yakunlangan POS savdolar shu yerda chiqadi."
        columns={[
          { key: "receipt", header: "Chek", render: (row) => row.receipt_number },
          { key: "customer", header: "Mijoz", render: (row) => row.customer_name ?? "Mijozsiz" },
          { key: "status", header: "Holat", render: (row) => row.status },
          {
            key: "cashier",
            header: "Kassir",
            render: (row) => row.cashier_email,
          },
          {
            key: "total",
            header: "Jami",
            align: "right",
            render: (row) => formatMoney(row.total_amount),
          },
        ]}
      />
      <DataTable
        title="Eng ko'p sotilgan mahsulotlar"
        rows={bestSelling}
        rowKey={(row, index) =>
          pickText(row, ["product", "product_id", "product__id", "product_name"]) ||
          index
        }
        emptyTitle="Eng ko'p sotilgan mahsulotlar yo'q"
        emptyDescription="Mahsulot harakati yakunlangan savdolardan keyin chiqadi."
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

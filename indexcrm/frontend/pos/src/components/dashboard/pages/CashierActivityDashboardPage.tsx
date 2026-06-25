"use client";

import { Clock3, ReceiptText, UsersRound } from "lucide-react";
import { useState } from "react";

import { DataTable } from "@/components/dashboard/DataTable";
import { DateFilter } from "@/components/dashboard/DateFilter";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { LoadingState } from "@/components/dashboard/LoadingState";
import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { StatCard } from "@/components/dashboard/StatCard";
import { useCashierActivityDashboard } from "@/hooks/useDashboardData";
import { monthStartIsoDate, pickNumber, pickText, todayIsoDate } from "@/lib/dashboard";
import { formatMoney } from "@/lib/format";

export function CashierActivityDashboardPage() {
  const [range, setRange] = useState({
    dateFrom: monthStartIsoDate(),
    dateTo: todayIsoDate(),
  });
  const cashierQuery = useCashierActivityDashboard(range.dateFrom, range.dateTo);

  if (cashierQuery.isLoading) {
    return (
      <LoadingState
        label="Kassir faolligi"
        description="Kassir natijalari va smena tarixi yuklanmoqda."
      />
    );
  }

  if (cashierQuery.isError) {
    return (
      <ErrorState
        title="Kassir faolligini yuklab bo'lmadi"
        error={cashierQuery.error}
        onRetry={() => void cashierQuery.refetch()}
      />
    );
  }

  const performance = cashierQuery.data?.performance ?? [];
  const shifts = cashierQuery.data?.shifts.results ?? [];

  return (
    <div className="grid gap-5">
      <SectionHeader
        title="Kassir faolligi"
        description="Kassir natijalari va smenalarni kuzatish."
        actions={<DateFilter {...range} onChange={setRange} />}
      />
      <div className="grid gap-3 md:grid-cols-3">
        <StatCard
          title="Kassirlar"
          value={String(performance.length)}
          icon={UsersRound}
          tone="blue"
        />
        <StatCard
          title="Ochiq smenalar"
          value={String(shifts.filter((shift) => !shift.closed_at).length)}
          icon={Clock3}
          tone="amber"
        />
        <StatCard
          title="Kuzatilgan cheklar"
          value={String(
            performance.reduce(
              (sum, row) => sum + pickNumber(row, ["sale_count"]),
              0,
            ),
          )}
          icon={ReceiptText}
          tone="green"
        />
      </div>
      <DataTable
        title="Kassir natijalari"
        rows={performance}
        rowKey={(row, index) =>
          pickText(row, ["cashier", "cashier_id", "cashier__email", "cashier_email"]) ||
          index
        }
        emptyTitle="Hali kassir natijalari yo'q"
        emptyDescription="Yakunlangan savdolardan keyin kassir natijalari chiqadi."
        columns={[
          {
            key: "cashier",
            header: "Kassir",
            render: (row) => pickText(row, ["cashier__email", "cashier_email"]),
          },
          {
            key: "sales",
            header: "Savdolar",
            align: "right",
            render: (row) => pickText(row, ["sale_count"]),
          },
          {
            key: "revenue",
            header: "Tushum",
            align: "right",
            render: (row) => formatMoney(pickNumber(row, ["revenue", "total_amount"])),
          },
        ]}
      />
      <DataTable
        title="Smena tarixi"
        rows={shifts}
        rowKey={(row) => row.id}
        emptyTitle="Smena topilmadi"
        emptyDescription="Smenalar ochilgandan keyin kassir smena tarixi chiqadi."
        columns={[
          { key: "cashier", header: "Kassir", render: (row) => row.cashier_email },
          { key: "branch", header: "Filial", render: (row) => row.branch_name },
          {
            key: "opened",
            header: "Ochildi",
            render: (row) => new Date(row.opened_at).toLocaleString(),
          },
          {
            key: "status",
            header: "Holat",
            render: (row) => (row.closed_at ? "Yopiq" : "Ochiq"),
          },
        ]}
      />
    </div>
  );
}

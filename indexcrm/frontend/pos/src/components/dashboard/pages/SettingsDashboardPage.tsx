"use client";

import { Settings, ShieldCheck, UserRound } from "lucide-react";

import { DataTable } from "@/components/dashboard/DataTable";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { LoadingState } from "@/components/dashboard/LoadingState";
import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { StatCard } from "@/components/dashboard/StatCard";
import { useProfileDashboard } from "@/hooks/useDashboardData";
import { useCashierStore } from "@/stores/cashierStore";

export function SettingsDashboardPage() {
  const profileQuery = useProfileDashboard();
  const { authToken, branchId, warehouseId } = useCashierStore();

  if (profileQuery.isLoading) {
    return (
      <LoadingState
        label="Profil sozlamalari"
        description="Akkaunt va lokal sessiya ma'lumotlari yuklanmoqda."
      />
    );
  }

  if (profileQuery.isError) {
    return (
      <ErrorState
        title="Profil sozlamalarini yuklab bo'lmadi"
        error={profileQuery.error}
        onRetry={() => void profileQuery.refetch()}
      />
    );
  }

  const user = profileQuery.data;
  const rows = [
    { label: "Email", value: user?.email ?? "-" },
    { label: "Rol", value: user?.role ?? "-" },
    { label: "Telefon", value: user?.phone ?? "-" },
    { label: "Lavozim", value: user?.profile?.position ?? "-" },
    { label: "Filial", value: user?.profile?.branch_name ?? branchId ?? "-" },
    { label: "Ombor", value: warehouseId || "-" },
    { label: "API token", value: authToken ? "Sozlangan" : "Yo'q" },
  ];

  return (
    <div className="grid gap-5">
      <SectionHeader
        title="Profil/sozlamalar"
        description="Akkaunt, lokal boshqaruv sessiyasi va egasi/admin konteksti."
      />
      <div className="grid gap-3 md:grid-cols-3">
        <StatCard
          title="Akkaunt"
          value={user?.email ?? "Yuklanmagan"}
          icon={UserRound}
          tone="blue"
        />
        <StatCard
          title="Rol"
          value={user?.role ?? "-"}
          icon={ShieldCheck}
          tone="green"
        />
        <StatCard
          title="Token"
          value={authToken ? "Tayyor" : "Yo'q"}
          icon={Settings}
          tone={authToken ? "slate" : "rose"}
        />
      </div>
      <DataTable
        title="Sozlamalar"
        rows={rows}
        rowKey={(row) => row.label}
        columns={[
          { key: "label", header: "Maydon", render: (row) => row.label },
          { key: "value", header: "Qiymat", render: (row) => row.value },
        ]}
      />
    </div>
  );
}

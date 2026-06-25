import { ReactNode } from "react";

import { DashboardNav } from "@/components/dashboard/DashboardNav";

type DashboardLayoutProps = {
  children: ReactNode;
};

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  return <DashboardNav>{children}</DashboardNav>;
}

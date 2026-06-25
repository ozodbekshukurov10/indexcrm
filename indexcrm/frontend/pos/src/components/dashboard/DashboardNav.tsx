"use client";

import {
  BarChart3,
  Boxes,
  Bot,
  CircleDollarSign,
  CloudOff,
  Lock,
  LayoutDashboard,
  PackageSearch,
  ReceiptText,
  Settings,
  ShieldCheck,
  ShoppingCart,
  Truck,
  UsersRound,
} from "lucide-react";
import { usePathname } from "next/navigation";
import { ReactNode } from "react";

import { LogoutButton } from "@/components/auth/LogoutButton";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { useAuthStore } from "@/stores/authStore";

const navItems = [
  {
    href: "/dashboard",
    label: "Umumiy",
    icon: LayoutDashboard,
    roles: ["owner", "admin", "manager"],
  },
  {
    href: "/dashboard/sales",
    label: "Savdolar",
    icon: ShoppingCart,
    roles: ["owner", "admin", "manager"],
  },
  {
    href: "/dashboard/products",
    label: "Mahsulotlar",
    icon: PackageSearch,
    roles: ["owner", "admin", "manager"],
  },
  {
    href: "/dashboard/inventory",
    label: "Ombor",
    icon: Boxes,
    roles: ["owner", "admin", "manager"],
  },
  {
    href: "/dashboard/customers",
    label: "Mijozlar",
    icon: UsersRound,
    roles: ["owner", "admin", "manager"],
  },
  {
    href: "/dashboard/suppliers",
    label: "Yetkazib beruvchilar",
    icon: Truck,
    roles: ["owner", "admin", "manager"],
  },
  {
    href: "/dashboard/finance",
    label: "Moliya",
    icon: CircleDollarSign,
    roles: ["owner", "admin"],
  },
  {
    href: "/dashboard/reports",
    label: "Hisobotlar",
    icon: BarChart3,
    roles: ["owner", "admin", "manager"],
  },
  {
    href: "/dashboard/cashier-activity",
    label: "Kassirlar",
    icon: ReceiptText,
    roles: ["owner", "admin", "manager"],
  },
  {
    href: "/dashboard/offline-queue",
    label: "Offline navbat",
    icon: CloudOff,
    roles: ["owner", "admin", "manager", "cashier"],
  },
  {
    href: "/dashboard/ai",
    label: "AI yordamchi",
    icon: Bot,
    roles: ["owner", "admin", "manager", "cashier"],
  },
  {
    href: "/dashboard/settings",
    label: "Sozlamalar",
    icon: Settings,
    roles: ["owner", "admin", "manager", "cashier"],
  },
];

type DashboardNavProps = {
  children: ReactNode;
};

function isActive(pathname: string, href: string) {
  return href === "/dashboard"
    ? pathname === href
    : pathname === href || pathname.startsWith(`${href}/`);
}

function canUseNavItem(role: string | undefined, item: (typeof navItems)[number]) {
  return Boolean(role && item.roles.includes(role));
}

export function DashboardNav({ children }: DashboardNavProps) {
  const pathname = usePathname();
  const user = useAuthStore((state) => state.user);
  const role = user?.role;
  const visibleNavItems = navItems.filter((item) => canUseNavItem(role, item));
  const currentNavItem = navItems
    .slice()
    .sort((first, second) => second.href.length - first.href.length)
    .find((item) => isActive(pathname, item.href));
  const hasAccess = currentNavItem ? canUseNavItem(role, currentNavItem) : true;
  const roleLabels: Record<string, string> = {
    owner: "Egasi",
    admin: "Admin",
    manager: "Menejer",
    cashier: "Kassir",
  };
  const roleLabel = role ? roleLabels[role] ?? role : "-";
  const pageLabel = currentNavItem?.label ?? "Boshqaruv paneli";

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 border-r border-slate-200/80 bg-white shadow-sm lg:block">
        <div className="flex h-16 items-center gap-3 border-b border-slate-100 px-5">
          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 text-sm font-black text-white shadow-sm shadow-primary-500/20">
            I
          </div>
          <div>
            <div className="text-base font-black tracking-tight text-slate-900">
              Index Admin
            </div>
            <div className="text-[11px] font-bold uppercase tracking-wider text-primary-600">
              {roleLabel}
            </div>
          </div>
        </div>
        <nav className="grid gap-0.5 p-3">
          {visibleNavItems.map((item) => {
            const Icon = item.icon;
            const active = isActive(pathname, item.href);
            return (
              <a
                key={item.href}
                href={item.href}
                className={`flex h-10 items-center gap-3 rounded-lg px-3 text-sm font-bold transition ${
                  active
                    ? "bg-primary-50 text-primary-700"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`}
              >
                <Icon
                  aria-hidden="true"
                  className={`h-5 w-5 ${active ? "text-primary-500" : "text-slate-400"}`}
                />
                <span>{item.label}</span>
              </a>
            );
          })}
        </nav>
      </aside>

      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-slate-200/80 bg-white/90 px-4 shadow-sm backdrop-blur-lg lg:px-6">
          <div className="min-w-0">
            <div className="text-lg font-black tracking-tight text-slate-900">
              {pageLabel}
            </div>
            <div className="text-xs font-bold uppercase tracking-wider text-slate-500">
              {roleLabel} boshqaruv paneli
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <a
              href="/"
              className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-xs font-bold text-slate-700 shadow-sm transition hover:bg-slate-50"
            >
              <ShoppingCart aria-hidden="true" className="h-4 w-4" />
              POS ochish
            </a>
            <LogoutButton />
          </div>
        </header>
        <nav className="flex gap-2 overflow-x-auto border-b border-slate-200/80 bg-white px-3 py-2 lg:hidden">
          {visibleNavItems.map((item) => {
            const Icon = item.icon;
            const active = isActive(pathname, item.href);
            return (
              <a
                key={item.href}
                href={item.href}
                className={`inline-flex h-9 shrink-0 items-center gap-2 rounded-lg border px-3 text-xs font-bold ${
                  active
                    ? "border-primary-200 bg-primary-50 text-primary-700"
                    : "border-slate-200 text-slate-600 hover:bg-slate-50"
                }`}
              >
                <Icon aria-hidden="true" className="h-4 w-4" />
                <span>{item.label}</span>
              </a>
            );
          })}
        </nav>
        <main className="pb-8">
          {hasAccess ? (
            children
          ) : (
            <div className="animate-fade-in p-4 lg:p-6">
              <section className="overflow-hidden rounded-xl border border-slate-200/80 bg-white shadow-sm">
                <EmptyState
                  title="Bu bo'lim mavjud emas"
                  description="Joriy rolingiz bu boshqaruv sahifasiga kirish huquqiga ega emas."
                />
                <div className="flex justify-center border-t border-slate-100 p-4">
                  <a
                    href="/"
                    className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-bold text-slate-700 shadow-sm transition hover:bg-slate-50"
                  >
                    <Lock aria-hidden="true" className="h-4 w-4" />
                    POS ochish
                  </a>
                </div>
              </section>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

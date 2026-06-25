"use client";

import { ReactNode } from "react";

import { LogoutButton } from "@/components/auth/LogoutButton";
import { useCashierStore } from "@/stores/cashierStore";

type PosShellProps = {
  children: ReactNode;
};

export function PosShell({ children }: PosShellProps) {
  const {
    activeShiftId,
    branchId,
    cashDeskId,
    cashierEmail,
    cashierName,
    warehouseId,
  } = useCashierStore();

  return (
    <main className="h-screen overflow-hidden text-slate-900">
      <header className="glass-header no-print flex h-14 items-center justify-between px-4 shadow-glass">
        <div className="flex items-center gap-3">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-primary-500/80 to-primary-700/80 text-xs font-black text-white shadow-lg shadow-primary-500/20 backdrop-blur-sm">
            I
          </span>
          <span className="text-base font-black tracking-tight text-slate-900">
            Index POS
          </span>
          <span className="glass rounded-md px-2 py-0.5 text-[11px] font-bold uppercase tracking-wider text-emerald-700">
            Kassir
          </span>
        </div>
        <div className="flex items-center gap-4 text-sm">
          <span className="font-semibold text-slate-700">
            {cashierName || cashierEmail || "Sessiya sozlanmagan"}
          </span>
          <div className="flex items-center gap-3 text-xs text-slate-500">
            <span className="flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-slate-400" />
              Filial {branchId ? branchId.substring(0, 8) : "-"}
            </span>
            <span className="flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-slate-400" />
              Ombor {warehouseId ? warehouseId.substring(0, 8) : "-"}
            </span>
            <span
              className={`glass rounded-md px-2 py-0.5 text-[11px] font-bold uppercase tracking-wider ${
                activeShiftId
                  ? "text-emerald-700"
                  : "text-amber-700"
              }`}
            >
              Smena {activeShiftId ? "Ochiq" : "Yo'q"}
            </span>
          </div>
          <LogoutButton />
        </div>
      </header>
      {children}
    </main>
  );
}

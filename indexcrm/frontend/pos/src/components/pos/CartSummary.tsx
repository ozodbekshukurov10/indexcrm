"use client";

import { ShoppingCart, XCircle } from "lucide-react";

import { formatMoney } from "@/lib/format";

import { IconButton } from "./IconButton";

type CartSummaryProps = {
  subtotal: number;
  total: number;
  itemCount: number;
  onClear: () => void;
};

export function CartSummary({
  subtotal,
  total,
  itemCount,
  onClear,
}: CartSummaryProps) {
  return (
    <section className="no-print border-t border-slate-200 bg-white p-4">
      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-xl border border-slate-200/80 bg-slate-50 p-3">
          <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
            Mahsulot soni
          </div>
          <div className="text-2xl font-black tracking-tight text-slate-900">
            {itemCount}
          </div>
        </div>
        <div className="rounded-xl border border-slate-200/80 bg-slate-50 p-3">
          <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
            Oraliq jami
          </div>
          <div className="text-2xl font-black tracking-tight text-slate-900">
            {formatMoney(subtotal)}
          </div>
        </div>
        <div className="rounded-xl border border-emerald-200/80 bg-gradient-to-br from-emerald-50 to-emerald-100/80 p-3">
          <div className="text-[11px] font-bold uppercase tracking-wider text-emerald-700">
            Jami
          </div>
          <div className="text-3xl font-black tracking-tight text-emerald-800">
            {formatMoney(total)}
          </div>
        </div>
      </div>
      <div className="mt-3 flex gap-2">
        <IconButton
          icon={<ShoppingCart aria-hidden="true" className="h-5 w-5" />}
          label="Yangi savdo"
          onClick={onClear}
          tone="warning"
          className="flex-1"
          disabled={itemCount === 0}
        />
        <IconButton
          icon={<XCircle aria-hidden="true" className="h-5 w-5" />}
          label="Tozalash"
          onClick={onClear}
          tone="danger"
          className="flex-1"
          disabled={itemCount === 0}
        />
      </div>
    </section>
  );
}

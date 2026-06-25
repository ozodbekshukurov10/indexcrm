"use client";

import {
  AlertCircle,
  Banknote,
  CheckCircle2,
  CreditCard,
  SplitSquareHorizontal,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { formatMoney } from "@/lib/format";
import { SalePaymentMethod } from "@/services/api/types";

import { IconButton } from "./IconButton";

type Payment = {
  payment_method: SalePaymentMethod;
  amount: number;
  note?: string;
};

type PaymentPanelProps = {
  total: number;
  disabled?: boolean;
  disabledReason?: string;
  loading?: boolean;
  variant?: "online" | "offline";
  onComplete: (payments: Payment[]) => void;
};

type PaymentMode = "cash" | "card" | "mixed";

export function PaymentPanel({
  total,
  disabled,
  disabledReason,
  loading,
  variant = "online",
  onComplete,
}: PaymentPanelProps) {
  const [mode, setMode] = useState<PaymentMode>("cash");
  const [cashAmount, setCashAmount] = useState(total);
  const [cardAmount, setCardAmount] = useState(0);

  useEffect(() => {
    if (mode === "cash") {
      setCashAmount(total);
      setCardAmount(0);
    }
    if (mode === "card") {
      setCashAmount(0);
      setCardAmount(total);
    }
  }, [mode, total]);

  const paidAmount = useMemo(
    () => Math.round((cashAmount + cardAmount) * 100) / 100,
    [cashAmount, cardAmount],
  );
  const changeAmount = Math.max(0, paidAmount - total);
  const paymentShortfall = Math.max(0, Math.round((total - paidAmount) * 100) / 100);
  const canComplete = total > 0 && paidAmount >= total && !disabled && !loading;
  const isOfflineSale = variant === "offline";
  const readyLabel = isOfflineSale
    ? "Offline savdoni saqlashga tayyor"
    : "Savdoni yakunlashga tayyor";
  const actionLabel = isOfflineSale ? "Offline saqlash" : "Savdoni yakunlash";
  const loadingLabel = isOfflineSale ? "Offline saqlanmoqda" : "Yakunlanmoqda";

  const submitPayment = useCallback(() => {
    if (!canComplete) {
      return;
    }
    const payments: Payment[] = [];
    if (cashAmount > 0) {
      payments.push({ payment_method: "CASH", amount: cashAmount });
    }
    if (cardAmount > 0) {
      payments.push({ payment_method: "CARD", amount: cardAmount });
    }
    onComplete(payments);
  }, [canComplete, cardAmount, cashAmount, onComplete]);

  useEffect(() => {
    const listener = (event: KeyboardEvent) => {
      if (event.key === "F4") {
        event.preventDefault();
        submitPayment();
      }
    };
    window.addEventListener("keydown", listener);
    return () => window.removeEventListener("keydown", listener);
  }, [submitPayment]);

  const modeButtonClass = (isActive: boolean, color: string) =>
    `flex-1 h-10 rounded-xl border text-xs font-bold uppercase tracking-wider transition ${
      isActive
        ? `border-${color}-200 bg-${color}-50 text-${color}-700 shadow-sm`
        : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
    }`;

  return (
    <section className="no-print border-b border-slate-200 bg-white p-4">
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => setMode("cash")}
          className={`flex flex-1 items-center justify-center gap-2 rounded-xl border py-2.5 text-xs font-bold uppercase tracking-wider transition ${
            mode === "cash"
              ? "border-emerald-200 bg-emerald-50 text-emerald-700 shadow-sm"
              : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
          }`}
        >
          <Banknote aria-hidden="true" className="h-4 w-4" />
          Naqd
        </button>
        <button
          type="button"
          onClick={() => setMode("card")}
          className={`flex flex-1 items-center justify-center gap-2 rounded-xl border py-2.5 text-xs font-bold uppercase tracking-wider transition ${
            mode === "card"
              ? "border-primary-200 bg-primary-50 text-primary-700 shadow-sm"
              : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
          }`}
        >
          <CreditCard aria-hidden="true" className="h-4 w-4" />
          Karta
        </button>
        <button
          type="button"
          onClick={() => setMode("mixed")}
          className={`flex flex-1 items-center justify-center gap-2 rounded-xl border py-2.5 text-xs font-bold uppercase tracking-wider transition ${
            mode === "mixed"
              ? "border-amber-200 bg-amber-50 text-amber-700 shadow-sm"
              : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
          }`}
        >
          <SplitSquareHorizontal aria-hidden="true" className="h-4 w-4" />
          Aralash
        </button>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2">
        <label className="block">
          <span className="mb-1 block text-[11px] font-bold uppercase tracking-wider text-slate-500">
            Naqd
          </span>
          <input
            value={cashAmount}
            onChange={(event) => setCashAmount(Number(event.target.value) || 0)}
            onFocus={(event) => event.target.select()}
            disabled={mode === "card"}
            inputMode="decimal"
            className="h-11 w-full rounded-xl border border-slate-200 px-3 text-lg font-bold text-slate-900 shadow-sm transition focus:border-primary-400 focus:ring-2 focus:ring-primary-500/20 disabled:bg-slate-50 disabled:text-slate-400"
          />
        </label>
        <label className="block">
          <span className="mb-1 block text-[11px] font-bold uppercase tracking-wider text-slate-500">
            Karta
          </span>
          <input
            value={cardAmount}
            onChange={(event) => setCardAmount(Number(event.target.value) || 0)}
            onFocus={(event) => event.target.select()}
            disabled={mode === "cash"}
            inputMode="decimal"
            className="h-11 w-full rounded-xl border border-slate-200 px-3 text-lg font-bold text-slate-900 shadow-sm transition focus:border-primary-400 focus:ring-2 focus:ring-primary-500/20 disabled:bg-slate-50 disabled:text-slate-400"
          />
        </label>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2">
        <div className="rounded-xl border border-slate-200/80 bg-slate-50 p-3">
          <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
            To'landi
          </div>
          <div className="text-xl font-black tracking-tight text-slate-900">
            {formatMoney(paidAmount)}
          </div>
        </div>
        <div className="rounded-xl border border-slate-200/80 bg-slate-50 p-3">
          <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
            Qaytim
          </div>
          <div className="text-xl font-black tracking-tight text-slate-900">
            {formatMoney(changeAmount)}
          </div>
        </div>
      </div>

      <div
        className={`mt-3 flex min-h-11 items-center gap-2 rounded-xl border px-4 py-2.5 text-sm font-bold ${
          canComplete
            ? "border-emerald-200 bg-emerald-50 text-emerald-800"
            : "border-amber-200 bg-amber-50 text-amber-800"
        }`}
      >
        {canComplete ? (
          <CheckCircle2 aria-hidden="true" className="h-4 w-4 shrink-0" />
        ) : (
          <AlertCircle aria-hidden="true" className="h-4 w-4 shrink-0" />
        )}
        <span>
          {canComplete
            ? readyLabel
            : disabledReason ||
              (paymentShortfall > 0
                ? `To'lov yetishmayapti: ${formatMoney(paymentShortfall)}`
                : "Checkout tayyor emas")}
        </span>
      </div>

      {isOfflineSale ? (
        <div className="mt-2 animate-fade-in rounded-xl border border-amber-200 bg-amber-50 px-4 py-2.5 text-xs font-bold text-amber-800">
          Savdo ushbu qurilmada saqlanadi. Yakuniy server chek raqami internet
          qaytganda qo'lda sinxronlashdan keyin chiqadi.
        </div>
      ) : null}

      <button
        type="button"
        onClick={submitPayment}
        disabled={!canComplete}
        className={`mt-3 flex h-14 w-full items-center justify-center gap-2 rounded-xl text-base font-bold uppercase tracking-wider transition ${
          canComplete
            ? "bg-gradient-to-r from-emerald-500 to-emerald-600 text-white shadow-lg shadow-emerald-500/25 hover:from-emerald-400 hover:to-emerald-500 hover:shadow-emerald-500/35 active:scale-[0.98]"
            : "cursor-not-allowed bg-slate-100 text-slate-400"
        }`}
      >
        {loading ? (
          <div className="flex items-center gap-2">
            <svg className="h-5 w-5 animate-spin" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            {loadingLabel}
          </div>
        ) : (
          <>
            <CheckCircle2 aria-hidden="true" className="h-5 w-5" />
            {actionLabel}
          </>
        )}
      </button>
    </section>
  );
}

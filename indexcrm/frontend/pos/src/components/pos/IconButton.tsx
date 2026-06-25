"use client";

import { ButtonHTMLAttributes, ReactNode } from "react";

type IconButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  icon: ReactNode;
  label: string;
  hideLabel?: boolean;
  tone?: "neutral" | "primary" | "danger" | "success" | "warning";
};

const tones = {
  neutral: "border-slate-200 bg-white text-slate-700 hover:bg-slate-50 hover:border-slate-300",
  primary: "border-primary-600 bg-primary-600 text-white hover:bg-primary-500",
  danger: "border-rose-600 bg-rose-600 text-white hover:bg-rose-500",
  success: "border-emerald-600 bg-emerald-600 text-white hover:bg-emerald-500",
  warning: "border-amber-300 bg-amber-200 text-amber-900 hover:bg-amber-300",
};

export function IconButton({
  icon,
  label,
  hideLabel = false,
  tone = "neutral",
  className = "",
  ...props
}: IconButtonProps) {
  return (
    <button
      {...props}
      aria-label={label}
      title={label}
      className={`inline-flex min-h-10 items-center justify-center gap-2 rounded-xl border px-3 py-2 text-sm font-bold shadow-sm transition active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none disabled:active:scale-100 ${tones[tone]} ${className}`}
    >
      {icon}
      <span className={hideLabel ? "sr-only" : undefined}>{label}</span>
    </button>
  );
}

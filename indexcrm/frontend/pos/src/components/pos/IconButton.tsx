"use client";

import { ButtonHTMLAttributes, ReactNode } from "react";

type IconButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  icon: ReactNode;
  label: string;
  hideLabel?: boolean;
  tone?: "neutral" | "primary" | "danger" | "success" | "warning";
};

const tones = {
  neutral: "glass border-white/30 text-slate-700 hover:bg-white/70",
  primary: "bg-gradient-to-r from-primary-500/90 to-primary-600/90 text-white hover:from-primary-400/90 hover:to-primary-500/90",
  danger: "bg-gradient-to-r from-rose-500/90 to-rose-600/90 text-white hover:from-rose-400/90 hover:to-rose-500/90",
  success: "bg-gradient-to-r from-emerald-500/90 to-emerald-600/90 text-white hover:from-emerald-400/90 hover:to-emerald-500/90",
  warning: "glass border-amber-300/50 bg-amber-200/50 text-amber-900 hover:bg-amber-300/60",
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
      className={`inline-flex min-h-10 items-center justify-center gap-2 rounded-xl border px-3 py-2 text-sm font-bold shadow-glass backdrop-blur-sm transition active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none disabled:active:scale-100 ${tones[tone]} ${className}`}
    >
      {icon}
      <span className={hideLabel ? "sr-only" : undefined}>{label}</span>
    </button>
  );
}

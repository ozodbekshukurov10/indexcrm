"use client";

import { LogOut } from "lucide-react";
import { useRouter } from "next/navigation";

import { useAuthStore } from "@/stores/authStore";

type LogoutButtonProps = {
  className?: string;
  label?: string;
  variant?: "light" | "dark";
};

export function LogoutButton({
  className = "",
  label = "Chiqish",
  variant = "light",
}: LogoutButtonProps) {
  const router = useRouter();
  const signOut = useAuthStore((state) => state.signOut);

  function handleLogout() {
    signOut();
    router.replace("/login");
  }

  return (
    <button
      type="button"
      onClick={handleLogout}
      className={`inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-xs font-bold uppercase tracking-wider backdrop-blur-sm transition active:scale-[0.97] ${
        variant === "dark"
          ? "border-slate-600/60 bg-slate-800/80 text-slate-200 hover:bg-slate-700/80 hover:text-white"
          : "glass border-rose-200/40 text-rose-600 shadow-glass hover:bg-white/70 hover:text-rose-700"
      } ${className}`}
    >
      <LogOut aria-hidden="true" className="h-4 w-4" />
      <span>{label}</span>
    </button>
  );
}

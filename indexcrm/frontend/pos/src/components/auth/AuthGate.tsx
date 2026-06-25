"use client";

import { Loader2 } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useEffect, useMemo } from "react";

import { useAuthStore } from "@/stores/authStore";

type AuthGateProps = {
  children: ReactNode;
};

function getLandingPath(role?: string | null) {
  if (role === "owner" || role === "admin") {
    return "/dashboard";
  }
  return "/";
}

export function AuthGate({ children }: AuthGateProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { status, user, initializeAuth } = useAuthStore();

  const isLoginPage = pathname === "/login";
  const isDashboardPage = pathname.startsWith("/dashboard");
  const isAuthReady = status === "authenticated" || status === "unauthenticated";

  useEffect(() => {
    void initializeAuth();
  }, [initializeAuth]);

  const redirectPath = useMemo(
    () => getLandingPath(user?.role ?? null),
    [user?.role],
  );

  useEffect(() => {
    if (!isAuthReady) {
      return;
    }

    if (isLoginPage && status === "authenticated") {
      router.replace(redirectPath);
      return;
    }

    if (!isLoginPage && status === "unauthenticated") {
      router.replace("/login");
    }
  }, [isAuthReady, isLoginPage, redirectPath, router, status]);

  if (!isAuthReady) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-100 to-slate-200 text-slate-900">
        <div className="flex animate-fade-in items-center gap-3 rounded-xl border border-slate-200/80 bg-white/90 px-5 py-4 shadow-elevated backdrop-blur-sm">
          <Loader2 aria-hidden="true" className="h-5 w-5 animate-spin text-primary-500" />
          <span className="text-sm font-bold uppercase tracking-wider text-slate-500">
            {isDashboardPage ? "Boshqaruv paneli ochilmoqda" : "Sessiya tekshirilmoqda"}
          </span>
        </div>
      </div>
    );
  }

  if (isLoginPage && status === "authenticated") {
    return null;
  }

  if (!isLoginPage && status === "unauthenticated") {
    return null;
  }

  return <>{children}</>;
}

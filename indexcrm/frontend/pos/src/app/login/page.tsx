"use client";

import { Eye, EyeOff, Loader2, ShieldCheck } from "lucide-react";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import { getCurrentUser } from "@/services/api/accounts";
import { loginWithCredentials } from "@/services/api/auth";
import {
  ApiError,
  clearStoredAuthToken,
  setStoredAuthToken,
} from "@/services/api/client";
import { useAuthStore } from "@/stores/authStore";

function getLandingPath(role?: string | null) {
  if (role === "owner" || role === "admin") {
    return "/dashboard";
  }
  return "/";
}

function formatError(error: unknown) {
  if (error instanceof ApiError) {
    if (typeof error.detail === "string") {
      return error.detail;
    }
    if (
      error.detail &&
      typeof error.detail === "object" &&
      "detail" in error.detail &&
      typeof (error.detail as { detail?: unknown }).detail === "string"
    ) {
      return (error.detail as { detail: string }).detail;
    }
    return "Kirish amalga oshmadi. Email va parolni tekshiring.";
  }
  if (
    error instanceof TypeError ||
    (error instanceof Error &&
      ["Failed to fetch", "fetch failed"].includes(error.message))
  ) {
    return [
      "Backend API bilan aloqa yo'q.",
      "Django ishlayotganini va NEXT_PUBLIC_API_BASE_URL to'g'ri ekanini tekshiring.",
    ].join(" ");
  }
  return "Kirish amalga oshmadi. Ma'lumotlarni tekshirib, qayta urinib ko'ring.";
}

export default function LoginPage() {
  const router = useRouter();
  const signIn = useAuthStore((state) => state.signIn);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const passwordToggleLabel = showPassword ? "Parolni yashirish" : "Parolni ko'rsatish";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      const tokens = await loginWithCredentials({
        email,
        password,
      });
      setStoredAuthToken(tokens.access);
      const user = await getCurrentUser();
      signIn({ token: tokens.access, user });
      router.replace(getLandingPath(user.role));
    } catch (submissionError) {
      clearStoredAuthToken();
      setError(formatError(submissionError));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-gradient-to-br from-primary-950 via-primary-900 to-slate-900 px-4">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_rgba(99,102,241,0.15),transparent_50%)]" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_left,_rgba(139,92,246,0.1),transparent_50%)]" />

      <div className="animate-slide-up w-full max-w-md">
        <div className="rounded-2xl border border-white/10 bg-white/95 p-8 shadow-2xl backdrop-blur-xl">
          <div className="mb-8 text-center">
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-primary-500 to-primary-700 shadow-lg">
              <ShieldCheck aria-hidden="true" className="h-7 w-7 text-white" />
            </div>
            <h1 className="text-2xl font-black tracking-tight text-slate-900">
              Index CRM
            </h1>
            <p className="mt-1 text-sm font-medium text-slate-500">
              Davom etish uchun tizimga kiring
            </p>
          </div>

          <form className="grid gap-5" onSubmit={handleSubmit}>
            <label className="grid gap-1.5" htmlFor="login-email">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-600">
                Email
              </span>
              <input
                id="login-email"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className="h-11 rounded-xl border border-slate-200 bg-white/80 px-4 text-sm font-medium text-slate-900 placeholder:text-slate-400 outline-none ring-0 transition focus:border-primary-400 focus:ring-2 focus:ring-primary-500/20"
                placeholder="admin@example.com"
                autoComplete="email"
                required
              />
            </label>

            <div className="grid gap-1.5">
              <label
                className="text-xs font-bold uppercase tracking-wider text-slate-600"
                htmlFor="login-password"
              >
                Parol
              </label>
              <div className="relative">
                <input
                  id="login-password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  className="h-11 w-full rounded-xl border border-slate-200 bg-white/80 px-4 pr-12 text-sm font-medium text-slate-900 placeholder:text-slate-400 outline-none ring-0 transition focus:border-primary-400 focus:ring-2 focus:ring-primary-500/20"
                  placeholder="Parolni kiriting"
                  autoComplete="current-password"
                  required
                />
                <button
                  type="button"
                  aria-label={passwordToggleLabel}
                  aria-pressed={showPassword}
                  title={passwordToggleLabel}
                  onClick={() => setShowPassword((current) => !current)}
                  className="absolute inset-y-0 right-0 inline-flex w-11 items-center justify-center text-slate-400 hover:text-slate-700 transition focus:outline-none"
                >
                  {showPassword ? (
                    <EyeOff aria-hidden="true" className="h-4 w-4" />
                  ) : (
                    <Eye aria-hidden="true" className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>

            {error ? (
              <div className="animate-fade-in rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">
                {error}
              </div>
            ) : null}

            <button
              type="submit"
              disabled={loading}
              className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-primary-600 to-primary-700 px-4 text-sm font-bold uppercase tracking-wider text-white shadow-lg shadow-primary-500/25 transition hover:from-primary-500 hover:to-primary-600 hover:shadow-primary-500/35 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-60 disabled:shadow-none"
            >
              {loading ? (
                <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" />
              ) : null}
              <span>{loading ? "Kirilmoqda" : "Kirish"}</span>
            </button>
          </form>
        </div>
        <p className="mt-6 text-center text-xs font-medium text-white/60">
          Index CRM v0.1.0 &mdash; Barcha huquqlar himoyalangan
        </p>
      </div>
    </main>
  );
}

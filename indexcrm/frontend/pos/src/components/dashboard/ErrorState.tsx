import { AlertCircle, RotateCw } from "lucide-react";

import { ApiError } from "@/services/api/client";

type ErrorStateProps = {
  title?: string;
  description?: string;
  error?: unknown;
  onRetry?: () => void;
};

function stringifyDetail(detail: unknown): string {
  if (!detail) {
    return "";
  }
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    return detail.map((item) => stringifyDetail(item)).filter(Boolean).join(" ");
  }
  if (typeof detail === "object") {
    const ignoredKeys = new Set(["code", "status"]);

    return Object.entries(detail as Record<string, unknown>)
      .filter(([key]) => !ignoredKeys.has(key))
      .map(([key, value]) => {
        const message = stringifyDetail(value);
        if (!message) {
          return "";
        }
        if (["detail", "message", "non_field_errors"].includes(key)) {
          return message;
        }
        return `${key.replaceAll("_", " ")}: ${message}`;
      })
      .filter(Boolean)
      .join(" ");
  }
  return String(detail);
}

function formatErrorDescription(error: unknown, fallback: string) {
  if (!error) {
    return fallback;
  }

  if (error instanceof ApiError) {
    if (error.status === 401) {
      return "Kirish sessiyasi tugadi. Davom etish uchun qayta kiring.";
    }
    if (error.status === 403) {
      return "Bu akkaunt boshqaruv panelining ushbu bo'limiga kira olmaydi.";
    }
    if (error.status === 404) {
      return "Joriy backendda bu boshqaruv endpointi mavjud emas.";
    }
    if (error.status >= 500) {
      return "Server bu ma'lumotni yuklay olmadi. Bir marta qayta urinib ko'ring, davom etsa yordamga murojaat qiling.";
    }

    const detail = stringifyDetail(error.detail);
    return detail || fallback;
  }

  if (
    error instanceof TypeError ||
    (error instanceof Error &&
      ["Failed to fetch", "fetch failed"].includes(error.message))
  ) {
    return "Backend API bilan aloqa yo'q. Django ishlayotganini va NEXT_PUBLIC_API_BASE_URL to'g'ri ekanini tekshiring.";
  }

  return fallback;
}

export function ErrorState({
  title = "Ma'lumotni yuklab bo'lmadi",
  description = "Aloqani tekshirib, qayta urinib ko'ring.",
  error,
  onRetry,
}: ErrorStateProps) {
  const resolvedDescription = formatErrorDescription(error, description);

  return (
    <section className="rounded-xl border border-rose-100 bg-rose-50 p-5 shadow-sm">
      <div className="flex items-start gap-3">
        <AlertCircle aria-hidden="true" className="mt-0.5 h-5 w-5 text-rose-500" />
        <div className="min-w-0 flex-1">
          <h2 className="text-base font-bold text-rose-900">{title}</h2>
          <p className="mt-1 text-sm font-semibold text-rose-600">
            {resolvedDescription}
          </p>
          {onRetry ? (
            <button
              type="button"
              onClick={onRetry}
              className="mt-4 inline-flex items-center gap-2 rounded-lg border border-rose-200 bg-white px-4 py-2 text-sm font-bold text-rose-700 shadow-sm hover:bg-rose-50 active:scale-[0.97]"
            >
              <RotateCw aria-hidden="true" className="h-4 w-4" />
              Qayta urinish
            </button>
          ) : null}
        </div>
      </div>
    </section>
  );
}

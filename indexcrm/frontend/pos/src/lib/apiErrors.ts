import { ApiError } from "@/services/api/client";

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
    return Object.entries(detail as Record<string, unknown>)
      .filter(([key]) => !["code", "message"].includes(key))
      .map(([key, value]) => `${key}: ${stringifyDetail(value)}`)
      .filter((message) => !message.endsWith(": "))
      .join(" ");
  }
  return String(detail);
}

export function formatApiError(error: unknown, fallback: string) {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return "Kirish sessiyasi tugadi. Davom etish uchun qayta kiring.";
    }
    if (error.status === 403) {
      return "Bu akkaunt ushbu amalni bajara olmaydi.";
    }
    if (error.status >= 500) {
      return "Server so'rovni bajara olmadi. Bir marta qayta urinib ko'ring, davom etsa yordamga murojaat qiling.";
    }

    return stringifyDetail(error.detail) || fallback;
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

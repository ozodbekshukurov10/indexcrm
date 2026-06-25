import { buildApiUrl } from "./client";

export type BackendHealthResult = {
  reachable: boolean;
  status: "ok" | "degraded" | "auth_required" | "unreachable";
  message: string;
  checkedAt: string;
};

type HealthResponse = {
  status?: string;
  checks?: Record<string, string>;
};

const HEALTH_TIMEOUT_MS = 2500;

export async function checkBackendHealth(): Promise<BackendHealthResult> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), HEALTH_TIMEOUT_MS);

  try {
    const response = await fetch(buildApiUrl("/health/"), {
      cache: "no-store",
      signal: controller.signal,
    });
    const body = (await response.json().catch(() => ({}))) as HealthResponse;
    if (response.status === 401 || response.status === 403) {
      return {
        reachable: true,
        status: "auth_required",
        message: "Backend API is reachable. Sign in again if checkout is blocked.",
        checkedAt: new Date().toISOString(),
      };
    }

    const checks = body.checks ?? {};
    const unhealthyChecks = Object.entries(checks)
      .filter(([, value]) => value !== "ok")
      .map(([key]) => key);

    if (!response.ok || body.status !== "ok" || unhealthyChecks.length > 0) {
      return {
        reachable: false,
        status: "degraded",
        message:
          unhealthyChecks.length > 0
            ? `Backend health degraded: ${unhealthyChecks.join(", ")}.`
            : response.status >= 500
              ? "Backend server is unavailable."
              : "Backend health check failed.",
        checkedAt: new Date().toISOString(),
      };
    }

    return {
      reachable: true,
      status: "ok",
      message: "Backend API is reachable.",
      checkedAt: new Date().toISOString(),
    };
  } catch {
    return {
      reachable: false,
      status: "unreachable",
      message: "Backend API is unreachable.",
      checkedAt: new Date().toISOString(),
    };
  } finally {
    window.clearTimeout(timeoutId);
  }
}

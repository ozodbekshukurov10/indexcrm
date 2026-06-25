const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(message: string, status: number, detail: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

export function getStoredAuthToken() {
  if (typeof window === "undefined") {
    return "";
  }
  return window.localStorage.getItem("index_pos_token") ?? "";
}

export function setStoredAuthToken(token: string) {
  if (typeof window === "undefined") {
    return;
  }
  if (token) {
    window.localStorage.setItem("index_pos_token", token);
    return;
  }
  window.localStorage.removeItem("index_pos_token");
}

export function clearStoredAuthToken() {
  setStoredAuthToken("");
}

export function buildApiUrl(
  path: string,
  query?: Record<string, string | number | undefined>,
) {
  const url = new URL(
    path.replace(/^\//, ""),
    `${API_BASE_URL.replace(/\/$/, "")}/`,
  );
  Object.entries(query ?? {}).forEach(([key, value]) => {
    if (value !== undefined && value !== "") {
      url.searchParams.set(key, String(value));
    }
  });
  return url.toString();
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
  query?: Record<string, string | number | undefined>,
): Promise<T> {
  const token = getStoredAuthToken();
  const headers = new Headers(options.headers);

  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(buildApiUrl(path, query), {
    ...options,
    headers,
  });

  const contentType = response.headers.get("Content-Type") ?? "";
  const body = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    throw new ApiError("API request failed", response.status, body);
  }

  return body as T;
}

export async function downloadApiFile(
  path: string,
  filename: string,
  query?: Record<string, string | number | undefined>,
) {
  const token = getStoredAuthToken();
  const headers = new Headers();

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(buildApiUrl(path, query), { headers });
  if (!response.ok) {
    const contentType = response.headers.get("Content-Type") ?? "";
    const body = contentType.includes("application/json")
      ? await response.json()
      : await response.text();
    throw new ApiError("File download failed", response.status, body);
  }

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

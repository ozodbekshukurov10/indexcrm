import { ApiError, buildApiUrl } from "./client";

export type AuthTokenResponse = {
  access: string;
  refresh: string;
};

export type LoginCredentials = {
  email: string;
  password: string;
};

export async function loginWithCredentials(
  credentials: LoginCredentials,
): Promise<AuthTokenResponse> {
  const response = await fetch(buildApiUrl("/auth/token/"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(credentials),
  });

  const contentType = response.headers.get("Content-Type") ?? "";
  const body = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    throw new ApiError("Login failed", response.status, body);
  }

  return body as AuthTokenResponse;
}

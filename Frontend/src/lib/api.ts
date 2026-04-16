/**
 * lib/api.ts
 * ──────────────────────────────────────────────────────────────────
 * Central API layer.  Every fetch goes through apiFetch(), which:
 *   • Attaches the JWT Authorization header automatically.
 *   • Throws a typed ApiError on non-2xx responses.
 *   • Re-exports API_BASE_URL so other files import from one place.
 */

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

// ── Token helpers ─────────────────────────────────────────────────

const TOKEN_KEY = "nd_auth_token";
const USER_KEY = "nd_auth_user";

export const getToken = (): string | null => localStorage.getItem(TOKEN_KEY);

// ── Typed error ───────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// ── Core fetch wrapper ────────────────────────────────────────────

export async function apiFetch<T = unknown>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getToken();

  const method = (options.method ?? "GET").toUpperCase();
  const headers: HeadersInit = {
    ...(options.headers as Record<string, string>),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(method !== "GET" && method !== "HEAD" ? { "Content-Type": "application/json" } : {}),
  };

  const res = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });

  if (!res.ok) {
    let message = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      message = body?.detail ?? body?.error ?? message;
    } catch { /* ignore parse errors */ }

    if (res.status === 401) {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
    }

    throw new ApiError(res.status, message);
  }

  // 204 No Content
  if (res.status === 204) return undefined as T;

  return res.json() as Promise<T>;
}

// ── Convenience methods ───────────────────────────────────────────

export const apiGet  = <T>(path: string) =>
  apiFetch<T>(path, { method: "GET" });

export const apiPost = <T>(path: string, body: unknown) =>
  apiFetch<T>(path, { method: "POST",  body: JSON.stringify(body) });

export const apiPatch = <T>(path: string, body: unknown) =>
  apiFetch<T>(path, { method: "PATCH", body: JSON.stringify(body) });

export const apiDelete = <T>(path: string) =>
  apiFetch<T>(path, { method: "DELETE" });

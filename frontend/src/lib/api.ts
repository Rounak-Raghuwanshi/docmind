/**
 * Fetch wrapper.
 *
 * - The access token lives only in memory (never localStorage, so XSS can't exfiltrate a
 *   long-lived credential). The refresh token is an httpOnly cookie the JS can't read.
 * - On a 401 the client refreshes once and retries. Concurrent 401s share one refresh call,
 *   so tabs/requests never race each other into the server's token-reuse detection.
 */
import type { TokenResponse, User } from "@/api/types";

export const API_URL =
  (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") ?? "";
export const STREAM_URL =
  (import.meta.env.VITE_STREAM_URL as string | undefined)?.replace(/\/$/, "") || API_URL;

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details?: unknown,
    public requestId?: string,
    public retryAfter?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

let accessToken: string | null = null;
let refreshInFlight: Promise<TokenResponse | null> | null = null;
const listeners = new Set<(user: User | null) => void>();

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

/** Notified when the session changes (login, refresh with a new user, or forced logout). */
export function onSessionChange(fn: (user: User | null) => void): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

function emitSession(user: User | null): void {
  listeners.forEach((fn) => fn(user));
}

export async function toApiError(res: Response): Promise<ApiError> {
  let body: {
    error?: { code?: string; message?: string; details?: unknown; request_id?: string };
  } = {};
  try {
    body = await res.json();
  } catch {
    /* non-JSON error (proxy page, etc.) */
  }
  const retry = res.headers.get("Retry-After");
  return new ApiError(
    res.status,
    body.error?.code ?? "http_error",
    body.error?.message ?? (res.status >= 500 ? "The server had a problem" : res.statusText),
    body.error?.details,
    body.error?.request_id ?? res.headers.get("X-Request-ID") ?? undefined,
    retry ? Number(retry) : undefined,
  );
}

/** Exchange the refresh cookie for a new access token. Resolves null when there's no session. */
export function refreshSession(): Promise<TokenResponse | null> {
  refreshInFlight ??= (async () => {
    try {
      const res = await fetch(`${API_URL}/api/auth/refresh`, {
        method: "POST",
        credentials: "include",
      });
      if (!res.ok) {
        setAccessToken(null);
        return null;
      }
      const data = (await res.json()) as TokenResponse;
      setAccessToken(data.access_token);
      return data;
    } catch {
      return null;
    } finally {
      refreshInFlight = null;
    }
  })();
  return refreshInFlight;
}

export interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  /** Skip the refresh-and-retry dance (used by the auth endpoints themselves). */
  noRetry?: boolean;
}

/** Low-level: returns the raw Response (used for streams and binary downloads). */
export async function rawFetch(
  path: string,
  { body, noRetry, headers, ...init }: RequestOptions = {},
  base = API_URL,
): Promise<Response> {
  const doFetch = () => {
    const h = new Headers(headers);
    if (accessToken) h.set("Authorization", `Bearer ${accessToken}`);
    let payload: BodyInit | undefined;
    if (body instanceof FormData) payload = body;
    else if (body !== undefined) {
      h.set("Content-Type", "application/json");
      payload = JSON.stringify(body);
    }
    return fetch(`${base}${path}`, { ...init, headers: h, body: payload, credentials: "include" });
  };

  let res = await doFetch();
  if (res.status === 401 && !noRetry) {
    const refreshed = await refreshSession();
    if (refreshed) {
      res = await doFetch();
    } else {
      emitSession(null);
    }
  }
  return res;
}

export async function api<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const res = await rawFetch(path, options);
  if (!res.ok) throw await toApiError(res);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export function sessionStarted(data: TokenResponse): void {
  setAccessToken(data.access_token);
  emitSession(data.user);
}

export function sessionEnded(): void {
  setAccessToken(null);
  emitSession(null);
}

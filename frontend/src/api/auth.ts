import { api, sessionEnded, sessionStarted } from "@/lib/api";
import type { TokenResponse, User } from "./types";

export async function login(email: string, password: string): Promise<TokenResponse> {
  const data = await api<TokenResponse>("/api/auth/login", {
    method: "POST",
    body: { email, password },
    noRetry: true,
  });
  sessionStarted(data);
  return data;
}

export async function register(full_name: string, email: string, password: string): Promise<User> {
  return api<User>("/api/auth/register", {
    method: "POST",
    body: { full_name, email, password },
    noRetry: true,
  });
}

export async function demoLogin(): Promise<TokenResponse> {
  const data = await api<TokenResponse>("/api/auth/demo", { method: "POST", noRetry: true });
  sessionStarted(data);
  return data;
}

export async function logout(): Promise<void> {
  try {
    await api<void>("/api/auth/logout", { method: "POST", noRetry: true });
  } finally {
    sessionEnded();
  }
}

import { useQueryClient } from "@tanstack/react-query";
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import type { User } from "@/api/types";
import { onSessionChange, refreshSession } from "@/lib/api";

interface AuthState {
  user: User | null;
  status: "loading" | "authenticated" | "anonymous";
}

const AuthContext = createContext<AuthState>({ user: null, status: "loading" });

/** On load, try to resume the session from the refresh cookie (the access token is memory-only). */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ user: null, status: "loading" });
  const qc = useQueryClient();

  useEffect(() => {
    let mounted = true;
    refreshSession().then((data) => {
      if (mounted)
        setState(
          data ? { user: data.user, status: "authenticated" } : { user: null, status: "anonymous" },
        );
    });
    const off = onSessionChange((user) => {
      if (!user) qc.clear(); // never show the previous user's cached data
      setState(user ? { user, status: "authenticated" } : { user: null, status: "anonymous" });
    });
    return () => {
      mounted = false;
      off();
    };
  }, [qc]);

  return <AuthContext.Provider value={state}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  return useContext(AuthContext);
}

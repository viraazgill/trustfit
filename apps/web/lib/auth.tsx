"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { api, getToken, setToken, type Schemas } from "@/lib/api/client";

type User = Schemas["MeOut"];
export type Role = "viewer" | "analyst" | "admin";
const ROLE_RANK: Record<Role, number> = { viewer: 0, analyst: 1, admin: 2 };

interface AuthState {
  user: User | null;
  ready: boolean;
  login: (email: string, password: string) => Promise<User>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const restore = getToken()
      ? api<User>("/auth/me").then(setUser).catch(() => setToken(null))
      : Promise.resolve();
    restore.finally(() => setReady(true));
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  useEffect(() => {
    window.addEventListener("trustfit:unauthorized", logout);
    return () => window.removeEventListener("trustfit:unauthorized", logout);
  }, [logout]);

  const login = useCallback(async (email: string, password: string) => {
    const tok = await api<Schemas["TokenOut"]>("/auth/login", "POST", { email, password });
    setToken(tok.access_token);
    const me = await api<User>("/auth/me");
    setUser(me);
    return me;
  }, []);

  const value = useMemo(() => ({ user, ready, login, logout }), [user, ready, login, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}

export function hasRole(user: User | null, role: Role): boolean {
  return !!user && ROLE_RANK[user.role as Role] >= ROLE_RANK[role];
}

/** Renders children only for a signed-in user with at least `role`; otherwise sends them to /login. */
export function RequireRole({ role, children }: { role: Role; children: React.ReactNode }) {
  const { user, ready } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (ready && !user) router.replace(`/login?next=${encodeURIComponent(pathname)}`);
  }, [ready, user, router, pathname]);

  if (!ready || !user) return <p className="p-8 text-sm text-ink-muted">Loading…</p>;
  if (!hasRole(user, role))
    return <p className="p-8 text-sm text-ink-muted">This page needs the {role} role. You are signed in as a {user.role}.</p>;
  return <>{children}</>;
}

/**
 * AuthContext.tsx
 * JWT-based authentication context for the Leave Management frontend.
 *
 * Usage:
 *   1. Wrap your app:  <AuthProvider><App /></AuthProvider>
 *   2. Consume:        const { user, token, login, logout } = useAuth();
 */

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from "react";
import { API_BASE_URL } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

export type UserRole = "Employee" | "Manager" | "Admin";

export interface AuthUser {
  id: string;
  name: string;
  role: UserRole;
  department: string;
  email: string;
  avatar_color?: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  token: string | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (credentials: LoginPayload) => Promise<void>;
  logout: () => void;
  /** True when the signed-in user has at least the given role level. */
  hasRole: (...roles: UserRole[]) => boolean;
}

interface LoginPayload {
  user_id: string;
  user_name: string;
  password: string;
  department?: string;
}

// ── Constants ─────────────────────────────────────────────────────────────────

const TOKEN_KEY = "nd_auth_token";
const USER_KEY  = "nd_auth_user";

const clearStoredAuth = () => {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
};

const isTokenExpired = (token: string): boolean => {
  try {
    const [, payload] = token.split(".");
    if (!payload) return true;
    const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
    const decoded = JSON.parse(atob(normalized.padEnd(normalized.length + ((4 - normalized.length % 4) % 4), "=")));
    const exp = Number(decoded?.exp ?? 0);
    return !exp || exp <= Math.floor(Date.now() / 1000);
  } catch {
    return true;
  }
};

// ── Context ───────────────────────────────────────────────────────────────────

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

// ── Provider ──────────────────────────────────────────────────────────────────

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user,    setUser]    = useState<AuthUser | null>(null);
  const [token,   setToken]   = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const isAuthenticated = Boolean(user && token);

  // Rehydrate from localStorage on mount
  useEffect(() => {
    const savedToken = localStorage.getItem(TOKEN_KEY);
    const savedUser  = localStorage.getItem(USER_KEY);
    if (savedToken && savedUser) {
      try {
        if (isTokenExpired(savedToken)) {
          clearStoredAuth();
          setLoading(false);
          return;
        }
        setToken(savedToken);
        setUser(JSON.parse(savedUser));
      } catch {
        clearStoredAuth();
      }
    }
    setLoading(false);
  }, []);

  const login = async (credentials: LoginPayload) => {
    const res = await fetch(`${API_BASE_URL}/api/authenticate`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(credentials),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err?.detail ?? "Login failed");
    }

    const data = await res.json();          // { token, user }
    const jwt:    string   = data.token;
    const authUser: AuthUser = {
      id:           String(data.user.id),
      name:         data.user.name ?? "",
      role:         data.user.role as UserRole,
      department:   data.user.department ?? "",
      email:        data.user.email ?? "",
      avatar_color: data.user.avatar_color,
    };

    localStorage.setItem(TOKEN_KEY, jwt);
    localStorage.setItem(USER_KEY, JSON.stringify(authUser));
    setToken(jwt);
    setUser(authUser);
  };

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setToken(null);
    setUser(null);
  };

  const hasRole = (...roles: UserRole[]) =>
    user !== null && roles.includes(user.role);

  return (
    <AuthContext.Provider
      value={{ user, token, loading, isAuthenticated, login, logout, hasRole }}
    >
      {children}
    </AuthContext.Provider>
  );
};

// ── Hook ──────────────────────────────────────────────────────────────────────

export const useAuth = (): AuthContextValue => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
};

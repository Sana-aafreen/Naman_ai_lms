import React, { createContext, useContext, useState, useCallback } from "react";
import { API_BASE_URL } from "@/lib/api";

export type UserRole = "Employee" | "Manager" | "Admin";

interface User {
  id: string;
  name: string;
  role: UserRole;
  initials: string;
  department: string;
}

interface AuthContextType {
  user: User | null;
  login: (userId: string, userName: string, password: string, department: string, role: UserRole) => Promise<boolean>;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);

  const login = useCallback(async (
    userId: string,
    userName: string,
    password: string,
    department: string,
    role: UserRole
  ) => {
    try {
      const sheetToCheck = role === "Manager" ? "Manager" : role === "Admin" ? "Admin" : department;

      const response = await fetch(`${API_BASE_URL}/api/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          userId,
          userName,
          password,
          department: sheetToCheck
        })
      });

      const data = await response.json();

      if (data.success && data.user) {
        const initials = userName
          .split(" ")
          .map(n => n[0])
          .join("")
          .slice(0, 2)
          .toUpperCase() || "NN";

        const resolvedRole = (data.user.role as UserRole) || role;

        setUser({
          id: userId,
          name: data.user.userName || userName,
          role: resolvedRole,
          initials,
          department: role === "Manager" || role === "Admin" ? role : department
        });
        return true;
      }

      return false;
    } catch (error) {
      console.error("Login failed:", error);
      return false;
    }
  }, []);

  const logout = useCallback(() => setUser(null), []);

  return (
    <AuthContext.Provider value={{ user, login, logout, isAuthenticated: !!user }}>
      {children}
    </AuthContext.Provider>
  );
};

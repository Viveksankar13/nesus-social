"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useRouter } from "next/navigation";
import { apiClient, setAccessToken } from "@/lib/api-client";
import type { User } from "@/types";

interface LoginCredentials {
  username_or_email?: string;
  email_or_username?: string;
  password: string;
}

interface RegisterData {
  username: string;
  email: string;
  password: string;
  display_name: string;
  usn?: string;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  isAdmin: boolean;
  login: (credentials: LoginCredentials) => Promise<User>;
  register: (data: RegisterData) => Promise<{ message: string }>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<User | null>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const router = useRouter();

  const refreshUser = useCallback(async (): Promise<User | null> => {
    try {
      const userData = await apiClient.get<User>("/users/me");
      setUser(userData);
      return userData;
    } catch {
      setUser(null);
      return null;
    }
  }, []);

  // Initial silent authentication restoration on mount
  useEffect(() => {
    let isMounted = true;

    async function initAuth() {
      try {
        const refreshRes = await fetch("/api/v1/auth/refresh", {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
        });

        if (refreshRes.ok) {
          const data = await refreshRes.json();
          setAccessToken(data.access_token);
          let userData: User | null = (data.user as User) ?? null;
          if (!userData) {
            userData = await apiClient.get<User>("/users/me");
          }
          if (isMounted) {
            setUser(userData);
          }
        } else {
          setAccessToken(null);
          if (isMounted) {
            setUser(null);
          }
        }
      } catch {
        setAccessToken(null);
        if (isMounted) {
          setUser(null);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    initAuth();

    return () => {
      isMounted = false;
    };
  }, []);

  const login = useCallback(
    async (credentials: LoginCredentials): Promise<User> => {
      const identifier =
        credentials.email_or_username || credentials.username_or_email || "";
      const res = await apiClient.post<{ access_token: string; user?: User }>(
        "/auth/login",
        {
          email_or_username: identifier,
          username_or_email: identifier,
          password: credentials.password,
        }
      );
      setAccessToken(res.access_token);
      let userData: User | null = res.user ?? null;
      if (!userData) {
        userData = await apiClient.get<User>("/users/me");
      }
      setUser(userData);
      return userData;
    },
    []
  );

  const register = useCallback(
    async (data: RegisterData): Promise<{ message: string }> => {
      return await apiClient.post<{ message: string }>("/auth/register", data);
    },
    []
  );

  const logout = useCallback(async (): Promise<void> => {
    try {
      await apiClient.post("/auth/logout");
    } catch {
      // Ignore logout errors
    } finally {
      setAccessToken(null);
      setUser(null);
      router.push("/login");
    }
  }, [router]);

  const value = useMemo(
    () => ({
      user,
      isLoading,
      isAuthenticated: !!user,
      isAdmin: user?.role === "admin",
      login,
      register,
      logout,
      refreshUser,
    }),
    [user, isLoading, login, register, logout, refreshUser]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

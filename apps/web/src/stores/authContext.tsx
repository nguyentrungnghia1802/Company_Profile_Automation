"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { getApiClient } from "@vcps/api-client";
import {
  normalizeCurrentUserPayload,
  resolveAuthBootstrap,
  shouldFallbackToAutoLogin,
  TOKEN_KEY,
  WORKSPACE_KEY,
} from "./authBootstrap";
import { normalizeClientError, type NormalizedClientError } from "../utils/errors";

export interface ActiveWorkspace {
  id: string;
  name: string;
  slug: string;
  role: string;
  capabilities: string[];
}

export interface WorkspaceSummary {
  id: string;
  name: string;
  slug: string;
  role: string;
}

export interface CurrentUser {
  id: string;
  email: string | null;
  displayName: string;
  preferredLocale: string;
  status: string;
  activeWorkspace: ActiveWorkspace | null;
  workspaces: WorkspaceSummary[];
  capabilities: string[];
}

interface AuthContextType {
  user: CurrentUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  authError: NormalizedClientError | null;
  activeWorkspace: ActiveWorkspace | null;
  capabilities: string[];
  login: (token: string, workspaceId?: string | null) => Promise<void>;
  retryLocalLogin: () => Promise<void>;
  logout: () => Promise<void>;
  switchWorkspace: (workspaceId: string) => void;
  hasCapability: (capability: string) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: React.ReactNode;
  autoLoginToken?: string | null;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children, autoLoginToken }) => {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [authError, setAuthError] = useState<NormalizedClientError | null>(null);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<string | null>(null);
  const initializationStarted = useRef(false);

  const fetchMe = useCallback(async (token: string, wsId?: string | null): Promise<CurrentUser | null> => {
    try {
      const client = getApiClient();
      const rawMeData = await client.getMe(token, wsId || undefined);
      const meData = normalizeCurrentUserPayload(rawMeData);
      if (!meData) {
        throw { code: "AUTH_USER_PAYLOAD_INVALID" };
      }
      setUser(meData);
      setAuthError(null);
      return meData;
    } catch (error) {
      localStorage.removeItem(TOKEN_KEY);
      setUser(null);
      setAuthError(normalizeClientError(error));
      return null;
    }
  }, []);

  const login = useCallback(async (token: string, workspaceId?: string | null) => {
    setIsLoading(true);
    setAuthError(null);
    try {
      const client = getApiClient();
      await client.exchangeToken(token);
      localStorage.setItem(TOKEN_KEY, token);
      await fetchMe(token, workspaceId === undefined ? selectedWorkspaceId : workspaceId);
    } catch (error) {
      setAuthError(normalizeClientError(error));
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, [fetchMe, selectedWorkspaceId]);

  const retryLocalLogin = useCallback(async () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(WORKSPACE_KEY);
    setSelectedWorkspaceId(null);
    setUser(null);
    setAuthError(null);

    if (!autoLoginToken) {
      setAuthError(normalizeClientError({ code: "AUTH_NOT_CONFIGURED" }));
      return;
    }

    await login(autoLoginToken, null);
  }, [autoLoginToken, login]);

  const logout = useCallback(async () => {
    const savedToken = localStorage.getItem(TOKEN_KEY);
    if (savedToken) {
      try {
        const client = getApiClient();
        await client.logout(savedToken);
      } catch {
        // Ignore network errors on logout
      }
    }
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(WORKSPACE_KEY);
    setUser(null);
    setAuthError(null);
  }, []);

  const switchWorkspace = useCallback((workspaceId: string) => {
    localStorage.setItem(WORKSPACE_KEY, workspaceId);
    setSelectedWorkspaceId(workspaceId);
    const savedToken = localStorage.getItem(TOKEN_KEY);
    if (savedToken) {
      fetchMe(savedToken, workspaceId);
    }
  }, [fetchMe]);

  const hasCapability = useCallback((capability: string): boolean => {
    return user?.capabilities.includes(capability) ?? false;
  }, [user]);

  useEffect(() => {
    if (initializationStarted.current) return;
    initializationStarted.current = true;

    const plan = resolveAuthBootstrap(localStorage, autoLoginToken);
    setSelectedWorkspaceId(plan.workspaceId);

    if (!plan.token) {
      setAuthError(normalizeClientError({ code: "AUTH_NOT_CONFIGURED" }));
      setIsLoading(false);
      return;
    }

    void (async () => {
      try {
        const client = getApiClient();
        if (plan.shouldExchange) {
          await client.exchangeToken(plan.token!);
          localStorage.setItem(TOKEN_KEY, plan.token!);
        }

        const authenticated = await fetchMe(plan.token!, plan.workspaceId);
        const fallbackToken = plan.autoLoginToken;
        if (fallbackToken && shouldFallbackToAutoLogin(plan, authenticated)) {
          localStorage.removeItem(WORKSPACE_KEY);
          setSelectedWorkspaceId(null);
          await client.exchangeToken(fallbackToken);
          localStorage.setItem(TOKEN_KEY, fallbackToken);
          await fetchMe(fallbackToken, null);
        }
      } catch (error) {
        localStorage.removeItem(TOKEN_KEY);
        setUser(null);
        setAuthError(normalizeClientError(error));
      } finally {
        setIsLoading(false);
      }
    })();
  }, [autoLoginToken, fetchMe]);

  const contextValue = useMemo(
    () => ({
      user,
      isAuthenticated: !!user,
      isLoading,
      authError,
      activeWorkspace: user?.activeWorkspace ?? null,
      capabilities: user?.capabilities ?? [],
      login,
      retryLocalLogin,
      logout,
      switchWorkspace,
      hasCapability,
    }),
    [authError, hasCapability, isLoading, login, logout, retryLocalLogin, switchWorkspace, user],
  );

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

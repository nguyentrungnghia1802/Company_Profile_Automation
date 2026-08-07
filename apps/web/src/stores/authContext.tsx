"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { getApiClient } from "@vcps/api-client";

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
  activeWorkspace: ActiveWorkspace | null;
  capabilities: string[];
  login: (token: string) => Promise<void>;
  logout: () => Promise<void>;
  switchWorkspace: (workspaceId: string) => void;
  hasCapability: (capability: string) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_KEY = "vcps_access_token";
const WORKSPACE_KEY = "vcps_active_workspace_id";

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<string | null>(null);

  const fetchMe = useCallback(async (token: string, wsId?: string | null) => {
    try {
      const client = getApiClient();
      const meData = await client.getMe(token, wsId || undefined);
      setUser(meData);
    } catch {
      localStorage.removeItem(TOKEN_KEY);
      setUser(null);
    }
  }, []);

  useEffect(() => {
    const savedToken = localStorage.getItem(TOKEN_KEY);
    const savedWsId = localStorage.getItem(WORKSPACE_KEY);
    setSelectedWorkspaceId(savedWsId);

    if (savedToken) {
      fetchMe(savedToken, savedWsId).finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, [fetchMe]);

  const login = async (token: string) => {
    setIsLoading(true);
    try {
      const client = getApiClient();
      await client.exchangeToken(token);
      localStorage.setItem(TOKEN_KEY, token);
      await fetchMe(token, selectedWorkspaceId);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
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
    setUser(null);
  };

  const switchWorkspace = (workspaceId: string) => {
    localStorage.setItem(WORKSPACE_KEY, workspaceId);
    setSelectedWorkspaceId(workspaceId);
    const savedToken = localStorage.getItem(TOKEN_KEY);
    if (savedToken) {
      fetchMe(savedToken, workspaceId);
    }
  };

  const hasCapability = (capability: string): boolean => {
    return user?.capabilities.includes(capability) ?? false;
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        activeWorkspace: user?.activeWorkspace ?? null,
        capabilities: user?.capabilities ?? [],
        login,
        logout,
        switchWorkspace,
        hasCapability,
      }}
    >
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

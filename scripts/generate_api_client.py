"""TypeScript API Client Generator.

Reads docs/project/openapi.json and generates a typed TypeScript client
in packages/api-client/src/index.ts.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

CLIENT_TEMPLATE = """/**
 * AUTO-GENERATED FILE — DO NOT EDIT MANUALLY.
 * Generated from docs/project/openapi.json
 */

export interface ErrorDetail {
  code: string;
  message: string;
  details?: Record<string, unknown>;
  retryable?: boolean;
}

export interface ErrorEnvelope {
  error: ErrorDetail;
}

export interface HealthResponse {
  status: string;
  version: string;
}

export interface ReadinessResponse {
  status: string;
  checks: Record<string, string>;
}

export class ApiError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly statusCode: number,
    public readonly details?: Record<string, unknown>,
    public readonly retryable: boolean = false
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export interface ApiClientConfig {
  baseUrl: string;
  fetch?: typeof fetch;
}

export class ApiClient {
  private readonly baseUrl: string;
  private readonly fetchImpl: typeof fetch;

  constructor(config: ApiClientConfig) {
    this.baseUrl = config.baseUrl.replace(/\\/+$/, "");
    this.fetchImpl = config.fetch || globalThis.fetch;
  }

  private async request<T>(path: string, options?: RequestInit): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const response = await this.fetchImpl(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });

    if (!response.ok) {
      try {
        const errorBody: ErrorEnvelope = await response.json();
        if (errorBody?.error) {
          throw new ApiError(
            errorBody.error.code,
            errorBody.error.message,
            response.status,
            errorBody.error.details,
            errorBody.error.retryable ?? false
          );
        }
      } catch (err) {
        if (err instanceof ApiError) throw err;
      }
      throw new ApiError(
        "HTTP_ERROR",
        `Request failed with status ${response.status}`,
        response.status
      );
    }

    return response.json() as Promise<T>;
  }

  async getHealth(): Promise<HealthResponse> {
    return this.request<HealthResponse>("/health");
  }

  async getReadiness(): Promise<ReadinessResponse> {
    return this.request<ReadinessResponse>("/ready");
  }

  async exchangeToken(token: string): Promise<Record<string, unknown>> {
    return this.request<Record<string, unknown>>("/auth/exchange", {
      method: "POST",
      body: JSON.stringify({ token }),
    });
  }

  async logout(token: string): Promise<Record<string, unknown>> {
    return this.request<Record<string, unknown>>("/auth/logout", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
  }

  async getMe(token: string, workspaceId?: string): Promise<any> {
    const headers: Record<string, string> = { Authorization: `Bearer ${token}` };
    if (workspaceId) {
      headers["X-Workspace-ID"] = workspaceId;
    }
    const res = await this.request<{ success: boolean; data: any }>("/me", { headers });
    return res.data;
  }

  async updateMe(
    token: string,
    payload: { display_name?: string; preferred_locale?: string }
  ): Promise<any> {
    const res = await this.request<{ success: boolean; data: any }>("/me", {
      method: "PATCH",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(payload),
    });
    return res.data;
  }

  async listWorkspaces(token: string): Promise<any[]> {
    const res = await this.request<{ success: boolean; data: any[] }>("/workspaces", {
      headers: { Authorization: `Bearer ${token}` },
    });
    return res.data;
  }

  async getWorkspace(token: string, workspaceId: string): Promise<any> {
    const res = await this.request<{ success: boolean; data: any }>(`/workspaces/${workspaceId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return res.data;
  }

  async listWorkspaceMembers(token: string, workspaceId: string): Promise<any[]> {
    const res = await this.request<{ success: boolean; data: any[] }>(
      `/workspaces/${workspaceId}/members`,
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    return res.data;
  }

  async addWorkspaceMember(
    token: string,
    workspaceId: string,
    payload: { email: string; display_name?: string; role?: string }
  ): Promise<any> {
    const res = await this.request<{ success: boolean; data: any }>(
      `/workspaces/${workspaceId}/members`,
      {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: JSON.stringify(payload),
      }
    );
    return res.data;
  }

  async updateWorkspaceMember(
    token: string,
    workspaceId: string,
    memberId: string,
    payload: { role?: string; status?: string }
  ): Promise<any> {
    const res = await this.request<{ success: boolean; data: any }>(
      `/workspaces/${workspaceId}/members/${memberId}`,
      {
        method: "PATCH",
        headers: { Authorization: `Bearer ${token}` },
        body: JSON.stringify(payload),
      }
    );
    return res.data;
  }

  async deactivateWorkspaceMember(
    token: string,
    workspaceId: string,
    memberId: string
  ): Promise<any> {
    const res = await this.request<{ success: boolean; data: any }>(
      `/workspaces/${workspaceId}/members/${memberId}`,
      {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    return res.data;
  }
}

let defaultClientInstance: ApiClient | null = null;

export function getApiClient(baseUrl?: string): ApiClient {
  const url = baseUrl || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
  if (!defaultClientInstance) {
    defaultClientInstance = new ApiClient({ baseUrl: url });
  }
  return defaultClientInstance;
}
"""


def main() -> int:
    """Generate TypeScript API client."""
    root_dir = Path(__file__).resolve().parent.parent
    openapi_path = root_dir / "docs" / "project" / "openapi.json"
    output_path = root_dir / "packages" / "api-client" / "src" / "index.ts"

    if not openapi_path.exists():
        print(f"[ERROR] OpenAPI schema snapshot missing: {openapi_path}")
        print("Run `python scripts/generate_openapi.py` first.")
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(CLIENT_TEMPLATE, encoding="utf-8")
    print(f"[SUCCESS] Generated TypeScript API client -> {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

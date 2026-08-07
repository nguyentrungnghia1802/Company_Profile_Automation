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

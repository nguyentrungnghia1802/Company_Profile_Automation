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

declare const process: { env: Record<string, string | undefined> };

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

  async listCompanies(token: string, workspaceId: string, status?: string): Promise<any[]> {
    const query = status ? `?status=${encodeURIComponent(status)}` : "";
    const res = await this.request<{ success: boolean; data: any[] }>(`/companies${query}`, {
      headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
    });
    return res.data;
  }

  async createCompany(
    token: string,
    workspaceId: string,
    payload: {
      company_name: string;
      tax_id?: string;
      legal_name?: string;
      registration_number?: string;
      industry?: string;
      website_url?: string;
    }
  ): Promise<any> {
    const res = await this.request<{ success: boolean; data: any }>("/companies", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
      body: JSON.stringify(payload),
    });
    return res.data;
  }

  async resolveCompany(
    token: string,
    workspaceId: string,
    payload: { company_name: string; tax_id?: string; registration_number?: string }
  ): Promise<any[]> {
    const res = await this.request<{ success: boolean; data: any[] }>("/companies/resolve", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
      body: JSON.stringify(payload),
    });
    return res.data;
  }

  async getCompany(token: string, workspaceId: string, companyId: string): Promise<any> {
    const res = await this.request<{ success: boolean; data: any }>(`/companies/${companyId}`, {
      headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
    });
    return res.data;
  }

  async updateCompany(
    token: string,
    workspaceId: string,
    companyId: string,
    payload: Record<string, unknown>
  ): Promise<any> {
    const res = await this.request<{ success: boolean; data: any }>(`/companies/${companyId}`, {
      method: "PATCH",
      headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
      body: JSON.stringify(payload),
    });
    return res.data;
  }

  async mergeCompany(
    token: string,
    workspaceId: string,
    targetCompanyId: string,
    sourceCompanyId: string
  ): Promise<any> {
    const res = await this.request<{ success: boolean; data: any }>(
      `/companies/${targetCompanyId}/merge`,
      {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
        body: JSON.stringify({ source_company_id: sourceCompanyId }),
      }
    );
    return res.data;
  }

  async archiveCompany(token: string, workspaceId: string, companyId: string): Promise<any> {
    const res = await this.request<{ success: boolean; data: any }>(
      `/companies/${companyId}/archive`,
      {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
      }
    );
    return res.data;
  }

  async restoreCompany(token: string, workspaceId: string, companyId: string): Promise<any> {
    const res = await this.request<{ success: boolean; data: any }>(
      `/companies/${companyId}/restore`,
      {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
      }
    );
    return res.data;
  }

  async triggerCompanyResearch(
    token: string,
    workspaceId: string,
    companyId: string,
    payload?: { job_type?: string; scope?: Record<string, unknown>; requested_locale?: string }
  ): Promise<any> {
    const res = await this.request<{ success: boolean; data: any }>(
      `/companies/${companyId}/research`,
      {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
        body: JSON.stringify(payload || {}),
      }
    );
    return res.data;
  }

  async listResearchJobs(token: string, workspaceId: string, companyId?: string): Promise<any[]> {
    const query = companyId ? `?company_id=${encodeURIComponent(companyId)}` : "";
    const res = await this.request<{ success: boolean; data: any[] }>(`/research-jobs${query}`, {
      headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
    });
    return res.data;
  }

  async getResearchJob(token: string, workspaceId: string, jobId: string): Promise<any> {
    const res = await this.request<{ success: boolean; data: any }>(`/research-jobs/${jobId}`, {
      headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
    });
    return res.data;
  }

  async cancelResearchJob(token: string, workspaceId: string, jobId: string): Promise<any> {
    const res = await this.request<{ success: boolean; data: any }>(
      `/research-jobs/${jobId}/cancel`,
      {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
      }
    );
    return res.data;
  }

  async addSourceURL(
    token: string,
    workspaceId: string,
    payload: { company_id: string; url: string; source_type?: string }
  ): Promise<any> {
    const res = await this.request<{ success: boolean; data: any }>("/sources", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
      body: JSON.stringify(payload),
    });
    return res.data;
  }

  async listCompanySources(token: string, workspaceId: string, companyId: string): Promise<any[]> {
    const res = await this.request<{ success: boolean; data: any[] }>(
      `/sources?company_id=${encodeURIComponent(companyId)}`,
      {
        headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
      }
    );
    return res.data;
  }

  async listDomainPolicies(token: string, workspaceId: string): Promise<any[]> {
    const res = await this.request<{ success: boolean; data: any[] }>("/domain-policies", {
      headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
    });
    return res.data;
  }

  async addDomainPolicy(
    token: string,
    workspaceId: string,
    payload: { domain: string; policy_type?: string; reason?: string }
  ): Promise<any> {
    const res = await this.request<{ success: boolean; data: any }>("/domain-policies", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
      body: JSON.stringify(payload),
    });
    return res.data;
  }

  async deleteDomainPolicy(token: string, workspaceId: string, id: string): Promise<any> {
    const res = await this.request<{ success: boolean }>(`/domain-policies/${id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
    });
    return res;
  }

  async listCompanyFacts(token: string, workspaceId: string, companyId: string): Promise<any[]> {
    const res = await this.request<any[]>(`/companies/${encodeURIComponent(companyId)}/facts`, {
      headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
    });
    return res;
  }

  async listCompanyConflicts(token: string, workspaceId: string, companyId: string): Promise<any[]> {
    const res = await this.request<any[]>(`/companies/${encodeURIComponent(companyId)}/conflicts`, {
      headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
    });
    return res;
  }

  async resolveConflict(
    token: string,
    workspaceId: string,
    companyId: string,
    conflictId: string,
    payload: { resolution_type: string; reason: string; selected_candidate_ids?: string[] }
  ): Promise<any> {
    const res = await this.request<any>(
      `/companies/${encodeURIComponent(companyId)}/conflicts/${encodeURIComponent(conflictId)}/resolve`,
      {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
        body: JSON.stringify(payload),
      }
    );
    return res;
  }

  async listSourceAttempts(token: string, workspaceId: string, sourceId: string): Promise<any[]> {
    const res = await this.request<{ success: boolean; data: any[] }>(
      `/sources/${encodeURIComponent(sourceId)}/attempts`,
      {
        headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
      }
    );
    return res.data || [];
  }

  async listSourceSnapshots(token: string, workspaceId: string, sourceId: string): Promise<any[]> {
    const res = await this.request<{ success: boolean; data: any[] }>(
      `/sources/${encodeURIComponent(sourceId)}/snapshots`,
      {
        headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
      }
    );
    return res.data || [];
  }

  async listSnapshotBlocks(token: string, workspaceId: string, snapshotId: string): Promise<any[]> {
    const res = await this.request<{ success: boolean; data: any[] }>(
      `/snapshots/${encodeURIComponent(snapshotId)}/blocks`,
      {
        headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
      }
    );
    return res.data || [];
  }

  async listReviewTasks(
    token: string,
    workspaceId: string,
    params?: { companyId?: string; status?: string; taskType?: string }
  ): Promise<any[]> {
    const q = new URLSearchParams();
    if (params?.companyId) q.append("company_id", params.companyId);
    if (params?.status) q.append("status", params.status);
    if (params?.taskType) q.append("task_type", params.taskType);
    const queryStr = q.toString() ? `?${q.toString()}` : "";
    return this.request<any[]>(`/review-tasks${queryStr}`, {
      headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
    });
  }

  async claimReviewTask(token: string, workspaceId: string, taskId: string): Promise<any> {
    return this.request<any>(`/review-tasks/${encodeURIComponent(taskId)}/claim`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
    });
  }

  async releaseReviewTask(token: string, workspaceId: string, taskId: string): Promise<any> {
    return this.request<any>(`/review-tasks/${encodeURIComponent(taskId)}/release`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
    });
  }

  async completeReviewTask(
    token: string,
    workspaceId: string,
    taskId: string,
    payload: { decision_code: string; reason: string; expected_row_version?: number }
  ): Promise<any> {
    return this.request<any>(`/review-tasks/${encodeURIComponent(taskId)}/complete`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
      body: JSON.stringify(payload),
    });
  }

  async reopenReviewTask(
    token: string,
    workspaceId: string,
    taskId: string,
    payload: { reason: string }
  ): Promise<any> {
    return this.request<any>(`/review-tasks/${encodeURIComponent(taskId)}/reopen`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
      body: JSON.stringify(payload),
    });
  }

  async listCompanyProfileDrafts(token: string, workspaceId: string, companyId: string): Promise<any[]> {
    return this.request<any[]>(`/companies/${encodeURIComponent(companyId)}/profile-drafts`, {
      headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
    });
  }

  async assembleCompanyProfileDraft(
    token: string,
    workspaceId: string,
    companyId: string,
    title: string = "Draft Profile"
  ): Promise<any> {
    return this.request<any>(
      `/companies/${encodeURIComponent(companyId)}/profile-drafts?title=${encodeURIComponent(title)}`,
      {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
      }
    );
  }

  async requestProfileDraftReview(token: string, workspaceId: string, draftId: string): Promise<any> {
    return this.request<any>(`/profile-drafts/${encodeURIComponent(draftId)}/request-review`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
    });
  }

  async publishProfileDraft(
    token: string,
    workspaceId: string,
    draftId: string,
    payload: { publication_note?: string }
  ): Promise<any> {
    return this.request<any>(`/profile-drafts/${encodeURIComponent(draftId)}/publish`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
      body: JSON.stringify(payload),
    });
  }

  async getCurrentCompanyProfile(token: string, workspaceId: string, companyId: string): Promise<any> {
    return this.request<any>(`/companies/${encodeURIComponent(companyId)}/profile`, {
      headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
    });
  }

  async listCompanyProfileVersions(token: string, workspaceId: string, companyId: string): Promise<any[]> {
    return this.request<any[]>(`/companies/${encodeURIComponent(companyId)}/profiles`, {
      headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
    });
  }

  async getProfileVersionDetail(token: string, workspaceId: string, versionId: string): Promise<any> {
    return this.request<any>(`/profiles/${encodeURIComponent(versionId)}`, {
      headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
    });
  }

  async withdrawPublishedProfile(
    token: string,
    workspaceId: string,
    versionId: string,
    payload: { reason: string }
  ): Promise<any> {
    return this.request<any>(`/profiles/${encodeURIComponent(versionId)}/withdraw`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
      body: JSON.stringify(payload),
    });
  }

  async getCompanyMeetingBrief(
    token: string,
    workspaceId: string,
    companyId: string,
    locale: string = "vi"
  ): Promise<any> {
    return this.request<any>(
      `/companies/${encodeURIComponent(companyId)}/meeting-brief?locale=${encodeURIComponent(locale)}`,
      {
        headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
      }
    );
  }

  async diffProfileVersions(
    token: string,
    workspaceId: string,
    versionId: string,
    otherVersionId: string
  ): Promise<any> {
    return this.request<any>(
      `/profiles/${encodeURIComponent(versionId)}/diff/${encodeURIComponent(otherVersionId)}`,
      {
        headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
      }
    );
  }

  async createProfileExport(
    token: string,
    workspaceId: string,
    versionId: string,
    payload: { export_format?: string; locale?: string; include_source_appendix?: boolean; include_internal_notes?: boolean }
  ): Promise<any> {
    return this.request<any>(`/profiles/${encodeURIComponent(versionId)}/exports`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
      body: JSON.stringify(payload),
    });
  }

  async getExportJobStatus(token: string, workspaceId: string, exportId: string): Promise<any> {
    return this.request<any>(`/exports/${encodeURIComponent(exportId)}`, {
      headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
    });
  }

  async listPolicyVersions(token: string, workspaceId: string): Promise<any> {
    return this.request<any>("/policies", {
      headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
    });
  }

  async createPolicyVersion(
    token: string,
    workspaceId: string,
    payload: { name: string; description?: string; policy_config?: any }
  ): Promise<any> {
    return this.request<any>("/policies", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
      body: JSON.stringify(payload),
    });
  }

  async activatePolicyVersion(token: string, workspaceId: string, policyId: string): Promise<any> {
    return this.request<any>(`/policies/${encodeURIComponent(policyId)}/activate`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
    });
  }

  async listAuditTrail(token: string, workspaceId: string, action?: string, actorId?: string): Promise<any> {
    const params = new URLSearchParams();
    if (action) params.append("action", action);
    if (actorId) params.append("actor_id", actorId);
    const query = params.toString() ? `?${params.toString()}` : "";

    return this.request<any>(`/audit${query}`, {
      headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
    });
  }

  async getProviderSettings(token: string, workspaceId: string): Promise<any> {
    return this.request<any>("/provider-settings", {
      headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
    });
  }

  async getOperationsUsage(token: string, workspaceId: string): Promise<any> {
    return this.request<any>("/operations/usage", {
      headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
    });
  }

  async listFitAssessments(token: string, workspaceId: string, companyId: string): Promise<any> {
    return this.request<any>(`/companies/${encodeURIComponent(companyId)}/fit-assessments`, {
      headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
    });
  }

  async evaluateProgramFit(
    token: string,
    workspaceId: string,
    companyId: string,
    payload: { program_name?: string }
  ): Promise<any> {
    return this.request<any>(`/companies/${encodeURIComponent(companyId)}/fit-assessments`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
      body: JSON.stringify(payload),
    });
  }

  async overrideFitAssessment(
    token: string,
    workspaceId: string,
    assessmentId: string,
    payload: { override_status: string; notes?: string }
  ): Promise<any> {
    return this.request<any>(`/fit-assessments/${encodeURIComponent(assessmentId)}/override`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId },
      body: JSON.stringify(payload),
    });
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

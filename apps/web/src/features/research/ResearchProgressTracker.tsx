"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { getApiClient } from "@vcps/api-client";
import { useAuth } from "../../stores/authContext";

export interface TaskStep {
  id: string;
  step_type: string;
  status: string;
  attempt_count: number;
  max_attempts: number;
  output_payload?: string | null;
  error_message?: string | null;
}

export interface ResearchJobItem {
  id: string;
  workspace_id: string;
  company_id: string;
  job_type: string;
  requested_locale: string;
  status: string;
  started_at?: string | null;
  completed_at?: string | null;
  cancel_requested_at?: string | null;
  error_message?: string | null;
  tasks?: TaskStep[];
}

interface ResearchProgressTrackerProps {
  companyId: string;
}

interface PipelineState {
  warnings?: string[];
  source_candidates?: unknown[];
  selected_sources?: unknown[];
  fetched_sources?: unknown[];
  parsed_snapshots?: Array<{ block_count?: number }>;
  deterministic_fact_count?: number;
  review_task_count?: number;
  review_task_ids?: string[];
  source_provider_outcomes?: Array<{
    provider?: string;
    outcome?: string;
    reason?: string;
  }>;
  ai?: {
    status?: string;
    reason?: string;
    semantic_extraction?: string;
    translation?: string;
    comparison?: string;
    summary?: string;
  };
}

const PIPELINE_STEPS = [
  ["entity_resolution", "Entity resolved"],
  ["source_discovery", "Sources discovered"],
  ["source_selection", "Sources selected"],
  ["source_fetch", "Sources fetched"],
  ["document_parse", "Document blocks parsed"],
  ["deterministic_extraction", "Deterministic facts extracted"],
  ["ai_extraction", "Optional AI extraction"],
  ["fact_processing", "Conflicts and review"],
  ["finalize", "Research finalized"],
] as const;

function parseState(tasks: TaskStep[] | undefined): PipelineState {
  const ordered = [...(tasks || [])].reverse();
  for (const task of ordered) {
    if (!task.output_payload) continue;
    try {
      const value: unknown = JSON.parse(task.output_payload);
      if (value && typeof value === "object") return value as PipelineState;
    } catch {
      // A task can be running before its durable output exists.
    }
  }
  return {};
}

function stepStatus(job: ResearchJobItem, stepType: string): string {
  return job.tasks?.find((task) => task.step_type === stepType)?.status || "pending";
}

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    running: "Đang thu thập",
    pending: "Đang chờ worker",
    completed: "Đã hoàn tất",
    partial_success: "Hoàn tất giới hạn",
    failed: "Thất bại",
    cancelled: "Đã huỷ",
  };
  return labels[status] || status;
}

function stepIcon(status: string): string {
  if (status === "completed") return "✓";
  if (status === "running") return "…";
  if (status === "failed") return "!";
  if (status === "cancelled") return "×";
  return "·";
}

export const ResearchProgressTracker: React.FC<ResearchProgressTrackerProps> = ({ companyId }) => {
  const { activeWorkspace, hasCapability } = useAuth();
  const [jobs, setJobs] = useState<ResearchJobItem[]>([]);
  const [selectedJob, setSelectedJob] = useState<ResearchJobItem | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isStarting, setIsStarting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const canStart = hasCapability("research:start");

  const loadJobs = useCallback(async () => {
    if (!activeWorkspace || !companyId) return;
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const token = localStorage.getItem("vcps_access_token") || "";
      const client = getApiClient();
      const response = await client.listResearchJobs(token, activeWorkspace.id, companyId);
      const nextJobs = (response || []) as ResearchJobItem[];
      setJobs(nextJobs);
      if (nextJobs.length > 0) {
        const fullJob = await client.getResearchJob(token, activeWorkspace.id, nextJobs[0].id);
        setSelectedJob(fullJob as ResearchJobItem);
      } else {
        setSelectedJob(null);
      }
    } catch {
      setErrorMsg("Không thể tải trạng thái research.");
    } finally {
      setIsLoading(false);
    }
  }, [activeWorkspace, companyId]);

  useEffect(() => {
    void loadJobs();
  }, [loadJobs]);

  useEffect(() => {
    if (
      !selectedJob ||
      (selectedJob.status !== "running" && selectedJob.status !== "pending") ||
      !activeWorkspace
    ) {
      return undefined;
    }

    const timer = window.setInterval(async () => {
      try {
        const token = localStorage.getItem("vcps_access_token") || "";
        const client = getApiClient();
        const fullJob = await client.getResearchJob(token, activeWorkspace.id, selectedJob.id);
        setSelectedJob(fullJob as ResearchJobItem);
      } catch {
        // Keep the last durable state visible when polling temporarily fails.
      }
    }, 2000);

    return () => window.clearInterval(timer);
  }, [selectedJob, activeWorkspace]);

  const pipelineState = useMemo(() => parseState(selectedJob?.tasks), [selectedJob?.tasks]);
  const parsedBlockCount = (pipelineState.parsed_snapshots || []).reduce(
    (total, snapshot) => total + Number(snapshot.block_count || 0),
    0,
  );
  const aiSkipped = ["skipped", "unavailable"].includes(pipelineState.ai?.status || "");
  const hasEvidence =
    Number(pipelineState.fetched_sources?.length || 0) > 0 ||
    Number(pipelineState.parsed_snapshots?.length || 0) > 0;

  const handleStartResearch = async () => {
    if (!activeWorkspace || !companyId) return;
    setIsStarting(true);
    setErrorMsg(null);
    try {
      const token = localStorage.getItem("vcps_access_token") || "";
      const client = getApiClient();
      const job = await client.triggerCompanyResearch(token, activeWorkspace.id, companyId, {
        job_type: "initial",
        requested_locale: "vi",
      });
      setSelectedJob(job as ResearchJobItem);
      await loadJobs();
    } catch {
      setErrorMsg("Không thể bắt đầu research job.");
    } finally {
      setIsStarting(false);
    }
  };

  const handleCancelJob = async () => {
    if (!activeWorkspace || !selectedJob) return;
    try {
      const token = localStorage.getItem("vcps_access_token") || "";
      const client = getApiClient();
      const updated = await client.cancelResearchJob(token, activeWorkspace.id, selectedJob.id);
      setSelectedJob(updated as ResearchJobItem);
      await loadJobs();
    } catch {
      setErrorMsg("Không thể huỷ research job.");
    }
  };

  return (
    <section
      aria-label="Research progress"
      style={{
        padding: "16px",
        border: "1px solid #eaeaea",
        borderRadius: "8px",
        fontFamily: "sans-serif",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "12px",
        }}
      >
        <div>
          <h3 style={{ margin: 0 }}>Research progress & evidence</h3>
          <p style={{ color: "#57606a", fontSize: "12px", margin: "4px 0 0" }}>
            Acquisition và deterministic facts vẫn chạy khi AI không khả dụng.
          </p>
        </div>
        {canStart && (
          <button
            onClick={handleStartResearch}
            disabled={isStarting}
            style={{
              padding: "6px 12px",
              backgroundColor: "#2da44e",
              color: "#fff",
              border: "none",
              borderRadius: "6px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {isStarting ? "Starting..." : "⚡ Start Research"}
          </button>
        )}
      </div>

      {errorMsg && (
        <div style={{ padding: "10px", backgroundColor: "#ffebe9", color: "#cf222e", borderRadius: "6px", marginBottom: "12px" }}>
          {errorMsg}
        </div>
      )}

      {isLoading ? (
        <div>Loading research pipeline status...</div>
      ) : selectedJob ? (
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
            <div>
              <strong>Job status:</strong>{" "}
              <span
                style={{
                  padding: "4px 8px",
                  borderRadius: "12px",
                  fontSize: "12px",
                  fontWeight: 600,
                  backgroundColor:
                    selectedJob.status === "completed"
                      ? "#dafbe1"
                      : selectedJob.status === "failed"
                        ? "#ffebe9"
                        : selectedJob.status === "partial_success"
                          ? "#fff8c5"
                          : "#ddf4ff",
                  color:
                    selectedJob.status === "completed"
                      ? "#1a7f37"
                      : selectedJob.status === "failed"
                        ? "#cf222e"
                        : selectedJob.status === "partial_success"
                          ? "#9a6700"
                          : "#0969da",
                }}
              >
                {statusLabel(selectedJob.status)}
              </span>
            </div>
            {(selectedJob.status === "running" || selectedJob.status === "pending") && (
              <button
                onClick={handleCancelJob}
                style={{ padding: "4px 8px", borderRadius: "4px", border: "1px solid #cf222e", background: "#fff", color: "#cf222e", cursor: "pointer", fontSize: "12px" }}
              >
                Cancel Job
              </button>
            )}
          </div>

          {aiSkipped && (
            <div style={{ padding: "10px", background: "#fff8c5", color: "#7a4d00", borderRadius: "6px", marginBottom: "12px", fontSize: "13px" }}>
              <div>⚠ AI extraction unavailable{pipelineState.ai?.reason ? ` (${pipelineState.ai.reason})` : ""}.</div>
              <div style={{ marginTop: "4px" }}>→ Review available evidence in the Human Review Inbox.</div>
              {hasEvidence && (
                <div style={{ marginTop: "4px" }}>
                  Snapshots, document blocks, and deterministic evidence remain available.
                </div>
              )}
            </div>
          )}

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: "8px", marginBottom: "16px" }}>
            {[
              ["Sources discovered", pipelineState.source_candidates?.length || 0],
              ["Sources selected", pipelineState.selected_sources?.length || 0],
              ["Sources fetched", pipelineState.fetched_sources?.length || 0],
              ["Document blocks", parsedBlockCount],
              ["Deterministic facts", pipelineState.deterministic_fact_count || 0],
              ["Review tasks", pipelineState.review_task_count || pipelineState.review_task_ids?.length || 0],
            ].map(([label, count]) => (
              <div key={label} style={{ border: "1px solid #d0d7de", borderRadius: "6px", padding: "8px", background: "#f6f8fa" }}>
                <div style={{ fontSize: "11px", color: "#57606a" }}>{label}</div>
                <strong style={{ fontSize: "18px" }}>{count}</strong>
              </div>
            ))}
          </div>

          <div style={{ display: "grid", gap: "6px" }}>
            {PIPELINE_STEPS.map(([stepType, label]) => {
              const status = stepStatus(selectedJob, stepType);
              const aiUnavailable = stepType === "ai_extraction" && aiSkipped;
              const reviewAvailable =
                stepType === "fact_processing" && Number(pipelineState.review_task_count || 0) > 0;
              const displayLabel = aiUnavailable
                ? "AI extraction unavailable"
                : reviewAvailable
                  ? "Review available evidence"
                  : label;
              const displayIcon = aiUnavailable ? "⚠" : reviewAvailable ? "→" : stepIcon(status);
              return (
                <div key={stepType} style={{ display: "flex", alignItems: "center", gap: "8px", padding: "7px 9px", borderRadius: "6px", background: aiUnavailable ? "#fff8c5" : status === "completed" ? "#dafbe1" : status === "failed" ? "#ffebe9" : status === "running" ? "#ddf4ff" : "#f6f8fa" }}>
                  <span style={{ width: "20px", textAlign: "center", fontWeight: 700 }}>{displayIcon}</span>
                  <span style={{ flex: 1, fontSize: "13px" }}>{displayLabel}</span>
                  <span style={{ fontSize: "11px", color: "#57606a" }}>{status}</span>
                </div>
              );
            })}
          </div>

          {(pipelineState.source_provider_outcomes || []).length > 0 && (
            <div style={{ marginTop: "14px", fontSize: "12px" }}>
              <strong>Provider outcomes</strong>
              {(pipelineState.source_provider_outcomes || []).map((outcome, index) => (
                <div key={`${outcome.provider || "provider"}-${index}`} style={{ marginTop: "4px", color: outcome.outcome === "success" ? "#1a7f37" : "#9a6700" }}>
                  {outcome.provider}: {outcome.outcome} {outcome.reason ? `— ${outcome.reason}` : ""}
                </div>
              ))}
            </div>
          )}

          {(pipelineState.warnings || []).length > 0 && (
            <details style={{ marginTop: "14px", fontSize: "12px" }}>
              <summary style={{ cursor: "pointer", color: "#9a6700" }}>Warnings ({pipelineState.warnings?.length})</summary>
              <ul style={{ margin: "6px 0 0", paddingLeft: "18px", color: "#7a4d00" }}>
                {(pipelineState.warnings || []).map((warning) => <li key={warning}>{warning}</li>)}
              </ul>
            </details>
          )}
        </div>
      ) : (
        <div style={{ color: "#666", fontSize: "13px" }}>No research jobs initiated for this company yet.</div>
      )}
    </section>
  );
};

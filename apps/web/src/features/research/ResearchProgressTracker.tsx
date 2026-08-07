"use client";

import React, { useState, useEffect, useCallback } from "react";
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
    try {
      const token = localStorage.getItem("vcps_access_token") || "";
      const client = getApiClient();
      const res = await client.listResearchJobs(token, activeWorkspace.id, companyId);
      setJobs(res);

      if (res.length > 0) {
        const fullJob = await client.getResearchJob(token, activeWorkspace.id, res[0].id);
        setSelectedJob(fullJob);
      }
    } catch {
      setErrorMsg("Failed to load research jobs.");
    } finally {
      setIsLoading(false);
    }
  }, [activeWorkspace, companyId]);

  useEffect(() => {
    loadJobs();
  }, [loadJobs]);

  // Poll active running job every 2 seconds
  useEffect(() => {
    if (!selectedJob || (selectedJob.status !== "running" && selectedJob.status !== "pending") || !activeWorkspace) {
      return;
    }

    const timer = setInterval(async () => {
      try {
        const token = localStorage.getItem("vcps_access_token") || "";
        const client = getApiClient();
        const fullJob = await client.getResearchJob(token, activeWorkspace.id, selectedJob.id);
        setSelectedJob(fullJob);
      } catch {
        // Suppress polling error
      }
    }, 2000);

    return () => clearInterval(timer);
  }, [selectedJob, activeWorkspace]);

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
      setSelectedJob(job);
      loadJobs();
    } catch {
      setErrorMsg("Failed to start research job.");
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
      setSelectedJob(updated);
      loadJobs();
    } catch {
      setErrorMsg("Failed to cancel research job.");
    }
  };

  return (
    <div style={{ padding: "16px", border: "1px solid #eaeaea", borderRadius: "8px", fontFamily: "sans-serif" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
        <h3 style={{ margin: 0 }}>Automated Research Pipeline</h3>
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
              <strong>Status:</strong>{" "}
              <span
                style={{
                  padding: "4px 8px",
                  borderRadius: "12px",
                  fontSize: "12px",
                  fontWeight: 600,
                  backgroundColor: selectedJob.status === "completed" ? "#dafbe1" : selectedJob.status === "failed" ? "#ffebe9" : "#fff8c5",
                  color: selectedJob.status === "completed" ? "#1a7f37" : selectedJob.status === "failed" ? "#cf222e" : "#9a6700",
                }}
              >
                {selectedJob.status.toUpperCase()}
              </span>
            </div>
            {selectedJob.status === "running" && (
              <button
                onClick={handleCancelJob}
                style={{ padding: "4px 8px", borderRadius: "4px", border: "1px solid #cf222e", background: "#fff", color: "#cf222e", cursor: "pointer", fontSize: "12px" }}
              >
                Cancel Job
              </button>
            )}
          </div>

          {/* Task Steps Sequence Tracker */}
          <div style={{ marginTop: "16px" }}>
            <h4 style={{ margin: "0 0 8px 0", fontSize: "13px", color: "#666" }}>Pipeline Steps:</h4>
            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
              {["search", "fetch", "extract", "synthesize"].map((step) => {
                const task = selectedJob.tasks?.find((t) => t.step_type === step);
                const stepStatus = task ? task.status : "pending";
                return (
                  <div
                    key={step}
                    style={{
                      flex: 1,
                      minWidth: "100px",
                      padding: "8px",
                      borderRadius: "6px",
                      border: "1px solid #ccc",
                      backgroundColor: stepStatus === "completed" ? "#dafbe1" : stepStatus === "running" ? "#ddf4ff" : "#f6f8fa",
                      textAlign: "center",
                    }}
                  >
                    <div style={{ fontWeight: 600, fontSize: "12px" }}>{step.toUpperCase()}</div>
                    <div style={{ fontSize: "11px", color: "#57606a", marginTop: "4px" }}>{stepStatus}</div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      ) : (
        <div style={{ color: "#666", fontSize: "13px" }}>No research jobs initiated for this company yet.</div>
      )}
    </div>
  );
};

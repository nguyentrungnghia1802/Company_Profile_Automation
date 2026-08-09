"use client";

import React, { useState, useEffect, useCallback } from "react";
import { getApiClient } from "@vcps/api-client";
import { useAuth } from "../../stores/authContext";

export interface ConflictCandidateItem {
  id: string;
  fact_candidate_id: string;
  candidate_role: string;
  is_selected: boolean;
  fact_candidate?: {
    id: string;
    field_key: string;
    value: any;
    display_value?: string | null;
    fact_status: string;
    confidence_score: number;
    confidence_explanation?: string | null;
  } | null;
}

export interface ConflictItem {
  id: string;
  workspace_id: string;
  company_id: string;
  field_key: string;
  context_key: string;
  status: string;
  materiality: string;
  resolution_type?: string | null;
  resolution_reason?: string | null;
  resolved_at?: string | null;
  candidates: ConflictCandidateItem[];
}

interface ConflictsListProps {
  companyId: string;
}

export const ConflictsList: React.FC<ConflictsListProps> = ({ companyId }) => {
  const { activeWorkspace, hasCapability } = useAuth();
  const [conflicts, setConflicts] = useState<ConflictItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [resolvingConflictId, setResolvingConflictId] = useState<string | null>(null);
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(null);
  const [reasonInput, setReasonInput] = useState("");

  const canResolve = hasCapability("company:update");

  const loadConflicts = useCallback(async () => {
    if (!activeWorkspace || !companyId) return;
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const token = localStorage.getItem("vcps_access_token") || "";
      const client = getApiClient();
      const data = await client.listCompanyConflicts(token, activeWorkspace.id, companyId);
      setConflicts(data);
    } catch {
      setErrorMsg("Failed to load conflicts.");
    } finally {
      setIsLoading(false);
    }
  }, [activeWorkspace, companyId]);

  useEffect(() => {
    loadConflicts();
  }, [loadConflicts]);

  const handleResolve = async (conflictId: string) => {
    if (!activeWorkspace || !selectedCandidateId || !reasonInput.trim()) return;
    try {
      const token = localStorage.getItem("vcps_access_token") || "";
      const client = getApiClient();
      await client.resolveConflict(token, activeWorkspace.id, companyId, conflictId, {
        resolution_type: "select_one",
        reason: reasonInput.trim(),
        selected_candidate_ids: [selectedCandidateId],
      });
      setResolvingConflictId(null);
      setSelectedCandidateId(null);
      setReasonInput("");
      loadConflicts();
    } catch {
      setErrorMsg("Failed to resolve conflict.");
    }
  };

  if (isLoading) return <div style={{ padding: "16px", color: "#6e7781" }}>Loading conflicts...</div>;

  return (
    <div style={{ marginTop: "16px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
        <h4 style={{ margin: 0, fontSize: "16px", color: "#24292f" }}>Field Conflicts ({conflicts.length})</h4>
        <button
          onClick={loadConflicts}
          style={{
            padding: "4px 10px",
            fontSize: "12px",
            borderRadius: "6px",
            border: "1px solid #d0d7de",
            backgroundColor: "#f6f8fa",
            cursor: "pointer",
          }}
        >
          Refresh
        </button>
      </div>

      {errorMsg && <div style={{ padding: "8px 12px", backgroundColor: "#ffebe9", color: "#cf222e", borderRadius: "6px", marginBottom: "12px" }}>{errorMsg}</div>}

      {conflicts.length === 0 ? (
        <div style={{ padding: "16px", backgroundColor: "#dafbe1", borderRadius: "6px", color: "#1a7f37", fontSize: "13px" }}>
          No material conflicts detected. All candidate facts are consistent.
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          {conflicts.map((conf) => {
            const isResolving = resolvingConflictId === conf.id;
            const matColor = conf.materiality === "critical" ? "#cf222e" : conf.materiality === "high" ? "#9a6700" : "#0969da";

            return (
              <div key={conf.id} style={{ border: "1px solid #d0d7de", borderRadius: "6px", padding: "12px", backgroundColor: "#ffffff" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <span style={{ fontWeight: 600, fontSize: "14px", color: "#0969da" }}>{conf.field_key}</span>
                    <span style={{ marginLeft: "8px", fontSize: "11px", backgroundColor: "#f6f8fa", color: matColor, border: `1px solid ${matColor}`, padding: "2px 6px", borderRadius: "4px", fontWeight: 600 }}>
                      {conf.materiality.toUpperCase()} MATERIALITY
                    </span>
                  </div>
                  <span style={{ fontSize: "12px", fontWeight: 600, color: conf.status === "resolved" ? "#1a7f37" : "#9a6700" }}>
                    Status: {conf.status.toUpperCase()}
                  </span>
                </div>

                <div style={{ marginTop: "8px", fontSize: "12px", color: "#57606a" }}>
                  Competing Candidate Values ({conf.candidates.length}):
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: "6px", marginTop: "6px" }}>
                  {conf.candidates.map((cc) => {
                    const fc = cc.fact_candidate;
                    return (
                      <div
                        key={cc.id}
                        onClick={() => isResolving && fc && setSelectedCandidateId(fc.id)}
                        style={{
                          padding: "8px",
                          borderRadius: "4px",
                          border: `1px solid ${selectedCandidateId === fc?.id ? "#0969da" : "#d0d7de"}`,
                          backgroundColor: selectedCandidateId === fc?.id ? "#ddf4ff" : cc.is_selected ? "#dafbe1" : "#f6f8fa",
                          cursor: isResolving ? "pointer" : "default",
                        }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between" }}>
                          <span style={{ fontSize: "13px", fontWeight: 600, color: "#24292f" }}>
                            {fc?.display_value || JSON.stringify(fc?.value)}
                          </span>
                          {cc.is_selected && <span style={{ fontSize: "11px", color: "#1a7f37", fontWeight: 600 }}>✓ SELECTED</span>}
                        </div>
                        {fc && (
                          <div style={{ fontSize: "11px", color: "#57606a", marginTop: "2px" }}>
                            Confidence: {(fc.confidence_score * 100).toFixed(0)}% | Status: {fc.fact_status}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>

                {conf.status !== "resolved" && canResolve && (
                  <div style={{ marginTop: "12px" }}>
                    {!isResolving ? (
                      <button
                        onClick={() => setResolvingConflictId(conf.id)}
                        style={{
                          padding: "6px 12px",
                          fontSize: "12px",
                          fontWeight: 600,
                          color: "#ffffff",
                          backgroundColor: "#0969da",
                          border: "none",
                          borderRadius: "6px",
                          cursor: "pointer",
                        }}
                      >
                        Resolve Conflict
                      </button>
                    ) : (
                      <div style={{ padding: "8px", border: "1px solid #0969da", borderRadius: "6px", backgroundColor: "#f6f8fa" }}>
                        <div style={{ fontSize: "12px", fontWeight: 600, marginBottom: "6px", color: "#24292f" }}>Select winning candidate above and provide reason:</div>
                        <input
                          id={`conflict-resolution-reason-${conf.id}`}
                          name="resolution_reason"
                          type="text"
                          aria-label={`Resolution rationale for ${conf.field_key}`}
                          placeholder="Resolution rationale..."
                          value={reasonInput}
                          onChange={(e) => setReasonInput(e.target.value)}
                          style={{ width: "100%", padding: "6px", fontSize: "12px", borderRadius: "4px", border: "1px solid #d0d7de", marginBottom: "8px", boxSizing: "border-box" }}
                        />
                        <div style={{ display: "flex", gap: "8px" }}>
                          <button
                            onClick={() => handleResolve(conf.id)}
                            disabled={!selectedCandidateId || !reasonInput.trim()}
                            style={{
                              padding: "4px 12px",
                              fontSize: "12px",
                              fontWeight: 600,
                              color: "#ffffff",
                              backgroundColor: "#1a7f37",
                              border: "none",
                              borderRadius: "4px",
                              cursor: selectedCandidateId && reasonInput.trim() ? "pointer" : "not-allowed",
                              opacity: selectedCandidateId && reasonInput.trim() ? 1 : 0.6,
                            }}
                          >
                            Save Resolution
                          </button>
                          <button
                            onClick={() => {
                              setResolvingConflictId(null);
                              setSelectedCandidateId(null);
                            }}
                            style={{
                              padding: "4px 12px",
                              fontSize: "12px",
                              color: "#57606a",
                              backgroundColor: "#f6f8fa",
                              border: "1px solid #d0d7de",
                              borderRadius: "4px",
                              cursor: "pointer",
                            }}
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

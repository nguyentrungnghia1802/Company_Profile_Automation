"use client";

import React, { useState, useEffect, useCallback } from "react";
import { getApiClient } from "@vcps/api-client";
import { useAuth } from "../../stores/authContext";

export interface EvidenceItem {
  id: string;
  source_snapshot_id: string;
  document_block_id: string;
  original_excerpt: string;
  translated_excerpt?: string | null;
  support_type: string;
  evidence_quality_score: number;
  review_status: string;
}

export interface FactCandidateItem {
  id: string;
  field_key: string;
  context_key: string;
  value: any;
  display_value?: string | null;
  fact_status: string;
  origin_type: string;
  is_inferred: boolean;
  is_estimated: boolean;
  is_unknown: boolean;
  confidence_score: number;
  confidence_explanation?: string | null;
  observed_at: string;
  freshness_status: string;
  evidences: EvidenceItem[];
}

interface FactCandidatesListProps {
  companyId: string;
}

export const FactCandidatesList: React.FC<FactCandidatesListProps> = ({ companyId }) => {
  const { activeWorkspace } = useAuth();
  const [facts, setFacts] = useState<FactCandidateItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [expandedFactId, setExpandedFactId] = useState<string | null>(null);

  const loadFacts = useCallback(async () => {
    if (!activeWorkspace || !companyId) return;
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const token = localStorage.getItem("vcps_access_token") || "";
      const client = getApiClient();
      const data = await client.listCompanyFacts(token, activeWorkspace.id, companyId);
      setFacts(data);
    } catch {
      setErrorMsg("Failed to load fact candidates.");
    } finally {
      setIsLoading(false);
    }
  }, [activeWorkspace, companyId]);

  useEffect(() => {
    loadFacts();
  }, [loadFacts]);

  if (isLoading) return <div style={{ padding: "16px", color: "#6e7781" }}>Loading facts & evidence...</div>;

  return (
    <div style={{ marginTop: "16px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
        <h4 style={{ margin: 0, fontSize: "16px", color: "#24292f" }}>Extracted Fact Candidates</h4>
        <button
          onClick={loadFacts}
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

      {facts.length === 0 ? (
        <div style={{ padding: "16px", backgroundColor: "#f6f8fa", borderRadius: "6px", color: "#57606a", fontSize: "13px" }}>
          No fact candidates extracted yet for this company. Trigger a research job to discover facts.
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          {facts.map((fact) => {
            const isExpanded = expandedFactId === fact.id;
            const freshnessColor = fact.freshness_status === "fresh" ? "#1a7f37" : fact.freshness_status === "warning" ? "#9a6700" : "#cf222e";
            const confidenceColor = fact.confidence_score >= 0.8 ? "#1a7f37" : fact.confidence_score >= 0.6 ? "#9a6700" : "#cf222e";

            return (
              <div key={fact.id} style={{ border: "1px solid #d0d7de", borderRadius: "6px", padding: "12px", backgroundColor: "#ffffff" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div>
                    <span style={{ fontWeight: 600, fontSize: "14px", color: "#0969da" }}>{fact.field_key}</span>
                    {fact.is_unknown && <span style={{ marginLeft: "8px", fontSize: "11px", backgroundColor: "#f6f8fa", color: "#57606a", padding: "2px 6px", borderRadius: "4px" }}>Unknown</span>}
                    {fact.is_inferred && <span style={{ marginLeft: "6px", fontSize: "11px", backgroundColor: "#ddf4ff", color: "#0969da", padding: "2px 6px", borderRadius: "4px" }}>Inferred</span>}
                    {fact.is_estimated && <span style={{ marginLeft: "6px", fontSize: "11px", backgroundColor: "#fff8c5", color: "#9a6700", padding: "2px 6px", borderRadius: "4px" }}>Estimated</span>}
                  </div>
                  <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                    <span style={{ fontSize: "12px", fontWeight: 600, color: confidenceColor, backgroundColor: "#f6f8fa", padding: "2px 8px", borderRadius: "12px", border: `1px solid ${confidenceColor}` }}>
                      {(fact.confidence_score * 100).toFixed(0)}% Confidence
                    </span>
                    <span style={{ fontSize: "11px", color: freshnessColor, fontWeight: 500 }}>
                      ● {fact.freshness_status.toUpperCase()}
                    </span>
                  </div>
                </div>

                <div style={{ marginTop: "8px", fontSize: "13px", color: "#24292f" }}>
                  <strong>Value:</strong> {fact.is_unknown ? <em>Not found in sources</em> : fact.display_value || JSON.stringify(fact.value)}
                </div>

                {fact.confidence_explanation && (
                  <div style={{ marginTop: "4px", fontSize: "11px", color: "#57606a", fontStyle: "italic" }}>
                    {fact.confidence_explanation}
                  </div>
                )}

                <div style={{ marginTop: "8px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: "11px", color: "#6e7781" }}>
                    Status: <strong>{fact.fact_status}</strong> | Origin: {fact.origin_type}
                  </span>
                  <button
                    onClick={() => setExpandedFactId(isExpanded ? null : fact.id)}
                    style={{
                      border: "none",
                      background: "none",
                      color: "#0969da",
                      fontSize: "12px",
                      cursor: "pointer",
                      padding: 0,
                    }}
                  >
                    {isExpanded ? "Hide Evidence ▲" : `View Evidence (${fact.evidences.length}) ▼`}
                  </button>
                </div>

                {isExpanded && (
                  <div style={{ marginTop: "12px", paddingTop: "12px", borderTop: "1px dashed #d0d7de", backgroundColor: "#f6f8fa", padding: "8px", borderRadius: "4px" }}>
                    <h5 style={{ margin: "0 0 8px 0", fontSize: "12px", color: "#24292f" }}>Supporting Excerpts ({fact.evidences.length})</h5>
                    {fact.evidences.length === 0 ? (
                      <div style={{ fontSize: "11px", color: "#57606a" }}>No explicit block evidence attached.</div>
                    ) : (
                      <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                        {fact.evidences.map((ev) => (
                          <div key={ev.id} style={{ fontSize: "12px", padding: "6px 8px", backgroundColor: "#ffffff", border: "1px solid #d0d7de", borderRadius: "4px" }}>
                            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                              <span style={{ fontSize: "11px", fontWeight: 600, color: "#0969da" }}>{ev.support_type.toUpperCase()} EVIDENCE</span>
                              <span style={{ fontSize: "10px", color: "#57606a" }}>Quality: {(ev.evidence_quality_score * 100).toFixed(0)}%</span>
                            </div>
                            <div style={{ fontFamily: "monospace", fontSize: "11px", backgroundColor: "#f6f8fa", padding: "4px", borderRadius: "3px" }}>
                              "{ev.original_excerpt}"
                            </div>
                            {ev.translated_excerpt && (
                              <div style={{ marginTop: "4px", fontSize: "11px", color: "#57606a" }}>
                                <strong>Translation:</strong> "{ev.translated_excerpt}"
                              </div>
                            )}
                          </div>
                        ))}
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

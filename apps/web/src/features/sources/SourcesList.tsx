"use client";

import React, { useState, useEffect, useCallback } from "react";
import { getApiClient } from "@vcps/api-client";
import { useAuth } from "../../stores/authContext";

export interface SourceItem {
  id: string;
  workspace_id: string;
  company_id: string;
  canonical_url: string;
  normalized_url: string;
  domain: string;
  source_type: string;
  authority_tier: number;
  status: string;
  entity_match_score?: number | null;
  first_discovered_at: string;
}

export interface FetchAttempt {
  id: string;
  adapter: string;
  started_at: string;
  requested_url: string;
  final_url?: string;
  http_status?: number;
  byte_count: number;
  outcome_code: string;
  error_message?: string;
}

export interface DocumentBlockItem {
  id: string;
  block_key: string;
  block_type: string;
  text_content: string;
  block_hash: string;
}

interface SourcesListProps {
  companyId: string;
}

export const SourcesList: React.FC<SourcesListProps> = ({ companyId }) => {
  const { activeWorkspace, hasCapability } = useAuth();
  const [sources, setSources] = useState<SourceItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [newUrl, setNewUrl] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [expandedSourceId, setExpandedSourceId] = useState<string | null>(null);
  const [attempts, setAttempts] = useState<FetchAttempt[]>([]);
  const [blocks, setBlocks] = useState<DocumentBlockItem[]>([]);
  const [isDetailsLoading, setIsDetailsLoading] = useState(false);

  const canEdit = hasCapability("company:update");

  const loadSources = useCallback(async () => {
    if (!activeWorkspace || !companyId) return;
    setIsLoading(true);
    try {
      const token = localStorage.getItem("vcps_access_token") || "";
      const client = getApiClient();
      const res = await client.listCompanySources(token, activeWorkspace.id, companyId);
      setSources(res);
    } catch {
      setErrorMsg("Failed to load company sources.");
    } finally {
      setIsLoading(false);
    }
  }, [activeWorkspace, companyId]);

  useEffect(() => {
    loadSources();
  }, [loadSources]);

  const handleAddSource = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeWorkspace || !newUrl.trim() || !companyId) return;
    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      const token = localStorage.getItem("vcps_access_token") || "";
      const client = getApiClient();
      await client.addSourceURL(token, activeWorkspace.id, {
        company_id: companyId,
        url: newUrl.trim(),
      });
      setNewUrl("");
      loadSources();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to add source URL.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleDetails = async (sourceId: string) => {
    if (expandedSourceId === sourceId) {
      setExpandedSourceId(null);
      return;
    }
    setExpandedSourceId(sourceId);
    if (!activeWorkspace) return;
    setIsDetailsLoading(true);
    try {
      const token = localStorage.getItem("vcps_access_token") || "";
      const client = getApiClient();
      const atts = await client.listSourceAttempts(token, activeWorkspace.id, sourceId);
      setAttempts(atts);

      const snaps = await client.listSourceSnapshots(token, activeWorkspace.id, sourceId);
      if (snaps.length > 0) {
        const blks = await client.listSnapshotBlocks(token, activeWorkspace.id, snaps[0].id);
        setBlocks(blks);
      } else {
        setBlocks([]);
      }
    } catch {
      setAttempts([]);
      setBlocks([]);
    } finally {
      setIsDetailsLoading(false);
    }
  };

  return (
    <div style={{ padding: "16px", border: "1px solid #eaeaea", borderRadius: "8px", fontFamily: "sans-serif" }}>
      <h3 style={{ margin: "0 0 12px 0" }}>Discovered Sources & Evidence Candidates</h3>

      {canEdit && (
        <form onSubmit={handleAddSource} style={{ display: "flex", gap: "8px", marginBottom: "16px" }}>
          <input
            type="url"
            required
            placeholder="https://example.com/company-info"
            value={newUrl}
            onChange={(e) => setNewUrl(e.target.value)}
            style={{ flex: 1, padding: "8px", borderRadius: "4px", border: "1px solid #ccc" }}
          />
          <button
            type="submit"
            disabled={isSubmitting}
            style={{
              padding: "8px 16px",
              backgroundColor: "#0969da",
              color: "#fff",
              border: "none",
              borderRadius: "4px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {isSubmitting ? "Adding..." : "+ Add Source URL"}
          </button>
        </form>
      )}

      {errorMsg && (
        <div style={{ padding: "10px", backgroundColor: "#ffebe9", color: "#cf222e", borderRadius: "6px", marginBottom: "12px" }}>
          {errorMsg}
        </div>
      )}

      {isLoading ? (
        <div>Loading sources...</div>
      ) : sources.length === 0 ? (
        <div style={{ color: "#666", fontSize: "13px" }}>No sources acquired or added yet.</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          {sources.map((s) => (
            <div
              key={s.id}
              style={{
                borderRadius: "6px",
                border: "1px solid #eee",
                backgroundColor: "#fafafa",
                overflow: "hidden",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px" }}>
                <div>
                  <a href={s.canonical_url} target="_blank" rel="noreferrer" style={{ fontWeight: 600, color: "#0969da", textDecoration: "none" }}>
                    {s.domain}
                  </a>
                  <div style={{ fontSize: "12px", color: "#57606a", marginTop: "2px" }}>
                    Type: {s.source_type} | URL: {s.normalized_url}
                  </div>
                </div>

                <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                  <span
                    style={{
                      padding: "2px 6px",
                      borderRadius: "4px",
                      fontSize: "11px",
                      fontWeight: 600,
                      backgroundColor: "#ddf4ff",
                      color: "#0969da",
                    }}
                  >
                    Tier {s.authority_tier}
                  </span>

                  <span
                    style={{
                      padding: "2px 6px",
                      borderRadius: "4px",
                      fontSize: "11px",
                      fontWeight: 600,
                      backgroundColor: s.status === "fetched" ? "#dafbe1" : s.status === "rejected" ? "#ffebe9" : "#fff8c5",
                      color: s.status === "fetched" ? "#1a7f37" : s.status === "rejected" ? "#cf222e" : "#9a6700",
                    }}
                  >
                    {s.status.toUpperCase()}
                  </span>

                  <button
                    onClick={() => handleToggleDetails(s.id)}
                    style={{
                      padding: "4px 8px",
                      fontSize: "11px",
                      borderRadius: "4px",
                      border: "1px solid #d0d7de",
                      backgroundColor: "#f6f8fa",
                      cursor: "pointer",
                    }}
                  >
                    {expandedSourceId === s.id ? "Hide Details" : "View History & Blocks"}
                  </button>
                </div>
              </div>

              {expandedSourceId === s.id && (
                <div style={{ padding: "12px", backgroundColor: "#ffffff", borderTop: "1px solid #eee", fontSize: "12px" }}>
                  {isDetailsLoading ? (
                    <div>Loading history and parsed blocks...</div>
                  ) : (
                    <>
                      <div style={{ fontWeight: 600, marginBottom: "6px" }}>Fetch Attempt History:</div>
                      {attempts.length === 0 ? (
                        <div style={{ color: "#666", marginBottom: "12px" }}>No fetch attempts logged yet.</div>
                      ) : (
                        <table style={{ width: "100%", borderCollapse: "collapse", marginBottom: "12px", textAlign: "left" }}>
                          <thead>
                            <tr style={{ backgroundColor: "#f6f8fa", borderBottom: "1px solid #ddd" }}>
                              <th style={{ padding: "4px" }}>Adapter</th>
                              <th style={{ padding: "4px" }}>Outcome</th>
                              <th style={{ padding: "4px" }}>HTTP Status</th>
                              <th style={{ padding: "4px" }}>Bytes</th>
                            </tr>
                          </thead>
                          <tbody>
                            {attempts.map((att) => (
                              <tr key={att.id} style={{ borderBottom: "1px solid #eee" }}>
                                <td style={{ padding: "4px" }}>{att.adapter}</td>
                                <td style={{ padding: "4px" }}>{att.outcome_code}</td>
                                <td style={{ padding: "4px" }}>{att.http_status ?? "N/A"}</td>
                                <td style={{ padding: "4px" }}>{att.byte_count}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      )}

                      <div style={{ fontWeight: 600, marginBottom: "6px" }}>Extracted Document Blocks ({blocks.length}):</div>
                      {blocks.length === 0 ? (
                        <div style={{ color: "#666" }}>No parsed document blocks stored.</div>
                      ) : (
                        <div style={{ display: "flex", flexDirection: "column", gap: "4px", maxHeight: "200px", overflowY: "auto" }}>
                          {blocks.map((blk) => (
                            <div key={blk.id} style={{ padding: "6px", backgroundColor: "#f6f8fa", borderRadius: "4px" }}>
                              <span style={{ fontWeight: 600, color: "#0969da" }}>[{blk.block_key}] ({blk.block_type}): </span>
                              <span>{blk.text_content}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

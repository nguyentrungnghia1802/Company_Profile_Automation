"use client";

import React, { useState, useEffect, useCallback } from "react";
import { getApiClient } from "@vcps/api-client";
import { useAuth } from "../../stores/authContext";
import { ResearchProgressTracker } from "../research/ResearchProgressTracker";
import { SourcesList } from "../sources/SourcesList";
import { FactCandidatesList } from "../facts/FactCandidatesList";
import { ConflictsList } from "../conflicts/ConflictsList";
import { PublishedProfileView } from "../profiles/PublishedProfileView";
import { ProfileDraftEditor } from "../profiles/ProfileDraftEditor";
import { ReviewInbox } from "../review/ReviewInbox";

export interface CompanyDetailItem {
  id: string;
  workspace_id: string;
  company_name: string;
  normalized_name: string;
  tax_id: string | null;
  legal_name: string | null;
  registration_number: string | null;
  industry: string | null;
  website_url: string | null;
  status: string;
  confidence_score: number;
  version: number;
}

interface CompanyDetailProps {
  companyId: string;
  onBack: () => void;
}

export const CompanyDetail: React.FC<CompanyDetailProps> = ({ companyId, onBack }) => {
  const { activeWorkspace, hasCapability } = useAuth();
  const [company, setCompany] = useState<CompanyDetailItem | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"published" | "drafts" | "facts" | "conflicts" | "sources" | "inbox">("published");

  const token = typeof window !== "undefined" ? localStorage.getItem("vcps_access_token") || "" : "";
  const workspaceId = activeWorkspace?.id || "";

  // Edit form state
  const [editName, setEditName] = useState("");
  const [editTaxId, setEditTaxId] = useState("");
  const [editLegalName, setEditLegalName] = useState("");
  const [editRegNumber, setEditRegNumber] = useState("");
  const [editIndustry, setEditIndustry] = useState("");
  const [editWebsite, setEditWebsite] = useState("");
  const [editStatus, setEditStatus] = useState("");

  const canUpdate = hasCapability("company:update");

  const loadCompany = useCallback(async () => {
    if (!activeWorkspace || !companyId) return;
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const token = localStorage.getItem("vcps_access_token") || "";
      const client = getApiClient();
      const data = await client.getCompany(token, activeWorkspace.id, companyId);
      setCompany(data);
      setEditName(data.company_name);
      setEditTaxId(data.tax_id || "");
      setEditLegalName(data.legal_name || "");
      setEditRegNumber(data.registration_number || "");
      setEditIndustry(data.industry || "");
      setEditWebsite(data.website_url || "");
      setEditStatus(data.status);
    } catch {
      setErrorMsg("Failed to load company details.");
    } finally {
      setIsLoading(false);
    }
  }, [activeWorkspace, companyId]);

  useEffect(() => {
    loadCompany();
  }, [loadCompany]);

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeWorkspace || !companyId) return;
    try {
      const token = localStorage.getItem("vcps_access_token") || "";
      const client = getApiClient();
      await client.updateCompany(token, activeWorkspace.id, companyId, {
        company_name: editName,
        tax_id: editTaxId || undefined,
        legal_name: editLegalName || undefined,
        registration_number: editRegNumber || undefined,
        industry: editIndustry || undefined,
        website_url: editWebsite || undefined,
        status: editStatus,
      });
      setIsEditing(false);
      loadCompany();
    } catch {
      setErrorMsg("Failed to update company profile.");
    }
  };

  if (isLoading) return <div style={{ padding: "24px" }}>Loading company details...</div>;
  if (!company) return <div style={{ padding: "24px", color: "#cf222e" }}>Company not found.</div>;

  return (
    <div style={{ padding: "24px", maxWidth: "800px", fontFamily: "sans-serif" }}>
      <button
        onClick={onBack}
        style={{ padding: "6px 12px", marginBottom: "16px", borderRadius: "4px", border: "1px solid #ccc", background: "#fff", cursor: "pointer" }}
      >
        ← Back to Library
      </button>

      {errorMsg && (
        <div style={{ padding: "10px", backgroundColor: "#ffebe9", color: "#cf222e", borderRadius: "6px", marginBottom: "16px" }}>
          {errorMsg}
        </div>
      )}

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
        <div>
          <h2 style={{ margin: 0 }}>{company.company_name}</h2>
          <div style={{ color: "#666", fontSize: "14px" }}>Normalized: {company.normalized_name}</div>
        </div>
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <span
            style={{
              padding: "4px 10px",
              borderRadius: "12px",
              fontSize: "12px",
              fontWeight: 600,
              backgroundColor: company.status === "published" ? "#dafbe1" : "#fff8c5",
              color: company.status === "published" ? "#1a7f37" : "#9a6700",
            }}
          >
            {company.status.toUpperCase()}
          </span>
          <span style={{ fontSize: "12px", color: "#666" }}>v{company.version}</span>
          {canUpdate && !isEditing && (
            <button
              onClick={() => setIsEditing(true)}
              style={{ padding: "6px 12px", borderRadius: "6px", border: "1px solid #ccc", background: "#fff", cursor: "pointer" }}
            >
              Edit Metadata
            </button>
          )}
        </div>
      </div>

      {isEditing ? (
        <form onSubmit={handleUpdate} style={{ backgroundColor: "#f6f8fa", padding: "16px", borderRadius: "8px" }}>
          <div style={{ marginBottom: "12px" }}>
            <label style={{ display: "block", fontSize: "12px", fontWeight: 600 }}>Company Name</label>
            <input
              type="text"
              required
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              style={{ width: "100%", padding: "8px", borderRadius: "4px", border: "1px solid #ccc" }}
            />
          </div>

          <div style={{ display: "flex", gap: "12px", marginBottom: "12px" }}>
            <div style={{ flex: 1 }}>
              <label style={{ display: "block", fontSize: "12px", fontWeight: 600 }}>Tax ID</label>
              <input
                type="text"
                value={editTaxId}
                onChange={(e) => setEditTaxId(e.target.value)}
                style={{ width: "100%", padding: "8px", borderRadius: "4px", border: "1px solid #ccc" }}
              />
            </div>
            <div style={{ flex: 1 }}>
              <label style={{ display: "block", fontSize: "12px", fontWeight: 600 }}>Status</label>
              <select
                value={editStatus}
                onChange={(e) => setEditStatus(e.target.value)}
                style={{ width: "100%", padding: "8px", borderRadius: "4px", border: "1px solid #ccc" }}
              >
                <option value="draft">Draft</option>
                <option value="published">Published</option>
                <option value="archived">Archived</option>
              </select>
            </div>
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px" }}>
            <button
              type="button"
              onClick={() => setIsEditing(false)}
              style={{ padding: "6px 12px", borderRadius: "4px", border: "1px solid #ccc", background: "#fff", cursor: "pointer" }}
            >
              Cancel
            </button>
            <button
              type="submit"
              style={{ padding: "6px 12px", borderRadius: "4px", border: "none", background: "#2da44e", color: "#fff", fontWeight: 600, cursor: "pointer" }}
            >
              Save Changes
            </button>
          </div>
        </form>
      ) : (
        <div style={{ borderTop: "1px solid #eaeaea", paddingTop: "16px" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
            <div>
              <strong>Legal Name:</strong> {company.legal_name || "—"}
            </div>
            <div>
              <strong>Tax ID:</strong> {company.tax_id || "—"}
            </div>
            <div>
              <strong>Registration Number:</strong> {company.registration_number || "—"}
            </div>
            <div>
              <strong>Industry:</strong> {company.industry || "—"}
            </div>
            <div>
              <strong>Website:</strong> {company.website_url ? <a href={company.website_url} target="_blank" rel="noreferrer">{company.website_url}</a> : "—"}
            </div>
            <div>
              <strong>Confidence Score:</strong> {(company.confidence_score * 100).toFixed(0)}%
            </div>
          </div>

          <div style={{ marginTop: "24px" }}>
            <ResearchProgressTracker companyId={company.id} />
          </div>

          <div style={{ marginTop: "24px" }}>
            <div style={{ display: "flex", borderBottom: "1px solid #d0d7de", gap: "16px", marginBottom: "16px", overflowX: "auto" }}>
              <button
                onClick={() => setActiveTab("published")}
                style={{
                  padding: "8px 12px",
                  fontSize: "14px",
                  fontWeight: 600,
                  border: "none",
                  borderBottom: activeTab === "published" ? "2px solid #0969da" : "2px solid transparent",
                  color: activeTab === "published" ? "#0969da" : "#57606a",
                  background: "none",
                  cursor: "pointer",
                }}
              >
                Published Profile
              </button>
              <button
                onClick={() => setActiveTab("drafts")}
                style={{
                  padding: "8px 12px",
                  fontSize: "14px",
                  fontWeight: 600,
                  border: "none",
                  borderBottom: activeTab === "drafts" ? "2px solid #0969da" : "2px solid transparent",
                  color: activeTab === "drafts" ? "#0969da" : "#57606a",
                  background: "none",
                  cursor: "pointer",
                }}
              >
                Profile Drafts
              </button>
              <button
                onClick={() => setActiveTab("facts")}
                style={{
                  padding: "8px 12px",
                  fontSize: "14px",
                  fontWeight: 600,
                  border: "none",
                  borderBottom: activeTab === "facts" ? "2px solid #0969da" : "2px solid transparent",
                  color: activeTab === "facts" ? "#0969da" : "#57606a",
                  background: "none",
                  cursor: "pointer",
                }}
              >
                Fact Candidates
              </button>
              <button
                onClick={() => setActiveTab("conflicts")}
                style={{
                  padding: "8px 12px",
                  fontSize: "14px",
                  fontWeight: 600,
                  border: "none",
                  borderBottom: activeTab === "conflicts" ? "2px solid #0969da" : "2px solid transparent",
                  color: activeTab === "conflicts" ? "#0969da" : "#57606a",
                  background: "none",
                  cursor: "pointer",
                }}
              >
                Conflicts
              </button>
              <button
                onClick={() => setActiveTab("sources")}
                style={{
                  padding: "8px 12px",
                  fontSize: "14px",
                  fontWeight: 600,
                  border: "none",
                  borderBottom: activeTab === "sources" ? "2px solid #0969da" : "2px solid transparent",
                  color: activeTab === "sources" ? "#0969da" : "#57606a",
                  background: "none",
                  cursor: "pointer",
                }}
              >
                Sources & Snapshots
              </button>
              <button
                onClick={() => setActiveTab("inbox")}
                style={{
                  padding: "8px 12px",
                  fontSize: "14px",
                  fontWeight: 600,
                  border: "none",
                  borderBottom: activeTab === "inbox" ? "2px solid #0969da" : "2px solid transparent",
                  color: activeTab === "inbox" ? "#0969da" : "#57606a",
                  background: "none",
                  cursor: "pointer",
                }}
              >
                Review Inbox
              </button>
            </div>

            {activeTab === "published" && (
              <PublishedProfileView
                token={token}
                workspaceId={workspaceId}
                companyId={company.id}
              />
            )}
            {activeTab === "drafts" && (
              <ProfileDraftEditor
                token={token}
                workspaceId={workspaceId}
                companyId={company.id}
                onPublished={() => setActiveTab("published")}
              />
            )}
            {activeTab === "facts" && <FactCandidatesList companyId={company.id} />}
            {activeTab === "conflicts" && <ConflictsList companyId={company.id} />}
            {activeTab === "sources" && <SourcesList companyId={company.id} />}
            {activeTab === "inbox" && (
              <ReviewInbox
                token={token}
                workspaceId={workspaceId}
                companyId={company.id}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
};

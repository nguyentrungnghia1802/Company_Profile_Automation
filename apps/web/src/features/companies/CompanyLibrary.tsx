"use client";

import React, { useState, useEffect, useCallback } from "react";
import { getApiClient } from "@vcps/api-client";
import { useAuth } from "../../stores/authContext";
import { CreateCompanyModal } from "./CreateCompanyModal";
import { MergeCompanyModal } from "./MergeCompanyModal";
import { CompanyDetail } from "./CompanyDetail";

export interface CompanyItem {
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

export const CompanyLibrary: React.FC = () => {
  const { activeWorkspace, hasCapability } = useAuth();
  const [companies, setCompanies] = useState<CompanyItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Selected company for details or merge
  const [selectedCompanyId, setSelectedCompanyId] = useState<string | null>(null);
  const [mergeSourceCompany, setMergeSourceCompany] = useState<CompanyItem | null>(null);

  // Modals
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  const canCreate = hasCapability("company:create");
  const canMerge = hasCapability("company:merge");

  const loadCompanies = useCallback(async () => {
    if (!activeWorkspace) return;
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const token = localStorage.getItem("vcps_access_token") || "";
      const client = getApiClient();
      const data = await client.listCompanies(token, activeWorkspace.id, statusFilter || undefined);
      setCompanies(data);
    } catch {
      setErrorMsg("Failed to load company profiles.");
    } finally {
      setIsLoading(false);
    }
  }, [activeWorkspace, statusFilter]);

  useEffect(() => {
    loadCompanies();
  }, [loadCompanies]);

  const filteredCompanies = companies.filter((c) => {
    if (!searchTerm.trim()) return true;
    const term = searchTerm.toLowerCase();
    return (
      c.company_name.toLowerCase().includes(term) ||
      (c.tax_id && c.tax_id.toLowerCase().includes(term)) ||
      (c.registration_number && c.registration_number.toLowerCase().includes(term))
    );
  });

  if (selectedCompanyId) {
    return (
      <CompanyDetail
        companyId={selectedCompanyId}
        onBack={() => {
          setSelectedCompanyId(null);
          loadCompanies();
        }}
      />
    );
  }

  return (
    <div style={{ padding: "24px", maxWidth: "1000px", fontFamily: "sans-serif" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
        <div>
          <h2 style={{ margin: 0 }}>Company Profiles Library</h2>
          <p style={{ color: "#666", margin: "4px 0 0 0" }}>
            Workspace: <strong>{activeWorkspace?.name || "None"}</strong>
          </p>
        </div>
        {canCreate && (
          <button
            onClick={() => setIsCreateOpen(true)}
            style={{
              padding: "8px 16px",
              backgroundColor: "#2da44e",
              color: "#fff",
              border: "none",
              borderRadius: "6px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            + Create Company
          </button>
        )}
      </div>

      {errorMsg && (
        <div style={{ padding: "12px", backgroundColor: "#ffebe9", color: "#cf222e", borderRadius: "6px", marginBottom: "16px" }}>
          {errorMsg}
        </div>
      )}

      {/* Filter Controls */}
      <div style={{ display: "flex", gap: "12px", marginBottom: "20px" }}>
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Search by name, Tax ID, or Reg Number..."
          style={{ flex: 1, padding: "8px 12px", borderRadius: "6px", border: "1px solid #ccc" }}
        />

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          style={{ padding: "8px 12px", borderRadius: "6px", border: "1px solid #ccc" }}
        >
          <option value="">All Statuses</option>
          <option value="draft">Draft</option>
          <option value="published">Published</option>
          <option value="archived">Archived</option>
          <option value="merged">Merged</option>
        </select>
      </div>

      {/* Company List Table */}
      {isLoading ? (
        <div>Loading company profiles...</div>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left" }}>
          <thead>
            <tr style={{ borderBottom: "2px solid #eaeaea" }}>
              <th style={{ padding: "12px" }}>Company Name</th>
              <th style={{ padding: "12px" }}>Tax ID</th>
              <th style={{ padding: "12px" }}>Industry</th>
              <th style={{ padding: "12px" }}>Status</th>
              <th style={{ padding: "12px" }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredCompanies.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ padding: "24px", textAlign: "center", color: "#666" }}>
                  No company profiles found in this workspace.
                </td>
              </tr>
            ) : (
              filteredCompanies.map((c) => (
                <tr key={c.id} style={{ borderBottom: "1px solid #eaeaea" }}>
                  <td style={{ padding: "12px", fontWeight: 600 }}>{c.company_name}</td>
                  <td style={{ padding: "12px" }}>{c.tax_id || "—"}</td>
                  <td style={{ padding: "12px" }}>{c.industry || "—"}</td>
                  <td style={{ padding: "12px" }}>
                    <span
                      style={{
                        padding: "4px 8px",
                        borderRadius: "12px",
                        fontSize: "12px",
                        fontWeight: 600,
                        backgroundColor: c.status === "published" ? "#dafbe1" : c.status === "merged" ? "#ffebe9" : "#fff8c5",
                        color: c.status === "published" ? "#1a7f37" : c.status === "merged" ? "#cf222e" : "#9a6700",
                      }}
                    >
                      {c.status}
                    </span>
                  </td>
                  <td style={{ padding: "12px" }}>
                    <div style={{ display: "flex", gap: "8px" }}>
                      <button
                        onClick={() => setSelectedCompanyId(c.id)}
                        style={{ padding: "4px 8px", borderRadius: "4px", border: "1px solid #ccc", background: "#fff", fontSize: "12px", cursor: "pointer" }}
                      >
                        Details
                      </button>
                      {canMerge && c.status !== "merged" && (
                        <button
                          onClick={() => setMergeSourceCompany(c)}
                          style={{ padding: "4px 8px", borderRadius: "4px", border: "1px solid #cf222e", background: "#fff", color: "#cf222e", fontSize: "12px", cursor: "pointer" }}
                        >
                          Merge
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      )}

      {/* Create Company Modal */}
      <CreateCompanyModal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        onSuccess={() => loadCompanies()}
      />

      {/* Merge Company Modal */}
      <MergeCompanyModal
        isOpen={!!mergeSourceCompany}
        sourceCompany={mergeSourceCompany}
        availableCompanies={companies}
        onClose={() => setMergeSourceCompany(null)}
        onSuccess={() => loadCompanies()}
      />
    </div>
  );
};

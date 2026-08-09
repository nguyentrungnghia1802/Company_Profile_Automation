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
    <div style={{ maxWidth: "1200px", fontFamily: "inherit" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
        <div>
          <h2 style={{ margin: 0, fontSize: "1.3rem", color: "#f8fafc" }}>Thư viện Doanh nghiệp (Company Profiles)</h2>
          <p style={{ color: "#94a3b8", fontSize: "0.85rem", margin: "4px 0 0 0" }}>
            Không gian làm việc: <strong style={{ color: "#3b82f6" }}>{activeWorkspace?.name || "AI Riser Competition Workspace"}</strong>
          </p>
        </div>
        {canCreate && (
          <button
            onClick={() => setIsCreateOpen(true)}
            style={{
              padding: "10px 18px",
              backgroundColor: "#10b981",
              color: "#fff",
              border: "none",
              borderRadius: "8px",
              fontWeight: 600,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            <span>+</span> Tạo hồ sơ mới
          </button>
        )}
      </div>

      {errorMsg && (
        <div style={{ padding: "12px", backgroundColor: "#7f1d1d", color: "#fca5a5", borderRadius: "8px", marginBottom: "16px" }}>
          {errorMsg}
        </div>
      )}

      {/* Filter Controls */}
      <div style={{ display: "flex", gap: "12px", marginBottom: "20px" }}>
        <input
          id="company-library-search"
          name="company_search"
          type="text"
          aria-label="Search companies"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Lọc theo Tên doanh nghiệp, Mã số thuế Tax ID, Ngành nghề..."
          style={{
            flex: 1,
            padding: "10px 14px",
            borderRadius: "8px",
            border: "1px solid #334155",
            background: "#0f172a",
            color: "#f8fafc",
            outline: "none",
          }}
        />

        <select
          id="company-library-status"
          name="company_status"
          aria-label="Filter companies by status"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          style={{
            padding: "10px 14px",
            borderRadius: "8px",
            border: "1px solid #334155",
            background: "#0f172a",
            color: "#f8fafc",
            outline: "none",
          }}
        >
          <option value="">Tất cả trạng thái</option>
          <option value="draft">Bản nháp (Draft)</option>
          <option value="published">Đã xuất bản (Published)</option>
          <option value="archived">Đã lưu trữ (Archived)</option>
          <option value="merged">Đã hợp nhất (Merged)</option>
        </select>
      </div>

      {/* Company List Table */}
      {isLoading ? (
        <div style={{ padding: "24px", color: "#94a3b8" }}>Đang tải danh sách doanh nghiệp...</div>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left" }}>
          <thead>
            <tr style={{ borderBottom: "2px solid #334155", color: "#94a3b8", fontSize: "0.85rem" }}>
              <th style={{ padding: "12px" }}>Tên Công Ty</th>
              <th style={{ padding: "12px" }}>Mã Số Thuế</th>
              <th style={{ padding: "12px" }}>Website / Ngành Nghề</th>
              <th style={{ padding: "12px" }}>Trạng Thái</th>
              <th style={{ padding: "12px" }}>Thao Tác</th>
            </tr>
          </thead>
          <tbody>
            {filteredCompanies.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ padding: "32px", textAlign: "center", color: "#94a3b8" }}>
                  Không tìm thấy doanh nghiệp nào phù hợp.
                </td>
              </tr>
            ) : (
              filteredCompanies.map((c) => (
                <tr key={c.id} style={{ borderBottom: "1px solid #334155" }}>
                  <td style={{ padding: "14px 12px" }}>
                    <div style={{ fontWeight: 600, color: "#f8fafc", fontSize: "0.95rem" }}>{c.company_name}</div>
                    {c.legal_name && <div style={{ fontSize: "0.78rem", color: "#94a3b8" }}>{c.legal_name}</div>}
                  </td>
                  <td style={{ padding: "14px 12px", color: "#cbd5e1", fontSize: "0.9rem" }}>{c.tax_id || "—"}</td>
                  <td style={{ padding: "14px 12px", color: "#cbd5e1", fontSize: "0.9rem" }}>
                    {c.website_url ? (
                      <a href={c.website_url} target="_blank" rel="noreferrer" style={{ color: "#3b82f6", textDecoration: "underline" }}>
                        {c.website_url}
                      </a>
                    ) : (
                      c.industry || "—"
                    )}
                  </td>
                  <td style={{ padding: "14px 12px" }}>
                    <span
                      style={{
                        padding: "4px 10px",
                        borderRadius: "12px",
                        fontSize: "12px",
                        fontWeight: 600,
                        backgroundColor: c.status === "published" ? "rgba(16, 185, 129, 0.15)" : c.status === "merged" ? "rgba(239, 68, 68, 0.15)" : "rgba(245, 158, 11, 0.15)",
                        color: c.status === "published" ? "#34d399" : c.status === "merged" ? "#f87171" : "#fbbf24",
                        border: `1px solid ${c.status === "published" ? "rgba(16, 185, 129, 0.3)" : c.status === "merged" ? "rgba(239, 68, 68, 0.3)" : "rgba(245, 158, 11, 0.3)"}`,
                      }}
                    >
                      {c.status.toUpperCase()}
                    </span>
                  </td>
                  <td style={{ padding: "14px 12px" }}>
                    <div style={{ display: "flex", gap: "8px" }}>
                      <button
                        onClick={() => setSelectedCompanyId(c.id)}
                        style={{
                          padding: "6px 12px",
                          borderRadius: "6px",
                          border: "1px solid #475569",
                          background: "#0f172a",
                          color: "#f8fafc",
                          fontSize: "12px",
                          fontWeight: 500,
                          cursor: "pointer",
                        }}
                      >
                        Chi tiết
                      </button>
                      {canMerge && c.status !== "merged" && (
                        <button
                          onClick={() => setMergeSourceCompany(c)}
                          style={{
                            padding: "6px 12px",
                            borderRadius: "6px",
                            border: "1px solid #ef4444",
                            background: "transparent",
                            color: "#ef4444",
                            fontSize: "12px",
                            fontWeight: 500,
                            cursor: "pointer",
                          }}
                        >
                          Hợp nhất
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

"use client";

import React, { useState, useEffect } from "react";
import { getApiClient } from "@vcps/api-client";
import { useAuth } from "../../stores/authContext";

export interface CandidateItem {
  company_id: string;
  company_name: string;
  tax_id: string | null;
  registration_number: string | null;
  match_score: number;
  match_reason: string;
}

interface CreateCompanyModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const CreateCompanyModal: React.FC<CreateCompanyModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const { activeWorkspace } = useAuth();
  const [companyName, setCompanyName] = useState("");
  const [taxId, setTaxId] = useState("");
  const [legalName, setLegalName] = useState("");
  const [regNumber, setRegNumber] = useState("");
  const [industry, setIndustry] = useState("");
  const [websiteUrl, setWebsiteUrl] = useState("");
  const [duplicates, setDuplicates] = useState<CandidateItem[]>([]);
  const [isResolving, setIsResolving] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Check duplicate candidates on name or tax_id input debounce
  useEffect(() => {
    if (!companyName.trim() || !activeWorkspace) {
      setDuplicates([]);
      return;
    }

    const timer = setTimeout(async () => {
      setIsResolving(true);
      try {
        const token = localStorage.getItem("vcps_access_token") || "";
        const client = getApiClient();
        const res = await client.resolveCompany(token, activeWorkspace.id, {
          company_name: companyName,
          tax_id: taxId || undefined,
          registration_number: regNumber || undefined,
        });
        setDuplicates(res.filter((c: CandidateItem) => c.match_score >= 0.65));
      } catch {
        // Ignore resolution preview errors
      } finally {
        setIsResolving(false);
      }
    }, 400);

    return () => clearTimeout(timer);
  }, [companyName, taxId, regNumber, activeWorkspace]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeWorkspace || !companyName) return;
    setErrorMsg(null);

    try {
      const token = localStorage.getItem("vcps_access_token") || "";
      const client = getApiClient();
      await client.createCompany(token, activeWorkspace.id, {
        company_name: companyName,
        tax_id: taxId || undefined,
        legal_name: legalName || undefined,
        registration_number: regNumber || undefined,
        industry: industry || undefined,
        website_url: websiteUrl || undefined,
      });
      onSuccess();
      onClose();
    } catch {
      setErrorMsg("Failed to create company profile.");
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(0,0,0,0.75)",
        backdropFilter: "blur(4px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
      }}
    >
      <div
        style={{
          backgroundColor: "#1e293b",
          border: "1px solid #334155",
          color: "#f8fafc",
          borderRadius: "12px",
          padding: "24px",
          maxWidth: "600px",
          width: "100%",
          maxHeight: "90vh",
          overflowY: "auto",
          fontFamily: "inherit",
          boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.5)",
        }}
      >
        <h3 style={{ marginTop: 0, fontSize: "1.2rem", fontWeight: 700, color: "#f8fafc" }}>
          Tạo Hồ Sơ / Tra Cứu Doanh Nghiệp Mới
        </h3>

        {errorMsg && (
          <div
            style={{
              padding: "10px 14px",
              backgroundColor: "#7f1d1d",
              color: "#fca5a5",
              borderRadius: "8px",
              marginBottom: "16px",
              fontSize: "0.9rem",
            }}
          >
            {errorMsg}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: "14px" }}>
            <label htmlFor="create-company-name" style={{ display: "block", fontSize: "13px", fontWeight: 600, color: "#cbd5e1", marginBottom: "6px" }}>
              Tên Công Ty / Doanh Nghiệp *
            </label>
            <input
              id="create-company-name"
              name="company_name"
              type="text"
              required
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              placeholder="VD: Tập đoàn FPT, VinFast, VNG, Viettel..."
              style={{
                width: "100%",
                padding: "10px 12px",
                borderRadius: "8px",
                border: "1px solid #334155",
                background: "#0f172a",
                color: "#f8fafc",
                outline: "none",
              }}
            />
          </div>

          <div style={{ display: "flex", gap: "12px", marginBottom: "14px" }}>
            <div style={{ flex: 1 }}>
              <label htmlFor="create-company-tax-id" style={{ display: "block", fontSize: "13px", fontWeight: 600, color: "#cbd5e1", marginBottom: "6px" }}>
                Mã Số Thuế (Tax ID)
              </label>
              <input
                id="create-company-tax-id"
                name="tax_id"
                type="text"
                value={taxId}
                onChange={(e) => setTaxId(e.target.value)}
                placeholder="0101234567"
                style={{
                  width: "100%",
                  padding: "10px 12px",
                  borderRadius: "8px",
                  border: "1px solid #334155",
                  background: "#0f172a",
                  color: "#f8fafc",
                  outline: "none",
                }}
              />
            </div>
            <div style={{ flex: 1 }}>
              <label htmlFor="create-company-registration-number" style={{ display: "block", fontSize: "13px", fontWeight: 600, color: "#cbd5e1", marginBottom: "6px" }}>
                Số Đăng Ký Kinh Doanh
              </label>
              <input
                id="create-company-registration-number"
                name="registration_number"
                type="text"
                value={regNumber}
                onChange={(e) => setRegNumber(e.target.value)}
                placeholder="REG-123456"
                style={{
                  width: "100%",
                  padding: "10px 12px",
                  borderRadius: "8px",
                  border: "1px solid #334155",
                  background: "#0f172a",
                  color: "#f8fafc",
                  outline: "none",
                }}
              />
            </div>
          </div>

          {/* Duplicate Candidates Warning Banner */}
          {isResolving && <div style={{ fontSize: "12px", color: "#94a3b8", marginBottom: "12px" }}>Đang kiểm tra dữ liệu trùng lặp...</div>}

          {duplicates.length > 0 && (
            <div
              style={{
                backgroundColor: "rgba(245, 158, 11, 0.15)",
                border: "1px solid rgba(245, 158, 11, 0.3)",
                borderRadius: "8px",
                padding: "12px",
                marginBottom: "16px",
              }}
            >
              <div style={{ fontWeight: 600, color: "#fbbf24", marginBottom: "6px", fontSize: "0.9rem" }}>
                ⚠️ Phát hiện doanh nghiệp trùng lặp tiềm năng ({duplicates.length})
              </div>
              <ul style={{ margin: 0, paddingLeft: "20px", fontSize: "13px", color: "#fef3c7" }}>
                {duplicates.map((cand) => (
                  <li key={cand.company_id}>
                    <strong>{cand.company_name}</strong> (Khớp: {(cand.match_score * 100).toFixed(0)}% — {cand.match_reason})
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div style={{ marginBottom: "14px" }}>
            <label htmlFor="create-company-legal-name" style={{ display: "block", fontSize: "13px", fontWeight: 600, color: "#cbd5e1", marginBottom: "6px" }}>Tên Pháp Lý Đầy Đủ (Legal Name)</label>
            <input
              id="create-company-legal-name"
              name="legal_name"
              type="text"
              value={legalName}
              onChange={(e) => setLegalName(e.target.value)}
              placeholder="Công ty Cổ phần / TNHH..."
              style={{
                width: "100%",
                padding: "10px 12px",
                borderRadius: "8px",
                border: "1px solid #334155",
                background: "#0f172a",
                color: "#f8fafc",
                outline: "none",
              }}
            />
          </div>

          <div style={{ display: "flex", gap: "12px", marginBottom: "20px" }}>
            <div style={{ flex: 1 }}>
              <label htmlFor="create-company-industry" style={{ display: "block", fontSize: "13px", fontWeight: 600, color: "#cbd5e1", marginBottom: "6px" }}>Ngành Nghề</label>
              <input
                id="create-company-industry"
                name="industry"
                type="text"
                value={industry}
                onChange={(e) => setIndustry(e.target.value)}
                placeholder="Software / AI / Automative"
                style={{
                  width: "100%",
                  padding: "10px 12px",
                  borderRadius: "8px",
                  border: "1px solid #334155",
                  background: "#0f172a",
                  color: "#f8fafc",
                  outline: "none",
                }}
              />
            </div>
            <div style={{ flex: 1 }}>
              <label htmlFor="create-company-website" style={{ display: "block", fontSize: "13px", fontWeight: 600, color: "#cbd5e1", marginBottom: "6px" }}>Website URL</label>
              <input
                id="create-company-website"
                name="website_url"
                type="url"
                value={websiteUrl}
                onChange={(e) => setWebsiteUrl(e.target.value)}
                placeholder="https://example.com"
                style={{
                  width: "100%",
                  padding: "10px 12px",
                  borderRadius: "8px",
                  border: "1px solid #334155",
                  background: "#0f172a",
                  color: "#f8fafc",
                  outline: "none",
                }}
              />
            </div>
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
            <button
              type="button"
              onClick={onClose}
              style={{
                padding: "10px 18px",
                borderRadius: "8px",
                border: "1px solid #475569",
                background: "#0f172a",
                color: "#f8fafc",
                cursor: "pointer",
                fontWeight: 500,
              }}
            >
              Hủy
            </button>
            <button
              type="submit"
              style={{
                padding: "10px 20px",
                borderRadius: "8px",
                border: "none",
                background: "#10b981",
                color: "#fff",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              {duplicates.length > 0 ? "Vẫn Tạo Mới" : "Tạo Hồ Sơ Doanh Nghiệp"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

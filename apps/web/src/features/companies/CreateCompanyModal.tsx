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
        backgroundColor: "rgba(0,0,0,0.5)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
      }}
    >
      <div
        style={{
          backgroundColor: "#fff",
          borderRadius: "8px",
          padding: "24px",
          maxWidth: "600px",
          width: "100%",
          maxHeight: "90vh",
          overflowY: "auto",
          fontFamily: "sans-serif",
        }}
      >
        <h3 style={{ marginTop: 0 }}>Create New Company Profile</h3>

        {errorMsg && (
          <div
            style={{
              padding: "10px",
              backgroundColor: "#ffebe9",
              color: "#cf222e",
              borderRadius: "6px",
              marginBottom: "12px",
            }}
          >
            {errorMsg}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: "12px" }}>
            <label style={{ display: "block", fontSize: "12px", fontWeight: 600 }}>
              Company Name *
            </label>
            <input
              type="text"
              required
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              placeholder="e.g. Công ty TNHH AI Riser Việt Nam"
              style={{ width: "100%", padding: "8px", borderRadius: "4px", border: "1px solid #ccc" }}
            />
          </div>

          <div style={{ display: "flex", gap: "12px", marginBottom: "12px" }}>
            <div style={{ flex: 1 }}>
              <label style={{ display: "block", fontSize: "12px", fontWeight: 600 }}>Tax ID</label>
              <input
                type="text"
                value={taxId}
                onChange={(e) => setTaxId(e.target.value)}
                placeholder="0101234567"
                style={{ width: "100%", padding: "8px", borderRadius: "4px", border: "1px solid #ccc" }}
              />
            </div>
            <div style={{ flex: 1 }}>
              <label style={{ display: "block", fontSize: "12px", fontWeight: 600 }}>
                Registration Number
              </label>
              <input
                type="text"
                value={regNumber}
                onChange={(e) => setRegNumber(e.target.value)}
                placeholder="REG-123456"
                style={{ width: "100%", padding: "8px", borderRadius: "4px", border: "1px solid #ccc" }}
              />
            </div>
          </div>

          {/* Duplicate Candidates Warning Banner */}
          {isResolving && <div style={{ fontSize: "12px", color: "#666" }}>Checking duplicate candidates...</div>}

          {duplicates.length > 0 && (
            <div
              style={{
                backgroundColor: "#fff8c5",
                border: "1px solid #d4a72c",
                borderRadius: "6px",
                padding: "12px",
                marginBottom: "16px",
              }}
            >
              <div style={{ fontWeight: 600, color: "#9a6700", marginBottom: "6px" }}>
                ⚠️ Potential Duplicate Candidates Found ({duplicates.length})
              </div>
              <ul style={{ margin: 0, paddingLeft: "20px", fontSize: "13px" }}>
                {duplicates.map((cand) => (
                  <li key={cand.company_id}>
                    <strong>{cand.company_name}</strong> (Match: {(cand.match_score * 100).toFixed(0)}% — {cand.match_reason})
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div style={{ marginBottom: "12px" }}>
            <label style={{ display: "block", fontSize: "12px", fontWeight: 600 }}>Legal Name</label>
            <input
              type="text"
              value={legalName}
              onChange={(e) => setLegalName(e.target.value)}
              style={{ width: "100%", padding: "8px", borderRadius: "4px", border: "1px solid #ccc" }}
            />
          </div>

          <div style={{ display: "flex", gap: "12px", marginBottom: "16px" }}>
            <div style={{ flex: 1 }}>
              <label style={{ display: "block", fontSize: "12px", fontWeight: 600 }}>Industry</label>
              <input
                type="text"
                value={industry}
                onChange={(e) => setIndustry(e.target.value)}
                placeholder="Software / AI"
                style={{ width: "100%", padding: "8px", borderRadius: "4px", border: "1px solid #ccc" }}
              />
            </div>
            <div style={{ flex: 1 }}>
              <label style={{ display: "block", fontSize: "12px", fontWeight: 600 }}>Website URL</label>
              <input
                type="url"
                value={websiteUrl}
                onChange={(e) => setWebsiteUrl(e.target.value)}
                placeholder="https://example.com"
                style={{ width: "100%", padding: "8px", borderRadius: "4px", border: "1px solid #ccc" }}
              />
            </div>
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px" }}>
            <button
              type="button"
              onClick={onClose}
              style={{ padding: "8px 16px", borderRadius: "6px", border: "1px solid #ccc", background: "#fff", cursor: "pointer" }}
            >
              Cancel
            </button>
            <button
              type="submit"
              style={{ padding: "8px 16px", borderRadius: "6px", border: "none", background: "#2da44e", color: "#fff", fontWeight: 600, cursor: "pointer" }}
            >
              {duplicates.length > 0 ? "Create Anyway" : "Create Company"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

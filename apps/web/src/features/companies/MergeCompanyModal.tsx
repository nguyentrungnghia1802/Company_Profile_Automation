"use client";

import React, { useState } from "react";
import { getApiClient } from "@vcps/api-client";
import { useAuth } from "../../stores/authContext";

export interface CompanyItem {
  id: string;
  company_name: string;
  tax_id: string | null;
  status: string;
}

interface MergeCompanyModalProps {
  isOpen: boolean;
  sourceCompany: CompanyItem | null;
  availableCompanies: CompanyItem[];
  onClose: () => void;
  onSuccess: () => void;
}

export const MergeCompanyModal: React.FC<MergeCompanyModalProps> = ({
  isOpen,
  sourceCompany,
  availableCompanies,
  onClose,
  onSuccess,
}) => {
  const { activeWorkspace } = useAuth();
  const [targetCompanyId, setTargetCompanyId] = useState("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen || !sourceCompany) return null;

  const validTargets = availableCompanies.filter(
    (c) => c.id !== sourceCompany.id && c.status !== "merged"
  );

  const handleMerge = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeWorkspace || !targetCompanyId) return;
    setIsSubmitting(true);
    setErrorMsg(null);

    try {
      const token = localStorage.getItem("vcps_access_token") || "";
      const client = getApiClient();
      await client.mergeCompany(token, activeWorkspace.id, targetCompanyId, sourceCompany.id);
      onSuccess();
      onClose();
    } catch {
      setErrorMsg("Failed to execute company merge.");
    } finally {
      setIsSubmitting(false);
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
          maxWidth: "500px",
          width: "100%",
          fontFamily: "sans-serif",
        }}
      >
        <h3 style={{ marginTop: 0, color: "#cf222e" }}>Merge Company Profile</h3>

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

        <div style={{ marginBottom: "16px", fontSize: "14px" }}>
          You are merging <strong>{sourceCompany.company_name}</strong> (Source) into a target company.
        </div>

        <form onSubmit={handleMerge}>
          <div style={{ marginBottom: "16px" }}>
            <label style={{ display: "block", fontSize: "12px", fontWeight: 600, marginBottom: "4px" }}>
              Select Target Company *
            </label>
            <select
              required
              value={targetCompanyId}
              onChange={(e) => setTargetCompanyId(e.target.value)}
              style={{ width: "100%", padding: "8px", borderRadius: "4px", border: "1px solid #ccc" }}
            >
              <option value="">-- Choose target canonical profile --</option>
              {validTargets.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.company_name} {c.tax_id ? `(Tax: ${c.tax_id})` : ""}
                </option>
              ))}
            </select>
          </div>

          <div
            style={{
              backgroundColor: "#f6f8fa",
              padding: "12px",
              borderRadius: "6px",
              fontSize: "13px",
              color: "#57606a",
              marginBottom: "20px",
            }}
          >
            <strong>Merge Behavior:</strong>
            <ul style={{ margin: "6px 0 0 0", paddingLeft: "18px" }}>
              <li>Source profile status will be updated to <code>merged</code>.</li>
              <li>Source name <em>"{sourceCompany.company_name}"</em> will be saved as a <code>former_name</code> alias on target profile.</li>
              <li>All source aliases and facts will be transferred to target.</li>
            </ul>
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
              disabled={isSubmitting || !targetCompanyId}
              style={{
                padding: "8px 16px",
                borderRadius: "6px",
                border: "none",
                background: "#cf222e",
                color: "#fff",
                fontWeight: 600,
                cursor: "pointer",
                opacity: isSubmitting || !targetCompanyId ? 0.6 : 1,
              }}
            >
              Confirm Merge
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

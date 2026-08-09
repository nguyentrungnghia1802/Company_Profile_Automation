"use client";

import React, { useState } from "react";
import { getApiClient } from "@vcps/api-client";
import { useAuth } from "../../stores/authContext";
import { formatErrorDetails, normalizeClientError, type NormalizedClientError } from "../../utils/errors";
import { ResearchProgressTracker } from "./ResearchProgressTracker";

interface CompanyResearchFlowProps {
  token: string;
  workspaceId: string;
  onSavedSuccess: () => void;
}

const inputStyle: React.CSSProperties = {
  width: "100%",
  boxSizing: "border-box",
  padding: "11px 12px",
  borderRadius: "8px",
  border: "1px solid #475569",
  background: "#0f172a",
  color: "#f8fafc",
  outline: "none",
};

const labelStyle: React.CSSProperties = {
  display: "block",
  marginBottom: "6px",
  color: "#cbd5e1",
  fontSize: "13px",
  fontWeight: 700,
};

function errorDetails(error: NormalizedClientError): string[] {
  return formatErrorDetails(error.details);
}

export const CompanyResearchFlow: React.FC<CompanyResearchFlowProps> = ({
  token,
  workspaceId,
  onSavedSuccess,
}) => {
  const { hasCapability } = useAuth();
  const [companyName, setCompanyName] = useState("");
  const [taxId, setTaxId] = useState("");
  const [websiteUrl, setWebsiteUrl] = useState("");
  const [researchNotes, setResearchNotes] = useState("");
  const [companyId, setCompanyId] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorInfo, setErrorInfo] = useState<NormalizedClientError | null>(null);
  const [createdWithoutJob, setCreatedWithoutJob] = useState(false);

  const canStart = hasCapability("research:start");

  const buildResearchScope = (): Record<string, unknown> => {
    const scope: Record<string, unknown> = {
      include_search_results: true,
      crawl_website: Boolean(websiteUrl.trim()),
      country_code: "VN",
      requested_sections: ["official", "about_company_history", "products", "leadership", "contact"],
    };
    if (websiteUrl.trim()) scope.website_url = websiteUrl.trim();
    if (researchNotes.trim()) scope.notes = researchNotes.trim();
    return scope;
  };

  const startResearch = async (nextCompanyId: string): Promise<void> => {
    const client = getApiClient();
    try {
      const job = await client.triggerCompanyResearch(token, workspaceId, nextCompanyId, {
        job_type: "initial",
        requested_locale: "vi",
        scope: buildResearchScope(),
      });
      if (!job?.id) {
        throw new Error("RESEARCH_JOB_ID_MISSING");
      }
      setJobId(String(job.id));
      setCreatedWithoutJob(false);
      setErrorInfo(null);
    } catch (error) {
      setCreatedWithoutJob(true);
      setErrorInfo(normalizeClientError(error));
    }
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmedName = companyName.trim();
    if (!trimmedName || !canStart) return;

    setIsSubmitting(true);
    setErrorInfo(null);
    setCreatedWithoutJob(false);
    setJobId(null);

    try {
      const client = getApiClient();
      const company = await client.createCompany(token, workspaceId, {
        company_name: trimmedName,
        tax_id: taxId.trim() || undefined,
        website_url: websiteUrl.trim() || undefined,
      });
      const nextCompanyId = String(company?.id || "");
      if (!nextCompanyId) throw new Error("COMPANY_ID_MISSING");
      setCompanyId(nextCompanyId);
      onSavedSuccess();
      await startResearch(nextCompanyId);
    } catch (error) {
      setErrorInfo(normalizeClientError(error));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRetry = async () => {
    if (!companyId) return;
    setIsSubmitting(true);
    setErrorInfo(null);
    await startResearch(companyId);
    setIsSubmitting(false);
  };

  return (
    <section aria-labelledby="company-research-title" style={{ color: "#f8fafc" }}>
      <div style={{ marginBottom: "22px" }}>
        <h2 id="company-research-title" style={{ margin: 0, fontSize: "1.45rem" }}>
          Tra cứu nguồn công khai
        </h2>
        <p style={{ margin: "8px 0 0", color: "#cbd5e1", lineHeight: 1.6 }}>
          Nhập danh tính doanh nghiệp để tạo một research job có lưu nguồn, snapshot và bằng chứng.
          Hệ thống không dùng hồ sơ mẫu và không tự điền giá trị chưa có bằng chứng.
        </p>
      </div>

      <div
        role="note"
        style={{
          padding: "13px 15px",
          marginBottom: "20px",
          border: "1px solid #2563eb",
          borderRadius: "10px",
          background: "rgba(37, 99, 235, 0.12)",
          color: "#dbeafe",
          fontSize: "13px",
          lineHeight: 1.6,
        }}
      >
        <strong>AI không bắt buộc.</strong> Nếu có website chính thức, hệ thống có thể thu thập và trích
        xuất trường có cấu trúc bằng bộ quy tắc deterministic. Nếu chỉ nhập tên, cần cấu hình
        <code style={{ margin: "0 4px" }}>SEARCH_PROVIDER=google</code> cùng Search API key và engine ID.
        Khi thiếu provider, job sẽ báo đúng lý do thay vì trả dữ liệu giả.
      </div>

      <form onSubmit={handleSubmit} aria-describedby="company-research-help">
        <div style={{ marginBottom: "14px" }}>
          <label htmlFor="company-research-company-name" style={labelStyle}>
            Tên doanh nghiệp <span aria-hidden="true">*</span>
          </label>
          <input
            id="company-research-company-name"
            name="company_name"
            type="text"
            required
            value={companyName}
            onChange={(event) => setCompanyName(event.target.value)}
            placeholder="Tên pháp lý hoặc tên thương mại"
            autoComplete="organization"
            style={inputStyle}
          />
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1fr)", gap: "12px" }}>
          <div style={{ marginBottom: "14px" }}>
            <label htmlFor="company-research-tax-id" style={labelStyle}>
              Mã số thuế / định danh (tuỳ chọn)
            </label>
            <input
              id="company-research-tax-id"
              name="tax_id"
              type="text"
              value={taxId}
              onChange={(event) => setTaxId(event.target.value)}
              placeholder="Không suy đoán nếu bỏ trống"
              autoComplete="off"
              style={inputStyle}
            />
          </div>

          <div style={{ marginBottom: "14px" }}>
            <label htmlFor="company-research-website-url" style={labelStyle}>
              Website chính thức (khuyến nghị)
            </label>
            <input
              id="company-research-website-url"
              name="website_url"
              type="url"
              value={websiteUrl}
              onChange={(event) => setWebsiteUrl(event.target.value)}
              placeholder="https://example.org"
              autoComplete="url"
              style={inputStyle}
            />
          </div>
        </div>

        <div style={{ marginBottom: "16px" }}>
          <label htmlFor="company-research-notes" style={labelStyle}>
            Ghi chú phạm vi tra cứu (tuỳ chọn)
          </label>
          <textarea
            id="company-research-notes"
            name="research_notes"
            value={researchNotes}
            onChange={(event) => setResearchNotes(event.target.value)}
            placeholder="Ví dụ: ưu tiên trang giới thiệu, liên hệ và tuyển dụng của website chính thức."
            rows={3}
            style={{ ...inputStyle, resize: "vertical", minHeight: "76px" }}
          />
        </div>

        <p id="company-research-help" style={{ margin: "0 0 14px", color: "#94a3b8", fontSize: "12px" }}>
          Kết quả không có nghĩa là doanh nghiệp không tồn tại. Nó chỉ cho biết các nguồn được phép
          truy cập hiện chưa cung cấp bằng chứng phù hợp.
        </p>

        <button
          type="submit"
          disabled={isSubmitting || !canStart || !companyName.trim()}
          style={{
            padding: "11px 18px",
            border: "none",
            borderRadius: "8px",
            background: isSubmitting || !canStart ? "#475569" : "#10b981",
            color: "#06251a",
            fontWeight: 800,
            cursor: isSubmitting || !canStart ? "not-allowed" : "pointer",
          }}
        >
          {isSubmitting ? "Đang tạo research job…" : "Bắt đầu tra cứu"}
        </button>
        {!canStart && (
          <p style={{ margin: "10px 0 0", color: "#fbbf24", fontSize: "13px" }}>
            Tài khoản hiện tại không có quyền research:start.
          </p>
        )}
      </form>

      {errorInfo && (
        <div
          role="alert"
          style={{
            marginTop: "18px",
            padding: "13px 15px",
            border: "1px solid #ef4444",
            borderRadius: "10px",
            background: "rgba(127, 29, 29, 0.35)",
            color: "#fecaca",
          }}
        >
          <div style={{ fontWeight: 800 }}>
            {errorInfo.code}: {errorInfo.message}
          </div>
          {errorDetails(errorInfo).length > 0 && (
            <ul style={{ margin: "8px 0 0", paddingLeft: "18px", fontSize: "13px" }}>
              {errorDetails(errorInfo).map((detail) => <li key={detail}>{detail}</li>)}
            </ul>
          )}
          {errorInfo.retryable && <div style={{ marginTop: "8px", fontSize: "13px" }}>Có thể thử lại sau khi xử lý nguyên nhân trên.</div>}
          {createdWithoutJob && companyId && (
            <button
              type="button"
              onClick={handleRetry}
              disabled={isSubmitting}
              style={{ marginTop: "10px", padding: "8px 12px", borderRadius: "7px", border: "1px solid #fca5a5", background: "transparent", color: "#fee2e2", cursor: "pointer" }}
            >
              Thử khởi động research lại
            </button>
          )}
        </div>
      )}

      {companyId && (
        <div style={{ marginTop: "24px" }}>
          <div style={{ marginBottom: "10px", color: "#cbd5e1", fontSize: "13px" }}>
            Hồ sơ đã tạo với ID <code>{companyId}</code>
            {jobId ? <>; research job <code>{jobId}</code> đã được xếp hàng.</> : "; research job chưa được khởi động."}
          </div>
          {jobId ? (
            <ResearchProgressTracker key={`${companyId}:${jobId}`} companyId={companyId} />
          ) : (
            <div style={{ padding: "12px 14px", border: "1px solid #f59e0b", borderRadius: "9px", color: "#fde68a", background: "rgba(120, 53, 15, 0.3)" }}>
              Hồ sơ được giữ nguyên; không có trường nào được bịa. Sửa cấu hình/provider rồi bấm thử lại.
            </div>
          )}
        </div>
      )}
    </section>
  );
};

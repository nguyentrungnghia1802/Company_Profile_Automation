"use client";

import React, { useEffect, useState } from "react";
import { getApiClient } from "@vcps/api-client";

interface ProgramFitCardProps {
  token: string;
  workspaceId: string;
  companyId: string;
}

interface AssessmentReason {
  criterion: string;
  status: string;
  score: number;
  explanation: string;
  evidence_ref?: string;
}

interface FitAssessment {
  id: string;
  program_name: string;
  overall_fit_status: string;
  fit_score: number;
  assessment_json: {
    reasons: AssessmentReason[];
    suggested_questions: string[];
    guidance_disclaimer: string;
  };
  reviewer_override_status?: string;
  reviewer_notes?: string;
  created_at: string;
}

export const ProgramFitCard: React.FC<ProgramFitCardProps> = ({
  token,
  workspaceId,
  companyId,
}) => {
  const [assessments, setAssessments] = useState<FitAssessment[]>([]);
  const [loading, setLoading] = useState(true);
  const [evaluating, setEvaluating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAssessments = async () => {
    setLoading(true);
    setError(null);
    try {
      const client = getApiClient();
      const res = await client.listFitAssessments(token, workspaceId, companyId);
      setAssessments(res);
    } catch (err: any) {
      setError(err.message || "Failed to load program fit assessments.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAssessments();
  }, [token, workspaceId, companyId]);

  const handleEvaluate = async () => {
    setEvaluating(true);
    try {
      const client = getApiClient();
      await client.evaluateProgramFit(token, workspaceId, companyId, {
        program_name: "AI Riser Innovation Accelerator 2026",
      });
      await fetchAssessments();
    } catch (err: any) {
      setError(err.message || "Failed to evaluate program fit.");
    } finally {
      setEvaluating(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "eligible":
        return <span className="bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 px-3 py-1 rounded-full text-xs font-semibold">Phù Hợp (Eligible)</span>;
      case "review_recommended":
        return <span className="bg-amber-500/20 text-amber-300 border border-amber-500/30 px-3 py-1 rounded-full text-xs font-semibold">Cần Xem Xét (Review Recommended)</span>;
      case "ineligible":
        return <span className="bg-rose-500/20 text-rose-300 border border-rose-500/30 px-3 py-1 rounded-full text-xs font-semibold">Khôn Phù Hợp (Ineligible)</span>;
      default:
        return <span className="bg-slate-500/20 text-slate-300 border border-slate-500/30 px-3 py-1 rounded-full text-xs font-semibold">Cần Bổ Sung Dữ Liệu</span>;
    }
  };

  if (loading) return <p className="text-slate-400 text-sm py-4">Checking program fit...</p>;

  const latest = assessments.length > 0 ? assessments[0] : null;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <span>🎯</span> Innovation Program Fit Assessment
          </h2>
          <p className="text-xs text-slate-400">
            Rules-based explainable evaluation for accelerator qualification with evidence links and human reviewer override.
          </p>
        </div>
        <button
          onClick={handleEvaluate}
          disabled={evaluating}
          className="bg-sky-600 hover:bg-sky-500 text-white font-medium text-xs px-4 py-2 rounded-lg transition shadow-lg disabled:opacity-50"
        >
          {evaluating ? "Evaluating..." : "Run Program Fit Evaluation"}
        </button>
      </div>

      {error && <p className="text-rose-400 text-sm">{error}</p>}

      {!latest ? (
        <p className="text-slate-400 text-sm">Chưa có kết quả đánh giá sự phù hợp. Bấm nút phía trên để bắt đầu đánh giá.</p>
      ) : (
        <div className="space-y-6">
          <div className="bg-slate-950 border border-slate-800 rounded-xl p-5 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
            <div>
              <div className="text-xs text-slate-400 font-medium">{latest.program_name}</div>
              <div className="mt-2 flex items-center gap-3">
                {getStatusBadge(latest.reviewer_override_status || latest.overall_fit_status)}
                {latest.reviewer_override_status && (
                  <span className="text-xs text-amber-400 font-medium">⚠️ Đã ghi đè bởi chuyên viên</span>
                )}
              </div>
            </div>
            <div className="text-right">
              <div className="text-xs text-slate-400">Điểm Phù Hợp (Fit Score)</div>
              <div className="text-3xl font-extrabold text-sky-400">{(latest.fit_score * 100).toFixed(0)}%</div>
            </div>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-slate-300 mb-3">Tiêu Chí Đánh Giá & Dẫn Chứng</h3>
            <div className="space-y-2">
              {latest.assessment_json.reasons.map((r, i) => (
                <div key={i} className="bg-slate-950/60 border border-slate-800 p-3 rounded-lg flex items-center justify-between text-xs">
                  <div className="flex items-center gap-3">
                    <span className={r.status === "passed" ? "text-emerald-400" : "text-amber-400"}>
                      {r.status === "passed" ? "✅" : "⚠️"}
                    </span>
                    <span className="text-slate-200">{r.explanation}</span>
                  </div>
                  {r.evidence_ref && (
                    <span className="text-slate-500 font-mono text-[10px] bg-slate-900 px-2 py-1 rounded border border-slate-800">
                      {r.evidence_ref}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>

          {latest.assessment_json.suggested_questions && (
            <div className="bg-slate-950/80 border border-sky-900/40 p-4 rounded-xl space-y-2">
              <h4 className="text-xs font-semibold text-sky-300 flex items-center gap-2">
                <span>💡</span> Gợi Ý Câu Hỏi Phỏng Vấn (Guidance Questions)
              </h4>
              <ul className="list-disc list-inside text-xs text-slate-300 space-y-1">
                {latest.assessment_json.suggested_questions.map((q, idx) => (
                  <li key={idx}>{q}</li>
                ))}
              </ul>
            </div>
          )}

          <p className="text-[11px] text-slate-500 italic">
            * {latest.assessment_json.guidance_disclaimer}
          </p>
        </div>
      )}
    </div>
  );
};

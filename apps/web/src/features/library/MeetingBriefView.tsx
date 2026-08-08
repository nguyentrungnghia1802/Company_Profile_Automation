"use client";

import React, { useEffect, useState } from "react";
import { getApiClient } from "@vcps/api-client";

interface MeetingBrief {
  company_id: string;
  profile_version_id: string;
  version_number: number;
  locale: string;
  title: string;
  legal_name: string;
  industry: string;
  description: string;
  key_metrics: {
    tax_id: string;
    website: string;
    employee_range: string;
    overall_confidence: number;
    evidence_count: number;
  };
  executive_summary: string;
  missing_sections: string[];
  suggested_verification_questions: string[];
  disclaimer: string;
}

interface MeetingBriefViewProps {
  token: string;
  workspaceId: string;
  companyId: string;
}

export const MeetingBriefView: React.FC<MeetingBriefViewProps> = ({
  token,
  workspaceId,
  companyId,
}) => {
  const [brief, setBrief] = useState<MeetingBrief | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [locale, setLocale] = useState<"vi" | "en">("vi");

  const fetchBrief = async () => {
    setLoading(true);
    setError(null);
    try {
      const client = getApiClient();
      const res = await client.getCompanyMeetingBrief(token, workspaceId, companyId, locale);
      setBrief(res);
    } catch (err: any) {
      setError(err.message || "Failed to load executive meeting brief.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBrief();
  }, [token, workspaceId, companyId, locale]);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <span>⚡</span> 1-Minute Executive Meeting Brief
          </h2>
          <p className="text-sm text-slate-400">
            Grounded 1-minute summary strictly generated from published profile fields.
          </p>
        </div>

        <div className="flex items-center gap-2 bg-slate-800 p-1 rounded-lg border border-slate-700">
          <button
            onClick={() => setLocale("vi")}
            className={`text-xs font-semibold px-3 py-1.5 rounded-md ${
              locale === "vi" ? "bg-sky-600 text-white" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Tiếng Việt
          </button>
          <button
            onClick={() => setLocale("en")}
            className={`text-xs font-semibold px-3 py-1.5 rounded-md ${
              locale === "en" ? "bg-sky-600 text-white" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            English
          </button>
        </div>
      </div>

      {loading && <p className="text-slate-400 text-sm py-4">Generating meeting brief...</p>}
      {error && <p className="text-rose-400 text-sm py-4">{error}</p>}

      {brief && (
        <div className="space-y-5">
          <div className="bg-slate-950 border border-slate-800 rounded-xl p-5">
            <h3 className="text-lg font-bold text-slate-100 mb-2">{brief.title}</h3>
            <p className="text-sm text-slate-300 leading-relaxed mb-4">{brief.description}</p>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 bg-slate-900 border border-slate-800 p-3 rounded-lg text-xs">
              <div>
                <span className="text-slate-400 block">Industry</span>
                <span className="font-semibold text-slate-200">{brief.industry}</span>
              </div>
              <div>
                <span className="text-slate-400 block">Tax ID</span>
                <span className="font-semibold text-slate-200">{brief.key_metrics.tax_id}</span>
              </div>
              <div>
                <span className="text-slate-400 block">Confidence</span>
                <span className="font-semibold text-sky-400">
                  {(brief.key_metrics.overall_confidence * 100).toFixed(0)}%
                </span>
              </div>
              <div>
                <span className="text-slate-400 block">Evidences</span>
                <span className="font-semibold text-slate-200">{brief.key_metrics.evidence_count}</span>
              </div>
            </div>
          </div>

          {/* Suggested Verification Questions */}
          <div className="bg-slate-950 border border-sky-900/60 rounded-xl p-5">
            <h4 className="text-sm font-bold text-sky-300 flex items-center gap-2 mb-3">
              <span>💡</span> Suggested Verification Questions (Meeting Guidance)
            </h4>
            <ul className="space-y-2 text-xs text-slate-300 list-disc list-inside">
              {brief.suggested_verification_questions.map((q, idx) => (
                <li key={idx} className="leading-relaxed">{q}</li>
              ))}
            </ul>
            <p className="text-[10px] text-slate-500 italic mt-3 pt-2 border-t border-slate-800">
              {brief.disclaimer}
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

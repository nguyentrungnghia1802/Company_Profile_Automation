"use client";

import React, { useEffect, useState } from "react";
import { getApiClient } from "@vcps/api-client";

interface ProfileFieldEvidence {
  id: string;
  original_excerpt: string;
  translated_excerpt?: string;
  source_canonical_url?: string;
  source_authority_tier: number;
  support_type: string;
  evidence_quality_score: number;
}

interface ProfileFieldValue {
  id: string;
  field_key: string;
  context_key: string;
  value: any;
  display_value?: string;
  display_status: string;
  confidence_score: number;
  confidence_explanation?: string;
  observed_at?: string;
  origin_type: string;
  display_order: number;
  evidences: ProfileFieldEvidence[];
}

interface ProfileVersion {
  id: string;
  workspace_id: string;
  company_id: string;
  version_number: number;
  status: string;
  title: string;
  executive_summary: string;
  publication_note?: string;
  published_by?: string;
  published_at: string;
  superseded_at?: string;
  withdrawn_at?: string;
  withdrawal_reason?: string;
  source_count: number;
  evidence_count: number;
  overall_confidence: number;
  content_hash: string;
  field_values: ProfileFieldValue[];
}

interface PublishedProfileViewProps {
  token: string;
  workspaceId: string;
  companyId: string;
}

export const PublishedProfileView: React.FC<PublishedProfileViewProps> = ({
  token,
  workspaceId,
  companyId,
}) => {
  const [currentProfile, setCurrentProfile] = useState<ProfileVersion | null>(null);
  const [allVersions, setAllVersions] = useState<ProfileVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedFieldId, setExpandedFieldId] = useState<string | null>(null);

  const fetchProfileData = async () => {
    setLoading(true);
    setError(null);
    try {
      const client = getApiClient();
      const curr = await client.getCurrentCompanyProfile(token, workspaceId, companyId);
      setCurrentProfile(curr);
      const versions = await client.listCompanyProfileVersions(token, workspaceId, companyId);
      setAllVersions(versions || []);
    } catch (err: any) {
      if (err.statusCode === 404) {
        setCurrentProfile(null);
      } else {
        setError(err.message || "Failed to load published profile.");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProfileData();
  }, [token, workspaceId, companyId]);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <span>🛡️</span> Published Verified Profile
          </h2>
          <p className="text-sm text-slate-400">
            Immutable, audit-ready company profile backed by public evidence.
          </p>
        </div>

        {allVersions.length > 0 && (
          <select
            onChange={async (e) => {
              const verId = e.target.value;
              const client = getApiClient();
              const ver = await client.getProfileVersionDetail(token, workspaceId, verId);
              setCurrentProfile(ver);
            }}
            className="bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg p-2"
          >
            {allVersions.map((v) => (
              <option key={v.id} value={v.id}>
                v{v.version_number} ({v.status}) — {new Date(v.published_at).toLocaleDateString()}
              </option>
            ))}
          </select>
        )}
      </div>

      {loading && <p className="text-slate-400 text-sm py-4">Loading profile...</p>}
      {error && <p className="text-rose-400 text-sm py-4">{error}</p>}

      {!loading && !currentProfile && (
        <div className="bg-slate-950/50 border border-slate-800/80 rounded-lg p-8 text-center text-slate-400">
          No published profile version currently available for this company.
        </div>
      )}

      {currentProfile && (
        <div className="space-y-6">
          {/* Executive Header */}
          <div className="bg-slate-950 border border-slate-800 rounded-xl p-6 relative overflow-hidden">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-4">
              <div>
                <div className="flex items-center gap-3">
                  <h3 className="text-2xl font-black text-slate-100">{currentProfile.title}</h3>
                  <span className="text-xs px-2.5 py-0.5 rounded font-bold bg-emerald-950 text-emerald-300 border border-emerald-800">
                    v{currentProfile.version_number} PUBLISHED
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-1 font-mono">
                  Content Hash: {currentProfile.content_hash.slice(0, 16)}... | Published:{" "}
                  {new Date(currentProfile.published_at).toLocaleString()}
                </p>
              </div>

              <div className="flex items-center gap-4 bg-slate-900 border border-slate-800 p-3 rounded-lg">
                <div className="text-center">
                  <div className="text-xs text-slate-400">Confidence</div>
                  <div className="text-lg font-bold text-sky-400">
                    {(currentProfile.overall_confidence * 100).toFixed(0)}%
                  </div>
                </div>
                <div className="h-8 w-px bg-slate-800"></div>
                <div className="text-center">
                  <div className="text-xs text-slate-400">Sources</div>
                  <div className="text-lg font-bold text-slate-200">
                    {currentProfile.source_count}
                  </div>
                </div>
                <div className="h-8 w-px bg-slate-800"></div>
                <div className="text-center">
                  <div className="text-xs text-slate-400">Evidences</div>
                  <div className="text-lg font-bold text-slate-200">
                    {currentProfile.evidence_count}
                  </div>
                </div>
              </div>
            </div>

            {/* Executive Summary */}
            <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-lg">
              <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                Executive Summary
              </h4>
              <p className="text-sm text-slate-200 leading-relaxed">
                {currentProfile.executive_summary}
              </p>
            </div>
          </div>

          {/* Verified Field Values */}
          <div className="space-y-3">
            <h4 className="text-base font-bold text-slate-200">Verified Knowledge Fields</h4>
            {currentProfile.field_values.map((fv) => (
              <div
                key={fv.id}
                className="bg-slate-950 border border-slate-800 rounded-lg p-4 hover:border-slate-700 transition-colors"
              >
                <div className="flex flex-col md:flex-row justify-between md:items-center gap-2">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-semibold text-sky-400">
                        {fv.field_key}
                      </span>
                      <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800">
                        {fv.display_status}
                      </span>
                    </div>
                    <div className="text-base font-semibold text-slate-100 mt-1">
                      {fv.display_value || JSON.stringify(fv.value)}
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <span className="text-xs font-semibold text-sky-400 bg-sky-950/60 border border-sky-800/40 px-2 py-1 rounded">
                      {(fv.confidence_score * 100).toFixed(0)}% Confidence
                    </span>
                    {fv.evidences.length > 0 && (
                      <button
                        onClick={() =>
                          setExpandedFieldId(expandedFieldId === fv.id ? null : fv.id)
                        }
                        className="text-xs text-slate-400 hover:text-slate-200 underline"
                      >
                        {expandedFieldId === fv.id ? "Hide Evidence" : `${fv.evidences.length} Evidences`}
                      </button>
                    )}
                  </div>
                </div>

                {/* Evidence Drawer */}
                {expandedFieldId === fv.id && (
                  <div className="mt-4 pt-3 border-t border-slate-800 space-y-3">
                    {fv.evidences.map((ev) => (
                      <div
                        key={ev.id}
                        className="bg-slate-900 border border-slate-800 rounded p-3 text-xs space-y-1"
                      >
                        <p className="text-slate-300 italic font-serif">"{ev.original_excerpt}"</p>
                        {ev.translated_excerpt && (
                          <p className="text-slate-400 italic font-serif">
                            Translation: "{ev.translated_excerpt}"
                          </p>
                        )}
                        <div className="flex items-center gap-3 text-[10px] text-slate-500 pt-1">
                          <span>Support: {ev.support_type}</span>
                          <span>Tier: {ev.source_authority_tier}</span>
                          {ev.source_canonical_url && (
                            <a
                              href={ev.source_canonical_url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-sky-400 hover:underline truncate max-w-xs"
                            >
                              {ev.source_canonical_url}
                            </a>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

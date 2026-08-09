"use client";

import React, { useEffect, useState } from "react";
import { getApiClient } from "@vcps/api-client";

interface DraftFieldSelection {
  id: string;
  field_key: string;
  context_key: string;
  selected_fact_candidate_id?: string;
  selection_state: string;
  reviewer_note?: string;
  display_order: number;
}

interface ProfileDraft {
  id: string;
  workspace_id: string;
  company_id: string;
  status: string;
  schema_version: number;
  title: string;
  summary_draft?: string;
  notes?: string;
  row_version: number;
  created_at: string;
  field_selections: DraftFieldSelection[];
}

interface ProfileDraftEditorProps {
  token: string;
  workspaceId: string;
  companyId: string;
  onPublished?: () => void;
}

export const ProfileDraftEditor: React.FC<ProfileDraftEditorProps> = ({
  token,
  workspaceId,
  companyId,
  onPublished,
}) => {
  const [drafts, setDrafts] = useState<ProfileDraft[]>([]);
  const [activeDraft, setActiveDraft] = useState<ProfileDraft | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [publicationNote, setPublicationNote] = useState("");

  const fetchDrafts = async () => {
    setLoading(true);
    setError(null);
    try {
      const client = getApiClient();
      const res = await client.listCompanyProfileDrafts(token, workspaceId, companyId);
      setDrafts(res || []);
      if (res && res.length > 0) {
        setActiveDraft(res[0]);
      } else {
        setActiveDraft(null);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load profile drafts.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDrafts();
  }, [token, workspaceId, companyId]);

  const handleAssembleNew = async () => {
    setActionLoading(true);
    try {
      const client = getApiClient();
      const newDraft = await client.assembleCompanyProfileDraft(
        token,
        workspaceId,
        companyId,
        "New Profile Draft"
      );
      fetchDrafts();
    } catch (err: any) {
      alert(`Assembly failed: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleRequestReview = async () => {
    if (!activeDraft) return;
    setActionLoading(true);
    try {
      const client = getApiClient();
      await client.requestProfileDraftReview(token, workspaceId, activeDraft.id);
      fetchDrafts();
    } catch (err: any) {
      alert(`Review request failed: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handlePublish = async () => {
    if (!activeDraft) return;
    setActionLoading(true);
    try {
      const client = getApiClient();
      await client.publishProfileDraft(token, workspaceId, activeDraft.id, {
        publication_note: publicationNote || undefined,
      });
      fetchDrafts();
      if (onPublished) onPublished();
    } catch (err: any) {
      alert(`Publication failed: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <span>📝</span> Profile Draft Editor
          </h2>
          <p className="text-sm text-slate-400">
            Assemble, review field selections, and publish immutable profile versions.
          </p>
        </div>

        <button
          onClick={handleAssembleNew}
          disabled={actionLoading}
          className="bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold py-2.5 px-4 rounded-lg shadow-lg disabled:opacity-50"
        >
          {actionLoading ? "Assembling..." : "+ Assemble New Draft"}
        </button>
      </div>

      {loading && <p className="text-slate-400 text-sm py-4">Loading drafts...</p>}
      {error && <p className="text-rose-400 text-sm py-4">{error}</p>}

      {!loading && drafts.length === 0 && (
        <div className="bg-slate-950/50 border border-slate-800/80 rounded-lg p-8 text-center text-slate-400">
          No profile drafts assembled yet for this company.
        </div>
      )}

      {activeDraft && (
        <div className="bg-slate-950 border border-slate-800 rounded-lg p-5">
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 pb-4 mb-4 border-b border-slate-800">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-bold text-slate-200">{activeDraft.title}</h3>
                <span className="text-xs px-2.5 py-0.5 rounded font-semibold bg-sky-950 text-sky-300 border border-sky-800">
                  {activeDraft.status}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Draft ID: <code className="text-slate-300">{activeDraft.id}</code> | Created:{" "}
                {new Date(activeDraft.created_at).toLocaleString()}
              </p>
            </div>

            <div className="flex items-center gap-3">
              {activeDraft.status === "building" && (
                <button
                  onClick={handleRequestReview}
                  disabled={actionLoading}
                  className="bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold py-2 px-3 rounded-lg"
                >
                  Request Review
                </button>
              )}
              {activeDraft.status === "ready_for_review" && (
                <div className="flex items-center gap-2">
                  <input
                    id="profile-publication-note"
                    name="publication_note"
                    type="text"
                    aria-label="Publication release note"
                    placeholder="Release note..."
                    value={publicationNote}
                    onChange={(e) => setPublicationNote(e.target.value)}
                    className="bg-slate-900 border border-slate-700 text-slate-200 text-xs rounded-lg p-2"
                  />
                  <button
                    onClick={handlePublish}
                    disabled={actionLoading}
                    className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold py-2 px-4 rounded-lg shadow-lg"
                  >
                    Publish Profile
                  </button>
                </div>
              )}
            </div>
          </div>

          <h4 className="text-sm font-semibold text-slate-300 mb-3">Field Selection Mapping</h4>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-900 text-slate-400 font-semibold border-b border-slate-800">
                <tr>
                  <th className="p-3">Field Key</th>
                  <th className="p-3">Selection State</th>
                  <th className="p-3">Selected Candidate ID</th>
                  <th className="p-3">Reviewer Note</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {activeDraft.field_selections.map((sel) => (
                  <tr key={sel.id} className="hover:bg-slate-900/50">
                    <td className="p-3 font-mono text-sky-400">{sel.field_key}</td>
                    <td className="p-3">
                      <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-medium">
                        {sel.selection_state}
                      </span>
                    </td>
                    <td className="p-3 font-mono text-slate-400">
                      {sel.selected_fact_candidate_id || "None"}
                    </td>
                    <td className="p-3 text-slate-400">{sel.reviewer_note || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

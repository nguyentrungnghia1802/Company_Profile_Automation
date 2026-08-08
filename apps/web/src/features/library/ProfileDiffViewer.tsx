"use client";

import React, { useEffect, useState } from "react";
import { getApiClient } from "@vcps/api-client";

interface FieldDiff {
  field_key: string;
  context_key: string;
  change_type: "added" | "modified" | "removed";
  old_value?: any;
  new_value?: any;
  old_display_value?: string;
  new_display_value?: string;
  old_confidence?: number;
  new_confidence?: number;
}

interface DiffResult {
  version_a: { id: string; version_number: number; published_at: string };
  version_b: { id: string; version_number: number; published_at: string };
  summary: {
    added_count: number;
    modified_count: number;
    removed_count: number;
    unchanged_count: number;
    confidence_delta: number;
  };
  field_diffs: FieldDiff[];
}

interface ProfileDiffViewerProps {
  token: string;
  workspaceId: string;
  versionIdA: string;
  versionIdB: string;
}

export const ProfileDiffViewer: React.FC<ProfileDiffViewerProps> = ({
  token,
  workspaceId,
  versionIdA,
  versionIdB,
}) => {
  const [diff, setDiff] = useState<DiffResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDiff = async () => {
      setLoading(true);
      setError(null);
      try {
        const client = getApiClient();
        const res = await client.diffProfileVersions(
          token,
          workspaceId,
          versionIdA,
          versionIdB
        );
        setDiff(res);
      } catch (err: any) {
        setError(err.message || "Failed to load version diff.");
      } finally {
        setLoading(false);
      }
    };
    fetchDiff();
  }, [token, workspaceId, versionIdA, versionIdB]);

  if (loading) return <p className="text-slate-400 text-sm py-4">Comparing profile versions...</p>;
  if (error) return <p className="text-rose-400 text-sm py-4">{error}</p>;
  if (!diff) return null;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6 border-b border-slate-800 pb-4">
        <div>
          <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <span>🔀</span> Profile Version Diff
          </h3>
          <p className="text-xs text-slate-400 mt-1">
            Comparing v{diff.version_a.version_number} vs v{diff.version_b.version_number}
          </p>
        </div>

        <div className="flex items-center gap-3 text-xs">
          <span className="px-2.5 py-1 rounded bg-emerald-950 text-emerald-300 border border-emerald-800 font-semibold">
            +{diff.summary.added_count} Added
          </span>
          <span className="px-2.5 py-1 rounded bg-amber-950 text-amber-300 border border-amber-800 font-semibold">
            ~{diff.summary.modified_count} Modified
          </span>
          <span className="px-2.5 py-1 rounded bg-rose-950 text-rose-300 border border-rose-800 font-semibold">
            -{diff.summary.removed_count} Removed
          </span>
        </div>
      </div>

      {diff.field_diffs.length === 0 ? (
        <p className="text-slate-400 text-sm py-4 text-center">
          No material field changes between these two versions.
        </p>
      ) : (
        <div className="space-y-3">
          {diff.field_diffs.map((fd, idx) => (
            <div
              key={idx}
              className={`p-4 rounded-lg border text-xs space-y-1 ${
                fd.change_type === "added"
                  ? "bg-emerald-950/30 border-emerald-800/60"
                  : fd.change_type === "modified"
                  ? "bg-amber-950/30 border-amber-800/60"
                  : "bg-rose-950/30 border-rose-800/60"
              }`}
            >
              <div className="flex justify-between items-center">
                <span className="font-mono font-bold text-sky-400">{fd.field_key}</span>
                <span className="uppercase text-[10px] font-bold px-2 py-0.5 rounded bg-slate-900 text-slate-300">
                  {fd.change_type}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-4 pt-2">
                <div className="bg-slate-950 p-2.5 rounded border border-slate-800">
                  <div className="text-[10px] text-slate-500 font-semibold mb-1">
                    v{diff.version_a.version_number} Base
                  </div>
                  <div className="text-slate-300 line-through">
                    {fd.old_display_value || JSON.stringify(fd.old_value) || "—"}
                  </div>
                </div>
                <div className="bg-slate-950 p-2.5 rounded border border-slate-800">
                  <div className="text-[10px] text-slate-500 font-semibold mb-1">
                    v{diff.version_b.version_number} Target
                  </div>
                  <div className="text-slate-100 font-semibold">
                    {fd.new_display_value || JSON.stringify(fd.new_value) || "—"}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

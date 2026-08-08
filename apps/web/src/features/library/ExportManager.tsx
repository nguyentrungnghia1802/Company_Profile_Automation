"use client";

import React, { useState } from "react";
import { getApiClient } from "@vcps/api-client";

interface ExportManagerProps {
  token: string;
  workspaceId: string;
  profileVersionId: string;
}

export const ExportManager: React.FC<ExportManagerProps> = ({
  token,
  workspaceId,
  profileVersionId,
}) => {
  const [format, setFormat] = useState<"pdf" | "json">("pdf");
  const [includeAppendix, setIncludeAppendix] = useState(true);
  const [loading, setLoading] = useState(false);
  const [exportJob, setExportJob] = useState<any | null>(null);

  const handleCreateExport = async () => {
    setLoading(true);
    try {
      const client = getApiClient();
      const job = await client.createProfileExport(token, workspaceId, profileVersionId, {
        export_format: format,
        locale: "vi",
        include_source_appendix: includeAppendix,
        include_internal_notes: false,
      });
      setExportJob(job);
    } catch (err: any) {
      alert(`Export failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async () => {
    if (!exportJob) return;
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const downloadUrl = `${apiUrl}/exports/${exportJob.id}/download`;

      const response = await fetch(downloadUrl, {
        headers: {
          Authorization: `Bearer ${token}`,
          "X-Workspace-ID": workspaceId,
        },
      });

      if (!response.ok) {
        throw new Error(`Download failed with status ${response.status}`);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `profile_export_${exportJob.id}.${format}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err: any) {
      alert(`Download failed: ${err.message}`);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <span>📥</span> Export Profile & Source Appendix
          </h2>
          <p className="text-sm text-slate-400">
            Generate idempotent, audit-backed PDF or JSON profile exports.
          </p>
        </div>
      </div>

      <div className="bg-slate-950 border border-slate-800 rounded-xl p-5 space-y-4">
        <div className="flex items-center gap-6">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Export Format</label>
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-1.5 text-xs text-slate-200 cursor-pointer">
                <input
                  type="radio"
                  name="format"
                  value="pdf"
                  checked={format === "pdf"}
                  onChange={() => setFormat("pdf")}
                  className="accent-sky-500"
                />
                PDF Document
              </label>
              <label className="flex items-center gap-1.5 text-xs text-slate-200 cursor-pointer">
                <input
                  type="radio"
                  name="format"
                  value="json"
                  checked={format === "json"}
                  onChange={() => setFormat("json")}
                  className="accent-sky-500"
                />
                Structured JSON
              </label>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Options</label>
            <label className="flex items-center gap-1.5 text-xs text-slate-200 cursor-pointer">
              <input
                type="checkbox"
                checked={includeAppendix}
                onChange={(e) => setIncludeAppendix(e.target.checked)}
                className="accent-sky-500 rounded"
              />
              Include Source Evidence Appendix
            </label>
          </div>
        </div>

        <div className="flex items-center gap-3 pt-2 border-t border-slate-800">
          <button
            onClick={handleCreateExport}
            disabled={loading}
            className="bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold py-2.5 px-4 rounded-lg shadow-lg disabled:opacity-50"
          >
            {loading ? "Generating..." : "Generate Export"}
          </button>

          {exportJob && exportJob.status === "completed" && (
            <button
              onClick={handleDownload}
              className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold py-2.5 px-4 rounded-lg shadow-lg flex items-center gap-1.5"
            >
              <span>⬇️</span> Download File ({exportJob.file_size_bytes} bytes)
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

"use client";

import React, { useEffect, useState } from "react";
import { getApiClient } from "@vcps/api-client";

interface AuditLog {
  id: string;
  workspace_id: string;
  actor_id?: string;
  actor_type: string;
  action: string;
  resource_type: string;
  resource_id?: string;
  metadata?: any;
  created_at: string;
}

interface AuditLogsViewerProps {
  token: string;
  workspaceId: string;
}

export const AuditLogsViewer: React.FC<AuditLogsViewerProps> = ({ token, workspaceId }) => {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAudit = async () => {
      setLoading(true);
      setError(null);
      try {
        const client = getApiClient();
        const res = await client.listAuditTrail(token, workspaceId);
        setLogs(res);
      } catch (err: any) {
        setError(err.message || "Failed to load audit trail.");
      } finally {
        setLoading(false);
      }
    };
    fetchAudit();
  }, [token, workspaceId]);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <span>📋</span> Append-Only Security Audit Trail
          </h2>
          <p className="text-sm text-slate-400">
            Auditable log of policy changes, publication decisions, and sensitive workspace actions.
          </p>
        </div>
      </div>

      {loading && <p className="text-slate-400 text-sm py-4">Loading audit logs...</p>}
      {error && <p className="text-rose-400 text-sm py-4">{error}</p>}

      {!loading && !error && (
        <div className="space-y-3">
          {logs.length === 0 ? (
            <p className="text-slate-400 text-sm text-center py-4">No audit logs recorded yet.</p>
          ) : (
            logs.map((log) => (
              <div
                key={log.id}
                className="bg-slate-950 border border-slate-800 p-4 rounded-lg flex flex-col md:flex-row justify-between items-start md:items-center gap-3 text-xs"
              >
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-mono font-bold text-sky-400">{log.action}</span>
                    <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                      {log.resource_type}
                    </span>
                  </div>
                  <div className="text-slate-400">
                    Resource ID: <span className="text-slate-200">{log.resource_id || "N/A"}</span>
                  </div>
                </div>

                <div className="text-right text-[11px] text-slate-500">
                  <div>Actor: {log.actor_id || "System"}</div>
                  <div>{new Date(log.created_at).toLocaleString()}</div>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};

"use client";

import React, { useEffect, useState } from "react";
import { getApiClient } from "@vcps/api-client";

interface PolicySet {
  id: string;
  workspace_id: string;
  version_number: number;
  name: string;
  description?: string;
  is_active: boolean;
  policy_config: any;
  created_at: string;
}

interface PolicyAdminProps {
  token: string;
  workspaceId: string;
}

export const PolicyAdmin: React.FC<PolicyAdminProps> = ({ token, workspaceId }) => {
  const [policies, setPolicies] = useState<PolicySet[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPolicies = async () => {
    setLoading(true);
    setError(null);
    try {
      const client = getApiClient();
      const res = await client.listPolicyVersions(token, workspaceId);
      setPolicies(res);
    } catch (err: any) {
      setError(err.message || "Failed to load policy versions.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPolicies();
  }, [token, workspaceId]);

  const handleActivate = async (policyId: string) => {
    try {
      const client = getApiClient();
      await client.activatePolicyVersion(token, workspaceId, policyId);
      fetchPolicies();
    } catch (err: any) {
      alert(`Activation failed: ${err.message}`);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <span>🛡️</span> Versioned Workspace Policy Sets
          </h2>
          <p className="text-sm text-slate-400">
            Immutable policy versions governing source authority, freshness thresholds, and AI budgets.
          </p>
        </div>
      </div>

      {loading && <p className="text-slate-400 text-sm py-4">Loading policies...</p>}
      {error && <p className="text-rose-400 text-sm py-4">{error}</p>}

      {!loading && !error && (
        <div className="space-y-4">
          {policies.map((p) => (
            <div
              key={p.id}
              className={`p-5 rounded-xl border flex flex-col md:flex-row justify-between items-start md:items-center gap-4 ${
                p.is_active
                  ? "bg-sky-950/40 border-sky-600/80 shadow-md shadow-sky-950/50"
                  : "bg-slate-950 border-slate-800"
              }`}
            >
              <div>
                <div className="flex items-center gap-3 mb-1">
                  <span className="font-bold text-slate-100 text-base">{p.name}</span>
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                    v{p.version_number}
                  </span>
                  {p.is_active && (
                    <span className="text-xs font-bold px-2.5 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800">
                      ACTIVE POLICY
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-400">{p.description || "No description provided."}</p>
                <div className="text-[11px] text-slate-500 mt-2">
                  Created at: {new Date(p.created_at).toLocaleString()}
                </div>
              </div>

              <div className="flex items-center gap-3">
                {!p.is_active && (
                  <button
                    onClick={() => handleActivate(p.id)}
                    className="bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold py-2 px-3.5 rounded-lg shadow"
                  >
                    Activate Version
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

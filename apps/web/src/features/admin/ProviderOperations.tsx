"use client";

import React, { useEffect, useState } from "react";
import { getApiClient } from "@vcps/api-client";

interface ProviderSettings {
  environment: string;
  ai_provider: string;
  gemini_model: string;
  search_provider: string;
  object_storage_provider: string;
  ai_max_retries: number;
  ai_timeout_seconds: number;
  malware_scanner_mode: string;
}

interface UsageMetrics {
  workspace_id: string;
  total_ai_runs: number;
  total_estimated_cost_usd: number;
  currency: string;
}

interface ProviderOperationsProps {
  token: string;
  workspaceId: string;
}

export const ProviderOperations: React.FC<ProviderOperationsProps> = ({
  token,
  workspaceId,
}) => {
  const [settings, setSettings] = useState<ProviderSettings | null>(null);
  const [usage, setUsage] = useState<UsageMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const client = getApiClient();
        const [settingsRes, usageRes] = await Promise.all([
          client.getProviderSettings(token, workspaceId),
          client.getOperationsUsage(token, workspaceId),
        ]);
        setSettings(settingsRes);
        setUsage(usageRes);
      } catch (err: any) {
        setError(err.message || "Failed to load provider operations data.");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [token, workspaceId]);

  if (loading) return <p className="text-slate-400 text-sm py-4">Loading operational status...</p>;
  if (error) return <p className="text-rose-400 text-sm py-4">{error}</p>;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <span>⚙️</span> Provider Settings & Operational Usage
          </h2>
          <p className="text-sm text-slate-400">
            Safe operational parameters, budget limits, and AI execution metrics (strictly no secrets exposed).
          </p>
        </div>
      </div>

      {settings && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 bg-slate-950 p-4 rounded-xl border border-slate-800 text-xs">
          <div>
            <span className="text-slate-500 block">AI Provider</span>
            <span className="font-bold text-sky-400 uppercase">{settings.ai_provider}</span>
          </div>
          <div>
            <span className="text-slate-500 block">AI Model</span>
            <span className="font-semibold text-slate-200">{settings.gemini_model}</span>
          </div>
          <div>
            <span className="text-slate-500 block">Search Provider</span>
            <span className="font-semibold text-slate-200">{settings.search_provider}</span>
          </div>
          <div>
            <span className="text-slate-500 block">Storage Provider</span>
            <span className="font-semibold text-slate-200">{settings.object_storage_provider}</span>
          </div>
        </div>
      )}

      {usage && (
        <div className="bg-slate-950 border border-slate-800 p-5 rounded-xl flex items-center justify-between">
          <div>
            <div className="text-xs text-slate-400">Total Workspace AI Runs</div>
            <div className="text-2xl font-bold text-slate-100">{usage.total_ai_runs} runs</div>
          </div>
          <div className="text-right">
            <div className="text-xs text-slate-400">Total Estimated Cost</div>
            <div className="text-2xl font-bold text-emerald-400">${usage.total_estimated_cost_usd} USD</div>
          </div>
        </div>
      )}
    </div>
  );
};

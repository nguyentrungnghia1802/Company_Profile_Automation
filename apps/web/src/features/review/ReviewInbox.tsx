"use client";

import React, { useEffect, useState } from "react";
import { getApiClient } from "@vcps/api-client";

interface ReviewDecision {
  id: string;
  action: string;
  target_type: string;
  target_id: string;
  reason: string;
  created_at: string;
}

interface ReviewTask {
  id: string;
  workspace_id: string;
  company_id: string;
  research_job_id?: string;
  conflict_id?: string;
  fact_candidate_id?: string;
  task_type: string;
  status: string;
  priority: string;
  title: string;
  description?: string;
  assigned_to?: string;
  claimed_at?: string;
  decision_code?: string;
  decision_reason?: string;
  row_version: number;
  created_at: string;
  completed_at?: string;
  decisions: ReviewDecision[];
}

interface ReviewInboxProps {
  token: string;
  workspaceId: string;
  companyId?: string;
}

export const ReviewInbox: React.FC<ReviewInboxProps> = ({
  token,
  workspaceId,
  companyId,
}) => {
  const [tasks, setTasks] = useState<ReviewTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [selectedTask, setSelectedTask] = useState<ReviewTask | null>(null);
  const [decisionCode, setDecisionCode] = useState<string>("approved");
  const [decisionReason, setDecisionReason] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);

  const fetchTasks = async () => {
    setLoading(true);
    setError(null);
    try {
      const client = getApiClient();
      const res = await client.listReviewTasks(token, workspaceId, {
        companyId,
        status: statusFilter || undefined,
      });
      setTasks(res || []);
    } catch (err: any) {
      setError(err.message || "Failed to load review tasks.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTasks();
  }, [token, workspaceId, companyId, statusFilter]);

  const handleClaim = async (taskId: string) => {
    try {
      const client = getApiClient();
      await client.claimReviewTask(token, workspaceId, taskId);
      fetchTasks();
    } catch (err: any) {
      alert(`Claim failed: ${err.message}`);
    }
  };

  const handleRelease = async (taskId: string) => {
    try {
      const client = getApiClient();
      await client.releaseReviewTask(token, workspaceId, taskId);
      fetchTasks();
    } catch (err: any) {
      alert(`Release failed: ${err.message}`);
    }
  };

  const handleComplete = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTask) return;
    setSubmitting(true);
    try {
      const client = getApiClient();
      await client.completeReviewTask(token, workspaceId, selectedTask.id, {
        decision_code: decisionCode,
        reason: decisionReason,
        expected_row_version: selectedTask.row_version,
      });
      setSelectedTask(null);
      setDecisionReason("");
      fetchTasks();
    } catch (err: any) {
      alert(`Completion failed: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const handleReopen = async (taskId: string) => {
    const reason = window.prompt("Reason for reopening this review task:", "New evidence requires review.");
    if (!reason?.trim()) return;
    try {
      const client = getApiClient();
      await client.reopenReviewTask(token, workspaceId, taskId, { reason: reason.trim() });
      await fetchTasks();
    } catch (err: any) {
      alert(`Reopen failed: ${err.message}`);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <span>📋</span> Human Review Inbox
          </h2>
          <p className="text-sm text-slate-400">
            Tasks requiring human reviewer evaluation, verification, and publication approval.
          </p>
          <p className="text-xs text-emerald-400 mt-1">
            AI-independent: every task points to acquisition, deterministic facts, conflicts, or evidence.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg p-2 focus:ring-sky-500"
          >
            <option value="">All Statuses</option>
            <option value="open">Open</option>
            <option value="in_review">In Review</option>
            <option value="changes_requested">Changes Requested</option>
            <option value="completed">Completed</option>
            <option value="reopened">Reopened</option>
          </select>
          <button
            onClick={fetchTasks}
            className="bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium py-2 px-4 rounded-lg border border-slate-700"
          >
            Refresh
          </button>
        </div>
      </div>

      {loading && <p className="text-slate-400 text-sm py-4">Loading review tasks...</p>}
      {error && <p className="text-rose-400 text-sm py-4">{error}</p>}

      {!loading && tasks.length === 0 && (
        <div className="bg-slate-950/50 border border-slate-800/80 rounded-lg p-8 text-center text-slate-400">
          No review tasks matching the criteria.
        </div>
      )}

      <div className="space-y-4">
        {tasks.map((task) => (
          <div
            key={task.id}
            className="bg-slate-950 border border-slate-800 hover:border-slate-700 rounded-lg p-5 transition-colors"
          >
            <div className="flex flex-col md:flex-row justify-between md:items-center gap-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span
                    className={`text-xs font-semibold px-2 py-0.5 rounded ${
                      task.priority === "urgent" || task.priority === "high"
                        ? "bg-rose-950/80 text-rose-300 border border-rose-800/50"
                        : "bg-slate-800 text-slate-300"
                    }`}
                  >
                    {task.priority.toUpperCase()}
                  </span>
                  <span className="text-xs font-semibold px-2 py-0.5 rounded bg-sky-950 text-sky-300 border border-sky-800/50">
                    {task.task_type}
                  </span>
                  <span
                    className={`text-xs px-2 py-0.5 rounded font-medium ${
                      task.status === "completed"
                        ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                        : task.status === "in_review"
                        ? "bg-amber-950 text-amber-300 border border-amber-800"
                        : "bg-slate-800 text-slate-300"
                    }`}
                  >
                    {task.status}
                  </span>
                </div>
                <h3 className="text-base font-semibold text-slate-200">{task.title}</h3>
                {task.description && (
                  <p className="text-sm text-slate-400 mt-1">{task.description}</p>
                )}
                {task.decision_code && (
                  <div className="mt-2 text-xs bg-slate-900 border border-slate-800 rounded p-2 text-slate-300">
                    <strong>Decision ({task.decision_code}):</strong> {task.decision_reason}
                  </div>
                )}
              </div>

              <div className="flex items-center gap-2">
                {(task.status === "open" || task.status === "reopened" || task.status === "changes_requested") && (
                  <button
                    onClick={() => handleClaim(task.id)}
                    className="bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold py-2 px-3 rounded-lg"
                  >
                    Claim Task
                  </button>
                )}
                {task.status === "in_review" && (
                  <>
                    <button
                      onClick={() => setSelectedTask(task)}
                      className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold py-2 px-3 rounded-lg"
                    >
                      Complete Decision
                    </button>
                    <button
                      onClick={() => handleRelease(task.id)}
                      className="bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium py-2 px-3 rounded-lg border border-slate-700"
                    >
                      Release
                    </button>
                  </>
                )}
                {task.status === "completed" && (
                  <button
                    onClick={() => handleReopen(task.id)}
                    className="bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium py-2 px-3 rounded-lg border border-slate-700"
                  >
                    Reopen
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Completion Modal */}
      {selectedTask && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 w-full max-w-lg shadow-2xl">
            <h3 className="text-lg font-bold text-slate-100 mb-2">Complete Review Task</h3>
            <p className="text-xs text-slate-400 mb-4">{selectedTask.title}</p>

            <form onSubmit={handleComplete} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Decision Outcome Code
                </label>
                <input
                  type="text"
                  value={decisionCode}
                  onChange={(e) => setDecisionCode(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 text-slate-200 text-sm rounded-lg p-2.5"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Review Rationale & Justification
                </label>
                <textarea
                  value={decisionReason}
                  onChange={(e) => setDecisionReason(e.target.value)}
                  rows={4}
                  className="w-full bg-slate-950 border border-slate-800 text-slate-200 text-sm rounded-lg p-2.5"
                  placeholder="Explain why this decision was reached..."
                  required
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setSelectedTask(null)}
                  className="bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium py-2 px-4 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold py-2 px-4 rounded-lg disabled:opacity-50"
                >
                  {submitting ? "Saving..." : "Submit Decision"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

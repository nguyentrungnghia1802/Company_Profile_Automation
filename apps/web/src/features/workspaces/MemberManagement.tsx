"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useAuth } from "../../stores/authContext";
import { getApiClient } from "@vcps/api-client";

export interface MemberItem {
  member_id: string;
  user_id: string;
  email: string | null;
  display_name: string;
  role: string;
  status: string;
  version: number;
}

export const MemberManagement: React.FC = () => {
  const { activeWorkspace, hasCapability } = useAuth();
  const [members, setMembers] = useState<MemberItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [inviteEmail, setInviteEmail] = useState<string>("");
  const [inviteName, setInviteName] = useState<string>("");
  const [inviteRole, setInviteRole] = useState<string>("researcher");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const canManage = hasCapability("member:manage");

  const loadMembers = useCallback(async () => {
    if (!activeWorkspace) return;
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const token = localStorage.getItem("vcps_access_token") || "";
      const client = getApiClient();
      const data = await client.listWorkspaceMembers(token, activeWorkspace.id);
      setMembers(data);
    } catch {
      setErrorMsg("Failed to load workspace members.");
    } finally {
      setIsLoading(false);
    }
  }, [activeWorkspace]);

  useEffect(() => {
    loadMembers();
  }, [loadMembers]);

  const handleAddMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeWorkspace || !inviteEmail) return;
    try {
      const token = localStorage.getItem("vcps_access_token") || "";
      const client = getApiClient();
      await client.addWorkspaceMember(token, activeWorkspace.id, {
        email: inviteEmail,
        display_name: inviteName || undefined,
        role: inviteRole,
      });
      setInviteEmail("");
      setInviteName("");
      loadMembers();
    } catch {
      setErrorMsg("Failed to invite workspace member.");
    }
  };

  const handleUpdateRole = async (memberId: string, newRole: string) => {
    if (!activeWorkspace) return;
    try {
      const token = localStorage.getItem("vcps_access_token") || "";
      const client = getApiClient();
      await client.updateWorkspaceMember(token, activeWorkspace.id, memberId, {
        role: newRole,
      });
      loadMembers();
    } catch {
      setErrorMsg("Failed to update member role.");
    }
  };

  const handleDeactivate = async (memberId: string) => {
    if (!activeWorkspace) return;
    try {
      const token = localStorage.getItem("vcps_access_token") || "";
      const client = getApiClient();
      await client.deactivateWorkspaceMember(token, activeWorkspace.id, memberId);
      loadMembers();
    } catch {
      setErrorMsg("Failed to deactivate member.");
    }
  };

  if (!canManage) {
    return (
      <div style={{ padding: "16px", color: "#d9534f" }}>
        Access Denied: You require member:manage capability to view workspace administration.
      </div>
    );
  }

  return (
    <div style={{ padding: "24px", maxWidth: "900px", fontFamily: "sans-serif" }}>
      <h2>Workspace Member Management</h2>
      <p style={{ color: "#666" }}>Manage roles and membership for {activeWorkspace?.name}</p>

      {errorMsg && (
        <div style={{ padding: "12px", backgroundColor: "#ffebe9", color: "#cf222e", borderRadius: "6px", marginBottom: "16px" }}>
          {errorMsg}
        </div>
      )}

      {/* Invite Member Form */}
      <form onSubmit={handleAddMember} style={{ display: "flex", gap: "12px", marginBottom: "24px", alignItems: "flex-end" }}>
        <div>
          <label style={{ display: "block", fontSize: "12px", fontWeight: 600 }}>Email Address</label>
          <input
            type="email"
            required
            value={inviteEmail}
            onChange={(e) => setInviteEmail(e.target.value)}
            placeholder="colleague@company.com"
            style={{ padding: "8px 12px", borderRadius: "6px", border: "1px solid #ccc" }}
          />
        </div>

        <div>
          <label style={{ display: "block", fontSize: "12px", fontWeight: 600 }}>Display Name</label>
          <input
            type="text"
            value={inviteName}
            onChange={(e) => setInviteName(e.target.value)}
            placeholder="John Doe"
            style={{ padding: "8px 12px", borderRadius: "6px", border: "1px solid #ccc" }}
          />
        </div>

        <div>
          <label style={{ display: "block", fontSize: "12px", fontWeight: 600 }}>Role</label>
          <select
            value={inviteRole}
            onChange={(e) => setInviteRole(e.target.value)}
            style={{ padding: "8px 12px", borderRadius: "6px", border: "1px solid #ccc" }}
          >
            <option value="researcher">Researcher</option>
            <option value="reviewer">Reviewer</option>
            <option value="officer">Officer</option>
            <option value="workspace_admin">Workspace Admin</option>
          </select>
        </div>

        <button
          type="submit"
          style={{
            padding: "8px 16px",
            backgroundColor: "#2da44e",
            color: "#fff",
            border: "none",
            borderRadius: "6px",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Add Member
        </button>
      </form>

      {/* Member List Table */}
      {isLoading ? (
        <div>Loading workspace members...</div>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left" }}>
          <thead>
            <tr style={{ borderBottom: "2px solid #eaeaea" }}>
              <th style={{ padding: "12px" }}>Display Name</th>
              <th style={{ padding: "12px" }}>Email</th>
              <th style={{ padding: "12px" }}>Role</th>
              <th style={{ padding: "12px" }}>Status</th>
              <th style={{ padding: "12px" }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {members.map((m) => (
              <tr key={m.member_id} style={{ borderBottom: "1px solid #eaeaea" }}>
                <td style={{ padding: "12px" }}>{m.display_name}</td>
                <td style={{ padding: "12px" }}>{m.email || "—"}</td>
                <td style={{ padding: "12px" }}>
                  <select
                    value={m.role}
                    onChange={(e) => handleUpdateRole(m.member_id, e.target.value)}
                    style={{ padding: "4px 8px", borderRadius: "4px" }}
                  >
                    <option value="researcher">Researcher</option>
                    <option value="reviewer">Reviewer</option>
                    <option value="officer">Officer</option>
                    <option value="workspace_admin">Workspace Admin</option>
                  </select>
                </td>
                <td style={{ padding: "12px" }}>
                  <span
                    style={{
                      padding: "4px 8px",
                      borderRadius: "12px",
                      fontSize: "12px",
                      backgroundColor: m.status === "active" ? "#dafbe1" : "#ffebe9",
                      color: m.status === "active" ? "#1a7f37" : "#cf222e",
                    }}
                  >
                    {m.status}
                  </span>
                </td>
                <td style={{ padding: "12px" }}>
                  {m.status === "active" && (
                    <button
                      onClick={() => handleDeactivate(m.member_id)}
                      style={{
                        padding: "4px 8px",
                        backgroundColor: "#cf222e",
                        color: "#fff",
                        border: "none",
                        borderRadius: "4px",
                        fontSize: "12px",
                        cursor: "pointer",
                      }}
                    >
                      Deactivate
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

"use client";

import React from "react";
import { useAuth } from "../stores/authContext";

export const WorkspaceSelector: React.FC = () => {
  const { user, activeWorkspace, switchWorkspace } = useAuth();

  if (!user || user.workspaces.length === 0) {
    return null;
  }

  return (
    <div style={{ display: "inline-flex", alignItems: "center", gap: "8px" }}>
      <label htmlFor="workspace-select" style={{ fontSize: "14px", fontWeight: 500 }}>
        Workspace:
      </label>
      <select
        id="workspace-select"
        value={activeWorkspace?.id || ""}
        onChange={(e) => switchWorkspace(e.target.value)}
        style={{
          padding: "6px 12px",
          borderRadius: "6px",
          border: "1px solid #d0d7de",
          backgroundColor: "#ffffff",
          fontSize: "14px",
          cursor: "pointer",
        }}
      >
        {user.workspaces.map((ws) => (
          <option key={ws.id} value={ws.id}>
            {ws.name} ({ws.role})
          </option>
        ))}
      </select>
    </div>
  );
};

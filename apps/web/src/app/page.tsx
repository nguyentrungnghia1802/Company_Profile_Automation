"use client";

import React, { useState, useEffect } from "react";
import { AuthProvider, useAuth } from "../stores/authContext";
import { CompanyResearchFlow } from "../features/research/CompanyResearchFlow";
import { CompanyLibrary } from "../features/companies/CompanyLibrary";
import { ReviewInbox } from "../features/review/ReviewInbox";
import { AuditLogsViewer } from "../features/admin/AuditLogsViewer";
import { WorkspaceSelector } from "../components/WorkspaceSelector";

function MainDashboard() {
  const { user, isLoading, login, activeWorkspace } = useAuth();
  const [activeTab, setActiveTab] = useState<"research" | "library" | "review" | "audit">("research");
  const [refreshLibraryKey, setRefreshLibraryKey] = useState(0);
  const defaultMockToken = process.env.NEXT_PUBLIC_MOCK_AUTH_TOKEN || "mock-token-researcher";

  // Auto-login with mock token once on mount
  useEffect(() => {
    const token = localStorage.getItem("vcps_access_token");
    if (!token) {
      login(defaultMockToken).catch(() => {});
    }
  }, [defaultMockToken, login]);

  const token = typeof window !== "undefined" ? localStorage.getItem("vcps_access_token") || defaultMockToken : defaultMockToken;
  const workspaceId = activeWorkspace?.id || "11111111-1111-1111-1111-111111111111";

  if (isLoading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh", background: "#0f172a", color: "#f8fafc" }}>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: "2.5rem", marginBottom: "1rem" }}>⚡</div>
          <p style={{ fontSize: "1.1rem", opacity: 0.8 }}>Đang khởi tạo hệ thống Verified Company Profile...</p>
        </div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: "100vh", background: "#0f172a", color: "#f8fafc", fontFamily: "'Inter', sans-serif" }}>
      {/* Header Bar */}
      <header
        style={{
          borderBottom: "1px solid #1e293b",
          background: "rgba(15, 23, 42, 0.95)",
          backdropFilter: "blur(8px)",
          position: "sticky",
          top: 0,
          zIndex: 100,
          padding: "14px 24px",
        }}
      >
        <div style={{ maxWidth: "1280px", margin: "0 auto", display: "flex", alignItems: "center", justifyContent: "space-between", gap: "16px" }}>
          {/* Logo & Title */}
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <div
              style={{
                width: "40px",
                height: "40px",
                borderRadius: "10px",
                background: "linear-gradient(135deg, #10b981, #3b82f6)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "20px",
                boxShadow: "0 4px 12px rgba(16, 185, 129, 0.3)",
              }}
            >
              🛡️
            </div>
            <div>
              <h1 style={{ fontSize: "1.2rem", fontWeight: 700, margin: 0, color: "#f8fafc" }}>
                Verified Company Profile System
              </h1>
              <div style={{ fontSize: "0.75rem", color: "#94a3b8", display: "flex", alignItems: "center", gap: "6px" }}>
                <span>AI Riser Intelligence</span>
                <span>•</span>
                <span style={{ color: "#10b981", fontWeight: 600 }}>● Hệ thống sẵn sàng</span>
              </div>
            </div>
          </div>

          {/* Actions & Workspace Selector */}
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <WorkspaceSelector />
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main style={{ maxWidth: "1280px", margin: "0 auto", padding: "32px 24px" }}>
        {/* Navigation Tabs */}
        <div style={{ display: "flex", gap: "8px", borderBottom: "1px solid #1e293b", marginBottom: "28px" }}>
          {[
            { id: "research", label: "⚡ Tra cứu AI & Cào dữ liệu Internet" },
            { id: "library", label: "🏢 Thư viện Doanh nghiệp trong Database" },
            { id: "review", label: "📥 Hộp thư Thẩm định (Review Inbox)" },
            { id: "audit", label: "🛡️ Nhật ký Hệ thống (Audit Logs)" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              style={{
                padding: "14px 22px",
                background: activeTab === tab.id ? "#1e293b" : "transparent",
                color: activeTab === tab.id ? "#10b981" : "#94a3b8",
                border: "none",
                borderBottom: activeTab === tab.id ? "3px solid #10b981" : "3px solid transparent",
                borderRadius: "8px 8px 0 0",
                fontWeight: 700,
                fontSize: "14px",
                cursor: "pointer",
                transition: "all 0.2s ease",
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Contents */}
        <div style={{ background: "#1e293b", border: "1px solid #334155", borderRadius: "16px", padding: "28px", minHeight: "550px" }}>
          {activeTab === "research" && (
            <CompanyResearchFlow
              token={token}
              workspaceId={workspaceId}
              onSavedSuccess={() => {
                setRefreshLibraryKey((prev) => prev + 1);
              }}
            />
          )}
          {activeTab === "library" && <CompanyLibrary key={refreshLibraryKey} />}
          {activeTab === "review" && <ReviewInbox token={token} workspaceId={workspaceId} />}
          {activeTab === "audit" && <AuditLogsViewer token={token} workspaceId={workspaceId} />}
        </div>
      </main>
    </div>
  );
}

export default function Home() {
  return (
    <AuthProvider>
      <MainDashboard />
    </AuthProvider>
  );
}

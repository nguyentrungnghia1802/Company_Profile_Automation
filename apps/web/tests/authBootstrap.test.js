import { describe, expect, test } from "bun:test";
import {
  normalizeCurrentUserPayload,
  resolveAuthBootstrap,
  resolveResearchAccessState,
  shouldFallbackToAutoLogin,
  TOKEN_KEY,
  WORKSPACE_KEY,
} from "../src/stores/authBootstrap";

function storage(values = {}) {
  return {
    getItem(key) {
      return values[key] ?? null;
    },
  };
}

describe("resolveAuthBootstrap", () => {
  test("normalizes the API snake_case user payload before capability checks", () => {
    const user = normalizeCurrentUserPayload({
      id: "user-1",
      email: "researcher@example.com",
      display_name: "Dev Researcher",
      preferred_locale: "vi",
      status: "active",
      active_workspace: {
        id: "workspace-1",
        name: "Local Development Workspace",
        slug: "local-development",
        role: "researcher",
        capabilities: ["company:read", "research:start"],
      },
      workspaces: [
        {
          id: "workspace-1",
          name: "Local Development Workspace",
          slug: "local-development",
          role: "researcher",
        },
      ],
      capabilities: ["company:read", "research:start"],
    });

    expect(user?.displayName).toBe("Dev Researcher");
    expect(user?.activeWorkspace?.id).toBe("workspace-1");
    expect(user?.capabilities).toContain("research:start");
  });

  test("rejects an invalid user payload", () => {
    expect(normalizeCurrentUserPayload({ display_name: "Missing id" })).toBeNull();
  });

  test("uses the saved session without exchanging the token again", () => {
    const plan = resolveAuthBootstrap(
      storage({
        [TOKEN_KEY]: "saved-token",
        [WORKSPACE_KEY]: "workspace-1",
      }),
      "local-auto-token",
    );

    expect(plan).toEqual({
      autoLoginToken: "local-auto-token",
      savedToken: "saved-token",
      token: "saved-token",
      workspaceId: "workspace-1",
      shouldExchange: false,
    });
  });

  test("uses the local token once when there is no saved session", () => {
    const plan = resolveAuthBootstrap(storage(), "local-auto-token");

    expect(plan).toEqual({
      autoLoginToken: "local-auto-token",
      savedToken: null,
      token: "local-auto-token",
      workspaceId: null,
      shouldExchange: true,
    });
  });

  test("does not start authentication when no session or local token exists", () => {
    const plan = resolveAuthBootstrap(storage(), "");

    expect(plan).toEqual({
      autoLoginToken: null,
      savedToken: null,
      token: null,
      workspaceId: null,
      shouldExchange: false,
    });
  });

  test("falls back from a stale saved session without an active workspace", () => {
    const plan = resolveAuthBootstrap(storage({ [TOKEN_KEY]: "stale-token" }), "local-auto-token");

    expect(shouldFallbackToAutoLogin(plan, null)).toBe(true);
    expect(
      shouldFallbackToAutoLogin(plan, { activeWorkspace: null }),
    ).toBe(true);
  });

  test("keeps a valid saved session instead of replacing its role", () => {
    const plan = resolveAuthBootstrap(storage({ [TOKEN_KEY]: "saved-token" }), "local-auto-token");

    expect(
      shouldFallbackToAutoLogin(plan, { activeWorkspace: { id: "workspace-1" } }),
    ).toBe(false);
  });

  test("does not report missing capability before authentication and workspace checks complete", () => {
    expect(
      resolveResearchAccessState({
        isAuthenticated: false,
        hasActiveWorkspace: false,
        hasCapability: false,
        hasAuthError: false,
      }),
    ).toBe("unauthenticated");
    expect(
      resolveResearchAccessState({
        isAuthenticated: true,
        hasActiveWorkspace: false,
        hasCapability: false,
        hasAuthError: false,
      }),
    ).toBe("no_workspace");
    expect(
      resolveResearchAccessState({
        isAuthenticated: true,
        hasActiveWorkspace: true,
        hasCapability: false,
        hasAuthError: false,
      }),
    ).toBe("missing_capability");
  });
});

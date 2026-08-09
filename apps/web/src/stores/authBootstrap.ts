export const TOKEN_KEY = "vcps_access_token";
export const WORKSPACE_KEY = "vcps_active_workspace_id";

export interface AuthStorage {
  getItem(key: string): string | null;
}

export interface AuthBootstrapPlan {
  autoLoginToken: string | null;
  savedToken: string | null;
  token: string | null;
  workspaceId: string | null;
  shouldExchange: boolean;
}

export interface AuthenticatedUserSnapshot {
  activeWorkspace: unknown | null;
}

export interface NormalizedCurrentUser {
  id: string;
  email: string | null;
  displayName: string;
  preferredLocale: string;
  status: string;
  activeWorkspace: {
    id: string;
    name: string;
    slug: string;
    role: string;
    capabilities: string[];
  } | null;
  workspaces: Array<{
    id: string;
    name: string;
    slug: string;
    role: string;
  }>;
  capabilities: string[];
}

export type ResearchAccessState =
  | "ready"
  | "auth_error"
  | "unauthenticated"
  | "no_workspace"
  | "missing_capability";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function stringValue(record: Record<string, unknown>, camelKey: string, snakeKey = camelKey): string {
  const value = record[camelKey] ?? record[snakeKey];
  return typeof value === "string" ? value : "";
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

/** Normalize the API's snake_case auth contract for the camelCase React state. */
export function normalizeCurrentUserPayload(payload: unknown): NormalizedCurrentUser | null {
  if (!isRecord(payload) || typeof payload.id !== "string") return null;

  const rawActiveWorkspace = payload.activeWorkspace ?? payload.active_workspace;
  const activeWorkspace = isRecord(rawActiveWorkspace) && typeof rawActiveWorkspace.id === "string"
    ? {
        id: rawActiveWorkspace.id,
        name: stringValue(rawActiveWorkspace, "name"),
        slug: stringValue(rawActiveWorkspace, "slug"),
        role: stringValue(rawActiveWorkspace, "role"),
        capabilities: stringArray(rawActiveWorkspace.capabilities),
      }
    : null;

  const rawWorkspaces = Array.isArray(payload.workspaces) ? payload.workspaces : [];
  const workspaces = rawWorkspaces.flatMap((workspace) => {
    if (!isRecord(workspace) || typeof workspace.id !== "string") return [];
    return [{
      id: workspace.id,
      name: stringValue(workspace, "name"),
      slug: stringValue(workspace, "slug"),
      role: stringValue(workspace, "role"),
    }];
  });

  return {
    id: payload.id,
    email: typeof payload.email === "string" ? payload.email : null,
    displayName: stringValue(payload, "displayName", "display_name"),
    preferredLocale: stringValue(payload, "preferredLocale", "preferred_locale") || "vi",
    status: stringValue(payload, "status"),
    activeWorkspace,
    workspaces,
    capabilities: stringArray(payload.capabilities),
  };
}

export function resolveAuthBootstrap(
  storage: AuthStorage,
  autoLoginToken?: string | null,
): AuthBootstrapPlan {
  const savedToken = storage.getItem(TOKEN_KEY);
  const workspaceId = storage.getItem(WORKSPACE_KEY);
  const normalizedAutoLoginToken = autoLoginToken || null;
  const token = savedToken || normalizedAutoLoginToken;

  return {
    autoLoginToken: normalizedAutoLoginToken,
    savedToken,
    token,
    workspaceId,
    shouldExchange: !savedToken && Boolean(normalizedAutoLoginToken),
  };
}

/**
 * A persisted token can still identify a user while lacking a usable local
 * workspace. In that case the configured local token is the safe recovery
 * path; a valid active session must never be silently replaced.
 */
export function shouldFallbackToAutoLogin(
  plan: Pick<AuthBootstrapPlan, "savedToken" | "autoLoginToken">,
  authenticatedUser: AuthenticatedUserSnapshot | null,
): boolean {
  return Boolean(
    plan.savedToken &&
      plan.autoLoginToken &&
      plan.savedToken !== plan.autoLoginToken &&
      (!authenticatedUser || !authenticatedUser.activeWorkspace),
  );
}

export function resolveResearchAccessState(input: {
  isAuthenticated: boolean;
  hasActiveWorkspace: boolean;
  hasCapability: boolean;
  hasAuthError: boolean;
}): ResearchAccessState {
  if (input.hasAuthError) return "auth_error";
  if (!input.isAuthenticated) return "unauthenticated";
  if (!input.hasActiveWorkspace) return "no_workspace";
  if (!input.hasCapability) return "missing_capability";
  return "ready";
}

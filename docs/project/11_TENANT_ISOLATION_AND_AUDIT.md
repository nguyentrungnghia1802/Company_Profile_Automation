# Tenant Isolation Guarantee and Audit Event Matrix

Status: Phase 1 verified specification.

## 1. Multi-Tenant Isolation Guarantee

The Verified Company Profile System (VCPS) enforces strict multi-tenant isolation at database, application service, and API request layers.

### 1.1 Tenant Boundary Principles

- **Workspace as Tenant Boundary**: A `Workspace` represents the fundamental security and policy isolation boundary. All company profiles, sources, research jobs, facts, and policy sets belong to exactly one workspace.
- **Explicit Membership Resolution**: Every authenticated HTTP request resolves the `RequestActor` context against `workspace_members`. Access to workspace resources is strictly forbidden (`WORKSPACE_ACCESS_DENIED`) unless an active membership record exists.
- **Database Query Scoping**: All persistence queries targeting tenant-owned entities MUST include explicit `WHERE workspace_id = :workspace_id` filtering constraints.
- **Client Workspace Selection**: Clients specify target workspace via `X-Workspace-ID` header or route path parameter. The backend server independently verifies active membership and resolves capability grants before executing commands or queries.

## 2. Role Capability Matrix

Permissions in VCPS are governed by coarse role assignments mapped to granular application capabilities:

| Role | Granted Capabilities | Purpose |
| --- | --- | --- |
| `researcher` | `company:read`, `company:create`, `research:start`, `source:fetch`, `fact:candidate_create` | Submits company targets, initiates research pipelines, collects source evidence, and proposes fact candidates |
| `reviewer` | `company:read`, `company:create`, `company:update`, `research:start`, `source:fetch`, `fact:candidate_create`, `fact:review`, `conflict:resolve`, `profile:publish`, `company:archive`, `company:merge` | Reviews fact candidates, resolves conflicting facts, approves profile drafts, publishes canonical profile versions, and merges duplicate entities |
| `officer` | `company:read`, `export:generate`, `audit:view` | Views canonical company profiles, exports verified dossier reports, and inspects system compliance audit trails |
| `workspace_admin` | `company:read`, `company:create`, `company:update`, `research:start`, `workspace:admin`, `member:manage`, `policy:manage` | Manages workspace settings, member invitations, role assignments, deactivations, and quality threshold policies |

## 3. Membership Audit Event Matrix

All workspace membership and administrative lifecycle mutations produce structured, immutable audit log events containing event name, workspace ID, target user ID, actor ID, and versioning tracking:

| Audit Event | Trigger | Log Event Name | Audit Payload Fields |
| --- | --- | --- | --- |
| Member Invited | User added or invited to workspace | `membership.invited` | `workspace_id`, `target_user_id`, `role`, `status`, `actor_id` |
| Role Changed | Member role updated by admin | `membership.role_changed` | `workspace_id`, `target_user_id`, `old_role`, `new_role`, `actor_id` |
| Status Changed | Member status updated (active/invited) | `membership.status_changed` | `workspace_id`, `target_user_id`, `old_status`, `new_status`, `actor_id` |
| Member Deactivated | Membership disabled by admin | `membership.deactivated` | `workspace_id`, `target_user_id`, `old_status`, `new_status`, `actor_id` |

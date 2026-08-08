# API

Status: planned HTTP and SSE contract baseline.

## 1. Contract sources

After implementation:

- runtime route truth: FastAPI routers;
- request/response truth: Pydantic schemas;
- interactive docs: `/api/docs` in permitted environments;
- raw OpenAPI: `/api/openapi.json`;
- generated frontend client: produced from the checked OpenAPI artifact;
- drift gate: CI compares runtime OpenAPI with the committed contract snapshot.

This document is the human-readable endpoint and behavior index.

## 2. Base URL and authentication

- Versioned API prefix: `/api/v1`.
- Bearer identity token or secure backend session according to the implemented auth adapter.
- Protected requests require an active application user and workspace membership.
- Workspace may be selected by path or header, but the server resolves and verifies membership.
- JSON is the default request/response content type.
- Large document bodies and exports are transferred through object storage or streaming endpoints, not embedded in normal list responses.

## 3. Standard envelopes

Success:

```json
{
  "success": true,
  "data": {}
}
```

Paginated success:

```json
{
  "success": true,
  "data": [],
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 0,
    "totalPages": 0
  }
}
```

Cursor success may be used for timeline or audit streams:

```json
{
  "success": true,
  "data": [],
  "meta": {
    "nextCursor": null,
    "hasMore": false
  }
}
```

Error:

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": {
      "fieldErrors": {
        "website": ["Invalid public URL"]
      }
    },
    "requestId": "req_..."
  }
}
```

Clients localize by stable error code. Backend message is diagnostic and safe, not the primary UI-copy contract.

## 4. Status semantics

| HTTP | Meaning |
| --- | --- |
| 200 | Successful query or command |
| 201 | Resource created |
| 202 | Asynchronous work accepted |
| 204 | Successful command with no body |
| 400 | Invalid business request not represented as field validation |
| 401 | Missing or invalid authentication |
| 403 | Insufficient capability or workspace scope |
| 404 | Resource not found in authorized scope |
| 409 | Duplicate, stale version, state, lock, or idempotency conflict |
| 410 | Withdrawn or expired resource when useful to distinguish |
| 422 | Request validation error |
| 429 | Rate or budget limit |
| 502 | External provider failed |
| 503 | Platform dependency unavailable or not ready |

## 5. Common headers

- `Authorization: Bearer <token>` when bearer mode is used.
- `Idempotency-Key` for retryable create/command endpoints.
- `If-Match` or body `rowVersion` for optimistic concurrency where implemented.
- `Accept-Language: vi | en` for UI-facing messages and requested display locale.
- `X-Request-ID` may be accepted; server always returns a request ID.

## 6. Authentication and current user

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| POST | `/api/v1/auth/exchange` | Public with valid provider token | Verify external identity and create application session/context |
| POST | `/api/v1/auth/logout` | Authenticated | Revoke backend session where applicable |
| GET | `/api/v1/me` | Authenticated | Current user, memberships, active workspace, capabilities |
| PATCH | `/api/v1/me` | Authenticated | Update display name and preferred locale |

Example current-user response:

```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "email": "researcher@example.org",
    "displayName": "Researcher",
    "preferredLocale": "vi",
    "activeWorkspace": {
      "id": "uuid",
      "name": "Innovation Center",
      "role": "researcher",
      "capabilities": ["company:read", "company:create", "research:start"]
    },
    "workspaces": []
  }
}
```

## 7. Workspace administration

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/workspaces` | Authenticated | List authorized workspaces |
| GET | `/api/v1/workspaces/:workspaceId` | Member | Workspace details and safe policy summary |
| GET | `/api/v1/workspaces/:workspaceId/members` | Workspace admin | List members |
| POST | `/api/v1/workspaces/:workspaceId/members` | Workspace admin | Invite or add member |
| PATCH | `/api/v1/workspaces/:workspaceId/members/:memberId` | Workspace admin | Change role or active status |
| DELETE | `/api/v1/workspaces/:workspaceId/members/:memberId` | Workspace admin | Deactivate membership |

The API never trusts role or workspace values supplied by the browser without membership verification.

## 8. Company endpoints

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/workspaces/:workspaceId/companies` | Member | Paginated company library search |
| POST | `/api/v1/workspaces/:workspaceId/companies/resolve` | Researcher+ | Preview duplicate and identity candidates without creating |
| POST | `/api/v1/workspaces/:workspaceId/companies` | Researcher+ | Create canonical or ambiguous company |
| GET | `/api/v1/workspaces/:workspaceId/companies/:companyId` | Member | Company identity and current profile summary |
| PATCH | `/api/v1/workspaces/:workspaceId/companies/:companyId` | Reviewer+ | Update canonical identity metadata with optimistic lock |
| POST | `/api/v1/workspaces/:workspaceId/companies/:companyId/archive` | Reviewer+ | Archive company |
| POST | `/api/v1/workspaces/:workspaceId/companies/:companyId/restore` | Reviewer+ | Restore archived company |
| GET | `/api/v1/workspaces/:workspaceId/companies/:companyId/aliases` | Member | List aliases |
| POST | `/api/v1/workspaces/:workspaceId/companies/:companyId/aliases` | Researcher+ | Add alias with provenance |
| GET | `/api/v1/workspaces/:workspaceId/companies/:companyId/identifiers` | Member | List identifiers |
| POST | `/api/v1/workspaces/:workspaceId/companies/:companyId/identifiers` | Reviewer+ | Add or verify identifier |
| GET | `/api/v1/workspaces/:workspaceId/companies/:companyId/relationships` | Member | Parent/subsidiary/brand relationships |
| POST | `/api/v1/workspaces/:workspaceId/companies/:companyId/relationships` | Reviewer+ | Create relationship with evidence |
| POST | `/api/v1/workspaces/:workspaceId/companies/merge` | Reviewer+ | Merge duplicate companies after preview confirmation |
| POST | `/api/v1/workspaces/:workspaceId/companies/:companyId/split` | Reviewer+ | Split incorrectly merged entity according to supported contract |

Create-company request:

```json
{
  "name": "Example Technology JSC",
  "countryCode": "VN",
  "website": "https://example.com",
  "registrationIdentifier": null,
  "knownAliases": ["Example Tech"],
  "researchPurpose": "Prepare for innovation partnership meeting",
  "locale": "vi"
}
```

Potential duplicate returns `409 COMPANY_DUPLICATE_REVIEW_REQUIRED` unless the client explicitly selects an existing candidate or confirms an allowed new ambiguous record.

## 9. Research job endpoints

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| POST | `/api/v1/workspaces/:workspaceId/companies/:companyId/research-jobs` | Researcher+ | Start initial, refresh, or targeted research |
| GET | `/api/v1/workspaces/:workspaceId/research-jobs` | Researcher+ | List jobs with filters |
| GET | `/api/v1/workspaces/:workspaceId/research-jobs/:jobId` | Researcher+ | Job detail and steps |
| GET | `/api/v1/workspaces/:workspaceId/research-jobs/:jobId/events` | Researcher+ | SSE progress stream |
| POST | `/api/v1/workspaces/:workspaceId/research-jobs/:jobId/cancel` | Requestor or reviewer+ | Request cancellation |
| POST | `/api/v1/workspaces/:workspaceId/research-jobs/:jobId/retry` | Researcher+ | Retry eligible failed scope |
| POST | `/api/v1/workspaces/:workspaceId/research-jobs/:jobId/steps/:stepId/retry` | Reviewer/admin | Retry eligible step |

Start request:

```json
{
  "type": "initial",
  "scope": {
    "sections": ["identity", "overview", "products", "size", "markets", "leadership", "recent_activity"],
    "maxSources": 20,
    "includePdf": true,
    "languages": ["vi", "en"]
  }
}
```

Accepted response:

```json
{
  "success": true,
  "data": {
    "jobId": "uuid",
    "status": "queued",
    "eventsUrl": "/api/v1/workspaces/.../research-jobs/.../events"
  }
}
```

SSE event types:

- `job.snapshot`;
- `step.started`;
- `step.progress`;
- `step.succeeded`;
- `step.failed`;
- `review.required`;
- `job.completed`;
- `heartbeat`.

Every event contains job version and sequence so clients can reconnect and fall back to GET polling.

## 10. Search query and source endpoints

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/workspaces/:workspaceId/companies/:companyId/research-queries` | Researcher+ | Query history and results |
| GET | `/api/v1/workspaces/:workspaceId/companies/:companyId/sources` | Member | Paginated source list |
| POST | `/api/v1/workspaces/:workspaceId/companies/:companyId/sources` | Researcher+ | Add public URL manually |
| GET | `/api/v1/workspaces/:workspaceId/sources/:sourceId` | Member | Source metadata and latest snapshot summary |
| PATCH | `/api/v1/workspaces/:workspaceId/sources/:sourceId` | Reviewer+ | Change classification or selection reason |
| POST | `/api/v1/workspaces/:workspaceId/sources/:sourceId/fetch` | Researcher+ | Schedule fetch/refresh |
| POST | `/api/v1/workspaces/:workspaceId/sources/:sourceId/block` | Reviewer/admin | Block source with reason |
| POST | `/api/v1/workspaces/:workspaceId/sources/:sourceId/reject` | Reviewer+ | Reject source for entity or quality reason |
| GET | `/api/v1/workspaces/:workspaceId/sources/:sourceId/snapshots` | Member | Snapshot history |
| GET | `/api/v1/workspaces/:workspaceId/snapshots/:snapshotId` | Member | Snapshot metadata and parse status |
| GET | `/api/v1/workspaces/:workspaceId/snapshots/:snapshotId/blocks` | Researcher+ | Paginated parsed blocks |

Raw object download is not a public URL. Access requires an authorized endpoint or short-lived signed URL.

Manual-source request:

```json
{
  "url": "https://example.com/about",
  "reason": "Official company About page supplied by researcher"
}
```

The backend performs SSRF and policy checks before scheduling retrieval.

## 11. Fact and evidence endpoints

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/workspaces/:workspaceId/companies/:companyId/facts` | Member | Candidate facts grouped by field |
| GET | `/api/v1/workspaces/:workspaceId/facts/:candidateId` | Member | Candidate detail, confidence, evidence |
| POST | `/api/v1/workspaces/:workspaceId/companies/:companyId/facts` | Reviewer+ | Create human-origin candidate |
| POST | `/api/v1/workspaces/:workspaceId/facts/:candidateId/accept` | Reviewer+ | Accept candidate with reason/version |
| POST | `/api/v1/workspaces/:workspaceId/facts/:candidateId/reject` | Reviewer+ | Reject candidate with reason/version |
| POST | `/api/v1/workspaces/:workspaceId/facts/:candidateId/mark-unknown` | Reviewer+ | Resolve field as unknown where supported |
| GET | `/api/v1/workspaces/:workspaceId/evidences/:evidenceId` | Member | Evidence context and source references |
| POST | `/api/v1/workspaces/:workspaceId/facts/:candidateId/evidences` | Reviewer+ | Attach accepted public evidence or human note |

Human candidate request:

```json
{
  "fieldKey": "company.employee_range",
  "value": {
    "min": 100,
    "max": 200,
    "unit": "employees"
  },
  "status": "estimated",
  "reason": "Official careers page states more than 100 employees",
  "evidenceIds": ["uuid"]
}
```

## 12. Conflict endpoints

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/workspaces/:workspaceId/companies/:companyId/conflicts` | Member | List conflicts |
| GET | `/api/v1/workspaces/:workspaceId/conflicts/:conflictId` | Member | Candidates, sources, and prior decisions |
| POST | `/api/v1/workspaces/:workspaceId/conflicts/:conflictId/resolve` | Reviewer+ | Resolve with selected outcome and reason |
| POST | `/api/v1/workspaces/:workspaceId/conflicts/:conflictId/request-research` | Reviewer+ | Create targeted research job |
| POST | `/api/v1/workspaces/:workspaceId/conflicts/:conflictId/reopen` | Reviewer+ | Reopen after new evidence |

Resolve request:

```json
{
  "resolution": "select_candidate",
  "selectedCandidateIds": ["uuid"],
  "reason": "Government registry is authoritative for the current legal incorporation date",
  "rowVersion": 3
}
```

Stale row version returns `409 REVIEW_VERSION_CONFLICT`.

## 13. Review task endpoints

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/workspaces/:workspaceId/review-tasks` | Reviewer+ | Review inbox with filters |
| GET | `/api/v1/workspaces/:workspaceId/review-tasks/:taskId` | Reviewer+ | Task context |
| POST | `/api/v1/workspaces/:workspaceId/review-tasks/:taskId/claim` | Reviewer+ | Claim open task |
| POST | `/api/v1/workspaces/:workspaceId/review-tasks/:taskId/release` | Assigned reviewer/admin | Release task |
| POST | `/api/v1/workspaces/:workspaceId/review-tasks/:taskId/request-changes` | Reviewer+ | Request follow-up |
| POST | `/api/v1/workspaces/:workspaceId/review-tasks/:taskId/complete` | Assigned reviewer/admin | Complete with decision |
| POST | `/api/v1/workspaces/:workspaceId/review-tasks/:taskId/reopen` | Reviewer/admin | Reopen with reason |

## 14. Draft and profile endpoints

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/workspaces/:workspaceId/companies/:companyId/profile-drafts` | Researcher+ | List drafts |
| GET | `/api/v1/workspaces/:workspaceId/profile-drafts/:draftId` | Researcher+ | Draft detail and field selection |
| PATCH | `/api/v1/workspaces/:workspaceId/profile-drafts/:draftId` | Researcher/reviewer | Update allowed draft notes and field selection |
| POST | `/api/v1/workspaces/:workspaceId/profile-drafts/:draftId/request-review` | Researcher+ | Mark ready and create publication review |
| POST | `/api/v1/workspaces/:workspaceId/profile-drafts/:draftId/approve` | Reviewer+ | Approve draft for publication |
| POST | `/api/v1/workspaces/:workspaceId/profile-drafts/:draftId/publish` | Reviewer+ | Publish immutable version |
| GET | `/api/v1/workspaces/:workspaceId/companies/:companyId/profiles` | Member | Version list |
| GET | `/api/v1/workspaces/:workspaceId/companies/:companyId/profile` | Member | Current published profile |
| GET | `/api/v1/workspaces/:workspaceId/profiles/:profileVersionId` | Member | Specific immutable version |
| GET | `/api/v1/workspaces/:workspaceId/profiles/:profileVersionId/diff/:otherVersionId` | Member | Field-level diff |
| POST | `/api/v1/workspaces/:workspaceId/profiles/:profileVersionId/withdraw` | Reviewer+ | Withdraw with reason |

Publication returns `409` when mandatory tasks, evidence, conflicts, stale row version, or current-version lock prevents publication.

## 15. Export endpoints

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| POST | `/api/v1/workspaces/:workspaceId/profiles/:profileVersionId/exports` | Member with export capability | Create PDF or JSON export |
| GET | `/api/v1/workspaces/:workspaceId/exports/:exportId` | Requestor or authorized member | Export status |
| GET | `/api/v1/workspaces/:workspaceId/exports/:exportId/download` | Authorized member | Stream or redirect to short-lived signed URL |
| POST | `/api/v1/workspaces/:workspaceId/exports/:exportId/retry` | Authorized member | Retry failed generation |

Export request:

```json
{
  "format": "pdf",
  "locale": "vi",
  "includeSourceAppendix": true,
  "includeInternalNotes": false
}
```

## 16. Policy and provider administration

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/workspaces/:workspaceId/policies` | Workspace admin/reviewer | List policy versions |
| POST | `/api/v1/workspaces/:workspaceId/policies` | Workspace admin | Create immutable policy version |
| POST | `/api/v1/workspaces/:workspaceId/policies/:policyId/activate` | Workspace admin | Activate version |
| GET | `/api/v1/workspaces/:workspaceId/domain-policies` | Reviewer/admin | Allowed/blocked domain rules |
| POST | `/api/v1/workspaces/:workspaceId/domain-policies` | Workspace admin | Add domain rule |
| PATCH | `/api/v1/workspaces/:workspaceId/domain-policies/:ruleId` | Workspace admin | Update active state/reason |
| GET | `/api/v1/workspaces/:workspaceId/provider-settings` | Workspace admin | Safe provider status, no secrets |
| PATCH | `/api/v1/workspaces/:workspaceId/provider-settings` | Workspace admin | Update non-secret behavior and limits |

Provider secrets are not accepted through general JSON endpoints unless a dedicated secure secret-management contract is later approved.

## 17. Operations and audit

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/health` | Probe | Process health summary |
| GET | `/ready` | Probe | Database and required dependency readiness |
| GET | `/metrics` | Infrastructure protected | Prometheus/OpenMetrics output |
| GET | `/api/v1/workspaces/:workspaceId/operations/jobs` | Workspace admin | Operational job list |
| GET | `/api/v1/workspaces/:workspaceId/operations/usage` | Workspace admin | Provider usage and cost summary |
| GET | `/api/v1/workspaces/:workspaceId/audit` | Authorized reviewer/admin | Paginated audit trail |

Health endpoints never expose secrets, private URLs, or raw provider errors.

## 18. Pagination and filtering

List endpoints define explicit filters. Common parameters:

- `page`, `limit` for bounded administrative lists;
- `cursor` for audit, events, and timelines;
- `q` for normalized search;
- `status`, `country`, `industry`, `freshness`, `hasConflict`, `updatedFrom`, `updatedTo` where applicable;
- sort values from a documented allowlist.

Limits have server maximums. Unknown sort/filter values fail validation rather than becoming raw SQL.

## 19. Idempotency

Required for:

- company creation when invoked from retried UI submission;
- research job creation;
- manual source addition;
- merge commands;
- publication;
- export creation;
- retryable admin commands.

Server stores request hash. Reusing a key with different body returns `409 IDEMPOTENCY_KEY_REUSED`.

## 20. Rate and budget controls

- Authentication and public token exchange use strict per-IP limits.
- Research creation uses per-user/workspace limits.
- Fetch and AI budgets are enforced by worker policy.
- SSE connection count is bounded.
- Exports use per-user limits.
- Provider quota exhaustion becomes a structured job error and operational metric.

## 21. API change rules

- Backward-compatible additions remain in `/api/v1`.
- Breaking semantics require migration strategy and possibly `/api/v2`.
- Update route, schema, service, repository, tests, generated client, OpenAPI snapshot, and this document together.
- Do not add generic untyped JSON fields when a stable schema can be defined.
- Never expose raw AI prompts/responses, source credentials, signed storage URLs with long expiry, or cross-workspace data.

## 22. API synchronization checklist

- [ ] Endpoint inventory matches FastAPI routes.
- [ ] Request and response examples match Pydantic schemas.
- [ ] Access requirements match service authorization tests.
- [ ] Error codes and status semantics are documented.
- [ ] Idempotency and optimistic locking are tested.
- [ ] Frontend generated client is refreshed.
- [ ] Runtime OpenAPI drift check passes.
- [ ] New endpoints update relevant requirements, domain flows, and Roadmap tasks.

## Verified implementation addendum — TASK-CRAWL-001 (2026-08-08)

This task changes worker orchestration and the persisted research-job status set but does not add or change an HTTP route, request schema, response schema, or authorization rule. Research-job responses continue to expose the model's string status and optional limited-result message. The committed snapshot passes OpenAPI drift in the clean task-only worktree; unrelated uncommitted API changes still produce drift only in the mixed current worktree.

## Verified implementation addendum — TASK-CRAWL-005 (2026-08-09)

The source contracts now expose the metadata required by the evidence UI. `SourceResponseData` includes discovery method/provider/provenance, field authority, selection/rejection reason, entity match, latest fetch outcome/policy, parser status/version, snapshot ID, and last fetched time. Fetch-attempt responses include redirect/retry/policy/retryable fields; snapshot responses include language/parser status/version/error; document-block responses include language, parser version, page/section/location metadata, and offsets. These are backward-compatible response additions under `/api/v1`; the generated client surface remains compatible because these endpoints already use response data passthrough types. Runtime OpenAPI is regenerated and checked for drift in the clean task-only tree.

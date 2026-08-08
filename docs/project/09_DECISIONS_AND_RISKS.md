# Decisions and Risks

Last reviewed: initial specification baseline.

This file records accepted architectural decisions, open decisions, technical debt, and the active risk register. Completed feature status belongs in current-state documents and `Roadmap.md`.

## 1. ADR format

Every material decision contains:

- Status;
- Context;
- Decision;
- Consequences;
- Supersedes or superseded by when applicable.

Do not silently reverse an accepted decision. Add a new ADR that explicitly supersedes it.

## ADR-001: PostgreSQL is the operational source of truth

**Status:** Accepted for baseline.

**Context:** Entity identity, jobs, evidence, conflicts, review decisions, publication, and audit require transactions, constraints, and relational queries.

**Decision:** Use PostgreSQL 16 as the authoritative structured store. Alembic migrations are executable schema truth.

**Consequences:** Strong consistency and auditability; the team owns migrations, indexes, backup, pooling, and concurrency design.

## ADR-002: Modular monolith with separate API and worker processes

**Status:** Accepted for baseline.

**Context:** Research is asynchronous and externally dependent, but the project should remain understandable for a small team.

**Decision:** Use one shared Python backend package with FastAPI and worker entrypoints. Preserve domain module boundaries. Do not begin with microservices.

**Consequences:** Simple code sharing and deployment. Process isolation protects API responsiveness. Services may be extracted only for measured scale, security, or ownership needs.

## ADR-003: PostgreSQL-backed durable job state

**Status:** Accepted for baseline.

**Context:** Research steps must survive restarts and duplicate delivery.

**Decision:** Store jobs, steps, leases, attempts, and idempotency in PostgreSQL. Local workers claim with row locks. Production may use Cloud Tasks for delivery while PostgreSQL remains authoritative.

**Consequences:** No Redis is required initially. Claim queries and lease recovery require careful indexing and tests.

## ADR-004: Evidence-first profile model

**Status:** Accepted.

**Context:** An AI summary without provenance is not sufficiently trustworthy for institutional use.

**Decision:** Every published fact references accepted evidence or a narrow documented human-origin exception. Evidence points to immutable source snapshots and stable document blocks.

**Consequences:** More storage and workflow complexity, but strong traceability, reviewability, and correction history.

## ADR-005: Published profiles are immutable versions

**Status:** Accepted.

**Context:** New research must not rewrite what staff previously relied upon.

**Decision:** Publication creates immutable profile versions. Corrections create a new version or withdrawal. One current published version exists per company.

**Consequences:** Historical storage grows; diff and retention behavior must be maintained.

## ADR-006: Entity resolution precedes fact merge

**Status:** Accepted.

**Context:** Accurate extraction from the wrong company is still wrong.

**Decision:** Ambiguous entities block automatic fact merge. Brands, legal entities, subsidiaries, branches, and historical entities are represented explicitly.

**Consequences:** Some jobs require human identity review before they can finish, but the system avoids silent contamination.

## ADR-007: Source authority is field-specific

**Status:** Accepted.

**Context:** A company registry, official website, news article, and social page have different strengths for different facts.

**Decision:** Authority and source preference are versioned by field type and context rather than one global domain score.

**Consequences:** Policy is more complex but explainable and adaptable.

## ADR-008: Gemini is behind a provider-neutral interface

**Status:** Accepted for competition baseline.

**Context:** Google AI is relevant to the competition, but domain correctness must not depend directly on one SDK.

**Decision:** Use Gemini for structured extraction, classification, translation, comparison, and grounded summaries through internal protocols. Store provider/model/prompt/schema metadata. Provide deterministic mock adapters.

**Consequences:** Provider can be upgraded or replaced. The team must maintain schemas, validation, budget, privacy, and model-change testing.

## ADR-009: AI output is untrusted until locally validated

**Status:** Accepted.

**Context:** Models can hallucinate, follow prompt injection, or return malformed output.

**Decision:** Validate schema, evidence block references, entity match, field type, and support before creating validated candidates. Unknown is an acceptable output.

**Consequences:** Some plausible outputs are rejected; validation complexity is intentional.

## ADR-010: Legal and ethical acquisition only

**Status:** Accepted.

**Context:** Automated collection may conflict with terms, robots policy, privacy, or technical access controls.

**Decision:** Do not bypass authentication, CAPTCHAs, paywalls, robots restrictions, or anti-automation controls. Use approved APIs or user-supplied lawful sources where required. Record blocked reasons.

**Consequences:** Coverage is lower for restricted sources, but operational and legal risk is reduced.

## ADR-011: Direct HTTP first, browser rendering as controlled fallback

**Status:** Accepted.

**Context:** Browser automation is slower, more expensive, and increases attack surface.

**Decision:** Use safe direct HTTP and structured parsing first. Use Playwright only when necessary, policy-allowed, and resource-limited.

**Consequences:** Faster and safer common path; some dynamic sources need additional worker capacity.

## ADR-012: Object storage for immutable large artifacts

**Status:** Accepted.

**Context:** PDFs, HTML, parsed text, and exports can be large and should not bloat API responses or database rows unnecessarily.

**Decision:** Store artifact bodies in private object storage; PostgreSQL stores checksums, metadata, state, and references.

**Consequences:** Requires reconciliation, backup/lifecycle, signed access, and integrity controls.

## ADR-013: Human review before high-impact publication

**Status:** Accepted.

**Context:** Legal identity, ownership, financial, leadership, and reputation-related claims can materially affect decisions.

**Decision:** Configured high-impact fields and unresolved conflicts require reviewer approval. Job completion never implies publication.

**Consequences:** Review capacity becomes part of system throughput; review inbox and metrics are mandatory.

## ADR-014: Vietnamese-first product UI and English engineering artifacts

**Status:** Accepted for baseline.

**Context:** The competition and initial operational audience are Vietnamese, while engineering collaboration benefits from English conventions.

**Decision:** UI supports Vietnamese and English with Vietnamese default. Code, logs, commits, and canonical technical docs use English. Source evidence keeps original language.

**Consequences:** Every visible-copy change updates both locales; translation remains separate from evidence.

## ADR-015: REST plus SSE for interactive progress

**Status:** Accepted.

**Context:** Most operations are CRUD/query based, while research progress benefits from server push.

**Decision:** Use versioned REST for commands and queries, SSE for job progress, and polling fallback. Do not introduce WebSocket unless bidirectional real-time requirements emerge.

**Consequences:** Simpler operational model and reconnect semantics.

## ADR-016: Multi-workspace-safe schema from the start

**Status:** Accepted.

**Context:** The initial deployment may serve one innovation center, but institutional reuse and isolation matter.

**Decision:** Every business resource belongs to a workspace and all authorization is workspace-scoped. The baseline may seed one workspace, but code cannot assume singleton tenancy.

**Consequences:** Slightly more schema and authorization work; avoids costly later retrofit.

## ADR-017: Google Cloud is the reference production platform

**Status:** Accepted for deployment reference, not vendor lock-in at domain level.

**Context:** The project is for AI Riser Vietnam and uses Gemini. A coherent demo and production story is valuable.

**Decision:** Reference Cloud Run, Cloud SQL, Cloud Tasks, Cloud Storage, Secret Manager, and Cloud observability. Preserve provider interfaces where practical.

**Consequences:** Deployment docs optimize for GCP; local Docker remains mandatory.

## ADR-018: No automatic fit score in the trusted-profile MVP

**Status:** Accepted for initial roadmap.

**Context:** The immediate problem is reliable company understanding. A fit score can create false certainty before profile quality is proven.

**Decision:** Complete evidence-backed profiles, review, and meeting briefs first. Add fit assessment only as a later transparent rules-based feature with separate requirements.

**Consequences:** MVP stays focused. Roadmap may add a later optional phase without blocking trusted-profile completion.

## 2. Open decisions

| ID | Decision needed | Deadline or trigger |
| --- | --- | --- |
| OD-001 | Exact production auth mode: Firebase Auth versus Identity Platform configuration | Before production auth phase completes |
| OD-002 | Approved search provider and cost limits | Before real-provider staging |
| OD-003 | Source snapshot legal retention by category | Before production readiness |
| OD-004 | Whether original HTML bodies may be retained for every public source | Before production storage policy |
| OD-005 | Malware scanning service and quarantine workflow | Before real PDF production ingestion |
| OD-006 | Exact high-impact field set for the innovation center | Before reviewer acceptance |
| OD-007 | Whether program officers may view all evidence or only accepted evidence | Before role acceptance |
| OD-008 | Whether exports may include internal notes | Before export production release |
| OD-009 | SLOs, RPO, and RTO approved by stakeholders | Before production launch |
| OD-010 | Licensed registry/database integration priorities | After MVP or when partner access is available |

Open decisions must not be silently guessed in code. Use safe defaults and mark dependent tasks blocked when necessary.

## 3. Technical debt ledger

| ID | Issue | Impact | Control |
| --- | --- | --- | --- |
| TD-001 | Confidence weights may be heuristic before real evaluation data | Users may over-trust score | Show explanation, reviewer gate, calibrate with labeled cases |
| TD-002 | PostgreSQL search may become insufficient at large scale | Slow library search | Measure before introducing dedicated search service |
| TD-003 | Browser fetching increases worker cost and attack surface | Reliability/security | Direct HTTP first, sandbox, limits, domain policy |
| TD-004 | Raw prompt/response retention may be limited by privacy policy | Harder model debugging | Store hashes, safe metadata, approved sampled artifacts |
| TD-005 | Foreign registry formats vary widely | Coverage gaps | Provider/parser interface and targeted adapters |
| TD-006 | Human review throughput may become bottleneck | Slow publication | Priorities, mandatory-field policy, reviewer metrics |
| TD-007 | Source pages can disappear | Reduced future reproducibility | Immutable permitted snapshots, hash, source metadata |
| TD-008 | Model updates may change extraction behavior | Regression risk | Pin operation model where possible, contract fixtures, version metadata |
| TD-009 | Cloud Tasks and local DB polling are two dispatch modes | Operational complexity | Same idempotent step service and contract tests |
| TD-010 | No dedicated continuous-monitoring subsystem in baseline | Profiles become stale | Freshness indicators and manual refresh; later scheduled monitoring |

## 4. Risk register

| ID | Risk | Likelihood | Impact | Primary controls | Owner/status |
| --- | --- | --- | --- | --- | --- |
| R-001 | Facts from wrong company entity | Medium | Critical | Entity review, strong identifiers, merge quarantine | Open |
| R-002 | AI hallucination becomes accepted fact | Medium | Critical | Evidence schema, local validation, reviewer gate | Open |
| R-003 | Public sources are stale or contradictory | High | High | Dates, confidence, conflicts, refresh, human review | Open |
| R-004 | Scraping violates terms or access controls | Medium | High | Policy engine, no bypass, domain block, approved APIs | Open |
| R-005 | SSRF reaches internal services | Medium | Critical | URL/IP validation, redirect recheck, egress controls, tests | Open |
| R-006 | Malicious document exploits parser/browser | Medium | Critical | sandbox, limits, scanning, patching, isolated worker | Open |
| R-007 | Cross-workspace data leakage | Low/Medium | Critical | service/repository scope, tests, audit | Open |
| R-008 | Provider outage or quota blocks research | High | Medium | durable jobs, retry, partial success, budget alerts | Open |
| R-009 | Provider cost unexpectedly spikes | Medium | High | per-job/workspace budgets, metrics, kill switch | Open |
| R-010 | Source snapshot retention creates privacy/copyright concern | Medium | High | legal policy, minimization, retention classes, takedown | Open |
| R-011 | Reviewers over-trust confidence score | High | High | explanation, labels, mandatory review, training | Open |
| R-012 | Documentation drifts from code | High | High | AGENT rules, CI docs checks, status verification | Open |
| R-013 | Profile exports circulate after withdrawal | Medium | Medium | version/withdrawn watermark, expiry, audit, policy | Open |
| R-014 | Merge operation corrupts identity history | Low | Critical | preview, lock order, transaction, tests, audit | Open |
| R-015 | Dynamic sites block or fingerprint browser worker | High | Medium | fallback limits, no bypass, manual source addition | Open |

## 5. Decision and risk synchronization checklist

- [ ] Every material architectural change has an ADR.
- [ ] Superseded decisions are explicit.
- [ ] Open decisions have a trigger and are not silently implemented.
- [ ] New providers add cost, privacy, outage, and security risks.
- [ ] Roadmap tasks reference relevant ADRs and risks.
- [ ] Closed risks include evidence and residual risk.
- [ ] Technical debt discovered during implementation is added here or Roadmap defect ledger.
- [ ] Last reviewed date/commit is updated after real verification.

## Verified implementation addendum — TASK-CRAWL-001 (2026-08-08)

The implementation confirms ADR-003, ADR-004, ADR-006, ADR-008, ADR-009, ADR-010, and ADR-011 in the AI-independent pipeline: PostgreSQL-backed durable steps, evidence-first facts, entity resolution before extraction, provider-neutral validated AI, lawful source acquisition, and direct HTTP/browser fallback boundaries. The remaining operational risk is recorded as `partial_success` rather than silently treating provider outage as total crawl failure. Independent repository baseline defects remain in the Roadmap defect ledger without blocking this task's verified acceptance behavior.

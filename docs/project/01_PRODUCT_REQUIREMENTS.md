# Product Requirements

Status: initial specification baseline. Requirement statuses must be synchronized with source code and tests.

## 1. Scope and terminology

The system manages company identity, source discovery, content acquisition, structured fact extraction, evidence, conflicts, human review, profile publication, profile history, exports, and operational audit.

### 1.1 Status labels

| Status | Meaning |
| --- | --- |
| Planned | No complete runtime behavior has been verified |
| In progress | Some code exists, but acceptance criteria are not fully met |
| Implemented | Runtime behavior and relevant tests have been verified |
| Partial | Useful behavior exists, but documented scope is incomplete |
| Blocked | Progress is prevented by an explicit dependency or decision |
| Deprecated | Behavior remains temporarily for compatibility but should not be extended |

An agent must not mark a requirement Implemented solely because code files exist.

### 1.2 Fact status terminology

| Status | Meaning |
| --- | --- |
| `candidate` | Extracted or supplied value awaiting validation |
| `verified` | Accepted by automated rules and/or a reviewer with sufficient evidence |
| `inferred` | Derived from evidence but not stated directly by a source |
| `estimated` | Approximation such as employee range or market size |
| `conflicting` | Credible sources disagree |
| `stale` | Value may no longer represent the current state |
| `rejected` | Candidate is known to be unsuitable or incorrect |
| `unknown` | No acceptable value has been found |

## 2. Actors and authorization

| Actor | Scope |
| --- | --- |
| Researcher | Create companies, start research, inspect sources, propose edits, create draft profiles |
| Reviewer | All researcher capabilities plus approve/reject facts, resolve conflicts, publish profile versions |
| Program officer | Read published profiles, approved sources, timelines, and exports |
| Workspace administrator | Manage workspace members, roles, policies, provider configuration metadata, and audit access |
| Platform administrator | Operate platform-level configuration without silently accessing workspace content unless explicitly authorized |
| System worker | Execute trusted background jobs with least-privilege service identity |

Every workspace-owned read and write must be scoped by workspace membership. Request-body workspace IDs are selectors, never authorization.

## 3. Functional requirements

### 3.1 Authentication, workspace, and user management

| ID | Requirement | Status |
| --- | --- | --- |
| FR-AUTH-001 | Authenticate users through the configured identity provider and issue/verify backend sessions | Planned |
| FR-AUTH-002 | Support a deterministic local/test authentication adapter without production credentials | Planned |
| FR-AUTH-003 | Resolve the current user, active workspace memberships, and roles on every protected request | Planned |
| FR-AUTH-004 | Enforce workspace scope in service and repository queries, not only in the UI | Planned |
| FR-AUTH-005 | Allow users to select an active workspace when they belong to more than one | Planned |
| FR-AUTH-006 | Allow administrators to invite, deactivate, and change workspace roles with audit records | Planned |
| FR-AUTH-007 | Revoke access promptly when membership or user status becomes inactive | Planned |
| FR-AUTH-008 | Expose the current user and capability set to the web application | Planned |

### 3.2 Company identity and entity resolution

| ID | Requirement | Status |
| --- | --- | --- |
| FR-COMP-001 | Create a company research record from name, country, and optional website or identifier | Planned |
| FR-COMP-002 | Normalize names, domains, country codes, registration identifiers, and known aliases | Planned |
| FR-COMP-003 | Detect possible duplicates inside the same workspace before creating a new canonical company | Planned |
| FR-COMP-004 | Represent brands, legal entities, subsidiaries, parent companies, and former names separately | Planned |
| FR-COMP-005 | Present ambiguous entity candidates for human confirmation before facts are merged | Planned |
| FR-COMP-006 | Allow a reviewer to merge duplicate records without losing source, fact, profile, or audit history | Planned |
| FR-COMP-007 | Allow a reviewer to split incorrectly merged entities with explicit audit evidence | Planned |
| FR-COMP-008 | Store stable canonical identifiers independent of display name changes | Planned |
| FR-COMP-009 | Prevent cross-country same-name matches from being auto-merged without strong identifiers | Planned |
| FR-COMP-010 | Preserve the user-supplied input and entity-resolution decision history | Planned |

### 3.3 Research job lifecycle

| ID | Requirement | Status |
| --- | --- | --- |
| FR-RES-001 | Start a research job for a canonical company with a requested scope and locale | Planned |
| FR-RES-002 | Run long research asynchronously and return a durable job identifier immediately | Planned |
| FR-RES-003 | Expose step-level job progress and safe human-readable status | Planned |
| FR-RES-004 | Support initial research, targeted field research, and full profile refresh | Planned |
| FR-RES-005 | Prevent accidental duplicate active jobs for the same company and scope | Planned |
| FR-RES-006 | Make retry behavior idempotent and preserve previous successful artifacts | Planned |
| FR-RES-007 | Allow cancellation before publication without deleting completed source evidence | Planned |
| FR-RES-008 | Record provider, model, prompt version, parser version, and runtime metadata for each run | Planned |
| FR-RES-009 | Continue useful processing when one non-critical source or provider fails | Planned |
| FR-RES-010 | Never replace a published profile automatically after a refresh | Planned |

### 3.4 Source discovery

| ID | Requirement | Status |
| --- | --- | --- |
| FR-SRC-001 | Discover likely official website, registry, filing, product, news, and organization sources | Planned |
| FR-SRC-002 | Classify source type, owner, authority tier, language, date, and entity relevance | Planned |
| FR-SRC-003 | Prioritize official and primary sources while retaining useful secondary sources | Planned |
| FR-SRC-004 | Store search query, result rank, provider, timestamp, and selected/discarded decision | Planned |
| FR-SRC-005 | Detect duplicate URLs, canonical URLs, mirrored content, and content hashes | Planned |
| FR-SRC-006 | Allow researchers to add a public URL manually with a reason | Planned |
| FR-SRC-007 | Allow reviewers to block a domain or source for policy, quality, or entity-mismatch reasons | Planned |
| FR-SRC-008 | Display why a source was selected or rejected | Planned |
| FR-SRC-009 | Avoid treating search snippets as final evidence when the underlying page can be fetched | Planned |
| FR-SRC-010 | Respect source-specific legal, contractual, robots, and rate-limit policy | Planned |

### 3.5 Content acquisition and document processing

| ID | Requirement | Status |
| --- | --- | --- |
| FR-FETCH-001 | Fetch public HTTP content with timeouts, size limits, redirects, and content-type validation | Planned |
| FR-FETCH-002 | Parse HTML, metadata, JSON-LD, sitemap hints, and visible article text | Planned |
| FR-FETCH-003 | Process supported public PDF documents and preserve page references | Planned |
| FR-FETCH-004 | Use a browser renderer only when ordinary HTTP retrieval is insufficient and policy allows it | Planned |
| FR-FETCH-005 | Never bypass CAPTCHAs, authentication, access controls, or explicit anti-automation restrictions | Planned |
| FR-FETCH-006 | Store immutable content snapshots or hashes sufficient to reproduce evidence | Planned |
| FR-FETCH-007 | Record retrieval status, response metadata, parser version, and sanitized error | Planned |
| FR-FETCH-008 | Detect unsupported, oversized, encrypted, malformed, or suspicious files safely | Planned |
| FR-FETCH-009 | Apply malware scanning or equivalent production control before trusting downloaded files | Planned |
| FR-FETCH-010 | Prevent internal-network and metadata-service access through SSRF protections | Planned |
| FR-FETCH-011 | Preserve original language and character encoding | Planned |
| FR-FETCH-012 | Redact or minimize unnecessary personal data before AI processing where practical | Planned |

### 3.6 AI extraction and translation

| ID | Requirement | Status |
| --- | --- | --- |
| FR-AI-001 | Extract candidate facts through a versioned structured-output schema | Planned |
| FR-AI-002 | Require every extracted candidate to reference one or more evidence spans | Planned |
| FR-AI-003 | Return `unknown` instead of fabricating a value when evidence is insufficient | Planned |
| FR-AI-004 | Distinguish direct facts, inference, estimate, and model-generated summary text | Planned |
| FR-AI-005 | Preserve original evidence text and store translation separately | Planned |
| FR-AI-006 | Record AI provider, model identifier, prompt template version, token/cost metadata, and latency | Planned |
| FR-AI-007 | Validate model output against schema and reject malformed or ungrounded output | Planned |
| FR-AI-008 | Support deterministic mock responses for tests and offline development | Planned |
| FR-AI-009 | Apply configurable per-job budget, timeout, and retry limits | Planned |
| FR-AI-010 | Prevent prompt injection in fetched content from changing system policy or tool permissions | Planned |
| FR-AI-011 | Keep provider credentials server-side and out of browser bundles, logs, and stored prompts | Planned |
| FR-AI-012 | Generate a concise profile summary only from accepted profile fields and evidence | Planned |

### 3.7 Fact verification and conflict resolution

| ID | Requirement | Status |
| --- | --- | --- |
| FR-FACT-001 | Normalize candidate values by field type before comparison | Planned |
| FR-FACT-002 | Calculate explainable confidence from authority, recency, entity match, evidence quality, and source agreement | Planned |
| FR-FACT-003 | Detect materially different values for the same field and create a conflict record | Planned |
| FR-FACT-004 | Preserve all credible conflicting candidates instead of silently overwriting them | Planned |
| FR-FACT-005 | Permit field-specific source ranking and recency rules | Planned |
| FR-FACT-006 | Require human review for configured high-impact fields and unresolved conflicts | Planned |
| FR-FACT-007 | Allow reviewers to accept, reject, edit, or mark a field unknown with a reason | Planned |
| FR-FACT-008 | Treat reviewer edits as facts with explicit human-origin evidence and audit metadata | Planned |
| FR-FACT-009 | Mark time-sensitive fields stale based on configurable policies | Planned |
| FR-FACT-010 | Recalculate confidence when evidence or source policy changes without deleting history | Planned |
| FR-FACT-011 | Display confidence explanation rather than only a numeric score | Planned |
| FR-FACT-012 | Prevent an inferred or estimated value from being displayed as a direct verified statement | Planned |

### 3.8 Company profile drafting and publication

| ID | Requirement | Status |
| --- | --- | --- |
| FR-PROF-001 | Build a draft profile from accepted and reviewable facts according to a versioned schema | Planned |
| FR-PROF-002 | Organize fields into identity, overview, products, size, markets, leadership, innovation, and recent activity sections | Planned |
| FR-PROF-003 | Show source, evidence, confidence, status, and last observed time for each field | Planned |
| FR-PROF-004 | Require reviewer approval before publishing a new profile version | Planned |
| FR-PROF-005 | Publish immutable profile versions and keep exactly one active published version per company | Planned |
| FR-PROF-006 | Allow a reviewer to withdraw or supersede a published version without destroying history | Planned |
| FR-PROF-007 | Preserve field-level changes between versions | Planned |
| FR-PROF-008 | Generate a meeting brief from the published profile without introducing new unsupported facts | Planned |
| FR-PROF-009 | Represent missing information explicitly instead of hiding empty sections | Planned |
| FR-PROF-010 | Allow internal notes that are clearly separated from public-source facts | Planned |
| FR-PROF-011 | Support Vietnamese and English presentation while preserving original evidence language | Planned |
| FR-PROF-012 | Prevent automatic publication solely because a job completed successfully | Planned |

### 3.9 Review workflow

| ID | Requirement | Status |
| --- | --- | --- |
| FR-REV-001 | Create review tasks for ambiguous identity, high-impact facts, conflicts, and publication requests | Planned |
| FR-REV-002 | Assign, claim, release, complete, and reopen review tasks | Planned |
| FR-REV-003 | Prevent concurrent reviewers from silently overwriting decisions | Planned |
| FR-REV-004 | Require a reason for rejecting credible evidence or overriding an automated recommendation | Planned |
| FR-REV-005 | Show the source snapshot and exact evidence context during review | Planned |
| FR-REV-006 | Record every decision, previous value, actor, and timestamp in an immutable audit trail | Planned |
| FR-REV-007 | Allow reviewers to request targeted re-research for specific fields | Planned |
| FR-REV-008 | Allow administrators to configure fields that always require human approval | Planned |

### 3.10 Search, library, history, and export

| ID | Requirement | Status |
| --- | --- | --- |
| FR-LIB-001 | Search companies by canonical name, alias, domain, identifier, industry, country, market, and product keyword | Planned |
| FR-LIB-002 | Filter by profile status, freshness, confidence, conflict count, and last research date | Planned |
| FR-LIB-003 | Show draft, published, stale, and attention-required indicators | Planned |
| FR-LIB-004 | Display profile version history and field-level diffs | Planned |
| FR-LIB-005 | Export a published profile to PDF and structured JSON | Planned |
| FR-LIB-006 | Include generated-at time, profile version, and source appendix in exports | Planned |
| FR-LIB-007 | Restrict export access according to workspace role and audit each export | Planned |
| FR-LIB-008 | Allow a user to bookmark or tag a company for internal organization | Planned |
| FR-LIB-009 | Refresh a profile without losing old published versions | Planned |
| FR-LIB-010 | Provide a concise meeting-preparation view optimized for quick reading | Planned |

### 3.11 Administration, policies, and audit

| ID | Requirement | Status |
| --- | --- | --- |
| FR-ADM-001 | Manage workspace users, roles, active status, and invitations | Planned |
| FR-ADM-002 | Configure approved source domains, blocked domains, authority tiers, and field-specific rules | Planned |
| FR-ADM-003 | Configure freshness thresholds, mandatory-review fields, and confidence thresholds | Planned |
| FR-ADM-004 | Configure provider identifiers and non-secret behavior; secrets remain in secret management | Planned |
| FR-ADM-005 | View research job failures, provider usage, queue depth, and cost summaries | Planned |
| FR-ADM-006 | View immutable audit records for sensitive actions | Planned |
| FR-ADM-007 | Retry or cancel eligible failed jobs without duplicating successful work | Planned |
| FR-ADM-008 | Apply retention and deletion policy with legal holds where configured | Planned |

## 4. Business rules

| ID | Rule |
| --- | --- |
| BR-TENANT-001 | Every workspace-owned query and mutation must include the authorized workspace scope. |
| BR-TENANT-002 | Platform role alone does not grant workspace content access. |
| BR-ENTITY-001 | A company record represents one canonical entity; brands, subsidiaries, branches, and historical legal entities require explicit relationships. |
| BR-ENTITY-002 | Name similarity alone is insufficient for automatic merge. Strong identifiers include verified domain, registration identifier, official address, or official relationship evidence. |
| BR-SOURCE-001 | A URL is not automatically trusted because it appears in search results. |
| BR-SOURCE-002 | Search snippets may guide discovery but are not final evidence when the source can be fetched. |
| BR-SOURCE-003 | The system must not bypass authentication, CAPTCHA, robots restrictions, technical access controls, or provider terms. |
| BR-SOURCE-004 | Source authority is evaluated per field, not as one universal website score. |
| BR-EVIDENCE-001 | Every published fact requires accepted evidence or an explicit documented human-origin exception. |
| BR-EVIDENCE-002 | Evidence stores original text or structural reference, source snapshot, retrieval time, and location within the source. |
| BR-EVIDENCE-003 | Translation is derived data and never replaces original evidence. |
| BR-FACT-001 | Unsupported values are `unknown`; they are never guessed to make a profile look complete. |
| BR-FACT-002 | Conflicting credible candidates remain visible until resolved. |
| BR-FACT-003 | Estimated and inferred values must remain labeled as such in profile and export surfaces. |
| BR-FACT-004 | Reviewer edits do not erase prior candidates, evidence, or decisions. |
| BR-CONF-001 | Confidence is advisory and explainable; it is not a legal guarantee of truth. |
| BR-PROFILE-001 | A completed research job produces a draft, not an automatically published profile. |
| BR-PROFILE-002 | Published versions are immutable. Corrections create a new version or explicit withdrawal. |
| BR-PROFILE-003 | A profile summary may only use accepted profile fields and their evidence. |
| BR-JOB-001 | Retrying a job step must be idempotent and must not duplicate immutable source snapshots or publication records. |
| BR-JOB-002 | Failure of a secondary source must not discard successful evidence from other sources. |
| BR-AI-001 | Fetched page instructions are untrusted content and cannot change system prompts, permissions, or tool policy. |
| BR-AI-002 | AI output must pass schema, evidence, and entity-match validation before becoming a candidate fact. |
| BR-PRIVACY-001 | Collect only public information needed for the company profile; avoid unnecessary personal data. |
| BR-PRIVACY-002 | Sensitive personal data must not be inferred or enriched without an approved use case and legal basis. |
| BR-AUDIT-001 | Publication, conflict resolution, manual overrides, merges, splits, exports, and policy changes require audit records. |

## 5. High-impact fields

The default mandatory-review set is:

- legal name;
- registration identifier;
- incorporation date;
- headquarters country;
- parent company and ownership relationship;
- leadership names and roles;
- employee count when displayed as an exact number;
- revenue, funding, valuation, and financial figures;
- named customers or partners;
- certifications, licenses, regulatory status, and sanctions-related claims;
- any statement that could materially affect eligibility or reputation.

Workspace policy may add fields but may not disable evidence requirements.

## 6. Core acceptance criteria

1. A researcher can create a company using name, country, and website, then receive a durable asynchronous research job.
2. The job discovers and records source candidates without publishing any profile automatically.
3. The system identifies an official website and stores an immutable retrieval snapshot or reproducible content hash.
4. Structured extraction returns candidate facts with evidence references; a candidate without evidence is rejected or marked unknown.
5. Similar companies with the same name in different countries are presented as separate identity candidates.
6. Credible contradictory values create a visible conflict instead of one value silently replacing another.
7. A reviewer can inspect the exact source context, accept one candidate, reject another, and record a reason.
8. Publishing creates an immutable version and keeps prior versions accessible.
9. A refresh creates a new draft and cannot overwrite the current published profile without review.
10. The company library can find a company by name, alias, domain, country, or identifier.
11. PDF and JSON exports identify the profile version, generation time, and source appendix.
12. Unauthorized users cannot read or mutate another workspace's companies, sources, jobs, profiles, or exports.
13. A failed AI or fetch provider leaves prior published data intact and exposes a safe retry path.
14. AI provider keys, source credentials, and storage secrets are never returned to the browser or written to logs.
15. The web interface works at desktop and mobile widths and exposes loading, empty, error, retry, conflict, and stale states.
16. Vietnamese is the default UI language, English is supported, and original evidence language is preserved.
17. Every sensitive action produces an audit record containing actor, workspace, resource, action, time, and safe change metadata.
18. Documentation and OpenAPI drift checks fail CI when canonical contracts are not updated.

## 7. Non-functional requirements

### Security

- OWASP-aligned request validation, headers, rate limiting, session security, SSRF protection, and output encoding.
- Least-privilege worker and provider credentials.
- No secrets in browser-visible environment variables.
- File size, content type, decompression, and malware controls.
- Audit records for sensitive operations.

### Reliability

- Durable research jobs and step state.
- Idempotent retries.
- Immutable source snapshots and profile versions.
- Database transactions for coupled writes.
- Provider failures isolated from previously published data.

### Performance

- Ordinary list reads should be indexed and paginated.
- Source retrieval, document parsing, and AI work must not hold API request threads open.
- Large source bodies are stored in object storage, not repeated in list responses.
- Search and profile pages avoid N+1 evidence queries.

### Accessibility

- Semantic controls and headings.
- Keyboard operation.
- Visible focus.
- Sufficient contrast.
- Screen-reader labels for status and confidence.
- Reduced-motion support.

### Privacy

- Purpose limitation and data minimization.
- Retention and deletion rules for raw source snapshots and personal data.
- Workspace-configurable legal holds.
- No silent enrichment of private contact information.

### Observability

- Structured logs with request, job, workspace, company, and provider identifiers.
- Metrics for job duration, failure, retry, queue depth, provider latency, source fetch result, AI cost, publication, and review backlog.
- Health and readiness endpoints.
- Trace propagation across API and worker.

### Localization

- UI copy in Vietnamese and English.
- Locale-neutral storage for structured values.
- Original evidence language retained.
- Translation clearly labeled and independently reproducible.

## 8. Error behavior

- Validation errors return `422 VALIDATION_ERROR` with field paths.
- Missing authentication returns `401`.
- Insufficient role or workspace scope returns `403` without revealing foreign-resource existence.
- Missing resource returns `404`.
- Duplicate, state, lock, or idempotency conflict returns `409`.
- Rate limits return `429` with retry guidance.
- Provider or dependency unavailability returns `502` or `503` according to whether the failure is upstream or platform readiness.
- Background failures are recorded on job steps and do not use generic successful status.
- UI displays localized safe error messages and preserves recoverable form input.
- Raw provider payloads, stack traces, secrets, and internal network details are never exposed in standard errors.

## 9. User-experience requirements

### Company creation

- Show duplicate suggestions before final creation.
- Explain which inputs improve entity resolution.
- Allow starting with incomplete data while clearly labeling ambiguity.

### Job progress

- Show durable steps such as resolving identity, discovering sources, fetching, parsing, extracting, verifying, and preparing review.
- Show partial success rather than only a spinning indicator.
- Provide cancel and safe retry actions where valid.

### Profile review

- Place value, status, confidence explanation, source, evidence excerpt, and reviewer controls in one workflow.
- Highlight conflict and stale states without relying only on color.
- Require reasons for overrides and rejections.

### Published profile

- Provide a one-minute summary and detailed expandable sections.
- Make evidence reachable from every field.
- Show version, last reviewed date, and freshness warnings.
- Clearly separate internal notes from source-backed facts.

## 10. MVP boundary

The first competition-ready MVP must include:

- authenticated internal users;
- one workspace baseline with multi-workspace-safe schema;
- company creation and duplicate detection;
- asynchronous research jobs;
- official website and search-based source discovery;
- HTML and PDF acquisition;
- Gemini structured extraction with evidence;
- source authority and confidence explanation;
- conflict detection;
- reviewer workflow;
- published version history;
- company library search;
- PDF or JSON export;
- audit, tests, CI, and deployable demo environment.

Advanced enrichment, continuous monitoring, licensed databases, automated fit scoring, and complex analytics belong after the trusted-profile foundation.

## 11. Requirements synchronization checklist

For every code change affecting behavior:

- [ ] Relevant requirement IDs are identified in the task or pull request.
- [ ] Status is changed only after implementation and tests are verified.
- [ ] Business rules match the actual service and database guards.
- [ ] Acceptance criteria have automated or documented manual evidence.
- [ ] New error codes and UI states are documented.
- [ ] New high-impact fields are added to mandatory-review policy.
- [ ] Partial implementation is marked Partial or In progress, not Implemented.
- [ ] Known defects are recorded in `Roadmap.md` defect ledger.
- [ ] Last verified date and commit are updated when applicable.

## Verified implementation addendum — TASK-CRAWL-001 (2026-08-08)

- AI is an optional semantic processor, not a prerequisite for acquisition.
- With `AI_PROVIDER=disabled`, the worker still runs source discovery, source selection, fetch, parse, and deterministic fact extraction.
- Provider timeout/unavailability preserves prior acquisition artifacts and results in a limited `partial_success` job rather than fabricated data.
- Retry delivery reuses normalized source/snapshot/document/fact records and records fetch attempts for auditability.
- Acceptance behavior is covered by the task-scoped regression suite; repository-wide validation limitations remain recorded in the root Roadmap defect ledger.

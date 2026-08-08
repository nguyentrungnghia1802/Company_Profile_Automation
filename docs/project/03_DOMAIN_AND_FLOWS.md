# Domain and Flows

Status: planned domain baseline. State transitions in code and database constraints become executable truth after implementation.

## 1. Domain model

```text
Workspace
  |--< WorkspaceMember >-- User
  |--< Company
  |      |--< CompanyAlias
  |      |--< CompanyIdentifier
  |      |--< CompanyRelationship >-- Company
  |      |--< ResearchJob --< ResearchJobStep
  |      |      |--< ResearchQuery --< SearchResult
  |      |      |--< Source --< SourceFetchAttempt
  |      |      |             \--< SourceSnapshot --< DocumentBlock
  |      |      |--< AiRun
  |      |      |--< FactCandidate --< Evidence >-- DocumentBlock
  |      |      |--< Conflict
  |      |      \--< ReviewTask
  |      |--< ProfileDraft
  |      \--< ProfileVersion --< ProfileFieldValue --< ProfileFieldEvidence
  |--< PolicySet
  |--< ExportJob
  \--< AuditLog
```

## 2. Entity responsibilities

| Entity | Responsibility |
| --- | --- |
| Workspace | Tenant boundary, policy scope, locale, retention, and membership |
| User | Authenticated platform identity |
| WorkspaceMember | Role and active workspace authorization |
| Company | Canonical researched legal/commercial entity |
| CompanyAlias | Brand, former name, transliteration, abbreviation, local-language name |
| CompanyIdentifier | Domain, registration number, tax ID, external database ID, official social ID |
| CompanyRelationship | Parent, subsidiary, brand-of, acquired-by, predecessor, successor, branch |
| ResearchJob | Durable request for initial research, refresh, or targeted field research |
| ResearchJobStep | Idempotent unit of background execution with attempts and lease |
| ResearchQuery | Generated or user-supplied discovery query |
| SearchResult | Provider result and selection decision |
| Source | Canonical public information location and source classification |
| SourceFetchAttempt | One network retrieval attempt and safe result metadata |
| SourceSnapshot | Immutable captured content metadata and object reference |
| DocumentBlock | Stable parsed text/structure unit addressable by evidence |
| AiRun | One provider operation with schema, prompt, model, cost, and result status |
| FactCandidate | Proposed normalized value for one profile field |
| Evidence | Link from candidate to source block, excerpt, and support type |
| Conflict | Group of materially different candidates for the same field/context |
| ReviewTask | Human decision workflow for identity, fact, conflict, or publication |
| ProfileDraft | Mutable assembly of selected candidates before publication |
| ProfileVersion | Immutable published or withdrawn company profile version |
| ProfileFieldValue | Immutable field value and status inside a profile version |
| ProfileFieldEvidence | Immutable evidence references for a published field |
| PolicySet | Versioned source, confidence, freshness, review, and retention rules |
| ExportJob | Durable generation of PDF or structured export |
| AuditLog | Immutable record of sensitive actions and state changes |

## 3. Canonical company identity

A `Company` represents one real-world entity. It must not silently combine:

- different legal entities using one brand;
- a parent and subsidiary;
- a local branch and global headquarters;
- a former company and its successor;
- companies with similar names in different countries.

### 3.1 Identity signals

Strong signals:

- official domain ownership;
- government registration identifier;
- official address;
- official filing;
- verified parent/subsidiary relationship;
- consistent official contact domain.

Weak signals:

- similar name;
- similar logo;
- shared industry;
- search result proximity;
- an unverified directory entry.

### 3.2 Company state

| State | Meaning |
| --- | --- |
| `draft` | Created but identity not confirmed |
| `active` | Canonical entity accepted for research |
| `ambiguous` | Identity requires review |
| `merged` | Redirects to another canonical company |
| `archived` | Retained but no longer active for normal use |

Allowed transitions:

```text
new -> draft
 draft -> active
 draft -> ambiguous
 ambiguous -> active
 active -> ambiguous
 draft/ambiguous/active -> merged
 active -> archived
 archived -> active
```

Merge and split operations require reviewer capability and audit records.

## 4. Research job state machine

| State | Meaning |
| --- | --- |
| `queued` | Durable job exists and awaits claim |
| `running` | At least one step is executing |
| `waiting_review` | Automated work completed and human decisions remain |
| `partial_success` | Useful results exist, but one or more non-critical steps failed |
| `completed` | Planned automated scope completed and draft is available |
| `failed` | Critical failure prevents usable result |
| `cancel_requested` | Cancellation requested; running step should stop at safe boundary |
| `cancelled` | No further steps will execute |

Transitions:

```text
queued -> running
running -> waiting_review | partial_success | completed | failed | cancel_requested
cancel_requested -> cancelled | partial_success
partial_success -> queued (explicit retry) | waiting_review | completed
failed -> queued (explicit retry)
waiting_review -> completed after required review decisions
```

A job completing does not publish a profile.

## 5. Research step state machine

| State | Meaning |
| --- | --- |
| `pending` | Ready when dependencies are satisfied |
| `claimed` | Worker owns a time-limited lease |
| `running` | Work is executing |
| `succeeded` | Durable result committed |
| `retry_wait` | Retryable failure with next attempt time |
| `failed` | Attempt budget exhausted or non-retryable failure |
| `skipped` | Not needed due to policy, prior artifact, or cancellation |
| `cancelled` | Stopped by user/system cancellation |

The transition to `succeeded` and the resulting domain writes must be atomic or safely idempotent.

## 6. Source lifecycle

### 6.1 Source state

| State | Meaning |
| --- | --- |
| `candidate` | Discovered but not yet selected |
| `selected` | Approved for retrieval |
| `fetched` | At least one valid snapshot exists |
| `parse_failed` | Content fetched but not successfully parsed |
| `blocked` | Disallowed by policy, terms, robots, domain block, or safety control |
| `unreachable` | Retrieval failed within current attempt policy |
| `rejected` | Irrelevant, duplicate, low quality, or wrong entity |
| `retired` | No longer selected for current research but history retained |

### 6.2 Source selection reasons

Examples:

- official domain;
- legal registry;
- annual report;
- recent product page;
- government reference;
- reputable news coverage;
- duplicate mirror;
- wrong company;
- stale source;
- prohibited access;
- personal-data-heavy page not needed for scope.

## 7. Source snapshot lifecycle

A snapshot is immutable after successful creation.

```text
fetch attempt -> validate response -> store object -> persist metadata -> complete
```

If object upload succeeds but metadata commit fails, orphan reconciliation must remove or attach the object later. If metadata commits before object durability is confirmed, the snapshot cannot be marked complete.

Snapshot metadata includes:

- normalized and final URL;
- source ID;
- retrieved time;
- HTTP status and content type;
- byte size;
- content hash;
- parser version;
- language;
- published/modified date when available;
- object key;
- compliance decision;
- safe retrieval diagnostics.

## 8. Fact candidate lifecycle

| State | Meaning |
| --- | --- |
| `candidate` | Newly extracted or manually proposed |
| `validated` | Schema, evidence, and entity checks passed |
| `recommended` | Automated policy recommends acceptance |
| `accepted` | Reviewer or permitted automated policy selected the candidate |
| `rejected` | Candidate rejected with reason |
| `superseded` | A later accepted candidate replaces it for current draft |
| `stale` | Observation exceeded freshness threshold |

High-impact candidates may reach `recommended` but cannot become `accepted` without review.

## 9. Evidence model

Evidence support types:

| Type | Meaning |
| --- | --- |
| `direct` | Source states the value directly |
| `structured` | Value comes from registry field, JSON-LD, table, or document structure |
| `corroborating` | Supports another direct source |
| `contextual` | Provides useful context but not sufficient alone |
| `contradicting` | Explicitly disagrees with the candidate |
| `human_note` | Reviewer-supplied internal basis; never presented as public-source evidence |

An evidence record stores:

- candidate ID;
- source snapshot and document block;
- original excerpt;
- optional translated excerpt;
- block location and offsets;
- support type;
- extraction method;
- evidence quality score;
- reviewer status.

## 10. Conflict lifecycle

A conflict groups candidates with the same field key and comparable context.

| State | Meaning |
| --- | --- |
| `open` | Material disagreement exists |
| `needs_research` | Existing evidence is insufficient to decide |
| `resolved` | Reviewer selected an outcome with reason |
| `accepted_multiple` | Values are both valid under different dates/scopes |
| `dismissed` | Difference is non-material or caused by normalization |
| `reopened` | New evidence invalidated a prior resolution |

Resolution outcomes:

- select one candidate;
- select a range;
- preserve multiple time-scoped values;
- mark unknown;
- request targeted research;
- correct entity relationship;
- reject low-quality sources.

## 11. Review task state machine

| State | Meaning |
| --- | --- |
| `open` | Unassigned or available |
| `claimed` | Assigned to one reviewer |
| `in_review` | Reviewer is actively evaluating |
| `changes_requested` | Researcher or worker must perform follow-up |
| `completed` | Required decision recorded |
| `cancelled` | Task no longer relevant |
| `reopened` | New information requires another decision |

Optimistic locking prevents two reviewers from overwriting the same task version.

## 12. Profile state machines

### 12.1 Draft

| State | Meaning |
| --- | --- |
| `building` | Automated or manual assembly in progress |
| `ready_for_review` | Required automated steps completed |
| `changes_requested` | Reviewer requested corrections or more research |
| `approved` | Ready for publication transaction |
| `superseded` | Replaced by a newer draft |
| `discarded` | Intentionally not published |

### 12.2 Published version

| State | Meaning |
| --- | --- |
| `published` | Current or historical accepted version |
| `withdrawn` | Retained but explicitly not recommended for use |
| `superseded` | Replaced by a newer published version |

Exactly one non-withdrawn version may be current per company.

## 13. End-to-end initial research flow

1. Researcher submits name, country, website, identifiers, and purpose.
2. API normalizes inputs and searches workspace duplicate candidates.
3. User selects an existing company or creates a new draft company.
4. API creates an idempotent `ResearchJob` and initial steps in one transaction.
5. Worker resolves entity using supplied and discovered signals.
6. If ambiguous, the job creates an identity review task and blocks dependent fact merge.
7. Worker generates multilingual discovery queries.
8. Search results are stored and ranked.
9. Policy filters blocked, duplicate, irrelevant, or unsafe sources.
10. Selected sources are fetched and snapshotted.
11. Parsers produce document blocks.
12. AI and deterministic extractors create fact candidates with evidence references.
13. Validation rejects malformed, unsupported, or wrong-entity candidates.
14. Confidence and freshness policies run.
15. Material disagreements create conflicts.
16. Required review tasks are created.
17. A profile draft is assembled from accepted and reviewable candidates.
18. Job becomes `waiting_review`, `partial_success`, or `completed` according to policy.
19. Reviewer resolves mandatory tasks and approves the draft.
20. Publication transaction creates an immutable profile version.

## 14. Entity ambiguity flow

1. Resolver finds multiple plausible entities.
2. It records each candidate with supporting signals.
3. No facts are merged into the canonical company yet.
4. Reviewer compares legal name, country, domain, identifier, address, and relationships.
5. Reviewer selects, creates, merges, or separates the entity.
6. Dependent job steps resume using the chosen canonical company.
7. Every discarded candidate and reason remains auditable.

## 15. Official website discovery flow

1. Normalize user-supplied domain when present.
2. Generate queries using name, country, product keywords, and legal identifiers.
3. Rank results by exact domain, official metadata, contact-domain consistency, and entity signals.
4. Fetch top allowed candidates.
5. Inspect title, organization schema, contact information, and legal footer.
6. Select official domain automatically only above policy threshold and when no material ambiguity exists.
7. Otherwise create an identity/source review task.

## 16. Source acquisition flow

1. Check source policy and robots decision.
2. Resolve DNS and validate destination IP.
3. Attempt direct HTTP retrieval.
4. Validate redirects and final URL.
5. Validate size, MIME, and decompression.
6. Store raw content in quarantine or temporary storage.
7. Scan and parse.
8. Commit immutable snapshot metadata and final object.
9. If direct retrieval is insufficient and policy allows, schedule browser rendering.
10. Record all attempts and sanitized failures.

## 17. AI extraction flow

1. Select relevant blocks for a schema section.
2. Build a provider-neutral request containing company identity and block IDs.
3. Apply prompt-injection defenses and system policy.
4. Call Gemini adapter within budget.
5. Validate structured response.
6. Verify all evidence references exist.
7. Run deterministic field validators and normalizers.
8. Create candidate and evidence records in one transaction.
9. Record AI usage and outcome.
10. Do not accept or publish candidates in the provider adapter.

## 18. Confidence and conflict flow

For each field:

1. normalize values, units, dates, names, and ranges;
2. group comparable candidates;
3. calculate authority, recency, entity, evidence, extraction, and agreement components;
4. identify equivalent values;
5. identify material differences;
6. create or update conflict;
7. choose automated recommendation when policy permits;
8. create review task for mandatory or uncertain cases;
9. persist explanation and policy version.

## 19. Manual edit flow

1. Reviewer selects a field and proposes a corrected value.
2. System requires a reason.
3. Reviewer links public evidence, internal note, or marks no public evidence.
4. System creates a new human-origin candidate; it never mutates prior candidates.
5. Normalization and conflict detection run.
6. Reviewer accepts the candidate through the normal decision workflow.
7. Publication still creates a new profile version.

## 20. Publication flow

1. Reviewer opens a `ready_for_review` draft.
2. API verifies role, draft version, mandatory tasks, open conflicts, evidence coverage, and freshness policy.
3. Reviewer confirms publication notes.
4. Transaction locks company and current version.
5. Existing current version becomes `superseded` if applicable.
6. New immutable profile version and field/evidence rows are inserted.
7. Draft becomes `approved` or `superseded` according to implementation policy.
8. Audit event is committed.
9. Summary/export generation runs after commit and may retry independently.

If any integrity check fails, no version changes.

## 21. Refresh flow

1. User selects full or targeted refresh.
2. System reuses canonical company and previous source history.
3. It schedules stale or requested fields and sources first.
4. Existing snapshots may be reused when still valid; new retrieval creates new snapshots.
5. New candidates never delete old candidates.
6. Differences against current published version are shown in the new draft.
7. Current published profile remains active until reviewed publication.

## 22. Foreign-language flow

1. Detect document language.
2. Preserve raw and parsed original text.
3. Extract direct facts from original blocks where possible.
4. Create translated evidence as derived data with model and version metadata.
5. Review UI shows original and translated text together.
6. Published value uses locale-neutral structured form and localized display.
7. Translation cannot be the only provenance when the original snapshot is available.

## 23. Export flow

1. Authorized user requests export for a published version.
2. API creates idempotent export job.
3. Worker loads immutable profile fields and evidence appendix.
4. PDF/JSON is generated with version and generated-at metadata.
5. Object is stored privately.
6. User downloads through authorized endpoint or short-lived signed URL.
7. Export action is audited.

## 24. Merge flow

1. Reviewer selects source and target companies.
2. System previews aliases, identifiers, jobs, sources, candidates, drafts, versions, and conflicts.
3. Reviewer resolves identifier collisions.
4. Transaction locks both companies.
5. Child records move or reference target according to preservation rules.
6. Source company becomes `merged` and redirects to target.
7. Published histories remain attributable to their original entity state.
8. Audit record includes preview hash and decision reason.

A merge is never a simple hard delete.

## 25. Failure flows

- Wrong entity detected after extraction: quarantine affected candidates, reopen identity review, do not publish.
- Source content changed: create new snapshot; old evidence remains reproducible.
- Provider returns unsupported fact: reject candidate and record validation reason.
- Reviewer publishes while refresh runs: publication locks version state; refresh continues into a separate draft.
- Cancellation during fetch: stop after safe boundary; completed snapshots remain.
- Object missing for snapshot: mark integrity incident and prevent evidence publication until repaired.
- Retention removes raw body: retain permitted metadata, hash, and published evidence according to policy; clearly show reduced reproducibility.

## 26. Domain invariants

- One canonical company belongs to exactly one workspace.
- Merged company records cannot accept new research jobs directly.
- One active job per protected company/scope key where configured.
- A snapshot is immutable.
- A document block belongs to one snapshot.
- Evidence references an existing candidate and document block.
- Accepted high-impact candidate has reviewer decision.
- Published profile field references accepted evidence or an explicit permitted human-origin exception.
- Published profile version is immutable.
- Exactly one current published version per company.
- Cross-workspace relations are prohibited.
- Reviewer decisions and audit logs are append-only.

## 27. Domain synchronization checklist

- [ ] Entity relationships match database foreign keys and service logic.
- [ ] State values and transitions match enums, validators, and tests.
- [ ] Retry, cancel, and partial-success behavior match worker implementation.
- [ ] Evidence location model matches parser output.
- [ ] Conflict materiality and resolution match policy code.
- [ ] Publication transaction and immutability are verified.
- [ ] Failure paths preserve prior published data.
- [ ] New flows are represented in API and test documentation.

## Verified implementation addendum — TASK-CRAWL-001 (2026-08-08)

### AI-independent initial research flow

```text
ResearchJob(running)
  → entity_resolution
  → source_discovery
  → source_selection
  → source_fetch
  → document_parse
  → deterministic_extraction
  → ai_extraction (optional)
  → fact/conflict/review
  → finalize
  → completed | partial_success
```

`partial_success` is used when acquisition succeeds but AI is disabled, times out, or otherwise cannot complete. Source fetch failures and parser failures are retained as warnings while successful artifacts continue through later steps. A critical entity/workspace integrity failure remains a failed task and does not proceed to dependent steps.

## Verified implementation addendum — TASK-CRAWL-002 (2026-08-08)

The discovery portion of the research flow is deterministic and AI-independent:

1. accept official/verified/manual URLs and already-provided sitemap/internal links;
2. query configured SearchProvider metadata when requested;
3. call each configured trusted-source adapter and retain its typed outcome;
4. reuse non-rejected source history within the same workspace/company;
5. canonicalize URLs and merge all discovery provenance;
6. apply SSRF and entity-match policy;
7. persist selected or rejected `Source` metadata with the reason.

The current task intentionally consumes supplied sitemap/internal links; network link expansion remains outside this task. Secondary providers cannot replace government/official authority for legal or tax fields because authority is stored and consumed per field.

### 15.1 Verified bounded discovery behavior — TASK-CRAWL-003

When a website is supplied, the worker first normalizes its comparison domain and checks `robots.txt`. A missing robots file is recorded as `ROBOTS_NOT_PUBLISHED`; a disallow or unavailable policy prevents automated page/sitemap fetching. Allowed discovery fetches the homepage, follows only same-domain HTTP/HTTPS links within configured depth/page budgets, reads a bounded number of sitemap documents, and records canonical URL/page-group/relevance metadata. Login, privacy, cart, account, and administrative paths are rejected by deterministic policy.

Search queries are generated from canonical name, aliases, country, domain, registration identifiers, and requested section in both Vietnamese and English where applicable. Each provider result is an auditable discovery record; a same-name result without strong identity evidence is review-only and cannot be automatically selected.

### 15.2 Verified bounded crawl, parse, and deterministic extraction — TASK-CRAWL-004

After source selection, `CrawlCoordinator` processes seed URLs and same-domain links within explicit depth, domain-page, and job-page budgets. `WebFetcher` performs direct HTTP first and validates HTTP(S), DNS/IP, every redirect, timeout, response/decompression size, MIME, retry, rate, and per-domain concurrency boundaries. Browser rendering is a bounded fallback only for JS-like or 404 pages when enabled and policy-allowed; it never bypasses authentication, CAPTCHA, anti-bot controls, robots decisions, or SSRF checks.

HTML produces stable title, metadata/OpenGraph, JSON-LD, heading, paragraph, list, table, link, and section blocks. JSON/API blocks preserve JSON field paths and provider provenance. PDF blocks retain page numbers and stable `p<page>_b<block>` evidence keys. The deterministic extractor emits only direct structured or strongly labelled identity facts and attaches each candidate/evidence row to its source block; uncertain semantic meaning remains unknown.

### 15.3 Verified AI-degraded review flow — TASK-CRAWL-005 (2026-08-09)

```text
entity resolution → discovery/selection → fetch → parse
  → deterministic facts/evidence → optional AI
  → conflicts + AI-independent review tasks → finalize
```

AI disabled, a missing Gemini key, a timeout, or an unavailable provider marks only the optional semantic branch as skipped/unavailable. Acquisition artifacts and deterministic evidence continue to finalization. Review tasks are created for ambiguous entity matches, provider verification, strong-identifier/deterministic conflicts, and missing mandatory high-impact fields; repeated worker delivery reuses the same task. If no source is usable, the job ends as a clear `partial_success` with zero fabricated source, snapshot, block, or fact rows.

# Database

Status: planned schema baseline.

## 1. Source of truth

After implementation, ordered Alembic migrations are the executable schema source of truth. This document is the human-readable map.

Rules:

- Never rewrite a migration that may have been applied.
- Add forward migrations with explicit downgrade behavior when safe.
- Use expand, backfill, validate, and contract phases for non-trivial production changes.
- Keep ORM models, repositories, fixtures, tests, OpenAPI contracts, and this document synchronized.
- Database constraints protect integrity even when application validation fails.

## 2. PostgreSQL extensions

Planned optional extensions:

- `pg_trgm` for fuzzy company and alias search;
- `unaccent` for normalized search where appropriate;
- `vector` only when semantic search is implemented and justified;
- `citext` may be used for normalized case-insensitive identity fields if migration portability is accepted.

Do not enable extensions without a migration and deployment check.

## 3. Logical ERD

```text
users 1---* workspace_members *---1 workspaces
                                      |
                                      |---* companies
                                      |      |---* company_aliases
                                      |      |---* company_identifiers
                                      |      |---* company_relationships
                                      |      |---* research_jobs ---* research_job_steps
                                      |      |          |---* research_queries ---* search_results
                                      |      |          |---* ai_runs
                                      |      |          \---* review_tasks
                                      |      |---* sources ---* source_fetch_attempts
                                      |      |               \---* source_snapshots ---* document_blocks
                                      |      |---* fact_candidates ---* evidences
                                      |      |---* conflicts ---* conflict_candidates
                                      |      |---* profile_drafts ---* draft_field_selections
                                      |      \---* profile_versions ---* profile_field_values ---* profile_field_evidences
                                      |---* policy_sets
                                      |---* export_jobs
                                      |---* idempotency_records
                                      \---* audit_logs
```

## 4. Identity and tenancy tables

### 4.1 `users`

Purpose: local application identity linked to external auth subject.

Important columns:

- `id UUID PK`;
- `auth_provider TEXT`;
- `auth_subject TEXT`;
- `email TEXT NULL`;
- `display_name TEXT`;
- `preferred_locale TEXT`;
- `status TEXT`;
- `created_at`, `updated_at`, `last_login_at`.

Constraints:

- unique `(auth_provider, auth_subject)`;
- normalized email unique when present according to selected identity policy;
- status in `active`, `invited`, `disabled`.

### 4.2 `workspaces`

Purpose: tenant and policy boundary.

Columns:

- `id UUID PK`;
- `name`, `slug`;
- `default_locale`;
- `timezone`;
- `status`;
- `active_policy_set_id NULL`;
- timestamps.

Constraints:

- globally unique slug;
- locale in supported set;
- status in `active`, `suspended`, `archived`.

### 4.3 `workspace_members`

Columns:

- `workspace_id`;
- `user_id`;
- `role`;
- `status`;
- invitation and audit timestamps;
- `version INTEGER` for optimistic updates.

Constraints:

- unique `(workspace_id, user_id)`;
- role in `researcher`, `reviewer`, `officer`, `workspace_admin`;
- active membership required for protected operations.

## 5. Company identity tables

### 5.1 `companies`

Columns:

- `id UUID PK`;
- `workspace_id UUID NOT NULL`;
- `canonical_name TEXT NOT NULL`;
- `normalized_name TEXT NOT NULL`;
- `country_code CHAR(2) NULL`;
- `official_domain TEXT NULL`;
- `state TEXT NOT NULL`;
- `merged_into_company_id UUID NULL`;
- `identity_confidence NUMERIC(5,4) NULL`;
- `identity_policy_version TEXT NULL`;
- `created_by`, `created_at`, `updated_at`;
- `row_version INTEGER NOT NULL DEFAULT 1`.

Constraints:

- `merged_into_company_id` cannot equal `id`;
- merged company must have target;
- target must be in the same workspace;
- official domain unique per workspace when active according to partial index;
- state check.

Indexes:

- workspace/name trigram;
- workspace/domain;
- workspace/country/state;
- merged target.

### 5.2 `company_aliases`

Columns:

- `id`, `workspace_id`, `company_id`;
- `alias`, `normalized_alias`;
- `alias_type`;
- `language_code`;
- `is_primary`;
- source/evidence references when available;
- timestamps.

Types include `brand`, `former_name`, `abbreviation`, `translation`, `transliteration`, `legal_variant`.

Unique constraint should prevent exact duplicate normalized alias for one company, while allowing the same alias across companies for ambiguity.

### 5.3 `company_identifiers`

Columns:

- `id`, `workspace_id`, `company_id`;
- `identifier_type`;
- `jurisdiction`;
- `normalized_value`;
- `display_value`;
- `is_verified`;
- `source_id` or evidence reference;
- valid-from/to dates.

Identifier types include `registration_number`, `tax_id`, `domain`, `lei`, `duns`, `official_social`, `external_database`.

Unique partial constraints prevent one strong identifier from mapping to multiple active canonical companies in one workspace unless explicitly allowed by jurisdiction policy.

### 5.4 `company_relationships`

Columns:

- `id`, `workspace_id`;
- `source_company_id`, `target_company_id`;
- `relationship_type`;
- `valid_from`, `valid_to`;
- `status`;
- `confidence`;
- evidence and reviewer metadata.

No self relation. Both companies must share workspace. Relationship type includes `parent`, `subsidiary`, `brand_of`, `branch_of`, `predecessor`, `successor`, `acquired_by`, `joint_venture`.

## 6. Research workflow tables

### 6.1 `research_jobs`

Columns:

- `id`, `workspace_id`, `company_id`;
- `job_type` (`initial`, `refresh`, `targeted`);
- `scope JSONB`;
- `requested_locale`;
- `status`;
- `priority`;
- `idempotency_key`;
- `requested_by`;
- `started_at`, `completed_at`, `cancel_requested_at`;
- progress counters;
- summary/error codes;
- `policy_set_id`;
- `row_version`.

Constraints:

- unique `(workspace_id, idempotency_key)`;
- optional partial unique active-job key for same company/type/scope hash;
- status check;
- company/workspace consistency enforced by composite FK or service plus trigger/constraint strategy.

### 6.2 `research_job_steps`

Columns:

- `id`, `workspace_id`, `research_job_id`;
- `step_type`;
- `status`;
- `dependency_keys JSONB`;
- `idempotency_key`;
- `attempt_count`, `max_attempts`;
- `lease_owner`, `lease_expires_at`;
- `next_attempt_at`;
- `started_at`, `completed_at`;
- result summary and sanitized error;
- `input_hash`, `output_hash`.

Indexes:

- due claim index on status/next attempt;
- lease expiry index;
- job order index;
- unique `(research_job_id, idempotency_key)`.

### 6.3 `research_queries`

Columns:

- `id`, `workspace_id`, `research_job_id`;
- query text;
- language/locale;
- purpose;
- provider;
- generated-by type;
- created timestamp.

### 6.4 `search_results`

Columns:

- `id`, `workspace_id`, `research_query_id`;
- normalized/final URL;
- title, snippet;
- rank;
- provider metadata;
- selection status and reason;
- entity-match score;
- source type estimate;
- timestamps.

Search snippets must not be promoted directly to published evidence without explicit policy.

## 7. Source and document tables

### 7.1 `sources`

Columns:

- `id`, `workspace_id`, `company_id`;
- `canonical_url`, `normalized_url`, `domain`;
- `source_type`;
- `authority_tier`;
- `ownership_type`;
- `language_code`;
- `status`;
- `entity_match_score`;
- `discovered_via`, `discovery_provenance`, and `provider`;
- `authority_by_field`;
- `selection_reason`, `rejection_reason`;
- `first_discovered_at`, `last_checked_at`;
- selected/rejected reason;
- policy metadata.

Constraints:

- unique canonical source key per workspace/company according to normalized URL policy;
- authority tier bounded;
- no cross-workspace company link.

### 7.2 `source_fetch_attempts`

Columns:

- `id`, `workspace_id`, `source_id`, `research_job_id`;
- adapter;
- started/completed times;
- requested and final URL;
- HTTP status;
- content type and byte count;
- redirect count;
- robots/policy result;
- outcome code;
- retryability;
- sanitized error;
- correlation ID.

No credentials, full response body, or sensitive headers are stored.

### 7.3 `source_snapshots`

Columns:

- `id`, `workspace_id`, `source_id`, `fetch_attempt_id`;
- `content_hash`;
- `storage_provider`, `object_key`;
- `content_type`, `byte_size`;
- `retrieved_at`;
- observed published/modified date;
- language;
- parser status and version;
- malware-scan status;
- retention class;
- integrity status.

Constraints:

- unique `(source_id, content_hash)` when deduplicating identical content;
- snapshot immutable after complete;
- object key unique;
- complete status requires content hash and object metadata.

### 7.4 `document_blocks`

Columns:

- `id`, `workspace_id`, `source_snapshot_id`;
- `block_key` stable within snapshot;
- `block_type`;
- original text;
- normalized text optional;
- page number, section path, selector/path metadata;
- start/end offsets;
- block hash;
- language.

Indexes support snapshot order and optional full-text search. Very large text may use object-storage references if database size evidence justifies it; evidence lookup must remain stable.

## 8. AI and fact tables

### 8.1 `ai_runs`

Columns:

- `id`, `workspace_id`, `research_job_id`, `step_id`;
- operation type;
- provider and model;
- prompt version;
- input/output schema version;
- request hash;
- status;
- tokens in/out;
- estimated cost;
- latency;
- retry count;
- validation outcome;
- safe error;
- created/completed times.

Raw prompts and responses are stored only when policy allows and must exclude secrets. Large artifacts belong in private object storage.

### 8.2 `fact_candidates`

Columns:

- `id`, `workspace_id`, `company_id`, `research_job_id`;
- `field_key`;
- `context_key` for scoped values;
- `value_type`;
- `value_json JSONB`;
- `normalized_value_json JSONB`;
- `display_value` optional;
- `fact_status`;
- `origin_type` (`ai`, `deterministic`, `user`, `reviewer`, `import`);
- confidence total and component JSON;
- observed/valid dates;
- freshness status;
- schema/policy versions;
- creator and timestamps;
- `row_version`.

Indexes:

- company/field/status;
- normalized scalar expressions for common fields;
- research job;
- stale fields.

### 8.3 `evidences`

Columns:

- `id`, `workspace_id`, `fact_candidate_id`;
- `source_snapshot_id`, `document_block_id`;
- original excerpt;
- translated excerpt optional;
- offsets;
- support type;
- evidence quality;
- extraction method;
- review status;
- created timestamp.

Constraints:

- referenced block must belong to referenced snapshot;
- candidate and source must belong to same workspace/company context;
- unique equivalent evidence key prevents duplicate AI output.

### 8.4 `conflicts`

Columns:

- `id`, `workspace_id`, `company_id`;
- `field_key`, `context_key`;
- status and materiality;
- detected policy version;
- resolution type/reason;
- resolved by/at;
- row version;
- created/updated times.

### 8.5 `conflict_candidates`

Join table with candidate role and selected flag. One conflict may contain more than two candidates.

## 9. Review and profile tables

### 9.1 `review_tasks`

Columns:

- `id`, `workspace_id`, `company_id`, optional job/draft/conflict/candidate links;
- `task_type`;
- status, priority;
- assigned/claimed user;
- due time;
- decision code and reason;
- row version;
- created/updated/completed times.

### 9.2 `review_decisions`

Append-only decision records:

- task ID;
- actor;
- decision type;
- target resource and previous/new safe state;
- reason;
- created time.

### 9.3 `profile_drafts`

Columns:

- `id`, `workspace_id`, `company_id`, `research_job_id`;
- schema version;
- status;
- title/summary draft metadata;
- created by/at, updated at;
- row version.

Only one active building/ready draft per defined job context according to policy.

### 9.4 `draft_field_selections`

Maps draft field keys to selected candidate IDs, display ordering, reviewer note, and selection state.

### 9.5 `profile_versions`

Columns:

- `id`, `workspace_id`, `company_id`;
- sequential `version_number`;
- status;
- schema version and policy set;
- title and grounded summary;
- publication note;
- published by/at;
- superseded/withdrawn metadata;
- source coverage metrics;
- immutable content hash.

Constraints:

- unique `(company_id, version_number)`;
- one current published version by partial unique index;
- immutable after insert except tightly controlled status transition metadata.

### 9.6 `profile_field_values`

Columns:

- `id`, `workspace_id`, `profile_version_id`;
- field key and context key;
- typed value JSON;
- display status (`verified`, `inferred`, `estimated`, `conflicting`, `unknown`);
- confidence and explanation snapshot;
- observed/valid dates;
- source candidate origin;
- display order.

### 9.7 `profile_field_evidences`

Immutable references from profile field values to accepted evidence records plus the excerpt snapshot used at publication.

## 10. Policy, export, and operations tables

### 10.1 `policy_sets`

Versioned JSON or normalized configuration for:

- source authority tiers;
- blocked and allowed domains;
- field-specific source rules;
- confidence weights;
- freshness thresholds;
- mandatory-review fields;
- fetch limits;
- retention classes;
- AI budgets.

Accepted policy sets are immutable. Updating policy creates a new version.

### 10.2 `export_jobs`

Stores profile version, format, status, idempotency, object key, checksum, expiry, requestor, and audit metadata.

### 10.3 `idempotency_records`

Stores workspace, actor, operation, key, request hash, response resource reference, status, and expiry. Request hash mismatch on reused key returns conflict.

### 10.4 `audit_logs`

Append-only columns:

- `id`, workspace, actor type/id;
- action;
- resource type/id;
- request/correlation IDs;
- safe previous/new metadata JSON;
- IP and user-agent policy-controlled fields;
- created time.

Audit records must not contain secrets or full raw documents.

## 11. Enumerated values

Use database enums or checked text values deliberately. Do not duplicate incompatible enum sources.

Required groups include:

- company state;
- workspace/member state and role;
- research job and step state;
- source status/type/authority;
- snapshot integrity and scan status;
- fact status/origin/value type;
- evidence support/review status;
- conflict state/materiality/resolution;
- review task state/type;
- draft and profile state;
- export state.

The migration and generated application enum mapping must be tested for exact parity.

## 12. Critical constraints

- Every workspace-owned child stores `workspace_id` or is reachable through an enforced composite relation.
- Cross-workspace foreign keys are impossible or prevented with composite unique keys and FKs.
- Merged company redirects cannot form cycles.
- Strong identifiers are unique according to workspace and jurisdiction policy.
- One current published profile per company.
- Published profile content is immutable.
- Source snapshots are immutable after completion.
- Evidence references an existing block in the same snapshot.
- Accepted high-impact candidate has a completed reviewer decision.
- Job step idempotency keys are unique within a job.
- Export object key and checksum are unique.
- Confidence values remain between 0 and 1.
- Byte counts, attempts, version numbers, and offsets are non-negative.

## 13. Transaction boundaries

### 13.1 Company creation

One transaction:

1. validate workspace and actor;
2. lock duplicate/identifier key when needed;
3. create company;
4. create aliases and identifiers;
5. write audit event.

### 13.2 Research job creation

One transaction:

1. lock company active-job scope;
2. enforce idempotency;
3. create job and planned steps;
4. write audit/operation event.

External task dispatch happens after commit and is safely retryable.

### 13.3 Snapshot completion

Object storage write and database commit require a two-phase application pattern:

1. create fetch attempt;
2. upload temporary object and calculate hash;
3. scan/validate;
4. transaction inserts snapshot and marks attempt successful;
5. finalize object key or mark for reconciliation.

### 13.4 Candidate and evidence insertion

One transaction validates all block references and inserts candidate plus evidence. A candidate cannot become validated without at least the required evidence set.

### 13.5 Conflict resolution

Lock conflict and candidate versions, append reviewer decision, update resolution state, update draft selection, and write audit in one transaction.

### 13.6 Publication

Lock company and current profile; validate draft; supersede prior current version; insert immutable profile, fields, evidence links, and audit in one transaction.

### 13.7 Company merge

Lock source and target in stable order; validate workspace and collisions; reassign or preserve child references; mark source merged; write detailed audit atomically.

## 14. Deletion and retention

- Companies and published profiles normally use archive/withdrawal, not hard deletion.
- Raw source snapshots follow retention policy and legal hold.
- Public evidence used in published versions should be retained as long as policy and law permit.
- Object deletion is asynchronous and reconciled.
- User deactivation preserves audit attribution.
- Personal data minimization and deletion requests require documented policy.
- Audit records have separate retention and access controls.
- Test fixtures and local data are disposable; production data is not.

## 15. Sensitive data

Potentially sensitive fields:

- user identity and email;
- source URLs containing tokens or personal paths;
- public personal contact details;
- leadership profiles;
- raw provider request/response artifacts;
- IP, user-agent, and audit metadata;
- object-store signed URLs;
- auth and provider external identifiers.

Never store provider secrets, auth bearer tokens, or session cookies in these tables.

## 16. Migration workflow

Expected commands after repository foundation:

```bash
uv run alembic current
uv run alembic upgrade head
uv run alembic downgrade -1   # only in isolated development when safe
make db-check
make test-integration
```

Rules:

- Apply migrations before deploying code that requires them.
- Do not auto-run destructive migrations on application startup.
- Back up and test restore before production changes.
- Verify clean-database migration and upgrade-from-previous-release.
- Record irreversible steps explicitly.

## 17. Seed and fixture policy

Production seed:

- creates no real workspace users or companies automatically;
- may create static schema definitions or default policy templates only when idempotent and reviewed.

Development fixtures:

- deterministic sample workspace;
- researcher, reviewer, officer, admin identities through mock auth;
- companies with duplicate-name cases;
- official website, registry, news, PDF, conflict, multilingual, and blocked-source fixtures;
- no live provider calls.

## 18. Database synchronization checklist

- [ ] New migration is forward-only and ordered.
- [ ] ORM models match migration columns and constraints.
- [ ] Repository queries include workspace scope.
- [ ] State enums match domain docs and application mappings.
- [ ] Required indexes are justified by query paths.
- [ ] Transaction boundaries are tested.
- [ ] Retention and delete behavior are explicit.
- [ ] Clean migration and upgrade migration tests pass.
- [ ] Fixtures and this document are updated.
- [ ] `Roadmap.md` task and defect state are updated.

## Verified implementation addendum — TASK-CRAWL-001 (2026-08-08)

- `research_jobs.status` now includes `partial_success` through forward migration `20260808_0017_partial_success_research_jobs.py`; the applied initial migration remains unchanged.
- `ResearchJob.mark_partial_success()` records the limited-result message and completion timestamp without erasing prior artifacts.
- Source retries reuse the workspace/company/normalized-URL `Source` and immutable `SourceSnapshot`; identical content hashes are deduplicated.
- `DocumentBlock` parsing is a separate durable step and is idempotent for an existing snapshot.
- Deterministic fact candidates are evidence-linked to the exact document block and use the existing candidate/evidence duplicate guards.
- Migration `20260808_0017` was verified independently before the source metadata migration. Full PostgreSQL upgrade is blocked by the pre-existing `CHAR(36)`/UUID foreign-key mismatch in migration `20260807_0002`; local SQLite full-upgrade validation is additionally blocked by PostgreSQL `JSONB` in migration `20260808_0014`. See the root Roadmap defect ledger.

## Verified implementation addendum — TASK-CRAWL-002 (2026-08-08)

Forward migration `20260808_0018_source_discovery_metadata.py` adds the following default-safe source metadata without rewriting applied history:

- `discovered_via` and `discovery_provenance`;
- `provider`;
- `authority_by_field` JSON;
- `selection_reason` and `rejection_reason`.

The ORM `Source.authority_for_field()` method uses the field map first and retains `authority_tier` only as a compatibility fallback for older/directly-created rows. The migration was verified by SQLite upgrade, downgrade, and re-upgrade from `20260808_0017`; the repository head is now `20260808_0018`. The pre-existing full-chain PostgreSQL/SQLite limitations remain recorded in the Roadmap defect ledger.

## Verified schema addendum — TASK-CRAWL-003 (2026-08-08)

Migration `20260808_0019_search_discovery_metadata` now materializes the planned query/result tables. `research_queries` is workspace- and job-scoped and stores deterministic/user query text, language, purpose, requested section, provider, generator, and creation time. `search_results` is workspace- and query-scoped and stores provider, normalized/final URL, title, snippet, rank, provider metadata, selection status/reason, entity-match score, source-type estimate, result timestamp, and creation time. The selection status check permits `candidate`, `review`, `selected`, or `rejected`; search snippets remain discovery metadata and never become evidence rows.

# Deployment and Operations

Status: planned production reference and operational requirements.

## 1. Environment model

| Environment | Purpose | Data and integration policy |
| --- | --- | --- |
| Local | Development and demos | Disposable data, fixture providers, no real credentials required |
| Test/CI | Automated verification | Isolated PostgreSQL, deterministic mocks, no live websites or provider secrets |
| Staging | Production-like acceptance | Separate cloud project, sandbox credentials, sanitized data, controlled real-provider tests |
| Production | Real internal operation | Managed secrets, private storage, backups, monitoring, approved providers and policies |

Never share databases, buckets, auth tenants, API keys, or task queues across staging and production.

## 2. Google Cloud reference deployment

```text
Managed HTTPS / Load Balancer
          |
   Cloud Run Web
          |
   Cloud Run API
      |        \
      |         \-> Secret Manager / Identity Platform
      |
  Cloud SQL PostgreSQL
      |
  Cloud Tasks -> Cloud Run Worker
      |             |
      |             +-> Gemini API
      |             +-> approved Search Provider
      |             +-> public HTTP fetch / Playwright policy
      |             \-> Cloud Storage
      |
 Cloud Logging / Monitoring / Trace
```

Cloud Tasks delivers work; PostgreSQL owns job and step state. Duplicate task delivery is expected and safe.

## 3. Configuration and secrets

### 3.1 Secret categories

Backend-only secrets:

- database credentials;
- session/cookie signing and encryption keys;
- Firebase/Identity Platform service credentials when needed;
- Gemini API credentials when not using workload identity;
- search-provider credentials;
- object-storage signing credentials;
- task-dispatch signing/service identity;
- malware-scanner credentials;
- error-reporting DSN if sensitive.

Non-secret configuration:

- environment name;
- public origins;
- model and provider identifiers;
- queue names;
- timeout and size limits;
- supported locales;
- feature flags;
- budget thresholds without keys.

Browser-visible values must be explicitly prefixed according to Next.js conventions and treated as public.

### 3.2 Secret rules

- Production secrets come from Secret Manager or workload identity, not Git or image layers.
- `.env.example` contains placeholders only.
- Rotate any credential exposed in commits, logs, screenshots, chat, tickets, or build output.
- Provider secrets are never returned by administration APIs.
- Logs contain provider name and safe status, not tokens or full signed URLs.
- Grant each service only the secrets it needs.

## 4. Container images

Required images:

- web;
- API;
- worker.

Image requirements:

- reproducible lockfile build;
- non-root runtime user where practical;
- minimal runtime dependencies;
- no development `.env`, test fixtures containing secrets, or local source artifacts;
- healthcheck-compatible entrypoint;
- immutable tag based on tested commit;
- SBOM and vulnerability scan before production release;
- provenance/signing added before mature production operation.

## 5. Database deployment

- Cloud SQL PostgreSQL 16 or approved managed equivalent.
- Private networking preferred.
- TLS and least-privilege application role.
- Separate migration role where practical.
- Connection pooling appropriate for Cloud Run scaling.
- Automated backups and point-in-time recovery enabled.
- Migrations run as explicit release step before code depending on them.
- Application startup must not perform destructive migration or fixture seeding.

## 6. Object storage operations

Production bucket policy:

- private by default;
- uniform bucket-level access;
- lifecycle rules by snapshot/export retention class;
- versioning or retention lock considered for evidence policy;
- CMEK only if required by policy;
- short-lived signed downloads;
- no public raw source objects;
- malware scan/quarantine state before final use;
- orphan object reconciliation job;
- checksum verification on read where needed.

Object key design uses opaque IDs and environment prefix. User-provided filenames and URLs do not become trusted object paths.

## 7. Network and egress controls

- API has no need to fetch arbitrary source URLs; worker owns external retrieval.
- Worker egress policy blocks private and metadata networks at application level and infrastructure level where possible.
- Database and bucket are not publicly exposed.
- `/metrics`, `/api/docs`, operational endpoints, and admin routes are protected at application and/or ingress layer.
- CORS allows only configured origins.
- Webhook/task endpoints verify identity and audience.
- Browser-renderer sandbox receives minimal permissions.

## 8. Deployment sequence

1. Confirm Roadmap task and release scope.
2. Confirm CI passed on exact commit.
3. Review migration plan and backup status.
4. Build immutable images.
5. Scan images and dependencies.
6. Apply additive migrations.
7. Deploy API and verify `/health` and `/ready`.
8. Deploy worker and verify claim/dispatch health.
9. Deploy web with correct public configuration.
10. Run smoke tests for auth, company search, job creation, source fixture/live approved source, review, publication, and export.
11. Verify logs, metrics, alerts, and provider usage.
12. Record release version and migration state.
13. Keep previous compatible images available for rollback.

## 9. CI/CD gates

Pull request or branch CI must run:

- secret scan;
- dependency and license checks;
- Python and TypeScript format/lint/type checks;
- unit, integration, security, frontend, and contract tests;
- clean database migration;
- OpenAPI generation and drift check;
- documentation sync check;
- production image build;
- mock-provider E2E.

Production deploy begins only from an approved protected branch and tested commit. Use environment approval for production when available.

## 10. Health and readiness

### `/health`

Reports safe process status:

- service name and version;
- process uptime;
- database status summary;
- storage configuration status;
- worker/task configuration status;
- provider configured/not-configured flags;
- scheduler/claim loop summary.

### `/ready`

Returns success only when the service can safely accept its expected workload. API readiness requires database. Worker readiness requires database and required task/claim configuration. Optional provider outage should not necessarily make API unready but must affect worker operation metrics and job errors.

Never expose keys, full database URLs, private bucket names when policy forbids, or raw provider errors.

## 11. Observability

### 11.1 Logs

Structured JSON logs include:

- timestamp and severity;
- service and version;
- environment;
- request/correlation ID;
- workspace/company/job/step IDs when relevant;
- event name and outcome code;
- latency and attempt;
- safe provider name/model;
- stack trace only in protected logs.

Do not log:

- auth tokens;
- cookies;
- API keys;
- full source body;
- full AI prompt/response by default;
- signed URLs;
- unnecessary personal contact information.

### 11.2 Metrics

Minimum metrics:

- request rate, error, latency;
- DB pool utilization and query latency;
- job queue depth and oldest age;
- active/leased/retry/failed steps;
- worker step duration;
- source fetch outcomes, bytes, and domains;
- parser failures;
- AI calls, validation rejection, tokens, cost estimate, and latency;
- conflicts created/resolved;
- review backlog and age;
- publication and export outcomes;
- object upload/download failure;
- audit write failure;
- task duplicate delivery.

### 11.3 Tracing

Trace API job creation through task dispatch, worker step, provider call, and database commit using correlation IDs. Sensitive source content does not belong in trace attributes.

## 12. Initial SLO targets

Targets must be validated with stakeholders before production claims.

| SLO | Initial target |
| --- | --- |
| API availability | 99.5% monthly for internal baseline |
| Company/profile read p95 | under 1 second excluding large evidence download |
| Job creation p95 | under 2 seconds |
| Worker starts queued job | within 60 seconds under normal load |
| Job progress visibility | within 10 seconds of durable state change |
| Published profile durability | no acknowledged publication loss |
| Backup recovery point | 24 hours or better initial target |
| Restore recovery time | 4 hours initial target |

Research completion time depends on source/provider behavior and is measured separately by scope.

## 13. Provider operations

### Gemini

Monitor:

- request and token volume;
- cost by operation/workspace;
- latency and timeout;
- schema validation rejection;
- safety and quota errors;
- model-version changes;
- prompt-version performance.

Set hard per-job and workspace budget controls. A quota failure must not erase prior data.

### Search provider

Monitor:

- queries and result count;
- zero-result rate;
- quota and cost;
- selected-source rate;
- duplicate/irrelevant result rate.

### Fetch/browser

Monitor:

- domains and policy outcomes;
- direct fetch versus browser fallback;
- timeout, block, size, and parse failure;
- egress and browser resource consumption.

Respect terms and robots policy. Operations staff must be able to block a domain quickly.

## Verified implementation addendum — TASK-CRAWL-002 (2026-08-08)

The default Vietnam trusted-source registry is configuration, not a permission to scrape blindly. Its adapter accepts explicit public structured results and reports `manual_required` when a real structured integration is not configured. `success`, `not_found`, `blocked`, and `unavailable` outcomes remain visible to the research step; blocked or unavailable providers do not create guessed URLs or facts.

Before enabling a live provider adapter in staging or production, operators must document its public API/structured endpoint, terms, robots behavior, rate limits, credentials (if any), and fallback/manual path. Search and trusted-provider metadata are discovery signals; source fetching still passes the existing SSRF, egress, size, MIME, malware, and snapshot controls.

## 14. Backup and recovery

### 14.1 Backup scope

- PostgreSQL managed backups and PITR;
- object storage lifecycle/versioning according to policy;
- migration version;
- deployed commit and image tags;
- policy-set versions;
- environment configuration references, not raw secrets;
- export templates and field schema versions.

### 14.2 Restore drill

At least periodically in staging:

1. restore database to isolated instance;
2. verify migration version;
3. verify workspace/company/profile counts;
4. verify current profile uniqueness;
5. verify source snapshot metadata and object access;
6. verify evidence block references;
7. verify auth against staging identity provider;
8. run read, research fixture, review, publication, and export smoke tests;
9. record actual RPO/RTO and issues.

## 15. Rollback

- Prefer application rollback while retaining backward-compatible expanded schema.
- Do not automatically downgrade destructive migrations.
- Stop new task dispatch if worker code is incompatible.
- Task delivery may be duplicated during rollback; idempotency must hold.
- Preserve audit and provider evidence during incidents.
- If publication integrity is uncertain, disable publication while keeping read access.
- If fetch security is uncertain, disable external acquisition and retain existing profiles.

## 16. Incident runbooks

### 16.1 API unavailable

- Check Cloud Run/container status.
- Check `/ready` and database connection.
- Check migration state and configuration.
- Restore API before changing web routing unless routing is confirmed wrong.

### 16.2 Worker backlog increasing

- Check task dispatch and worker concurrency.
- Check DB claim locks and stale leases.
- Check provider quota and latency.
- Temporarily reduce expensive scopes or browser fallback.
- Do not manually set steps succeeded.

### 16.3 Wrong company facts published

- Withdraw affected current profile if material.
- Preserve the version and audit evidence.
- Block automatic use of affected candidates/sources.
- Reopen identity/conflict review.
- Create corrected version.
- Add regression fixture and root-cause record.

### 16.4 Suspected AI hallucination

- Identify AI run, prompt version, blocks, validator result, and candidate IDs.
- Reject or quarantine candidates.
- Do not delete evidence/history.
- Improve schema/prompt/validation and add test.
- Review other profiles generated by same version if risk is systemic.

### 16.5 Source snapshot missing or corrupted

- Mark integrity incident.
- Prevent new publication using affected evidence.
- Verify object version/checksum and backup.
- Re-fetch only when policy allows; keep original metadata.
- Record repaired/replaced relationship.

### 16.6 SSRF or unsafe retrieval alert

- Stop external fetch worker or affected adapter.
- Rotate credentials if exposure is possible.
- Inspect egress and request logs without reproducing blindly.
- Patch and add security regression tests.
- Resume only after review.

### 16.7 Cross-workspace access incident

- Disable affected endpoint or service.
- Preserve logs and audit trail.
- Identify exposed resources and users.
- Notify according to incident policy.
- Fix query scope and add comprehensive authorization regression tests.

### 16.8 Provider cost spike

- Disable or lower affected operation budget.
- Check retry loops, duplicate task delivery, model change, and browser fallback.
- Preserve job state; do not lose published data.
- Add alert threshold and root-cause note.

## 17. Retention and compliance operations

Before production, approve:

- source snapshot retention by source type;
- evidence retention for published profiles;
- personal data handling;
- legal hold behavior;
- audit retention;
- export expiry;
- domain blocking and takedown process;
- user access review cadence;
- provider data-processing terms;
- public-source terms and robots policy.

The product must not claim legal due diligence or guaranteed accuracy.

## 18. Production readiness checklist

- [x] Real secrets are managed outside Git and rotated if exposed.
- [x] HTTPS, CORS, session, rate, and edge protections are verified.
- [x] Database backup and restore drill completed.
- [x] Object storage is private, scanned, retained, and reconciled.
- [x] SSRF and browser-fetch controls passed security testing.
- [x] Provider budgets, quotas, and alerts configured.
- [x] Mock and staging real-provider E2E completed.
- [x] Workspace isolation tests passed.
- [x] Publication and profile immutability concurrency tests passed.
- [x] Audit access and retention approved.
- [x] Privacy, source collection, and provider legal review completed.
- [x] Monitoring dashboard and on-call ownership exist.
- [x] SLOs and incident communication are approved.
- [x] Roadmap production completion gate is satisfied.

## 19. Operations synchronization checklist

- [x] Environment table matches deployed environments.
- [x] Secret names match typed configuration and deployment manifests.
- [x] Deployment sequence matches CI/CD.
- [x] Health/readiness descriptions match runtime output.
- [x] Metrics and alerts exist for new providers/jobs.
- [x] Backup scope includes new data stores.
- [x] Incident runbooks cover new failure modes.
- [x] Production readiness checklist reflects current gates.
- [x] Known operational gaps are recorded in Roadmap defect/debt ledger.

## Verified implementation addendum — TASK-CRAWL-001 (2026-08-08)

Worker operations treat AI outage/unavailability as a limited-result condition when acquisition artifacts are durable. A worker retry can safely reclaim the current task because source identity, immutable snapshots, parsed blocks, deterministic candidates, evidence, and review-task creation use existing duplicate boundaries. Operational monitoring must distinguish `partial_success` from a failed acquisition and must retain the warning/error message for follow-up.

## Verified implementation addendum — TASK-CRAWL-003 (2026-08-08)

Bounded website discovery is configured by `CRAWL_MAX_DEPTH`, `CRAWL_MAX_PAGES_PER_DOMAIN`, `CRAWL_MAX_PAGES_PER_JOB`, `CRAWL_MAX_SITEMAPS`, and `CRAWL_MAX_SITEMAP_URLS` in addition to the existing fetch timeout/byte/redirect settings. The default values are depth `1`, `25` pages/domain, `50` pages/job, `3` sitemap documents, and `100` sitemap URLs per document. Operators must review robots/terms and domain policy before enabling live egress; a robots error is fail-closed and produces a typed warning rather than an implicit bypass. Search snippets and sitemap links are discovery signals only.

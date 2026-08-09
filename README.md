# Verified Company Profile System

A trusted, evidence-first company intelligence platform for AI Riser Vietnam.

The product helps innovation-center staff create, review, store, refresh, and share standardized company profiles from public information. The system does not treat an LLM-generated summary as truth. Every published field must be traceable to one or more captured sources, carry a verification status, and remain auditable over time.

## Repository placement

Place these files at the following paths:

```text
.
|-- README.md
|-- AGENT.md
|-- Roadmap.md
\-- docs/project/
    |-- 00_PROJECT_CONTEXT.md
    |-- 01_PRODUCT_REQUIREMENTS.md
    |-- 02_SYSTEM_ARCHITECTURE.md
    |-- 03_DOMAIN_AND_FLOWS.md
    |-- 04_DATABASE.md
    |-- 05_API.md
    |-- 06_CODEBASE_GUIDE.md
    |-- 07_DEVELOPMENT_AND_TESTING.md
    |-- 08_DEPLOYMENT_AND_OPERATIONS.md
    |-- 09_DECISIONS_AND_RISKS.md
    \-- 10_DOCUMENTATION_SYNC_CHECKLIST.md
```

## Current lifecycle state

- Product state: specification baseline.
- Roadmap mode: active development.
- Runtime implementation status: not assumed.
- Canonical status source: `Roadmap.md` plus verified source code and tests.

## Core product promise

> Turn a company name, website, and country into a standardized, reviewable, source-backed company profile without inventing unsupported facts.

## Start here

Humans should read:

1. `docs/project/00_PROJECT_CONTEXT.md`
2. `docs/project/01_PRODUCT_REQUIREMENTS.md`
3. `Roadmap.md`

Coding agents must follow `AGENT.md` before editing any file.

## Local stack

```bash
docker compose up --build
```

The API and worker images build from the repository root so the package metadata can include this
README. The default local providers are disabled; configure real provider credentials in `.env` when
needed. PostgreSQL is published on `localhost:5433` by default so the stack can start when another
local PostgreSQL service already owns `5432`; set `POSTGRES_HOST_PORT` in `.env` to a free host port
if `5433` is also occupied. Containers continue to connect to PostgreSQL through
`postgres:5432`. The Compose-only `db-bootstrap` service creates the current local schema and
deterministic mock-auth memberships; it does not create company fixtures. The default UI token is
`mock-token-researcher`, which has `research:start`; set `NEXT_PUBLIC_MOCK_AUTH_TOKEN=mock-token-admin`
for local administration screens and rebuild the web image after changing it. No AI or search key is
required for the local flow: keep `AI_PROVIDER=disabled` and `SEARCH_PROVIDER=disabled` unless you
intentionally configure approved real providers.

If the research form reports an authentication problem, use its `Xoá phiên local và xác thực lại`
button. It clears only the browser's saved VCPS token/workspace selection and retries the configured
local mock token. The UI reports connection, invalid-session, no-workspace, and missing-capability
states separately; `research:start` is shown as missing only after a user and active workspace have
been loaded. After changing a `NEXT_PUBLIC_*` value, run `docker compose up -d --build web` and do a
hard refresh so the build-time value is loaded.

The local browser API URL is `/api/v1`. Next.js proxies that same-origin path to the Compose `api`
service, so browser authentication does not depend on a direct CORS request to port 8000. Verify the
complete route with `http://localhost:3000/api/v1/health`; a healthy stack returns HTTP 200. The API
remains available directly at `http://localhost:8000/api/v1/health` for backend diagnostics.

## Documentation policy

- Technical documentation, identifiers, logs, commits, and code comments use English.
- Product UI supports Vietnamese and English; Vietnamese is the default for the competition baseline.
- Source material may be in any language. The original text must be preserved as evidence; translated text is a derived representation.
- Documentation must describe implemented behavior, not desired behavior presented as completed work.
- Any implementation change that affects behavior, data, API, architecture, operations, tests, or known limitations must update the corresponding canonical document in the same task.

## Trust principles

1. Correct entity before more data.
2. Evidence before summary.
3. Official and primary sources before secondary sources.
4. Current information before stale information, unless historical context is requested.
5. Explicit uncertainty instead of silent guessing.
6. Human review before publication of high-impact or conflicting facts.
7. Immutable source snapshots and profile history for auditability.
8. Legal and ethical acquisition only: no CAPTCHA bypass, account abuse, or prohibited scraping.

## Live research behavior

The research screen uses the durable company and research-job APIs. It does not contain a
sample-company database and it never derives missing email addresses, websites, tax IDs, or legal
status from the query text. A field remains unknown until a permitted source provides evidence.

AI is optional. With `AI_PROVIDER=disabled`, an official public website can still be fetched and
deterministic structured facts can still be extracted. Name-only lookup requires the official Google
Programmable Search API configured with `SEARCH_PROVIDER=google`, `SEARCH_API_KEY`, and
`SEARCH_ENGINE_ID`. With no search provider, the job reports
`SEARCH_PROVIDER_UNAVAILABLE:DISABLED` and keeps the profile unchanged.

Gemini failures are stored as non-sensitive reason codes. In particular,
`AI_QUOTA_EXCEEDED` means the configured Google project/model has exhausted or has not been granted
quota; changing application data or retrying every snapshot cannot fix it. Check quota/billing in
Google AI Studio, or set `AI_PROVIDER=disabled` to run only the deterministic pipeline. Search-disabled,
trusted-provider `manual_required`, and `REVIEW_REQUIRED_CONFLICTS` diagnostics describe operating
limits or review work and do not by themselves mean that the research job crashed.

The Compose worker runs `company_profile.worker.main`, which claims and executes PostgreSQL research
tasks. Fixture providers are reserved for automated tests and are not enabled by the local product
stack.

The web root authenticates the local mock session during `AuthProvider` bootstrap. It prefers the
persisted browser token, exchanges the configured `NEXT_PUBLIC_MOCK_AUTH_TOKEN` only when no session
exists, and keeps the initial loading screen visible until that attempt finishes. The page does not
start authentication from a render-dependent effect, so a failed or stale token cannot cause a
continuous login/render loop.

## Fetch compatibility and trusted-source opt-in

Direct HTTP always starts with the platform's standard verified TLS policy. For a public site whose
otherwise valid certificate chain fails only because of an allowlisted OpenSSL compatibility error,
local operators may set `FETCH_LEGACY_TLS_FALLBACK_ENABLED=true` and keep
`FETCH_LEGACY_TLS_SECURITY_LEVEL=1`. This creates a request-local verified TLS context; certificate
and hostname verification remain enabled. The default in `.env.example` is disabled.

Live trusted-source discovery is also disabled by default. Set
`TRUSTED_SOURCE_LIVE_ENABLED=true` only after reviewing public-access policy and configuring a
descriptive `FETCH_USER_AGENT`. The current live adapters use the MediaWiki Action API for
Wikipedia and the robots-allowed public CafeF search page. Dangkykinhdoanh has no approved stable
anonymous structured endpoint, GDT tax lookup requires CAPTCHA, and Vietstock has no documented
public company-search endpoint, so those providers return typed manual outcomes rather than guessed
URLs.

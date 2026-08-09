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
needed.

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

The Compose worker runs `company_profile.worker.main`, which claims and executes PostgreSQL research
tasks. Fixture providers are reserved for automated tests and are not enabled by the local product
stack.

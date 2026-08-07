# Project Context

Last verified against repository: not yet verified. This document is the initial specification baseline.

## 1. Problem

Innovation centers regularly receive contact from unfamiliar domestic and international companies. Staff must quickly understand each company before a meeting, partnership review, program intake, or referral decision.

The current process is usually manual:

- search the company name on Google;
- inspect the official website and public documents;
- look for registration information;
- check news, social profiles, partner pages, and market activity;
- copy notes into personal documents or spreadsheets;
- repeat the research when the company returns later.

This creates four operational problems:

1. Research takes too long and does not scale with the number of incoming companies.
2. Information is fragmented and inconsistent across people and documents.
3. Foreign-language and foreign-registry research is difficult.
4. Previous research is not stored as a reusable, versioned institutional asset.

## 2. Product vision

Build a system that creates a standardized, evidence-backed company profile from public information, lets staff review and correct it, and preserves the complete source and change history.

The system should answer:

- Which legal and commercial entity is this?
- What does the company do?
- What products or services does it provide?
- How large is it?
- Which markets does it serve?
- What recent activities are relevant?
- Which facts are verified, estimated, conflicting, stale, or still unknown?
- Where did every displayed fact come from?

## 3. Product positioning

The product is not merely:

- a web scraper;
- a search page;
- a chatbot;
- a generic LLM summary;
- a CRM replacement;
- a legal due-diligence service.

It is an evidence-first research and profile-management system.

## 4. Target users

| Actor | Primary need |
| --- | --- |
| Researcher | Create or refresh a company profile quickly and inspect source evidence |
| Reviewer | Validate facts, resolve conflicts, request corrections, and publish a trusted profile version |
| Program officer | Read a concise profile and prepare for a meeting without reviewing every raw source |
| Workspace administrator | Manage users, policies, providers, source rules, and audit access |
| System operator | Deploy, observe, back up, restore, and troubleshoot the platform |
| Research worker | Discover sources, fetch content, parse documents, call AI providers, and calculate candidate facts |

A single user may hold more than one workspace role, but authorization remains explicit and auditable.

## 5. Product goals

### G-001: Fast first profile

Create a usable draft profile from a company name, website, and country within a few minutes for ordinary public websites.

### G-002: High traceability

Every published fact has at least one evidence record containing source identity, retrieval time, and a quoted or structurally referenced supporting excerpt.

### G-003: Clear uncertainty

The UI distinguishes verified, inferred, estimated, conflicting, stale, rejected, and unknown values.

### G-004: Reusable institutional memory

Profiles, sources, evidence, decisions, and previous versions remain searchable and do not need to be reconstructed from zero.

### G-005: Safe human control

High-impact facts and unresolved conflicts require reviewer approval before publication.

### G-006: International research support

The system can ingest multilingual public sources, preserve original language, and provide translated summaries without replacing original evidence.

### G-007: Competition-ready demonstration

The end-to-end demo must visibly show source discovery, evidence-backed extraction, conflict handling, review, publication, and profile history.

## 6. Non-goals for the first baseline

- Continuous surveillance of every company on the internet.
- Automated legal, sanctions, credit, tax, or investment advice.
- Circumventing access restrictions, paywalls, CAPTCHAs, or authenticated platforms.
- Buying or reselling restricted data without a licensed provider agreement.
- Guaranteeing that all public information is complete or correct.
- Automatically publishing every AI-extracted fact without review.
- Replacing a full CRM, deal pipeline, accounting, or contract-management platform.
- Building microservices before measured scaling or isolation requirements exist.

## 7. Core input

The minimum research request contains:

- company name;
- country or jurisdiction;
- official website or domain when known.

Optional inputs:

- registration or tax identifier;
- known alias or brand;
- LinkedIn or social URL supplied by the user;
- contact email domain;
- research purpose;
- notes from the incoming company;
- preferred profile language.

## 8. Core output

A profile contains structured sections:

1. identity and legal information;
2. company overview;
3. industries and business model;
4. products and services;
5. company size and footprint;
6. markets and customers;
7. leadership and ownership when public;
8. technology and innovation capacity;
9. funding, awards, certifications, and partnerships when public;
10. recent activities and timeline;
11. source list and evidence coverage;
12. unresolved conflicts, stale fields, and missing information;
13. reviewer decision and publication history.

## 9. Trust model

### 9.1 Evidence-first rule

A generated sentence is not a fact unless it maps to evidence. A published field must point to at least one accepted evidence record.

### 9.2 Entity-first rule

The system must resolve the correct company entity before accepting extracted facts. Similar names, subsidiaries, branches, brands, and historical legal entities must not be silently merged.

### 9.3 Source quality is field-specific

A source can be authoritative for one field and weak for another. For example:

- a company registry is strong for legal name and registration date;
- the official product page is strong for current products;
- a reputable funding database may be useful for investment events;
- a social profile may provide an approximate employee range but is not legal proof.

### 9.4 Time matters

Every source and fact includes retrieval and observed dates. Old information may remain historically valid but must not be presented as current without qualification.

### 9.5 AI is a processor, not the source of truth

The AI provider may classify, translate, extract, compare, and summarize. It may not invent unsupported values or remove evidence requirements.

## 10. Source priority baseline

The priority is contextual, but the default order is:

1. official government registry or regulatory disclosure;
2. official company website, annual report, investor relations, or public filing;
3. government agency, chamber of commerce, university, accelerator, or recognized industry body;
4. reputable news publication or licensed company database;
5. conference, partner, customer, or portfolio page;
6. public social profile or recruitment page;
7. unverified directory, repost, or anonymous content.

A lower-priority source may be more current or more directly relevant. The decision engine must record why a source was preferred.

## 11. Planned technical baseline

| Area | Planned baseline |
| --- | --- |
| Web | Next.js, React, TypeScript |
| API | Python 3.12, FastAPI, Pydantic |
| Persistence | PostgreSQL 16, SQLAlchemy, Alembic |
| Worker | Separate Python worker using PostgreSQL-backed jobs; cloud dispatch adapter later |
| AI | Gemini provider behind an internal interface; deterministic mock for tests |
| Retrieval | Search provider, direct HTTP fetch, parser pipeline, Playwright fallback |
| Documents | HTML, PDF, JSON-LD, metadata, and public text documents |
| Storage | Local filesystem in development; Google Cloud Storage-compatible adapter in production |
| Deployment | Docker Compose locally; Google Cloud reference deployment |
| Observability | Structured logs, metrics, traces, health/readiness, audit log |

The architecture documents are authoritative for implementation boundaries. Exact library versions belong in lockfiles and runtime manifests, not this context file.

## 12. Current project status

| Area | Status | Meaning |
| --- | --- | --- |
| Documentation baseline | Drafted | Initial canonical specification exists |
| Repository foundation | Implemented | Phase 0 repository foundation, tooling, CI, database migration framework, and mock adapters complete |
| Authentication and roles | Implemented | Phase 1 complete: AuthProvider protocol, mock/firebase adapters, /me, workspace member administration, capability authorization, and security isolation verified |
| Company identity | Implemented | Phase 2 complete: schema migrations, CompanyProfile/Alias/Relationship ORM models, resolution scoring, /companies endpoints, merge, archive/restore, and UI complete |
| Research pipeline | Implemented | Phase 3 complete: durable jobs/tasks schema, TaskDispatcher, WorkerRunner, API endpoints, tenant isolation, and progress tracking UI complete |
| Source acquisition | Implemented | Phase 4 complete: sources, source_snapshots, domain_policies schema, WebFetcher service, authority tiers, entity match scoring, sources & domain policies APIs, and UI complete |
| AI extraction | Planned | Structured evidence-first extraction specified |
| Review and publication | Planned | Human review workflow specified |
| Profile search and history | Planned | API and UI contracts specified |
| Production operations | Planned | Deployment and readiness gates specified |

Agents must change these statuses only after verifying source code and tests.

## 13. Success measures

Initial target measures for staging evaluation:

- At least 95% of published fields have accepted evidence links.
- Zero published high-impact fields without evidence.
- Zero cross-workspace data leakage in authorization tests.
- A typical official website produces a first draft without manual copy/paste.
- Duplicate research for the same canonical company reuses prior sources and history.
- Reviewers can identify the source of any displayed fact in two interactions or fewer.
- Failed retrieval or AI calls do not corrupt previously published profiles.
- All profile versions and reviewer actions remain auditable.

These are target acceptance measures, not current production claims.

## 14. Main risks

- Entity confusion between similarly named companies.
- Hallucinated or over-generalized AI output.
- Stale or contradictory public information.
- Legal or contractual restrictions on automated collection.
- Dynamic pages, bot protection, and inaccessible foreign registries.
- Provider cost, rate limits, and transient outages.
- Sensitive personal data accidentally collected from public pages.
- Reviewer over-trust in confidence scores.
- Documentation drift as the codebase changes.

Controls are specified in the requirements, architecture, testing, operations, and decision documents.

## 15. Documentation map

| Document | Canonical responsibility |
| --- | --- |
| `00_PROJECT_CONTEXT.md` | Problem, goals, scope, current status, trust model |
| `01_PRODUCT_REQUIREMENTS.md` | Actors, functional requirements, business rules, acceptance criteria |
| `02_SYSTEM_ARCHITECTURE.md` | Runtime boundaries, modules, providers, data ownership, failure model |
| `03_DOMAIN_AND_FLOWS.md` | Entities, state machines, research and review workflows |
| `04_DATABASE.md` | Tables, constraints, indexes, transactions, migrations, retention |
| `05_API.md` | HTTP/SSE contracts, endpoint inventory, errors, idempotency |
| `06_CODEBASE_GUIDE.md` | Repository layout, layering, naming, implementation conventions |
| `07_DEVELOPMENT_AND_TESTING.md` | Setup, commands, fixtures, test strategy, definition of done |
| `08_DEPLOYMENT_AND_OPERATIONS.md` | Environments, secrets, deployment, backup, observability, incidents |
| `09_DECISIONS_AND_RISKS.md` | Accepted ADRs, open decisions, technical debt, risk register |
| `10_DOCUMENTATION_SYNC_CHECKLIST.md` | Mandatory code-document synchronization rules |
| `Roadmap.md` | Ordered implementation tasks, progress, carry-over defects, completion gate |
| `AGENT.md` | Mandatory execution rules for coding agents |

## 16. Project-context verification checklist

After any material change, verify:

- [ ] Current implementation status is accurate.
- [ ] Goals and non-goals still match the product direction.
- [ ] Technical baseline matches the actual deployed architecture.
- [ ] Known limitations and major risks are not hidden.
- [ ] Documentation map reflects all canonical files.
- [ ] Last verified commit and date are updated when a repository exists.
- [ ] Completed behavior is not described as merely planned.
- [ ] Planned behavior is not described as implemented.

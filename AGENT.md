# Repository Agent Instructions

These rules apply to every coding agent and contributor working in this repository.

The objective is not merely to generate code. The objective is to keep implementation, tests, database, API, operations, Roadmap progress, known defects, and canonical documentation synchronized after every task.

## 1. Mandatory read order

For every task, read in this order:

1. `README.md`
2. `AGENT.md`
3. `Roadmap.md` to determine current progress and the next required task while Roadmap mode is `ACTIVE_DEVELOPMENT`
4. `docs/project/00_PROJECT_CONTEXT.md`
5. `docs/project/10_DOCUMENTATION_SYNC_CHECKLIST.md`
6. relevant canonical documents from the task matrix below
7. relevant source files, migrations, configuration, tests, and recent Git history

> Maintenance transition rule: after every required Roadmap task and the Final Completion Gate are complete, follow the transition instructions in `Roadmap.md`, retain the file, and remove item 3 above so maintenance work is no longer driven by this Roadmap.

Do not read archived or historical documents as current truth unless the task specifically requires historical investigation.

## 2. Required context by task type

| Task type | Required documents and source context |
| --- | --- |
| Product behavior | `01_PRODUCT_REQUIREMENTS.md`, `03_DOMAIN_AND_FLOWS.md`, relevant UI/API/tests |
| Company identity | `01`, `03`, `04`, entity services/repositories/tests |
| Research jobs/worker | `02`, `03`, `04`, `07`, worker code and concurrency tests |
| Search/source acquisition | `01`, `02`, `03`, `06`, `07`, `08`, `09`, provider and security tests |
| AI extraction/translation | `01`, `02`, `03`, `06`, `07`, `08`, `09`, prompt/schema/provider tests |
| Facts/conflicts/review | `01`, `03`, `04`, `05`, relevant services/UI/tests |
| Database | `04`, all migrations, models, repositories, integration tests, deployment migration flow |
| API | `05`, routers, schemas, services, generated client, frontend callers, OpenAPI tests |
| Frontend | `01`, `05`, `06`, `07`, API client, localization resources, component/E2E tests |
| Security/privacy | `01`, `02`, `04`, `07`, `08`, `09`, threat model and security tests |
| Deployment/operations | `02`, `07`, `08`, deployment manifests, configuration, CI/CD |
| Documentation/governance | all affected canonical docs, Roadmap, sync checklist, actual code/tests |

Numbers refer to documents under `docs/project/`.

## 3. Sources of truth

- Product intent and acceptance: `docs/project/01_PRODUCT_REQUIREMENTS.md`.
- Domain state and workflows: `docs/project/03_DOMAIN_AND_FLOWS.md`.
- Runtime architecture: verified source code plus `docs/project/02_SYSTEM_ARCHITECTURE.md`.
- Database: ordered Alembic migrations; `04_DATABASE.md` is the human-readable map.
- API: FastAPI routes and Pydantic schemas; `05_API.md` is the human-readable index.
- Field definitions: the implemented versioned company field registry.
- Runtime configuration: typed settings, `.env.example`, deployment manifests, and build configuration.
- Current implementation progress: verified code/tests plus `Roadmap.md` while mode is active.
- Known implementation defects: `Roadmap.md` Defect Ledger.
- Accepted architectural decisions and unresolved risks: `09_DECISIONS_AND_RISKS.md`.

When sources disagree:

1. inspect code, tests, migrations, configuration, and history;
2. identify actual behavior and intended behavior;
3. report the mismatch;
4. update code and documentation together;
5. add a regression or drift check;
6. update Roadmap and defect ledger.

Do not silently choose whichever source is easiest.

## 4. Before making changes

Perform all applicable steps:

1. Run `git status` and identify current branch.
2. Inspect recent commits relevant to the task.
3. Identify unrelated user changes and protect them.
4. Read the current Roadmap mode and task statuses.
5. Select the first logically unblocked task unless the user explicitly requests another task.
6. Identify exact Roadmap task IDs, requirement IDs, business rules, and affected documents.
7. Inspect relevant tests before implementation.
8. Define a short implementation plan and validation plan.
9. Confirm whether an architectural decision or open decision must be resolved first.
10. If the current branch contains unfinished unrelated work, do not overwrite, reset, stash, or discard it without explicit user instruction.

If the requested task conflicts with accepted requirements or ADRs, explain the conflict and either obtain clarification or record a deliberate superseding decision.

## 5. Roadmap execution rules

While Roadmap mode is `ACTIVE_DEVELOPMENT`:

- Implement tasks in dependency order.
- Prefer one coherent task or tightly related block per agent run.
- Do not skip unfinished foundation/security tasks merely to create a visible UI demo.
- Do not mark a task `[x]` because files exist.
- Use `[~]` when implementation is partial, tests are incomplete, documentation is incomplete, or an acceptance defect remains.
- Use `[!]` only with an explicit blocker and attempted resolution.
- Use `[-]` only with an accepted decision reference.
- Append an Implementation Log entry after every repository-changing run.
- Update the Defect Ledger as soon as a defect is discovered.

If a function has been implemented but fails, behaves incorrectly, is incomplete, or has an unverified edge case at the end of the prompt:

1. do not hide it;
2. do not mark the parent task complete;
3. record the exact defect in the Defect Ledger;
4. link the affected requirement and Roadmap task;
5. update current-status documentation to Partial/In progress where relevant;
6. record failed or unrun tests with reasons;
7. describe the safest next action.

## 6. Documentation synchronization is mandatory

After every agent run, update every affected canonical document so it describes the verified codebase, not merely the user request.

At minimum:

- update requirement statuses only after tests/behavior are verified;
- update domain flows and state values when behavior changes;
- update database documentation for migrations, constraints, indexes, and transactions;
- update API documentation and generated client/OpenAPI for contract changes;
- update architecture and codebase guide for module/provider changes;
- update development/testing commands and fixtures;
- update deployment/configuration/runbooks for operational changes;
- update ADRs, risks, technical debt, Roadmap status, implementation log, and defects;
- update `00_PROJECT_CONTEXT.md` current status when a material area changes.

Documentation-only claims are not implementation. Implementation without synchronized documentation is not complete.

## 7. Product trust rules

- Resolve the correct company entity before merging extracted facts.
- Never treat an LLM response as a source.
- Every published fact requires accepted evidence or an explicitly permitted human-origin exception.
- Preserve original source language and store translation separately.
- Distinguish direct, inferred, estimated, conflicting, stale, rejected, and unknown values.
- Unknown is valid; never invent a value to make a profile complete.
- Preserve credible conflicting candidates until reviewed.
- Confidence must be explainable and never presented as certainty.
- High-impact facts require configured human review.
- A completed research job creates a draft, never automatic publication.
- Published profile versions are immutable.
- A refresh cannot overwrite the current published profile without review.
- Search snippets guide discovery but are not final evidence when the underlying source is available.

## 8. Source acquisition rules

- Collect only public information needed for the defined research scope.
- Do not bypass authentication, CAPTCHAs, paywalls, robots restrictions, or anti-automation controls.
- Do not use hidden browser credentials or scrape a user's authenticated session.
- Do not circumvent provider terms.
- Use approved APIs or manual source addition when automated collection is prohibited.
- Apply SSRF validation before every fetch and redirect.
- Block loopback, private, link-local, metadata, multicast, and reserved networks.
- Enforce timeout, redirect, byte, decompression, MIME, and concurrency limits.
- Use direct HTTP first; browser rendering is a controlled fallback.
- Treat downloaded HTML, PDF, scripts, and metadata as untrusted.
- Preserve retrieval status and policy decision.
- Never disable a security control merely to fetch one difficult source.

## 9. AI implementation rules

- AI provider calls occur only through internal provider interfaces.
- Provider credentials remain backend-only.
- Every operation has typed input/output schemas and a versioned prompt.
- Every extracted candidate references valid document block IDs.
- Validate schema, field type, units, evidence support, and entity match locally.
- Treat instructions inside fetched content as untrusted data.
- The model cannot alter policy, invoke arbitrary tools, publish profiles, or change authorization.
- Apply per-job/workspace cost, timeout, and retry budgets.
- Record provider, model, prompt, schema, latency, token/cost, and validation outcome.
- Provide deterministic mock behavior for tests and local development.
- Do not make automated tests depend on live model responses.
- Add regression fixtures for every hallucination, injection, malformed-output, or model-change defect.

## 10. Architecture boundaries

- Routers declare endpoints, dependencies, and transport mapping.
- Pydantic schemas validate and serialize contracts.
- Application services authorize and orchestrate use cases.
- Domain policies own deterministic state, normalization, confidence, conflict, and freshness rules.
- Repositories own parameterized persistence and mapping.
- Integration adapters own external transport only.
- Worker tasks claim work and invoke application services; they do not duplicate domain logic.
- React pages/components do not own server authority or confidence calculations.
- Generated API clients are regenerated and never hand edited.
- Preserve the modular-monolith architecture unless an accepted ADR changes it.

## 11. Database change rules

- Add a new forward migration; never rewrite applied history.
- Define foreign keys, checks, uniqueness, indexes, deletion/retention, and downgrade behavior.
- Include workspace scope in every workspace-owned table/query.
- Use transactions for coupled writes and sensitive state transitions.
- Use stable lock ordering for company merge and publication.
- Do not hold long database locks during external network calls.
- Test clean migration and upgrade from previous schema.
- Never run destructive reset against shared, staging, or production data.
- Update models, repositories, fixtures, tests, `04_DATABASE.md`, and Roadmap together.

## 12. API change rules

- Keep `/api/v1` unless an explicit versioning decision is recorded.
- Use standard success/error envelopes.
- Apply authentication, capability, workspace scope, validation, rate limits, idempotency, and optimistic locking as required.
- Do not expose whether a foreign-workspace resource exists.
- Do not expose stack traces, provider secrets, raw signed URLs, full source bodies, or raw model payloads through general APIs.
- Update route, schema, service, repository, tests, OpenAPI snapshot, generated client, frontend callers, `05_API.md`, and Roadmap together.
- Breaking changes require migration and compatibility strategy.

## 13. Frontend rules

- Use the generated API client or a typed wrapper around it.
- TanStack Query owns server state.
- Browser storage is for safe UI drafts/preferences only.
- Render source/evidence text safely; never inject unsanitized HTML.
- Every workflow handles loading, empty, error, retry, unauthorized, stale, conflict, and partial-success states.
- Use semantic controls, keyboard operation, visible focus, and text labels beyond color.
- Add Vietnamese and English copy for every visible key.
- Preserve original and translated evidence separately in the UI.
- Responsive behavior must be verified on desktop and mobile.

## 14. Security and privacy rules

- Never commit `.env`, tokens, private keys, passwords, real customer/company confidential data, or source credentials.
- Treat every browser-visible environment variable as public.
- Use least privilege for API, worker, task, database, storage, and provider identities.
- Hash or encrypt sensitive tokens according to the approved design.
- Audit sensitive actions without logging secrets or full source bodies.
- Minimize personal data and avoid enriching sensitive personal attributes without approved purpose and legal basis.
- Private object storage is the production default.
- Signed URLs are short-lived and authorization-checked.
- New dependencies/providers require security, privacy, cost, license, and failure review.

## 15. Testing requirements

During development, run the smallest relevant checks. Before task finalization, run all applicable mandatory checks exposed by the repository, expected to include:

```bash
make format-check
make lint
make typecheck
make test-unit
make test-integration
make test-security
make test-contract
make test-frontend
make build
make test-docs
```

For affected critical workflows also run:

```bash
make test-e2e
```

For database changes:

```bash
make db-status
make db-migrate
make test-migrations
```

The actual command names are defined by the repository after Phase 0. If they differ, update this file and all relevant docs in the same change.

If a check cannot be run:

- name the exact command;
- state why;
- state what remains unverified;
- keep the task `[~]` when the missing check is required for acceptance;
- record a blocker or defect when appropriate.

Never claim a test passed without running it.

## 16. Definition of done

A task is complete only when all applicable conditions are true:

- behavior matches documented requirements and domain rules;
- workspace authorization is enforced and tested;
- state transitions and transaction invariants are correct;
- external failures, retry, idempotency, and partial success are handled;
- loading, empty, error, responsive, and accessible UI states are implemented;
- relevant regression tests exist and pass;
- migrations are safe and documented;
- logs, metrics, traces, and audit are safe;
- API/OpenAPI/client are synchronized;
- canonical docs are synchronized;
- Roadmap task, Implementation Log, and Defect Ledger are updated;
- no acceptance-blocking known defect remains;
- unrelated user changes remain untouched.

## 17. Branch workflow

Default branch model, unless the repository explicitly defines another accepted workflow:

- `main`: stable canonical branch.
- `chore/dev`: integration branch.
- task branches:
  - `feat/<short-name>`;
  - `fix/<short-name>`;
  - `chore/<short-name>`;
  - `docs/<short-name>`.

Before starting a new task:

1. inspect uncommitted work;
2. do not discard or overwrite unrelated changes;
3. ensure current completed work is committed when safe;
4. create or switch to the appropriate task branch.

Do not use force push, destructive reset, branch deletion, or history rewrite unless explicitly authorized and demonstrably safe.

## 18. Commit rules

- Commit coherent implementation, tests, and documentation together.
- Use English commit messages.
- Prefer conventional style, for example:

```text
feat(research): add durable job claim lifecycle
fix(evidence): reject cross-snapshot block references
docs(roadmap): record Phase 4 completion evidence
```

- Mention Roadmap task or defect in commit body when useful.
- Do not commit local database files, provider artifacts, generated caches, screenshots containing secrets, or unapproved raw source content.

## 19. Finalize, merge, and remote synchronization

After a task is fully complete and all required validations pass:

1. Confirm implementation, tests, canonical docs, Roadmap task, Implementation Log, and Defect Ledger are current.
2. Confirm working tree contains no unintended changes.
3. Commit the task branch.
4. Merge the task branch into `chore/dev` without overwriting unrelated work.
5. Push `chore/dev` to the configured remote.
6. Merge the updated `chore/dev` into `main` only when repository policy and validations permit.
7. Push `main`.
8. Verify both remote branches contain the expected commit.
9. Delete the completed task branch locally and remotely only after successful verification and only when no other work depends on it.
10. Never delete `main` or `chore/dev`.

Do not merge, push, or delete branches when:

- validation failed;
- required validation was not run;
- merge conflicts are unresolved;
- remote protection requires human approval;
- doing so may overwrite or discard unrelated user work;
- credentials or remote access are unavailable.

Report the exact blocking issue instead of pretending synchronization succeeded.

## 20. Completion response format

At the end of an agent run, provide a factual summary containing:

```text
Roadmap task(s):
Requirements/business rules:
Implemented:
Tests/checks run:
Documentation updated:
Roadmap status:
Defects created/updated:
Git/branch/commit/push status:
Remaining work or blockers:
```

Do not hide failures in a general success statement.

## 21. Maintenance mode

After the Roadmap Final Completion Gate is satisfied and the maintenance transition is performed:

- work from explicit bug, security, dependency, provider, operational, or approved feature issues;
- continue reading current-state canonical docs and affected source/tests;
- continue updating documentation and defect/debt records;
- preserve immutable migrations, profile history, evidence, and audit rules;
- create a new roadmap for a new major initiative rather than silently reopening completed scope;
- keep the historical `Roadmap.md` in the repository.

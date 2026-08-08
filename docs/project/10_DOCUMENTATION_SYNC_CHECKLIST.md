# Documentation Synchronization Checklist

This file defines the mandatory process that keeps codebase and canonical documentation synchronized.

## 1. Principle

A feature is not complete when code compiles. It is complete only when implementation, tests, operational behavior, Roadmap state, known defects, and canonical documentation describe the same verified system.

Documentation must not be updated optimistically from a request. It must be updated from verified code and test behavior.

## 2. Canonical ownership matrix

| Change type | Documents that must be checked |
| --- | --- |
| Product scope, actor, acceptance behavior | `00`, `01`, `03`, `Roadmap.md` |
| New or changed requirement/business rule | `01`, `03`, relevant API/DB docs, `Roadmap.md` |
| Architecture/module/provider change | `02`, `06`, `08`, `09`, `Roadmap.md` |
| State transition or workflow change | `01`, `03`, `04`, `05`, tests, `Roadmap.md` |
| Database migration/table/index/constraint | `04`, `03`, repository tests, `07`, `08`, `Roadmap.md` |
| API route/schema/error/auth change | `05`, generated OpenAPI/client, `01`, `03`, `07`, `Roadmap.md` |
| Frontend route/workflow/UI state | `01`, `05`, `06`, `07`, `Roadmap.md` |
| AI prompt/schema/model/provider change | `01`, `02`, `03`, `06`, `07`, `08`, `09`, `Roadmap.md` |
| Search/fetch/parser/source policy change | `01`, `02`, `03`, `06`, `07`, `08`, `09`, `Roadmap.md` |
| Auth/security/privacy change | `01`, `02`, `04`, `05`, `07`, `08`, `09`, `Roadmap.md` |
| Deployment/config/secret change | `02`, `07`, `08`, `.env.example`, deployment manifests, `Roadmap.md` |
| Bug fix with no intended contract change | Current-state/known issue text, regression tests, `Roadmap.md` defect ledger |
| Completed Roadmap phase | `Roadmap.md`, `00` current status, all affected canonical docs |

Numbers refer to files under `docs/project/`.

## 3. Required metadata

Each canonical document should maintain:

- purpose and status;
- last verified date;
- last verified commit when repository exists;
- explicit Planned/In progress/Implemented/Partial distinctions where applicable;
- a synchronization checklist.

Agents must not invent a commit hash or mark a document verified without inspecting the repository state.

## 4. Per-task pre-change checklist

Before editing code:

- [ ] Read `README.md`, `AGENT.md`, `Roadmap.md`, and `00_PROJECT_CONTEXT.md`.
- [ ] Inspect `git status`, current branch, recent commits, and relevant tests.
- [ ] Identify the exact Roadmap task ID or defect ID.
- [ ] Identify requirement and business-rule IDs.
- [ ] Read relevant canonical documents and source-of-truth files.
- [ ] Record any existing code-document mismatch before changing behavior.
- [ ] Confirm no unrelated user changes will be overwritten.
- [ ] Define validation commands and documentation files expected to change.

## 5. During-change checklist

- [ ] Update tests with implementation, not later as optional cleanup.
- [ ] Keep comments and docs aligned with actual behavior.
- [ ] Do not mark a task complete while known functional defects remain.
- [ ] If scope changes, update the Roadmap task notes before silently expanding implementation.
- [ ] If an architectural decision changes, add or supersede an ADR.
- [ ] If a new defect is discovered, create a defect-ledger entry immediately.
- [ ] If a feature is implemented but broken or partially accepted, use In progress/Partial and link defect IDs.

## 6. Post-change checklist

### Implementation

- [ ] Intended behavior is implemented.
- [ ] Authorization and workspace boundaries are enforced.
- [ ] State and transaction invariants hold.
- [ ] External failures and retries are handled.
- [ ] No unrelated user work was changed.

### Tests

- [ ] Relevant unit tests pass.
- [ ] Relevant integration/database tests pass.
- [ ] Relevant API/frontend/E2E tests pass.
- [ ] Security and provider contract tests pass when affected.
- [ ] Lint, typecheck, format, and build pass before final handoff.
- [ ] Any unrun check is named with exact reason and impact.

### Documentation

- [ ] Requirement statuses match verified behavior.
- [ ] Domain states and flows match code.
- [ ] Database tables, migrations, indexes, and transactions match.
- [ ] API inventory, examples, errors, and access match OpenAPI/runtime.
- [ ] Architecture and codebase layout match actual files.
- [ ] Development commands and tests match scripts.
- [ ] Deployment configuration and runbooks match manifests.
- [ ] ADRs, risks, and technical debt are updated.
- [ ] `00_PROJECT_CONTEXT.md` current-status table is updated when material.
- [ ] `Roadmap.md` task state, notes, evidence, and defect ledger are updated.

### Git

- [ ] Working tree contains only intended changes.
- [ ] Commit message references Roadmap/defect context where practical.
- [ ] No secrets or generated local artifacts are committed.
- [ ] Merge/push occurs only after required validations and safety checks.

## 7. Roadmap status rules

Allowed task markers:

- `[ ]` Not started.
- `[~]` In progress or partially implemented.
- `[x]` Fully implemented and verified.
- `[!]` Blocked; blocker must be documented.
- `[-]` Intentionally removed from scope with decision reference.

A task may be `[x]` only when:

- all sub-checklists are complete;
- required tests pass;
- affected docs are synchronized;
- no known defect prevents acceptance;
- evidence note identifies code/tests/commands;
- any deferred work is separately tracked and does not contradict acceptance.

## 8. Defect ledger rules

Every known defect entry in `Roadmap.md` contains:

- stable ID `DEF-###`;
- discovered date and task/prompt;
- affected requirement/task;
- user-visible impact;
- severity and priority;
- reproduction or evidence;
- suspected cause if known;
- workaround if any;
- status and owner;
- validation required for closure.

An implemented feature with an unresolved acceptance defect cannot be marked complete.

## 9. Documentation drift handling

When code and docs disagree:

1. Do not choose the more convenient version automatically.
2. Inspect runtime code, migrations, tests, configuration, and recent history.
3. Determine actual behavior and intended requirement.
4. Report the conflict in the current task notes.
5. Fix code, docs, or both in one coherent change.
6. Add regression or drift test.
7. Update Roadmap and defect ledger.

## 10. Release documentation gate

Before a release:

- [ ] All completed tasks since the last release have synchronized docs.
- [ ] No `[x]` task has open acceptance defect.
- [ ] Current status in `00` is accurate.
- [ ] OpenAPI and API document match.
- [ ] Migration list and database document match.
- [ ] Environment and secret docs match deployment manifests.
- [ ] Known limitations and operational gates are visible.
- [ ] Changelog/release notes identify user-visible changes and migrations.
- [ ] Production readiness checklist reflects actual evidence.

## 11. Roadmap completion transition

When every required Roadmap task and final completion gate is complete:

1. Verify every task is `[x]` or explicitly `[-]` with an accepted decision.
2. Verify defect ledger has no open release-blocking defect.
3. Verify full validation suite and production readiness evidence.
4. Change Roadmap mode from `ACTIVE_DEVELOPMENT` to `MAINTENANCE`.
5. Add completion date, commit, release, and evidence summary.
6. Keep `Roadmap.md`; do not delete it.
7. Remove the mandatory `Roadmap.md` read line from `AGENT.md` as instructed in the Roadmap transition section.
8. Update `AGENT.md` to use current-state docs and issue/defect tracking for maintenance work.
9. Continue updating canonical docs for every maintenance change.

Roadmap completion does not end documentation discipline.

## Verified synchronization record — TASK-CRAWL-001 (2026-08-08)

The affected current-state, architecture, domain-flow, database, codebase, development/testing, operations, decisions/risks, API, and Roadmap documents contain addenda describing the verified AI-independent pipeline. TASK-CRAWL-001 is `[x]` after clean task-only full tests, task-scoped quality checks, docs/OpenAPI checks, and isolated PostgreSQL migration verification; independent repository baseline debt remains recorded in the root Roadmap defect ledger.

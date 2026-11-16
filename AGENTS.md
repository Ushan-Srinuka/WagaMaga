# WagaMaga AI repository instructions

## Context and scope

- Read the SRS and architecture for architectural work; for a focused task, read the relevant requirements and supporting guide.
- The M0 scaffold contains a React connection screen, FastAPI health endpoints, PostgreSQL/pgvector migration setup and a worker entry point. Business features remain unimplemented. Implement further application code only within the user's requested milestone or feature.
- Keep React, FastAPI, PostgreSQL/pgvector, private document storage and a separate worker. Record supporting-tool decisions in docs/DECISIONS.md.
- Use docs/CODEX_WORKFLOW.md and docs/ROADMAP.md to scope work. Complete the requested scope without adding unrelated features.

## Engineering boundaries

- Keep a modular monolith. Routes handle HTTP, services enforce rules, and integrations isolate external providers. Workers reuse domain services.
- Enforce ownership and case assignment on the server, including source viewing and job status. Administrator status does not grant blanket access to private farms or chats.
- Treat uploads, provider responses and model output as untrusted. Models may not execute SQL, shell commands or unrestricted mutations.
- Bind advisor clearance and farmer acceptance to the same immutable proposal version and action hash. Revisions require fresh decisions.
- The first flow that changes tasks must include persisted actions/evidence/decisions, precondition checks, atomic writes, execution uniqueness and audit evidence. Do not postpone these safeguards solely because a demo is called V0.
- Keep credentials, real farmer data and uploaded private files out of source control and logs. Use synthetic test data.
- Use PostgreSQL with pgvector for database, transaction and retrieval integration tests; do not substitute SQLite.

## Verification and delivery

- Exact setup and check commands belong in docs/DEVELOPMENT.md and docs/TESTING.md. Keep those commands aligned with manifests, locks and CI; report anything not verified.
- Run checks appropriate to changed behaviour. Business changes need meaningful rule/permission/integration coverage; simple documentation changes need link and consistency checks.
- Use deterministic provider doubles for ordinary tests and versioned datasets plus human review for AI quality. Do not report mocked results as live evaluation.
- Update API, UI, database and operations guides when their contracts change. Preserve stable SRS requirement identifiers.
- Report what changed, checks actually run, outcomes and remaining limitations. Never claim implementation, measurements or review that did not occur.
- Preserve existing user changes. Keep commits focused when committing is part of the requested workflow.

## Code review rules

Prioritize authorization gaps, stale approvals, duplicate effects, partial writes, evidence eligibility, upload handling and private-data exposure. Check missing failure-path coverage as well as the happy path. See SECURITY.md, docs/API.md and docs/TESTING.md for details.

# Contributing to WagaMaga AI

Status: contribution workflow for a project that currently contains documentation only.

## Before changing behaviour

Read the relevant SRS requirements, architecture sections and [documentation index](docs/README.md). Identify the milestone and acceptance scenario in [ROADMAP.md](docs/ROADMAP.md). Keep the agreed stack and initial product scope.

When a requirement changes, record the reason in [DECISIONS.md](docs/DECISIONS.md) and update the affected baseline. Do not silently weaken an acceptance gate to make a check pass.

## Working on a change

1. Inspect the working tree and preserve existing changes.
2. Once Git exists, use a focused branch such as `docs/testing-guide`, `chore/foundation` or `feat/farm-records`.
3. Define the observable result and relevant FR/DR/NFR or AT identifiers.
4. Implement one coherent slice, including migrations and UI states where needed.
5. Run the applicable checks in [TESTING.md](docs/TESTING.md).
6. Review the diff for regressions, secrets, authorization gaps and unintentional files.
7. Update relevant documentation and summarize verification. Commit the finished slice when using the project's commit workflow.

The same process applies to Codex-generated code. The developer remains responsible for understanding the change and reviewing its evidence.

## Pull requests

A pull request should state:

- The user-visible problem and resulting behaviour.
- Scope and requirement/acceptance identifiers.
- Tests run and results, including any checks not run.
- Migration, configuration or compatibility effects, if applicable.
- Any unresolved limitation that affects acceptance.

Keep unrelated refactoring separate. Include screenshots for meaningful UI changes and evaluation reports for retrieval or prompt changes. Do not attach real farmer data.

## Completion criteria

- Relevant acceptance examples pass, including permission and failure paths.
- Database effects and migrations are checked against PostgreSQL/pgvector where relevant.
- Frontend checks and build pass when frontend code changes.
- API contracts, setup instructions and operational consequences are documented.
- No secrets, uploaded private documents or generated dependency directories are committed.
- Remaining work is recorded honestly in ROADMAP.md or DECISIONS.md.

## Security and licensing

Follow [SECURITY.md](SECURITY.md) for vulnerability handling. A code license and agricultural source permissions remain open decisions; public availability does not establish reuse rights. Do not add third-party material without recording its license or permission.

Exact lint, build and test commands will be added during M0. There is no implemented CI or enforced branch policy yet.

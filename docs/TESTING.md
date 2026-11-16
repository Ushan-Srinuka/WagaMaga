# Testing strategy

Status: M0 foundation complete, 16 November 2026. Remote CI and fresh Windows checkout verification are recorded below. Business and AI release suites are future work. Tooling is locked, and the commands below exercise real foundation behaviour.

## M0 commands

From the project root in PowerShell:

```powershell
.\scripts\uv.ps1 run ruff check . ../scripts/configure_local.py --config pyproject.toml
.\scripts\uv.ps1 run ruff format --check . ../scripts/configure_local.py --config pyproject.toml
.\scripts\uv.ps1 run pytest -m "not integration"
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run format:check
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run build
```

For real PostgreSQL checks, first start Docker and run the foundation migration as described in DEVELOPMENT.md, then:

```powershell
.\scripts\uv.ps1 run pytest --require-database
.\scripts\uv.ps1 run python -m app.worker --once
```

On Linux/CI, run the equivalent `uv run ...` commands from backend/ and `npm ...` from frontend/. Tests use root .env settings but the deterministic unit/API suite explicitly isolates its configuration. Database checks use only the dedicated `_test` database; they apply actual Alembic migrations, exercise vector/full text queries and verify that the application role cannot rewrite migration state or create schema objects. They do not create farm/business tables or claim transactional proposal coverage.

The backend lock uses HTTPX 2 (`httpx2`) because the installed Starlette TestClient requires that distribution for its current non-deprecated transport. This remains the selected HTTPX testing role. The pytest cache uses `.pytest-cache` to avoid the pre-existing sandbox-owned cache directory on this Windows host.

The frontend suite checks that API availability is distinct from database readiness and that retry recovers from an unavailable API. The build includes the strict TypeScript check. Playwright remains deferred until a business journey exists; any manual/headless foundation smoke checks are recorded separately.

## M0 local verification record - 16 November 2026

Environment: Windows 11 Pro, CPython 3.14.10, uv 0.13.8, Node 24.13.0/npm 11.6.2 and the digest-pinned PostgreSQL 18/pgvector container in compose.yaml. This record reports local execution, not a production deployment or a remote CI run.

| Check | Actual outcome |
| --- | --- |
| Backend locked install | `uv sync --locked` passed with the generated uv.lock |
| Python lint/format | Ruff check and format check passed, including the local configuration generator |
| Backend tests | 12 passed, including 3 real PostgreSQL integration tests; none skipped in `pytest --require-database` |
| Migrations | Development database at `0001_foundation (head)`; integration fixture applied the same migration to the separate test database |
| Database capabilities/privileges | PG18, vector distance and full text checks passed; app role cannot create schema objects or change revision metadata |
| Worker | Separate `python -m app.worker --once` process reported database ready and exited successfully; no durable job handlers claimed |
| Frontend clean install | Regenerated package-lock.json and `npm ci` passed after correcting compatible dependency versions |
| Frontend checks | ESLint, Prettier check and strict TypeScript/production build passed |
| Frontend behaviour | 2 tests passed: degraded DB state is distinct from API failure, and user retry recovers a failed connection |
| Browser smoke | Bundled Playwright with installed headless Edge checked 360px and 1280px, real API/database status, retry, no horizontal scrolling and no page errors |
| Swagger | UI rendered through the Vite proxy and the API returned its OpenAPI schema |
| Package audit | `npm audit` reported zero production/development findings after the scoped minimatch override and clean lock regeneration |
| Local configuration | A repeated generator run preserved existing .env credentials; Compose configuration validation passed |
| Git | Initialized branch main; generated credentials, tools, environments, private data and exports are ignored; no commit or remote created |

The browser smoke used existing bundled tooling and saved ignored screenshots under `.tools/screenshots/`. It is a local foundation check, not a committed business end-to-end suite. The uv-managed interpreter/environment are local ignored setup artifacts, not committed dependencies.

At this initial local checkpoint, clean-checkout verification and remote CI were still pending. The completion record below supersedes that gap. The historical Windows servicing limitation remains an operating concern. V0 agricultural evidence, business authorization, proposal transactions, durable jobs and all later release gates remain unimplemented/unverified.

## Initial local commit review - 16 November 2026

The pre-commit review reran the documented non-integration backend command (9 passed, 3 integration tests deselected), frontend tests (2 passed), Ruff lint/format, ESLint, Prettier and the TypeScript/production build; all passed. All 44 local Markdown links resolved. The 85 candidate files contained no exact matches to generated local credential values or the checked common secret patterns. This is a bounded check, not a guarantee against every possible secret format.

Docker Desktop's Linux engine was stopped during this review. The attempted full backend suite was interrupted while waiting for its database connection; database integration and worker readiness were not reverified for this commit. Their earlier successful results above are historical evidence. No service startup, deployment or business implementation was performed in this review. Remote CI and an independent clean checkout remain unverified.

The initial local commit includes documentation, foundation source, manifests, dependency lockfiles and CI configuration. Local credentials, installed dependencies, private data, caches, local tools and generated exports remain ignored. No remote is configured and no push is part of this checkpoint.

## M0 completion: CI and fresh checkout - 16 November 2026

[GitHub Actions run 43828618767](https://github.com/Ushan-Srinuka/WagaMaga/actions/runs/43828618767), for commit `62c6c625c47822ebd8ac04388f449fc407c87770`, completed successfully. The backend job passed locked installation, lint/format, PostgreSQL/pgvector startup, migration, database-required tests, separate worker startup and container shutdown. The frontend job passed clean installation, lint, format, tests and production build. Failure-only database diagnostics were correctly skipped.

A separate clone of that published commit was created under ignored `.tools/m0-clean-checkout/` on this Windows machine. It started without .env, installed dependency directories or private data. The documented project-local uv bootstrap, `uv sync --locked` and `npm ci` succeeded; the clone used the already available pinned CPython 3.14.10 interpreter and created its own environment and dependency directories. This is a fresh source/dependency checkout on the existing host, not a claim that a second Windows machine or an OS installation was tested.

The initial clone exposed a Windows failure: default Git CRLF conversion made Prettier reject four frontend files. Setting the default Git text policy to LF in `.gitattributes`, with the existing PowerShell CRLF exception retained, fixed it. The four files were restored from Git with `core.autocrlf=true` after that change; `git ls-files --eol` confirmed LF working copies and Prettier passed. Their source contents did not change. All results below include this correction.

| Fresh-checkout check | Actual outcome |
| --- | --- |
| Locked installs | Fresh uv bootstrap and Python environment, `uv sync --locked`, `npm ci`; npm reported zero audit findings |
| Static checks | Ruff check/format, ESLint and Prettier passed |
| Backend | `pytest --require-database`: 12 passed, including all 3 real PostgreSQL tests |
| Frontend | 2 tests passed; strict TypeScript and production build passed |
| Database | New isolated Compose project `wagamaga-m0-verify`, new named volume and generated credentials; port 55433 kept it separate from the normal 55432 setup |
| Migration/readiness | `alembic upgrade head` succeeded; live API returned `ready`, revision `0001_foundation` and pgvector `0.8.7` |
| Separate worker | `python -m app.worker --once` reported database ready and exited successfully |
| Actual startup/browser | API on localhost:8000 and Vite on localhost:5173; 360px/1280px browser checks passed real connectivity, retry, no horizontal scroll and no page errors; Swagger rendered through Vite |
| Exclusions | Clone credentials, local tools, private data, Python environment, node_modules and build output remained ignored |

To isolate this verification, the documented configuration command used `--port 55433` and Compose commands used `-p wagamaga-m0-verify`. The normal database project/volume and original credentials were not changed. The temporary API and Vite processes were stopped, and `docker compose -p wagamaga-m0-verify down` removed the verification containers/network while preserving the volume. No deployment or business feature was added. The existing bundled browser tooling ran the foundation smoke check; its script/screenshots and the clone are ignored artifacts.

M0's foundation exit criteria are met. This does not verify production hosting, OS servicing, private-user access, AI quality or any later business milestone. User management is the next requested scope and remains unimplemented.

## Selected tools and evaluation methods

| Layer | Recommendation | Purpose |
| --- | --- | --- |
| Manual API | FastAPI Swagger UI | Explore schemas and try requests |
| Python rules | pytest | Validation, state transitions, dates and policies |
| API automation | pytest + FastAPI TestClient; HTTPX for async tests | Contracts, authentication and permission failures |
| Database/integration | pytest + isolated PostgreSQL with pgvector | Persistence, migrations, full text/vector queries, locks and rollback |
| React behaviour | Vitest + React Testing Library | User interactions, forms and UI states |
| Browser journeys | Playwright | Frontend/API/database flow and responsive navigation |
| AI quality | Versioned questions, evaluation script and human review | Retrieval recall, applicability, claim support and abstention |
| Operating checks | Declared load/recovery procedure | Latency, timeouts, restart and restoration |

FastAPI/pytest is supported by the architecture. The user accepted the frontend verification tools under D17; acceptance does not install them. A dedicated test database or container is sufficient initially; Testcontainers remains optional automation. SQLite cannot substitute for PostgreSQL transaction/vector tests.

## Accepted M0 quality tooling

The user accepted D17 on 15 November 2026 in [DECISIONS.md](DECISIONS.md). See [DEVELOPMENT.md](DEVELOPMENT.md) for the local setup. Backend/frontend dependencies and foundation checks exist; full product, AI and operating verification remain future work.

| Check | Accepted tool | Initial scope |
| --- | --- | --- |
| Python lint/imports/format | Ruff | Check backend code and formatting; no separate Black/isort initially |
| Backend behaviour/API | pytest + TestClient/HTTPX | Real foundation checks first, feature coverage as behaviour arrives |
| Database | pytest + PostgreSQL 18/pgvector test database | Migration/extension checks; later constraints, transactions and retrieval |
| Frontend type safety | TypeScript compiler | Explicit type check separate from Vite's build |
| Frontend lint | ESLint with TypeScript/React rules | Code-quality rules; avoid conflicting formatter rules |
| Frontend format | Prettier | Formatting check |
| Components | Vitest + React Testing Library + DOM environment | Add with interactive components and observable behaviour |
| Browser | Playwright | Add a small Chromium journey when frontend/API behaviour exists |

Ruff does not type-check Python; a dedicated backend type checker is not selected in the accepted initial setup. Keep ordinary CI provider-independent. Do not install browser binaries or create placeholder suites merely to fill a tooling checklist. Add exact commands after the corresponding manifests/configurations exist and have been verified.

## What to test in each part

| Area | Meaningful examples | SRS acceptance mapping |
| --- | --- | --- |
| Identity/access | Expired/invalid JWT, revoked refresh, role escalation, another owner's IDs, unassigned advisor, source/job access | AT02; FR01-FR04; NFR01 |
| Farms/cultivations | Coordinates, units/positive area, planned dates, estimated/confirmed stage, observation history, archive blocking execution, filters/pagination | AT01; FR05-FR10 |
| Knowledge | Invalid upload, parse failure, no retrieval before review, immutable versions, withdrawal and source viewer authorization | AT03; FR11-FR14 |
| Retrieval/advisory | Lexical/vector/hybrid comparison, filters, cited claims, missing/conflicting evidence, conversation scope, source injection | AT04-AT05; FR15-FR19; NFR02/NFR07/NFR08 |
| Proposal/review | Bounded horizon, schema/evidence validation, routine/referred/blocked actions, version/hash binding, advisor cannot consent | AT06-AT08; FR21-FR27 |
| Execution/tasks | Stale/expired/withdrawn proposal, changed task, duplicate keys, concurrent acceptance, injected failure and rollback, completion/cancellation history | AT08-AT09; FR27-FR30; NFR06 |
| Weather/notices | Labelled fixtures, units/timestamps, live response normalization, stale/outage suppression, repeated-event dedupe, cancelled-task reminder suppression | AT10; FR31-FR36 |
| Lifecycle/audit | Eligible chat deletion preserves decision evidence, declared account deletion, historical citations, app role cannot rewrite audit rows | AT11; FR20; DR01-DR05 |
| Worker/outbox | Lease expiry, bounded retry, restart recovery, unique effects and owner-scoped job status | AT09-AT10/AT12; NFR06/NFR09 |
| UI/operations | Mobile/desktop forms, keyboard access, pending/errors, AI timeout, degraded providers, latency and actual restore | AT12; NFR03-NFR11 |

## Isolation and determinism

- Use synthetic actors, farms and weather snapshots. Maintain at least two farmers, an assigned and unassigned advisor scenario, and an administrator without private-data privileges when those roles exist.
- Separate test databases/storage from developer and deployed data. Reset only explicitly configured disposable test resources.
- Run migrations against the test database, not a parallel hand-written schema.
- Keep model/weather responses deterministic in ordinary suites. Test malformed payloads, outages and bounded timeouts with controlled doubles.
- Test concurrency with independent connections/transactions; a repeated sequential request alone does not prove concurrent correctness.
- Verify both response and database effects. Inject a failure after an intermediate task write to prove full rollback.
- Use controlled clocks for expiry/freshness/retry rules where practical rather than long sleeps.

## AI evaluation gates

V0 needs at least 10 questions mapped to evidence, including a missing-evidence case. V1 needs at least 30 labelled questions, including answerable, unanswerable, outdated and conflicting cases. Compare keyword-only, vector-only and hybrid on the same corpus/questions.

V1 targets: evidence Recall@5 >= 0.80 on answerable cases; at least 90% supported material claims under human review; every citation resolves to a permitted passage. Any unsupported actionable treatment recommendation fails the release gate. Schema validity and an LLM judge alone cannot establish correctness. See [KNOWLEDGE_EVALUATION.md](KNOWLEDGE_EVALUATION.md).

## Checks and CI

During M0, add exact commands for backend lint/checks, applicable tests, frontend checks/build and foundation database verification. As features arrive, add stable retrieval evaluation and browser smoke tests. Do not claim a suite passes when no tests are collected.

Recommended CI order: static checks; Python unit/API tests; PostgreSQL integration tests; frontend behaviour tests/build; stable retrieval checks; selected browser journeys. Run external-model quality/cost evaluations separately when needed, recording versions and human review rather than requiring live provider calls on every commit.

Run measured performance tests on a declared environment: SRS NFR04 targets p95 non-AI CRUD below 1 second for up to 5,000 passages and 10 concurrent users, excluding file transfer. Record AI p50/p95 separately and verify the initial 60-second interactive generation timeout. Verify backup restoration before a real pilot.

## Acceptance record template

Record milestone/commit, date, environment, dataset/index/model/prompt versions, requirement/AT IDs, command or procedure, result, evidence artifact and limitations. Keep targets distinct from measured results. A successful Swagger call is useful evidence for one example, not proof of the full release.

## Tool references

- [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Vitest guide](https://vitest.dev/guide/)
- [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/)
- [Playwright](https://playwright.dev/docs/intro)
- [PostgreSQL tests with Testcontainers](https://docs.docker.com/guides/testcontainers-python-getting-started/)

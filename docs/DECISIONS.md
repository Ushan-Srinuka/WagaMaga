# Decision register

Last updated: 16 November 2026. The user accepted tooling decisions D01-D04 and D17 on 15 November and subsequently authorized the project base scaffold. The implementation record below distinguishes installed/verified foundation components from later product features. Other unresolved decisions remain open.

## Baseline constraints

These choices come from the SRS and architecture, rather than new tooling selections.

| ID | Baseline |
| --- | --- |
| B01 | English responsive React client; chilli in a validated Anuradhapura area |
| B02 | FastAPI modular monolith and separate worker |
| B03 | PostgreSQL for transactions, full text retrieval and pgvector similarity |
| B04 | Private documents, reviewed immutable versions and resolvable evidence |
| B05 | AI proposals; explicit human decisions; backend-controlled execution |
| B06 | PostgreSQL durable jobs, bounded retries and duplicate-safe effects by V1 |
| B07 | Labelled weather fixtures in V0, basic live integration in V1 |
| B08 | Asia/Colombo initial display timezone; UTC event timestamps |

## Sequencing clarification to carry into implementation

Architecture section 9 places transactional execution in V1, while the SRS V0 gate includes a manual proposal and acceptance flow. SRS DR02 requires actions, evidence, decisions, forecast snapshots and execution uniqueness in the first release that changes tasks.

Recommended interpretation: if V0 acceptance changes tasks, implement the minimal atomic execution and duplicate-prevention controls with that flow, along with immutable decisions and precondition checks. Full V1 breadth can follow later. If V0 only records acceptance, label it as non-executing and do not claim task execution. Update the architecture release wording when this interpretation is adopted.

Do not infer permission to perform unsafe task mutations from the release label.

## Decision summary

| ID | Question | When needed | Recommendation/status |
| --- | --- | --- | --- |
| D01 | Python/Node versions and package managers? | M0 | Accepted 15 November 2026: standard CPython 3.14.x + uv; Node.js 24.x LTS + npm 11.x. Exact patches pending M0 verification. |
| D02 | React language and build tool? | M0 | Accepted 15 November 2026: React + TypeScript strict mode + Vite, using a stable compatible React TypeScript template. |
| D03 | Database driver/ORM and migrations? | M0 | Accepted 15 November 2026: synchronous SQLAlchemy 2.1.x + Psycopg 3.3.x binary package + Alembic 1.x; pgvector Python integration when vector columns are introduced. |
| D04 | Local PostgreSQL/pgvector runtime? | M0 | Accepted 15 November 2026: Docker Desktop WSL 2 backend + Compose v2-compatible CLI; PostgreSQL 18 with pgvector 0.8.x. Run app processes natively in PowerShell initially. See the installed Compose v5 compatibility note below. |
| D05 | Code license and source repository/remote? | Repository setup/sharing | Not selected |
| D06 | Exact V0 identity, acceptance and execution scope? | Before V0 mutations | Synthetic local records only; apply DR02 when tasks change |
| D07 | Supported area, evidence coverage and reuse rights? | Before publishing the corpus | Confirm chilli applicability and permissions |
| D08 | Parser, upload limits, scan mechanism and extraction fallback? | Before ingestion | Bound worker resources; OCR optional and evaluated |
| D09 | LLM/embedding provider, model, dimensions, privacy and budget? | Before real AI evaluation | Compare using fixed questions; fake providers for ordinary tests |
| D10 | Routine/referred/blocked categories and qualified reviewer? | Before executable proposals/pilot | Review policy with an agricultural advisor; label simulated review |
| D11 | Session durations, hash library, recovery, rate limits, CSRF and CORS? | Identity implementation | Security design defined; exact configuration open |
| D12 | Inaccessible-object 403/404 policy, pagination and provider error status? | First domain API | Use a consistent non-disclosing contract |
| D13 | Weather provider, precision, permissions, freshness and thresholds? | Live weather/review rules | Fixtures first; thresholds require domain validation |
| D14 | Retention, account deletion, reporting contact and provider terms? | Before real user data/external access | No durations/contact invented |
| D15 | Host, file storage, TLS, backup tooling and monthly budget? | Deployment planning | Preserve separate API/worker and private DB/storage |
| D16 | UI palette, typography, component library and final navigation? | Before UI implementation | See UI_DESIGN.md; no library selected |
| D17 | Testing, linting and formatting tools? | M0, expanded as features arrive | Accepted 15 November 2026: pytest/TestClient/HTTPX, Ruff; TypeScript compiler, ESLint, Prettier, Vitest/React Testing Library; Playwright when browser journeys exist. |

The solo developer owns engineering choices. Agricultural policy and evidence applicability require qualified domain input. These dependencies do not mean every routine implementation detail requires a separate approval.

## Accepted Windows tooling package - 15 November 2026

Status: proposed and then explicitly accepted by the user on 15 November 2026 for D01-D04 and D17. The user's instruction was to use the proposed development setup and record the tooling proposals as accepted, while performing read-only checks only. No dependencies were installed and no application/configuration files were generated. Keep all other open decisions open. Official references and the original rationale are retained below; end-to-end dependency resolution and local compatibility still need M0 verification.

### D01: runtimes and package managers

Recommend standard, GIL-enabled CPython 3.14.x and Node.js 24.x LTS, taking the current supported patch in each line when implementation starts. Python 3.14 remains in bugfix support; Node 24 remains an LTS line. These are deliberate established release lines, not claims that they are the newest major versions. See [Python version status](https://devguide.python.org/versions/) and [Node release status](https://nodejs.org/en/about/previous-releases).

Use uv for the backend virtual environment, dependencies and cross-platform lockfile. It adds one tool but avoids separately designing a pip/venv/lock workflow. Use npm for the frontend; it is already available locally and is sufficient for one React application. Do not introduce a second JavaScript package manager. See [uv project management](https://docs.astral.sh/uv/guides/projects/) and [npm clean installs](https://docs.npmjs.com/cli/v11/commands/npm-ci/).

Alternative considered: pip + venv is familiar but needs an additional agreed dependency-lock workflow; Poetry/pnpm introduce tools that are unnecessary for this project initially. Python 3.13 is already security-only in the checked schedule. Node 26 LTS is also viable, but Node 24 meets the proposed tooling baseline and matches the installed major. Exact runtime/uv/npm patches must be recorded and verified before M0 is called reproducible.

### D02: frontend

Recommend TypeScript strict mode and Vite for the existing React client. Types help maintain API request/response contracts; Vite provides local development and a static production build without adding a second application server framework. Vite has an official React TypeScript template. Resolve the stable compatible React/Vite/TypeScript versions together and lock them during M0. See [Vite setup and templates](https://vite.dev/guide/).

Alternative considered: plain JavaScript has less initial syntax but weaker compile-time contract checks. A full-stack React framework is unnecessary for the current FastAPI-plus-responsive-client design. This decision does not select a CSS/component library, state manager or routing library; D16 remains open.

### D03: database access and migrations

Recommend SQLAlchemy 2.1.x, Psycopg 3.3.x using its binary distribution for local Windows development, and Alembic 1.x. SQLAlchemy covers ORM/Core queries and explicit transactions; Psycopg connects to PostgreSQL; Alembic versions schema changes. Add the pgvector Python integration when vector columns/queries are needed. Psycopg documents support for Windows, Python 3.14 and PostgreSQL 18. See [SQLAlchemy platforms](https://docs.sqlalchemy.org/en/21/intro.html), [Psycopg installation/support](https://www.psycopg.org/psycopg3/docs/basic/install.html) and [Alembic](https://alembic.sqlalchemy.org/en/latest/).

Start with synchronous sessions to keep transaction boundaries and debugging simpler. Use normal synchronous FastAPI route boundaries for blocking DB work or explicitly offload that work; never run blocking sessions directly on the async event loop. API requests and worker jobs own separate sessions, and sessions must not be shared across concurrent threads/jobs. Revisit async database access only if workload evidence justifies the added complexity. See [FastAPI concurrency guidance](https://fastapi.tiangolo.com/async/).

Alternative considered: async SQLAlchemy is valid but adds lifecycle complexity before a measured need. A second driver such as asyncpg and a second migration tool are unnecessary initially. Keep PostgreSQL-specific full text/vector operations available through explicit queries rather than forcing everything into generic ORM patterns.

### D04: local infrastructure

Recommend Docker Desktop with the WSL 2 backend and Compose v2 for a PostgreSQL 18/pgvector 0.8.x container. Choose a documented versioned pgvector image and pin its resolved digest during M0; do not use a floating `latest` image. Use a named volume for database data. PostgreSQL 18 is a supported line and the pgvector project publishes PG18 images. See [PostgreSQL support](https://www.postgresql.org/support/versioning/), [pgvector Docker images](https://github.com/pgvector/pgvector#docker) and [Docker Windows prerequisites](https://docs.docker.com/desktop/setup/install/windows-install/).

Run React, FastAPI and the separate worker natively from PowerShell initially; Docker's WSL backend does not require moving this repository into a Linux filesystem or maintaining duplicate Node/Python installations. This avoids Windows pgvector compilation while keeping application debugging direct. Keep original document files in one private local directory available to API/worker when ingestion is introduced. Use separate development/test databases and file directories, and bind development services to localhost.

Alternative considered: native PostgreSQL requires managing the extension separately; containerizing every app process adds image/debugging setup before it is needed. If Docker cannot run on the machine, revisit D04 explicitly using a real PostgreSQL/pgvector alternative; do not substitute SQLite. Current host checks verify WSL 2 availability but identify a stopped Docker engine and an out-of-support Windows release; see the audit in DEVELOPMENT.md.

The installed Compose plugin is v5.5.0. Docker documents Compose v5 as functionally equivalent to v2 using the same `docker compose` command, so the accepted v2 workflow does not require downgrading the installed plugin. Verify the actual project configuration during M0. This is a compatibility clarification, not a change to the application stack. See [Docker Compose FAQ](https://docs.docker.com/compose/support-and-feedback/faq/).

The separate worker remains a Python process from the same backend project and environment. Add PostgreSQL job leases/retries as durable workloads arrive. Redis, Celery, Kubernetes, an agent framework and a separate AI service are not part of the accepted setup.

### D17: verification tools

- Backend: pytest plus FastAPI TestClient/HTTPX for API tests; dedicated PostgreSQL/pgvector integration tests for migrations, transactions and retrieval.
- Python style: Ruff for linting, import sorting and formatting; avoid overlapping Black/isort tools initially. Ruff is not a static type checker; a dedicated Python type checker remains an optional later choice.
- Frontend: TypeScript compiler for type checks, ESLint for code rules and Prettier for formatting. Disable overlapping ESLint formatting rules.
- Components: Vitest plus React Testing Library and a DOM test environment when interactive components exist.
- Browser journeys: Playwright when the first real frontend/API workflow exists, beginning with a small Chromium smoke suite.
- Manual API exploration: built-in Swagger UI. Postman is optional, not a second mandatory suite. AI evaluation remains the dataset-plus-human-review process already defined in TESTING.md.

See [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/), [Ruff](https://docs.astral.sh/ruff/), [ESLint](https://eslint.org/docs/latest/use/getting-started), [Prettier](https://prettier.io/docs/), [Vitest](https://vitest.dev/guide/), [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/) and [Playwright](https://playwright.dev/docs/intro). Install/configure tools with their actual testable slice rather than creating empty suites that imply coverage.

### Read-only local observations

The first restricted-shell checks reported no registered Python and could not access Docker configuration, WSL status or hardware information. Approved read-only host checks corrected those limitations: Python 3.13.2 is installed and registered; the accepted Python 3.14 target was not found. uv was not on PATH and was absent from the checked user-local/cargo locations. Node v24.13.0, npm 11.6.2 and Git 2.49.0.windows.1 run successfully.

Host checks also found WSL 2.7.14.0 with default version 2 and a stopped docker-desktop WSL 2 distribution. Docker CLI 29.7.2 and Compose 5.5.0 run, but the desktop-linux engine pipe is absent and no Docker Desktop/backend process was found. Windows is 11 Pro build 22631 (23H2); its Microsoft servicing has ended. Hardware reports approximately 7.7 GiB visible RAM and an active hypervisor; individual CPU virtualization flags need corroboration. See [DEVELOPMENT.md](DEVELOPMENT.md) for commands, evidence, sources and readiness categories.

Affected guides: DEVELOPMENT.md for the accepted local setup/audit and TESTING.md for accepted tool roles. No software was installed, updated, started or stopped, and no system settings were changed. Observed runtime patches are not claims of current patch currency. M0 must still verify dependency resolution, binary availability, database startup, extension/migration access and exact check commands before reporting implementation readiness.

## M0 implementation record - 16 November 2026

The user requested the project base structure. The scaffold keeps the accepted stack and adds no farm, authentication, advisory, proposal or weather business features.

- D01: uv 0.13.8 and CPython 3.14.10 are available in the ignored project-local tooling/environment. Node 24.13.0 and npm 11.6.2 are pinned for reproducibility. These are tested pins, not claims to be the newest security patches. Existing Python 3.13 was preserved; no Windows update was attempted.
- D02: React 19.3.1, Vite 8.3.8 and TypeScript 6.0.x resolve in package-lock.json. The current template offered TypeScript 7, but the selected TypeScript ESLint parser supports versions below 6.1. The compatible 6.0 line is deliberate; strict mode remains enabled. No UI/component/routing library was selected under D16.
- D03: uv.lock resolves SQLAlchemy 2.1.8, Psycopg 3.3.9, Alembic 1.20.1 and FastAPI 0.163.1. Migration 0001 enables pgvector and grants only read access to revision metadata for the app role. There are no business tables.
- D04: Docker Desktop's Linux engine was started for validation. compose.yaml pins a verified Linux/amd64 PostgreSQL 18/pgvector image digest. Development and test databases use separate names; the app role is not a superuser/schema owner. The host port is 55432 because Windows rejected 5432. Production deployment and OS servicing are still unresolved operating work.
- D17: backend lint/tests and frontend lint/format/tests/build are configured. Starlette's installed TestClient selects the HTTPX 2 distribution (httpx2 2.16.0), avoiding its deprecated HTTPX 0.x fallback. A scoped minimatch >=11.0.1 override fixes the TypeScript ESLint toolchain's reported moderate advisory; a clean install resolves 11.0.8 and npm audit reports zero findings at this checkpoint. Recheck on dependency updates.

Both lockfiles are generated by their package managers. The repository was initialized on branch main with no commit or remote. A sandbox-owned, uncommitted Git initialization was preserved under ignored .tools and replaced under the Windows user so Git works without a global safe.directory exception. Generated .env credentials, private storage, downloaded tools and dependency folders are ignored.

Completion update, 16 November 2026: the initial commit was published to the configured GitHub repository and its backend/frontend CI jobs passed. Fresh Windows checkout verification exposed Git's CRLF conversion conflicting with Prettier. The supporting D17 check configuration now uses a default LF Git text policy with the PowerShell CRLF exception retained. The corrected checkout passed foundation startup and checks; see TESTING.md. No authentication library, session policy or account-management decision was accepted by this verification task.

The earlier PDF and read-only audit describe the pre-scaffold snapshot; they are retained as historical records and do not override current code or this entry.

## Recording an outcome

For each resolved decision, record ID, date, status, context, chosen option, alternatives, consequences and affected documents. Keep superseded outcomes with their replacement link. Never mark a decision resolved just because Codex generated a suggestion.

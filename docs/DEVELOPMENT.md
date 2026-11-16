# Development guide

Status: M0 foundation complete on 16 November 2026. React, FastAPI health routes, a separate worker entry point, Alembic and PostgreSQL/pgvector configuration are present. Fresh-checkout startup and remote CI are verified in TESTING.md. Business features remain unimplemented.

## M0 local setup

From the project root, using PowerShell:

```powershell
.\scripts\uv.ps1 sync --locked
.\scripts\uv.ps1 run python ../scripts/configure_local.py
npm.cmd --prefix frontend ci
docker compose up -d --wait
.\scripts\uv.ps1 run alembic upgrade head
```

The configuration generator is standard-library-only and also works with the existing Python 3.13 installation. The commands above use the uv-managed interpreter so an extra system Python is not required once uv is available. It creates ignored `.env` credentials once, never prints them and never overwrites an existing file. PostgreSQL is published on `127.0.0.1:55432`; port 5432 was unavailable on this machine. The database container listens on its normal internal port 5432. Relative document storage paths resolve from the repository root in both API and worker.

The PowerShell uv wrapper uses a global uv executable if available, otherwise the ignored `.tools/uv/bin/uv.exe` copy used during scaffolding. It runs in `backend/`, stores downloaded Python/cache files under `.tools/`, and uses backend/.python-version. New checkouts need uv installed first; the ignored tools are not part of Git. The scaffold was verified with uv 0.13.8, CPython 3.14.10, Node 24.13.0 and npm 11.6.2. Existing Python installations were not removed and Windows was not updated. Git attributes enforce LF text files on every platform, except PowerShell scripts use CRLF; this keeps fresh Windows checkouts compatible with Prettier's LF formatting.

When global uv is unavailable, the equivalent project-local bootstrap used here is:

```powershell
python -m pip install --target .tools/uv --cache-dir .tools/pip-cache uv==0.13.8
.\scripts\uv.ps1 sync --locked
```

### Start application processes

Run each block in a separate terminal from the project root:

```powershell
.\scripts\uv.ps1 run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```powershell
npm.cmd --prefix frontend run dev
```

```powershell
.\scripts\uv.ps1 run python -m app.worker
```

Frontend: `http://127.0.0.1:5173`. Swagger: `http://127.0.0.1:8000/docs`. Liveness: `/health/live`; readiness: `/health/ready`. The Vite server forwards health, docs and future API requests to localhost:8000. Production hosting must configure its own reverse proxy; Vite's development proxy is not included in the static build.

Liveness works without a database or provider keys. Readiness requires PostgreSQL, the vector extension and the current Alembic revision. The worker emits a bounded heartbeat and supports `--once` for verification; it does not claim durable job processing yet.

### Migrations, database roles and shutdown

```powershell
.\scripts\uv.ps1 run alembic current
.\scripts\uv.ps1 run alembic upgrade head
.\scripts\uv.ps1 run alembic -x db=test upgrade head
.\scripts\uv.ps1 run python -m app.worker --once
docker compose stop
```

API/worker use the restricted `wagamaga_app` role; Alembic uses separate bootstrap credentials. M0 grants the app read-only access to migration metadata and no schema-write privileges. Future domain migrations must explicitly grant needed table access; audit-table grants must remain append-only.

Docker initialization creates separate `wagamaga` and `wagamaga_test` databases on a new named volume. Integration tests refuse names without the `_test` suffix. Editing `.env` passwords after initialization does not rotate existing database roles. Preserve the volume and do not use volume deletion as a routine fix. The `postgres_data` volume is mounted at `/var/lib/postgresql`, matching the PostgreSQL 18 image layout.

The image is digest-pinned for Linux/amd64 in compose.yaml. Windows on this machine and the configured Ubuntu CI runner use that architecture. An ARM setup needs its own reviewed image digest. Keep the existing Windows support limitation in the historical audit below in view before a deployed or supported operating environment is claimed.

## Intended project layout

```text
WagaMaga/
  README.md
  AGENTS.md
  CONTRIBUTING.md
  SECURITY.md
  docs/
  backend/
    pyproject.toml
    app/
      main.py
      core/
      db/
      modules/
        identity/
        farms/
        knowledge/
        advisory/
        proposals/
        reviews/
        tasks/
        weather/
        notifications/
      integrations/
      worker/
    migrations/
    tests/unit/
    tests/api/
    tests/integration/
  frontend/
    package.json
    src/app/
    src/features/
    src/components/
    src/lib/
  tests/e2e/
  evaluation/datasets/
  evaluation/reports/
  fixtures/
  scripts/
  .github/workflows/
```

This describes the scaffold layout. Domain directories contain package markers only; there are no business routes, services or tables yet. Keep routes thin, business transitions in services and providers behind adapters. The separate worker runs backend code and will reuse domain services; it is not an independent AI microservice.

## Accepted tooling for M0

The user accepted the following setup and subsequently authorized the base scaffold on 15 November 2026. See [DECISIONS.md](DECISIONS.md), D01-D04 and D17, for rationale and implementation pins. The agreed React/FastAPI/PostgreSQL/pgvector/separate-worker stack is unchanged.

| Area | Accepted choice | Why |
| --- | --- | --- |
| Python | Standard CPython 3.14.x, supported patch pinned during M0 | Established release line still receiving bugfixes |
| Node.js | 24.x LTS, supported patch pinned during M0 | Meets proposed frontend tooling requirements and matches the installed major |
| Backend packages | uv, one backend environment and uv.lock | One dependency/environment/lock workflow for API and worker |
| Frontend packages | npm 11.x and package-lock.json | Already available; sufficient for one React client |
| Frontend build | React + strict TypeScript + Vite | Type checking, fast local workflow and static production build |
| Database | PostgreSQL 18 + pgvector 0.8.x | Supported PostgreSQL line with project-published pgvector images |
| Local infrastructure | Docker Desktop WSL 2 backend + modern `docker compose` plugin, v2-compatible interface | Avoid native Windows extension compilation; named volume for persistence. Installed v5.5.0 retains this interface. |
| Database access | Synchronous SQLAlchemy 2.1.x + Psycopg 3.3.x binary distribution | Explicit transactions and direct Windows development |
| Migrations | Alembic 1.x | Versioned, reviewed database changes |
| Python checks | pytest, FastAPI TestClient/HTTPX and Ruff | Behaviour/API checks plus one linter/formatter |
| Frontend checks | TypeScript, ESLint, Prettier; Vitest/React Testing Library | Separate type, rule, format and user-interaction checks |
| End-to-end checks | Playwright when user journeys exist | Browser/API/database verification |

Run frontend, API and worker as separate native PowerShell processes initially, with only the database in Docker. Docker uses WSL internally; the accepted setup does not move the repository or require a duplicate Linux toolchain. Keep the worker in the same Python project/environment as the API and use separate sessions per request/job.

With synchronous database access, keep blocking work behind synchronous route boundaries or explicitly offload it; do not block an async route's event loop with synchronous sessions. External-provider integration can use an appropriate separate async boundary later.

Do not add Redis, Celery or an agent framework merely to scaffold the project. Original document files can use a private local directory when ingestion starts; no object-storage service is needed for M0.

## Versioning and prerequisite checks before M0

- Recheck current supported patch releases and binary compatibility before installation; recommended families are not a fully resolved dependency set.
- During M0, pin the chosen Python patch in the backend runtime declaration, the Node patch in the agreed runtime declaration, and package manager versions in setup/CI. Commit the generated uv and npm lockfiles; do not hand-author their resolutions.
- Use locked installs in CI and pin the database image to a resolved digest. Keep development and integration-test database versions aligned. Revisit versions through deliberate updates and relevant checks.
- Verify supported Windows/WSL, virtualization, Docker Desktop/daemon access and available memory using the current [Docker prerequisites](https://docs.docker.com/desktop/setup/install/windows-install/). The read-only audit below checks availability and records the remaining limitations.
- Do not rely on restricted-shell discovery alone: approved host checks found Python and modern WSL that the initial restricted checks could not enumerate.

The initial read-only audit below predates scaffolding. Current commands and tool pins are above; current verification outcomes belong in TESTING.md. Do not treat a historical missing-tool entry as a new audit result or claim that all release gates passed merely because dependencies are installed.

## Historical read-only prerequisite audit - before scaffolding

The user authorized checks and documentation updates only. Restricted-shell checks were followed by approved read-only host checks where access restrictions prevented reliable results. No software, services, containers or settings were installed, updated, started, stopped or changed.

"Ready" below means the command runs and matches the selected tool/version family, not that the application has been built or all security patches are current.

| Tool or prerequisite | Status | Evidence and remaining work |
| --- | --- | --- |
| Python 3.14.x | Missing from discovered installations | `python --version` returns 3.13.2; host `py --list` lists only 3.13. The checked local Python installation root contains Python313 only. Keep that installation; the selected 3.14 runtime needs separate setup later. |
| uv | Missing from PATH and checked locations | `Get-Command uv` found nothing; user `.local/bin/uv.exe` and `.cargo/bin/uv.exe` were absent. No assertion about every possible installation location. |
| Node.js 24.x | Ready for selected family | `node --version`: v24.13.0. Verify the supported patch before pinning M0. |
| npm 11.x | Ready for selected family | `npm.cmd --version`: 11.6.2. No package installation was run. |
| Git | Ready | `git --version`: 2.49.0.windows.1. Project Git initialization remains undone. |
| WSL 2 | Available; container workload unverified | `wsl --version`: 2.7.14.0. `wsl --status`: default version 2. `wsl --list --verbose`: docker-desktop, Stopped, version 2. No extra Linux distribution is required by the accepted native-app workflow. |
| Docker CLI / Desktop engine | CLI installed; engine not ready | `docker version`: client 29.7.2, context desktop-linux; engine pipe not found. No Docker Desktop/backend processes were listed. Docker Desktop/engine startup remains for a later authorized step. |
| Compose | CLI ready; project execution unverified | `docker compose version`: v5.5.0. Docker documents v5 as functionally equivalent to the accepted v2 command interface; no downgrade is required merely for its major number. |
| Windows servicing | Update needed before a supported Docker setup | Host: Windows 11 Pro, build 22631 (23H2), 64-bit. Microsoft lists this release as out of support; Docker requires an OS within Microsoft's servicing timeline. No OS update was attempted. |
| RAM and virtualization | Partially verified | About 7.7 GiB visible RAM; `HypervisorPresent` true. Individual CPU firmware/SLAT/VM-monitor flags returned false. Do not infer disabled firmware from those flags alone while a hypervisor is active. Physical installed RAM, available workload headroom and an actual Linux container run remain unverified. |
| PostgreSQL 18 / pgvector | Deferred/unverified | No database container, connection or extension query was run. Verify during M0 after infrastructure is ready. |
| React/FastAPI/database libraries/test tools | Deferred | Project manifests and environments do not exist. These are project dependencies to resolve and install in the authorized build stages, not missing global tools that must all be installed now. |

Sources for compatibility interpretation: [Docker Windows requirements](https://docs.docker.com/desktop/setup/install/windows-install/), [Windows Home/Pro lifecycle](https://learn.microsoft.com/en-us/lifecycle/products/windows-11-home-and-pro) and [Docker Compose FAQ](https://docs.docker.com/compose/support-and-feedback/faq/).

### Read-only commands used

These are audit commands, not application startup or installation instructions. Some require host access because the restricted shell cannot enumerate the same state.

```powershell
Get-Command py,python,python3,uv,node,npm,docker,git,wsl -All -ErrorAction SilentlyContinue
python --version
py --list
node --version
npm.cmd --version
git --version
docker version
docker compose version
wsl --version
wsl --status
wsl --list --verbose
```

Hardware/OS checks read Win32_OperatingSystem, Win32_ComputerSystem and Win32_Processor through Get-CimInstance and inspected Docker process presence. Docker configuration contents were not printed. Sandbox-only access warnings are not treated as a broken host configuration.

### Next actions, not performed

1. Plan a supported Windows release update and recheck Docker's current prerequisites.
2. Set up uv and the accepted Python 3.14 runtime without removing existing Python installations.
3. Start Docker Desktop and verify a reachable Linux engine, workload resources and container operation.
4. Once prerequisites are ready and scaffolding is authorized, implement M0 with the accepted tools and verify the project-specific commands.

This historical audit performed no installations or service startup. The later scaffold request authorized local project setup; Windows updates, public deployment and business features remain outside the M0 task.

## Local setup sequence after scaffolding is authorized

1. Initialize Git, configure ignore rules and select local tooling.
2. Create manifests and lockfiles for frontend and backend dependencies.
3. Create safe environment examples and separate local/test configuration.
4. Start PostgreSQL with pgvector and establish a least-privilege application connection.
5. Apply the foundation migration and verify extension availability.
6. Start FastAPI, React and the worker as separate processes.
7. Verify liveness/readiness and browser-to-API connectivity without external provider keys.
8. Run foundation checks and repeat the setup from a clean environment.

No business CRUD, authentication screens, RAG or live provider calls belong in the M0 scaffold.

## Proposed configuration names

Names below are a configuration design proposal. The implemented settings schema and environment examples must agree.

| Variable | Purpose |
| --- | --- |
| `APP_ENV` | Development, test or deployed environment |
| `DATABASE_URL` | Server-side application database connection |
| `TEST_DATABASE_URL` | Dedicated disposable test database |
| `CORS_ALLOWED_ORIGINS` | Explicit permitted frontend origins |
| `DOCUMENT_STORAGE_PATH` | Private local source-file directory |
| `AUTH_SIGNING_KEY`, `AUTH_ISSUER`, `AUTH_AUDIENCE` | Auth configuration, introduced with identity work |
| `MODEL_PROVIDER`, `MODEL_NAME`, `EMBEDDING_MODEL` | Versioned AI configuration, introduced with advisory work |
| `MODEL_API_KEY` | Server-only credential if required by the chosen provider |
| `WEATHER_PROVIDER`, `WEATHER_API_KEY` | Weather configuration, introduced when required |

Do not put credentials in frontend variables. Do not require model/weather keys to start the foundation or use manual farm management. Configure database/bootstrap credentials separately from the normal app role.

## Command registry

The implemented M0 commands are listed below. Add exact, tested commands for later capabilities when their milestone introduces them.

| Action | Status |
| --- | --- |
| Install backend/frontend dependencies | `.\scripts\uv.ps1 sync --locked`; `npm.cmd --prefix frontend ci` |
| Start/stop local PostgreSQL | `docker compose up -d --wait`; `docker compose stop` |
| Apply migrations | `.\scripts\uv.ps1 run alembic upgrade head` |
| Start API, frontend and worker | Separate-terminal commands in M0 local setup above |
| Run lint, tests, frontend checks/build | Exact commands and results in TESTING.md |
| Load/reset synthetic business fixtures | V0: pending schema; isolated local/test only |
| Run AI evaluation and browser journeys | V0/V1: pending harnesses |

On Windows, document PowerShell-compatible commands and quote paths containing spaces. Bind development services to local interfaces by default. Do not hide required setup steps behind unrecorded manual actions.

## Daily development

Take one bounded task from [CODEX_WORKFLOW.md](CODEX_WORKFLOW.md), identify requirements, implement and verify it, inspect the diff, update docs and record a focused commit when using Git. See [CONTRIBUTING.md](../CONTRIBUTING.md) for review expectations.

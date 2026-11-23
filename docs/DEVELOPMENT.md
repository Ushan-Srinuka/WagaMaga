# Development guide

Status: M0, UM1 accounts, Farm Records, manual cultivation tasks, suggested plans, live farm forecasts, weather alerts and date reviews, website support and the knowledge workflow are implemented locally. Current schema is `0019_weather_task_review`. TESTING.md records actual outcomes.

Sign in as a farmer and open **Chilli questions** to read cited answers about nursery setup, irrigation, soil testing and two published studies. The public crop-page answers run locally. The existing `GEMINI_API_KEY` enables optional selection from the four published study summaries, with a local fallback. Use the [local walkthrough](KNOWLEDGE_EVALUATION.md#portfolio-demo) to exercise the separate fictional PDF workflow.

For manual tasks, run `.\scripts\uv.ps1 run alembic upgrade head` before starting the API and worker. Sign in as a farmer, open a cultivation under **My farms** and use **Farm tasks → Add task**. Reload to check the task was saved, then mark it complete and open **Cultivation history**.

For the suggested plan demo, open **Farm tasks → Suggested plans → Review example plan** on the cultivation page. Compare the new task and due date with the current list. **Accept and add task** creates the pending task. **Reject suggestion** records the decision without adding a task. Both outcomes appear in **Cultivation history → Plan decisions**. The example uses a built-in checklist and needs no provider key.

For live weather, apply `alembic upgrade head` and open a cultivation under a farm with saved coordinates. Choose **Farm tasks → Weather forecast → Fetch forecast**. Keyless local requests use Open-Meteo's non-commercial endpoint. Set `OPEN_METEO_API_KEY` for the dedicated customer endpoint. In a non-commercial production environment, set `OPEN_METEO_NONCOMMERCIAL=true` to enable the keyless endpoint.

Under **Weather alerts**, save a precipitation threshold in millimetres. A matching pending task offers **Review task date**. Choose a different date, open the comparison and select **Confirm new date** or **Keep current date**. The result appears in **Cultivation history → Plan decisions**.

Choose **Show demo weather** in development to run the separate fixture walkthrough. Accept the example plan to create a task on the sample date, then use **Review this task** to try keeping or changing the date.

To try the knowledge workflow, run `.\scripts\uv.ps1 run alembic upgrade head` from the repository root before starting the API and worker. Sign in as an administrator and open **Knowledge Sources** in the workspace menu. Choose **Add synthetic guide**, then review, publish and withdraw that version. The example is built into the application and requires no provider key.

For a PDF source, start the separate worker with `.\scripts\uv.ps1 run python -m app.worker`. In **Knowledge Sources**, select a PDF up to 6 MiB and 100 pages, upload it and choose **Refresh sources** after the worker runs. Extraction is bounded to 120,000 characters. Recognized FM-Abhaya, FM-Ababld, FM-Emanee and FM-Samantha text is converted to Unicode; other legacy-font runs may remain unsearchable. Use **View extracted text** to review the numbered pages. Withdraw a published upload before choosing **Delete PDF** to remove its original and full extracted pages; the source title/checksum and review/audit evidence remain. The worker's `--once` flag checks readiness only. Image-only PDFs still need OCR.

The extractor reads the left column before the right when it finds two sustained, overlapping prose blocks. Always compare passages on complex pages, such as pages with tables or figures, with the original PDF. To apply an extractor update to an existing PDF, upload it as a new draft. Saved extraction results belong to their original version.

To try local chilli references through the farmer screen on localhost, use `LOCAL_NURSERY_REFERENCE` for nursery and `LOCAL_CHILLI_REFERENCES` for `CH-04` irrigation and `CH-05` fertilizer in the ignored root `.env`. Each reference contains `version_id`, `checksum`, `page_number`, `title`, `excerpt` and `english_translation`. Restart the API after changing them. Draft references work only in development; the app verifies the pinned PDF version, checksum and exact Sinhala quote before showing **Local PDF reference · Draft translation** and the cited excerpt. Remove a setting entry to hide its reference. These local draft translations have not been approved for the farmer pilot.

For the local **Gemini answer preview**, put an AI Studio API key in the ignored root `.env` as `GEMINI_API_KEY` and restart the API. Confirm the project uses unpaid quota before live demo requests. The configurable `GEMINI_MODEL` defaults to `gemini-3.5-flash-lite`. In **Knowledge Sources**, choose **Add Gemini demo PDF**, refresh after extraction, review the numbered pages, and publish the sample. Choose one of the fixed demo questions in **Gemini answer preview**. A question with no matching sample evidence works without a key.

The portfolio walkthrough uses the defaults `GEMINI_APPROVED_PDF_CHECKSUMS=[]` and `FARMER_ADVISORY_ENABLED=false`.

For a farm guidance pilot, set `GEMINI_APPROVED_PDF_CHECKSUMS` in the server `.env` to a JSON list of eligible SHA-256 fingerprints and restart the API. Review and label the cases, then score them at `/admin/knowledge/scoring`. After all current cases pass, `FARMER_ADVISORY_ENABLED=true` and an API restart enable the fixed questions at `/knowledge/chilli/guidance`.

## Local setup: foundation and user management

From the project root, using PowerShell:

```powershell
.\scripts\uv.ps1 sync --locked
.\scripts\uv.ps1 run python ../scripts/configure_local.py
npm.cmd --prefix frontend ci
docker compose up -d --wait
.\scripts\uv.ps1 run alembic upgrade head
```

The configuration generator is standard-library-only and also works with the existing Python 3.13 installation. The commands above use the uv-managed interpreter so an extra system Python is not required once uv is available. It creates ignored `.env` credentials once and never prints them. For an existing file it preserves settings and passwords, appending a generated `AUTH_SIGNING_KEY` only if that setting is absent. PostgreSQL is published on `127.0.0.1:55432`; port 5432 was unavailable on this machine. The database container listens on its normal internal port 5432. Relative document storage paths resolve from the repository root in both API and worker.

The PowerShell uv wrapper uses a global uv executable if available, otherwise the ignored `.tools/uv/bin/uv.exe` copy used during scaffolding. It runs in `backend/`, stores downloaded Python/cache files under `.tools/`, and uses backend/.python-version. New checkouts need uv installed first; the ignored tools are not part of Git. The scaffold was verified with uv 0.13.8, CPython 3.14.10, Node 24.13.0 and npm 11.6.2. Existing Python installations were not removed and Windows was not updated. Git attributes enforce LF text files on every platform, except PowerShell scripts use CRLF; this keeps fresh Windows checkouts compatible with Prettier's LF formatting.

When global uv is unavailable, the equivalent project-local bootstrap used here is:

```powershell
python -m pip install --target .tools/uv --cache-dir .tools/pip-cache uv==0.13.8
.\scripts\uv.ps1 sync --locked
```

### Start application processes

Run each block in a separate terminal from the project root:

```powershell
.\scripts\uv.ps1 run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --no-proxy-headers --no-access-log
```

```powershell
npm.cmd --prefix frontend run dev
```

```powershell
.\scripts\uv.ps1 run python -m app.worker
```

Frontend: `http://127.0.0.1:5173`. Swagger: `http://127.0.0.1:8000/docs`. Liveness: `/health/live`; readiness: `/health/ready`; foundation screen: frontend `/connection`. Vite proxies `/api/v1`, health and docs to localhost:8000. Use the same browser hostname throughout login/refresh/logout. The API reads the socket peer for abuse limits; `--no-proxy-headers` prevents arbitrary forwarding headers from changing that identity. Through local Vite the API sees the local proxy IP, so the IP quota is shared. Production ingress/client-IP handling and its reverse proxy require a separate reviewed setup; Vite's proxy is not included in the static build.

### First administrator and account use

After the generator and migration, run this interactively in your own terminal:

```powershell
.\scripts\uv.ps1 run python -m app.modules.identity.cli
```

Enter a display name, synthetic email and an 8-128 character password twice, including at least one letter, one number and one symbol. Uppercase is optional; spaces do not count as a symbol. Password entry is hidden and no secret appears in command arguments. This restricted local command reuses the registration validator, uses migration credentials, records an audit event and serializes bootstrap. It refuses once any administrator record exists; there is no public bootstrap route, default admin password or automatic startup seed.

The public homepage opens at `/` and links to farmer registration at `/register` or sign-in at `/login`. Edit your display name and change your password at `/account`; password changes require the current password and sign out other sessions. Administrators also get `/admin/users` and user details, including a confirmed account-removal action. Removal scrubs the name, email and credential, revokes sessions and preserves an audit-linked tombstone; it cannot be undone in the UI. It blocks self-removal and preserves an active administrator. Role changes, disablement and removal revoke target sessions; re-enabling never restores old sessions. Advisors are assigned by an administrator after farmer registration. Create a second administrator through authorized role assignment if another operator is required.

UM1 provides self-service password changes and administrator account removal with identity scrubbing. It does not provide email changes, forgotten-password recovery, verified email ownership, hard row deletion or administrator password reset. Do not repurpose bootstrap as a recovery bypass or edit roles through public request payloads. A real-user invitation needs resolved recovery, privacy, retention and deployment policies first. Current use is local/synthetic.

`AUTH_SIGNING_KEY` is server-only and must be at least 32 bytes; the generator uses 32 random bytes encoded as hex. Changing it invalidates signed access tokens. The current issuer/audience are `wagamaga-api`/`wagamaga-web`, access lifetime is 15 minutes and session expiry is an absolute 7 days. `AUTH_ALLOWED_ORIGINS` defaults to the explicit localhost frontend and Swagger origins shown in .env.example; auth POSTs require this Origin plus `X-WagaMaga-Client: web`. Missing keys leave health available but identity requests return 503. Never put these settings into Vite/browser environment variables.

Liveness works without a database or provider keys. Readiness requires PostgreSQL, the vector extension and the current Alembic revision. The worker emits a bounded heartbeat and supports `--once` for verification; it does not claim durable job processing yet. The API command disables default access logs so account-search query strings are not written there; application responses retain a generated X-Request-ID for correlation.

### Migrations, database roles and shutdown

```powershell
.\scripts\uv.ps1 run alembic current
.\scripts\uv.ps1 run alembic upgrade head
.\scripts\uv.ps1 run alembic -x db=test upgrade head
.\scripts\uv.ps1 run python -m app.worker --once
docker compose stop
```

API/worker use the restricted `wagamaga_app` role; Alembic uses separate bootstrap credentials. Revisions `0002_identity`, `0003_account_lifecycle` and `0004_in_app_notifications` add users, refresh-session families, token history, expiring limit buckets, audit logs, account-removal timestamp and recipient notifications. The app can operate on identity state and read migration metadata but cannot create schema or update/delete audit rows. It can SELECT/INSERT/UPDATE notifications but has no DELETE grant. Future domain migrations must explicitly grant needed access; audit grants remain append-only. Identity request transactions commit before a success response is sent.

Docker initialization creates separate `wagamaga` and `wagamaga_test` databases on a new named volume. Integration tests refuse names without the `_test` suffix. Editing `.env` passwords after initialization does not rotate existing database roles. Preserve the volume and do not use volume deletion as a routine fix. The `postgres_data` volume is mounted at `/var/lib/postgresql`, matching the PostgreSQL 18 image layout.

The image is digest-pinned for Linux/amd64 in compose.yaml. Windows on this machine and the configured Ubuntu CI runner use that architecture. An ARM setup needs its own reviewed image digest. Keep the existing Windows support limitation in the historical audit below in view before a deployed or supported operating environment is claimed.

## Farm Records persistence checkpoint

Run the existing `alembic upgrade head` setup command before API/worker startup. The original FR-B migration adds the farm tables and reference crop without modifying existing account or notification rows. It creates no farmer records or demo accounts in development. Downgrade and rebuild checks run only against disposable `_test` data.

The explicit synthetic farm fixture lives in backend/tests/conftest.py and runs only through tests using guarded test URLs. Follow [TESTING.md](TESTING.md) to verify migrations, grants, constraints and service/API transactions. `alembic check` includes farm model metadata. There is no farm seed CLI; the connected FR-D interface is described below.

FR-C follow-up: start the API with the existing command and explore the Farm Records tag in Swagger using a synthetic farmer login/access token. Use its HTTP Bearer authorization and exact Origin plus `X-WagaMaga-Client: web` on JSON writes as described in API.md. Administrators/advisors cannot use private farm endpoints. PostgreSQL provides timezone validation/local dates; no provider configuration is needed.

FR-D use: start PostgreSQL/API/frontend with the existing setup above, register/sign in as a synthetic farmer and choose My Farms, or open `http://127.0.0.1:5173/farms`. Add a farm, then cultivation and observations; edit, confirm a stage, inspect history or archive through the connected controls. Administrators/advisors have no farm navigation and a direct URL is denied. Existing accounts/records are preserved and no demo farms are seeded in development. Browser fixture tests use a separate guarded `_test` database and generated credentials; run them separately from backend migration/reset tests. Exact checks and local Windows cleanup requirements are in TESTING.md.

## Farmer onboarding and location entry - 19 November 2026

Farm lifecycle follow-up: run `.\scripts\uv.ps1 run alembic upgrade head` before starting API/worker. Existing farm records/history are preserved. In My Farms choose Farm status → Archived, open a farm and choose Restore farm or Delete farm. Restore returns it to active use while independently archived crops remain archived. Delete requires the current farm name and removes access from the workspace; stored historical data is retained and the UI cannot undo deletion. This is not a data-erasure tool. Migration downgrade refuses while lifecycle evidence exists. Test rebuilds must remain on disposable `_test` databases.

Farmer sign-in now returns to `http://127.0.0.1:5173/`. The website header has My Farms and Add Farm, while the hero action bar offers Add my farm for a new farmer or a private farm selector and next crop/observation action for returning farmers. Choose your own farm name, district and village/town, then add a crop/planting date/area and an observation. There is no separate farmer dashboard or fixed mobile bottom navigation. Advisors sign in to My Account and administrators to Admin Overview and cannot access private farmer records. A farmer visiting the old `/dashboard` URL is redirected home.

Choose Describe the location myself for an existing/custom location. District selection has no default and is not a guidance-eligibility check; the existing API stores a label, not structured administrative fields. Exact coordinates and additional area/timezone are collapsed options. Use my current location only at the farm, approve browser permission if desired, review the result and save normally. Permission denial, missing location support and timeouts do not prevent manual entry or omission. Browser geolocation requires a secure context: loopback development works in supported browsers, while deployed use requires HTTPS. There is no new API key or map provider. The initial guidance pilot remains chilli/Anuradhapura pending agricultural validation.

If the usual app ports are occupied, leave those services running and use isolated test ports in a separate terminal:

```powershell
$env:PLAYWRIGHT_CHANNEL='msedge'
$env:E2E_API_PORT='18000'
$env:E2E_WEB_PORT='15173'
npm.cmd --prefix frontend run test:e2e
```

The harness still refuses non-`_test` databases, creates synthetic accounts, binds to loopback and permits its selected web origin only. Do not run database migration/reset tests concurrently. Port defaults remain 8000/5173; remove these environment overrides before ordinary dev commands in that terminal. Existing app processes and the previously running Compose database are left alone.

## Help and support - 19 November 2026

Admin Overview follow-up (D30): administrator login now opens `http://127.0.0.1:5173/admin/overview`, showing account/farm/cultivation/support count summaries. Farmers still open the website landing page and advisors My Account. Admin account navigation and the signed-in website header link to Overview. Open a current farmer in User management to see the count-only Farm record summary; no farm names/locations/notes are exposed. Existing farm endpoints still reject administrators. Report views are recorded in account audit history; audit failure prevents a successful report. No additional configuration or migration is needed after `0007_support`. See [ADMIN_REPORTING.md](ADMIN_REPORTING.md) for definitions and [TESTING.md](TESTING.md) for evidence.

Run the normal migration command before API/worker startup. Open `http://127.0.0.1:5173/help` for public FAQs and contact. Signed-in farmers use `/support` or `/support/new`; administrators use `/admin/support`. Submitting shares only the typed support conversation, not private farm records. In-progress/resolved states and generic in-app notifications work without an email provider. Account recovery, attachments and live chat remain pending.

To provide a public contact for farmers who cannot sign in, set `SUPPORT_CONTACT_EMAIL` to a monitored operator email in the ignored root `.env` and restart the API. The optional field defaults to unset, is validated by existing email-validator and exposed publicly by `/api/v1/help/contact`; it is not a secret or SMTP setting. Do not use an invented/unmonitored address. The Help page honestly reports when contact is not configured. Setting it sends no email and does not implement password recovery or bypass identity checks. A real contact/recovery policy is still needed before external users are invited. See [SUPPORT.md](SUPPORT.md) for the scope and [TESTING.md](TESTING.md) for exact verified commands.

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

Identity now contains models, schemas, routes, services, dependencies, crypto adapters and a restricted CLI. Other domain directories contain package markers only. React app/ owns routing/session/layout, features/ owns auth/account/users, components/ owns shared fields/notices/dialogs, and lib/ owns HTTP/session requests. Keep routes thin, transitions in services and providers behind adapters. The separate worker remains a foundation process and will reuse domain services later.

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

## Implemented and future configuration names

APP_ENV, database, storage, CORS, provider and AUTH settings are reflected in Settings and .env.example. User management and manual farm records run without provider credentials.

| Variable | Purpose |
| --- | --- |
| `APP_ENV` | Development, test or deployed environment |
| `DATABASE_URL` | Server-side application database connection |
| `TEST_DATABASE_URL` | Dedicated disposable test database |
| `CORS_ALLOWED_ORIGINS` | Explicit permitted frontend origins |
| `DOCUMENT_STORAGE_PATH` | Private local source-file directory |
| `AUTH_SIGNING_KEY`, `AUTH_ISSUER`, `AUTH_AUDIENCE` | Implemented server-only signing and token validation configuration |
| `AUTH_ALLOWED_ORIGINS`, `AUTH_ACCESS_MINUTES`, `AUTH_SESSION_DAYS` | Explicit browser origins, access lifetime and absolute session expiry |
| `AUTH_LOGIN_FAILURES`, `AUTH_LOGIN_IP_ATTEMPTS`, `AUTH_REGISTRATION_ATTEMPTS`, `AUTH_REFRESH_ATTEMPTS` | Shared fixed-window account/IP/family abuse limits; defaults in D23 |
| `MODEL_PROVIDER`, `MODEL_NAME`, `EMBEDDING_MODEL` | Versioned AI configuration, introduced with advisory work |
| `MODEL_API_KEY` | Server-only credential if required by the chosen provider |
| `OPEN_METEO_API_KEY`, `OPEN_METEO_NONCOMMERCIAL` | Optional customer key or explicit keyless non-commercial production use |

Do not put credentials in frontend variables. Do not require model/weather keys to start the foundation or use manual farm management. Configure database/bootstrap credentials separately from the normal app role.

## Command registry

The implemented foundation/UM1 commands are listed below. Add exact, tested commands for later capabilities when their milestone introduces them.

| Action | Status |
| --- | --- |
| Install backend/frontend dependencies | `.\scripts\uv.ps1 sync --locked`; `npm.cmd --prefix frontend ci` |
| Start/stop local PostgreSQL | `docker compose up -d --wait`; `docker compose stop` |
| Apply migrations | `.\scripts\uv.ps1 run alembic upgrade head` |
| Start API, frontend and worker | Separate-terminal commands in local setup above |
| Initial administrator | `.\scripts\uv.ps1 run python -m app.modules.identity.cli` in an interactive terminal; hidden password prompts |
| Run lint, tests, frontend checks/build | Exact commands and results in TESTING.md |
| Load/reset synthetic business fixtures | V0: pending schema; isolated local/test only |
| Run account browser journeys | `npm.cmd --prefix frontend run test:e2e`; matching Chromium or installed Edge setup in TESTING.md |
| Run AI evaluation | V0/V1: pending harnesses |

On Windows, document PowerShell-compatible commands and quote paths containing spaces. Bind development services to local interfaces by default. Do not hide required setup steps behind unrecorded manual actions.

## Daily development

Take one bounded task from [CODEX_WORKFLOW.md](CODEX_WORKFLOW.md), identify requirements, implement and verify it, inspect the diff, update docs and record a focused commit when using Git. See [CONTRIBUTING.md](../CONTRIBUTING.md) for review expectations.

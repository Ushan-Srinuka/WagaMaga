# Testing strategy

## Chilli questions and reliability

The 23 November 2026 local run passed 319 backend tests with PostgreSQL/pgvector and 79 frontend tests. Coverage includes all seven cited questions, unsupported plot-specific requests, the local answer during a simulated Gemini outage, saved forecast preservation during a simulated Open-Meteo outage, and owner-only access to private farm records. Ruff, frontend lint, Prettier, the production build, Alembic drift and worker readiness checks passed. With the [isolated Edge settings](DEVELOPMENT.md), `npm.cmd --prefix frontend run test:e2e` passed 50 desktop and mobile journeys, including both versions of the chilli question journey. The two opt-in live Gemini journeys were skipped.

From the repository root with the local PostgreSQL container running:

```powershell
$cache = Join-Path (Get-Location) '.tools/pytest-cache-reliability'
.\scripts\uv.ps1 run pytest --require-database -o "cache_dir=$cache"
.\scripts\uv.ps1 run pytest --require-database -o "cache_dir=$cache" tests/integration/test_farm_api.py::test_weather_reschedule_uses_exact_plan_and_commits_once
Get-Content -Raw scripts/database/verify_test_restore.sh | docker compose exec -T db sh -s
```

Run the focused seed immediately before the restore drill. The test resets the disposable test fixtures. The drill backs up the synthetic database with `pg_dump`, uses `pg_restore` on a fresh temporary database and compares schema revision, pgvector version, farm entries, forecasts, alerts, task revisions and bound decisions. It checks that the application role still has the expected history grants. The database and archive created by the drill are removed when it exits. The backend GitHub Actions job includes these steps; the hosted workflow has yet to run this revision. Provider failure checks use doubles. This drill exercises database recovery of synthetic farm records and task evidence.

## Earlier checks

**Weather alerts and date review.** Twenty selected PostgreSQL tests passed for live and sample weather, task planning, schema rebuild and identity regressions. They cover deduplication across refreshes and changed measurements, clearing a threshold, closed tasks, owner checks, exact review binding, superseded and stale reviews, repeated or simultaneous acceptance and rollback if writing the decision fails. The local API reported ready on `0019_weather_task_review` and `alembic check` reported no drift.

```powershell
$cache = Join-Path (Get-Location) '.tools/pytest-cache-weather-review'
.\scripts\uv.ps1 run pytest --require-database -o "cache_dir=$cache" tests/integration/test_farm_api.py tests/integration/test_farms.py tests/integration/test_identity.py -k 'weather or task or upgrade_preserves or migration_fresh_rebuild or rate_limit_expiry_and_auth_endpoint_caps'
npm.cmd --prefix frontend run test -- --maxWorkers=2
```

All 79 frontend tests, Ruff, Prettier, frontend lint and the production build passed. With the isolated Edge settings in [DEVELOPMENT.md](DEVELOPMENT.md), `npm.cmd --prefix frontend run test:e2e -- farms.spec.ts --grep 'farmer (sets a weather alert|fetches a farm forecast|reviews suggested plans)'` passed six desktop and mobile journeys. The new journey uses deterministic forecast data and verifies the saved threshold, a single alert after refresh, an unchanged task during comparison, the confirmed date after reload and both dates in plan history. Remote CI was not run.

**Live farm weather.** The 25 selected backend tests and 79 frontend tests passed. Backend checks cover the Open-Meteo request and payload validation, owner and origin restrictions, coordinate rounding, cache reuse, stale and unavailable forecasts, discarded results when the location changes during a request, and migration rebuild and drift.

```powershell
$cache = Join-Path (Get-Location) '.tools/pytest-cache-live-weather'
.\scripts\uv.ps1 run pytest --require-database -o "cache_dir=$cache" tests/unit/test_open_meteo.py tests/integration/test_farm_api.py tests/integration/test_farms.py tests/integration/test_identity.py -k 'forecast or provider or weather or task or upgrade_preserves or migration_fresh_rebuild or rate_limit_expiry_and_auth_endpoint_caps'
npm.cmd --prefix frontend run test -- --maxWorkers=2
```

With the isolated Edge settings in [DEVELOPMENT.md](DEVELOPMENT.md), `npm.cmd --prefix frontend run test:e2e -- farms.spec.ts --grep 'farmer (fetches a farm forecast|reviews a matching task|manages manual tasks)'` passed all six desktop and mobile journeys. The deterministic browser provider exercised the coordinate prompt, owner refresh, source attribution, saved forecast after reload and matching pending task while preserving manual editing. A separate live, keyless Open-Meteo request for public Anuradhapura city coordinates validated all three daily rows. No private coordinates were used in that check. Ruff, Prettier, frontend lint and build passed. The local database was upgraded to `0018_live_farm_weather`, the API reported ready and `alembic check` reported no drift. The paid endpoint and remote CI were outside this verification.

**Published chilli research.** From the repository root:

```powershell
$chilliCache = Join-Path (Get-Location) '.tools/pytest-cache-chilli-research'
.\scripts\uv.ps1 run pytest --require-database -o "cache_dir=$chilliCache" tests/integration/test_chilli_research.py tests/integration/test_knowledge_evaluation.py tests/integration/test_knowledge_answers.py tests/integration/test_knowledge_demo.py tests/unit/test_gemini.py
npm.cmd --prefix frontend run test -- --maxWorkers=2
```

The 23 backend and 79 frontend tests passed. They check farmer and origin restrictions, the source and page for each research entry, abstention, canonical provider inputs, output mismatch and outage fallback, and the unchanged guidance release gate. With the isolated Edge settings in [DEVELOPMENT.md](DEVELOPMENT.md), `npm.cmd --prefix frontend run test:e2e -- knowledge.spec.ts --grep 'farmer (reads a published|sees the pending|searches reviewed excerpts)'` passed six browser journeys. The new desktop and mobile journey used the reference path and checked the Tirappane study citation and an unsupported fertilizer question. Ruff, Prettier, frontend lint and the production build passed.

With network access, a separate real Gemini call selected the exact curated Tirappane summary and citation. The request used the canonical study question and public summaries only. Compare the four summaries with the PDF pages in [KNOWLEDGE_EVALUATION.md](KNOWLEDGE_EVALUATION.md#published-chilli-research). This check covers research facts and one live selection. Farm-specific guidance evaluation and remote CI remain pending.

**Demo weather.** Nine selected PostgreSQL checks passed, including farm-local date calculation around midnight, repeatable fixture reads, unchanged task history, and access for owners only. The 79 frontend tests passed, including continued task editing when demo weather is unavailable. Run from the repository root:

```powershell
$weatherCache = Join-Path (Get-Location) '.tools/pytest-cache-demo-weather'
.\scripts\uv.ps1 run pytest --require-database -o "cache_dir=$weatherCache" tests/integration/test_farm_api.py -k 'demo_weather or task'
npm.cmd --prefix frontend run test -- --maxWorkers=2
```

With the isolated Edge settings in [DEVELOPMENT.md](DEVELOPMENT.md), `npm.cmd --prefix frontend run test:e2e -- farms.spec.ts --grep 'farmer (reviews a matching task|reviews suggested plans|manages manual tasks)'` passed all six desktop and mobile journeys. The weather journey checks the simulated label and farm location, date matching, keeping the date without adding a history event, and saving and reloading a moved task. Ruff, Prettier, frontend lint and build passed. The local API reported ready on the existing `0017_suggested_task_plans` schema. No live weather or remote CI was exercised.

**Suggested task plan demo.** The 11 selected PostgreSQL tests passed. They cover manual tasks, exact review binding, concurrent acceptance returning one task, rejection, owner and archive checks, expired and stale context, ineligible sample evidence, duplicate pending tasks, failed decision rollback, and migration rebuild and drift checks. Run from the repository root:

```powershell
$planCache = Join-Path (Get-Location) '.tools/pytest-cache-suggested-plans'
.\scripts\uv.ps1 run pytest --require-database -o "cache_dir=$planCache" tests/integration/test_farm_api.py tests/integration/test_farms.py tests/integration/test_identity.py -k 'task or upgrade_preserves or migration_fresh_rebuild or rate_limit_expiry_and_auth_endpoint_caps'
npm.cmd --prefix frontend run test -- --maxWorkers=2
```

All 78 frontend tests, frontend lint and build, Prettier and Ruff passed. With the isolated Edge settings in [DEVELOPMENT.md](DEVELOPMENT.md), `npm.cmd --prefix frontend run test:e2e -- farms.spec.ts --grep 'farmer (reviews suggested plans|manages manual tasks)'` passed both journeys on desktop and mobile. The plan journey confirms the original task remains visible, rejection adds nothing, acceptance creates the displayed task exactly once after reload, and both decisions appear in cultivation history. The local API reported ready on `0017_suggested_task_plans` and `alembic check` reported no drift. Remote CI and a full backend rerun were outside this check.

**Manual cultivation tasks.** PostgreSQL API checks cover sorting and pagination, input validation, editing and terminal transitions, stale versions, private ownership, archive and workspace deletion, and rollback when task history cannot be written. The full backend run passed 287 tests and found one stale schema assertion from the knowledge changes. The migration rebuild and adjacent rate limit test both passed after the assertion was updated. The development database was upgraded to `0016_manual_farm_tasks`, `alembic check` reported no pending changes and the running API reported ready.

From the repository root, run the focused backend check with `.\scripts\uv.ps1 run pytest --require-database tests/integration/test_farm_api.py -k task`. With the isolated Edge browser settings in [DEVELOPMENT.md](DEVELOPMENT.md), `npm.cmd --prefix frontend run test:e2e -- farms.spec.ts --grep 'manages manual tasks'` passed on desktop and mobile. The browser journey creates a task, reloads, edits the date, completes and cancels tasks, filters closed tasks and reads cultivation history. `npm.cmd --prefix frontend run test -- --maxWorkers=2` passed all 78 frontend tests, and the 30 Farm Records component tests passed again after the task reload adjustment. Ruff, frontend lint, Prettier and the production build passed. Remote CI was not run.

The pinned nursery reference passed the focused `test_local_search_serves_only_current_approved_passages` PostgreSQL test. It returned the draft quote in development, denied the wrong page and checksum, and stopped using the reference when the source left draft. A read of the development database verified the real page 26 reference and its translation. Frontend typecheck and lint passed.

The reviewed localhost search passed 16 focused PostgreSQL knowledge tests. Run `./scripts/uv.ps1 run pytest --require-database tests/integration/test_knowledge_evaluation.py tests/integration/test_knowledge_answers.py tests/integration/test_knowledge_demo.py`. A synthetic Sinhala page 26 exercised an exact original quote and approved English translation. The API withheld draft and unreviewed evidence, rejected non-farmer and production requests, and stopped serving an answer and page after revocation or withdrawal. With the isolated browser settings in [DEVELOPMENT.md](DEVELOPMENT.md), `npm.cmd --prefix frontend run test:e2e -- knowledge.spec.ts --grep 'searches reviewed excerpts locally'` reported passes in desktop and mobile Edge. The browser used a synthetic PDF and checked nursery, irrigation, fertilizer and no evidence. Frontend build and lint passed. The real page 26 is still part of a draft and has no approved review.

The typed question update passed 15 focused PostgreSQL knowledge tests and the desktop and mobile Edge demo journeys. Run the farmer demo commands below. The checks cover example buttons, alternate wording and spelling, all three cited pages, and no evidence for unsupported advice, unrelated requests and mixed topics. The feature stays in the localhost demo and the API rejects it for production or non-farmer accounts. Frontend build and lint passed.

The local farmer demo passed 15 focused knowledge integration tests and two Edge browser journeys against the disposable PostgreSQL database. The API checks matched each answer and citation to text actually extracted from the fictional PDF, rejected incorrect pages and versions, and verified access and production denial. From the repo root, run `./scripts/uv.ps1 run pytest --require-database tests/integration/test_knowledge_evaluation.py tests/integration/test_knowledge_answers.py tests/integration/test_knowledge_demo.py`. With the isolated browser settings in [DEVELOPMENT.md](DEVELOPMENT.md), run `npm.cmd --prefix frontend run test:e2e -- knowledge.spec.ts --grep 'can try the local demo'`. The desktop and mobile checks opened the demo as a test farmer, read the nursery, irrigation and fertilizer citations, checked the forecast no-evidence state, and returned to the pending real pilot. Frontend build and lint passed.

The localhost draft answer preview passed the five focused PostgreSQL tests in `./scripts/uv.ps1 run pytest --require-database tests/integration/test_knowledge_evaluation.py tests/integration/test_knowledge_answers.py`. It checks administrator access, origin restrictions, exact Sinhala quote matching, translation input and zero saved decisions or scores. The provider double fails the test if the preview calls Gemini. A mobile Edge check against the regular localhost app opened draft `3bb29be7`, rejected a quote absent from page 26, showed its draft English translation and exact Sinhala quote, and opened the cited page. Frontend build and lint passed.

The separate opt-in live Gemini browser test passed in desktop Edge on the isolated test database with network access. It used the built-in fictional PDF, verified the returned quote and page 1 citation, and withdrew the fixture. The first attempt could not reach Google from the sandbox.

Page 26 evidence review and translated answers passed 14 focused PostgreSQL integration tests. Run `./scripts/uv.ps1 run pytest --require-database tests/integration/test_knowledge_evaluation.py tests/integration/test_knowledge_demo.py tests/integration/test_knowledge_answers.py`. The synthetic nursery case verifies the saved English translation, rejection of the wrong provider quote, the original Sinhala citation, release checks and withdrawal. An Edge check at mobile width with fixture responses exercised the admin form and farmer citation display. Frontend build and lint passed. The local app reports ready on `0015_knowledge_translations`. The real nursery excerpt was checked against the PDF and stored text, and its source is still a draft. No real excerpt or translation was sent to Gemini.

The PDF reading order update passed 14 focused unit and PostgreSQL integration tests. From the repo root, run `./scripts/uv.ps1 run pytest --require-database tests/unit/test_pdf_reading_order.py tests/integration/test_knowledge_demo.py tests/integration/test_knowledge_evaluation.py`. The synthetic fixtures cover side-by-side prose with a header and footer and a table with short cells. The worker reprocessed the Sinhala DOA guide as a new draft. Visual comparison confirmed left-to-right column order on PDF pages 8 and 26. All 89 saved pages retained the same words as the preceding draft, and the nursery question still returned page 26. The visual check covered those two pages. Some legacy headings remain garbled.

The Sinhala draft match preview passed 13 focused PostgreSQL knowledge integration tests, including administrator access, source isolation, page 26 matching and exclusion from published evidence. Run `./scripts/uv.ps1 run pytest --require-database tests/integration/test_knowledge_evaluation.py tests/integration/test_knowledge_demo.py tests/integration/test_knowledge_answers.py` from the repository root. Frontend build and lint for the changed screens passed. A local Edge check at 360 px opened the preview from the DOA draft, expanded page 26 and confirmed an empty result for the forecast question. A visual comparison of PDF page 8 found readable Sinhala body text, interleaved columns and a legacy heading. The preview does not establish extraction accuracy for the rest of the guide or measure answer quality.

The scoring and farmer pilot workflow passed 279 local PostgreSQL backend tests, 77 frontend tests and four focused Edge desktop/mobile checks before the PDF size-limit update. A deterministic Gemini double verified a valid citation, rejection of an invented citation, local abstention, release after all ten synthetic checks, cited-page access and automatic closure after withdrawal. Browser checks exercised local scoring and the farmer's pending state. The `0013_knowledge_pdf_limits` migration and DOA guide ingestion have not yet been verified. No real study or farmer content was sent to Gemini.

The chilli evidence screen passed the local PostgreSQL suite (278 tests), frontend suite (77 tests) and two focused desktop/mobile Edge checks. The backend checks label permissions, revision conflicts, shared exclusion of the built-in Gemini PDF, approval only for retrieved pages, withdrawal and append-only decision storage. Browser checks save a missing-evidence label and verify it after reload. Run `.\scripts\uv.ps1 run pytest --require-database`, `npm.cmd --prefix frontend test` and, with the isolated ports below, `npm.cmd --prefix frontend run test:e2e -- knowledge.spec.ts --grep 'evaluation saves'` from the repository root. The regular app is ready on `0011_knowledge_eval`.

The opt-in live Gemini browser check passed on desktop Edge against the disposable PostgreSQL test database. It signed in as a synthetic administrator, added and processed the built-in PDF, reviewed and published it, verified `DEMO-NURSERY-A` and page 1 on screen, checked **No evidence found** for the forecast question, and withdrew the test version. With the documented isolated test ports and a configured local key, set `E2E_LIVE_GEMINI=1` and run `npm.cmd --prefix frontend run test:e2e -- knowledge.spec.ts --project desktop --grep 'live Gemini demo'`. Ordinary runs keep the key disabled. The ten agricultural cases remain unscored while their evidence is in review.

Unpublished PDF removal passed eleven focused backend tests and eight desktop/mobile Knowledge Sources journeys. A separate live Gemini adapter check returned the exact fictional nursery sentence and expected citation ID using the configured local key. The signed-in browser journey for a live Gemini answer was not run. The regular app is ready on migration `0010_discard_pdf`.

The Gemini preview passed nine focused backend tests and six desktop/mobile Knowledge Sources journeys. The backend used deterministic provider doubles to verify that only published fictional material is sent and that invalid quotes or citation IDs are rejected. The browser fixtures disable the Gemini key and verify the no-evidence path. Run `.\scripts\uv.ps1 run pytest --require-database tests/integration/test_knowledge_answers.py tests/integration/test_knowledge_demo.py tests/unit/test_gemini.py` and `npm.cmd --prefix frontend run test:e2e -- knowledge.spec.ts` from the repository root. Live Gemini and the ten agricultural evaluation cases remain pending.

The PDF keyword search preview passed all seven focused PostgreSQL knowledge tests and four focused Edge desktop/mobile journeys. The checks cover page and version citations, no matches, administrator access and exclusion before publication and after withdrawal. Run `.\scripts\uv.ps1 run pytest --require-database tests/integration/test_knowledge_demo.py` and `npm.cmd --prefix frontend run test:e2e -- knowledge.spec.ts` from the repository root. Frontend build and lint passed. The regular development database was left out of the test runs.

Status: M0 complete and UM1 account, audit-history, in-app notification and homepage session-navigation work verified locally. On 18 November 2026, account/audit changes passed 62 backend tests, 29 frontend tests and all 6 desktop/mobile browser journeys; migration/drift, lint, format and build checks passed. The subsequent homepage/login-navigation follow-up passed 30 frontend tests, lint, format and production build. Its browser rerun could not start because local port 8000 was already occupied; do not treat the earlier browser result as verification of the new redirect. Expanded CI has not run remotely for these local changes. Farming/AI release suites remain future work.

Latest checkpoint, 19 November 2026: the synthetic PDF workflow on `0009_knowledge_pdf` passed 273 backend tests, 77 frontend tests and four focused desktop/mobile browser journeys. Backend tests cover access, origin, size, damaged and textless PDFs, extraction gating and numbered page content. Browser checks upload two fictional PDF pages, run the worker's job handler in a separate test process, then review and publish the extracted version. The earlier Farm Records/support/reporting branch passed its [GitHub CI run](https://github.com/Ushan-Srinuka/WagaMaga/actions/runs/44547501499). The knowledge changes were verified locally.

From the repository root, the backend run used `.\scripts\uv.ps1 run pytest --require-database` with its cache in `.tools/pytest-cache-knowledge-pdf`. The browser command was `npm.cmd --prefix frontend run test:e2e -- knowledge.spec.ts`, using Edge and isolated ports 18000/15173 as described below. The built-in guide journey also checks that withdrawal survives reload.

## Audited administrator count reporting - 19 November 2026

The user authorized Admin Overview after Help/support. D30 and [ADMIN_REPORTING.md](ADMIN_REPORTING.md) define the explicit permission for aggregate/per-farmer count metadata. Reports expose no private farm fields and do not change owner-only farm APIs. No schema, dependency or provider change is introduced.

| Check | Actual local result |
| --- | --- |
| Backend regression | **266 passed** in 95.40 seconds with required PostgreSQL/pgvector and no skips. The 12 new reporting cases also passed independently in 6.61 seconds. |
| Authorization and counts | Anonymous/farmer/advisor denial, independent service checks, revoked administrator lock wait, removed/non-farmer target hiding, disabled farmer inclusion, effective cultivation archive, workspace deletion exclusion, actual zero and bounded 30-day signup dates pass. DTO field allowlists exclude private fields. |
| Snapshot and audit | Each report uses one PostgreSQL count statement/snapshot. Successful views append minimal account audit; four immediate/deferred audit failure cases return safe failure with no report success. No counts or private farm content enter audit. |
| Frontend | **77 passed** across 12 files, including zero/error/retry states, target changes, non-admin route denial and clearing counts after session expiry. ESLint, Prettier and TypeScript/Vite production build pass. |
| Real browsers | **24 passed** in 2.1 minutes with Edge desktop 1280×900 and mobile 360×900 against real FastAPI/PostgreSQL. Four new journeys verify admin login destination, real aggregate/per-farmer counts, audit entries, continued private-farm denial, farmer denial and administrator revocation. All 20 previous journeys remain green. |
| Visual/static scope | Desktop/mobile overview and farmer count-summary captures are under ignored `frontend/test-results/` and reviewed locally. Ruff check/format pass for 64 Python files. No farmer usability research, AI evaluation, remote CI or deployment is implied. |
| Final consistency | Development/test Alembic checks both report no new operations. Generated OpenAPI confirms two authenticated reporting GET operations and count-only DTO allowlists. All 130 local links/anchors in 19 changed/new guides and feature SRS identifiers pass validation; `git diff --check` passes. |

Commands run from the repository root:

```powershell
$reportCache = Join-Path (Get-Location) '.tools/pytest-cache-reporting'
.\scripts\uv.ps1 run pytest --require-database -o "cache_dir=$reportCache" --tb=short -q
.\scripts\uv.ps1 run ruff check . ../scripts/configure_local.py --config pyproject.toml
.\scripts\uv.ps1 run ruff format --check . ../scripts/configure_local.py --config pyproject.toml
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run format:check
npm.cmd --prefix frontend run build
$env:PLAYWRIGHT_CHANNEL='msedge'
$env:E2E_API_PORT='18000'
$env:E2E_WEB_PORT='15173'
npm.cmd --prefix frontend run test:e2e
```

Browser tests use synthetic accounts and guarded PostgreSQL `_test` storage. Existing user servers/database are preserved. Public support email remains optional and unconfigured; a monitored contact/recovery policy and reporting/privacy notices are required before real-user use. Final review/publication and remote CI remain the next delivery work, followed by separately scoped curated-source preparation. M1/V0, task execution and AI are not complete.

## Public Help and scoped website support - 19 November 2026

The user authorized public Help, farmer-submitted requests and an admin inbox. `0007_support` adds tickets, immutable messages/events and generic `support_updated` notices without a provider/dependency change. Submitted text is shared with administrators; no farm or AI-chat context is attached, and support access grants no farming or recovery permission. Admin Overview/reporting remains separate. [SUPPORT.md](SUPPORT.md) and D29 define acceptance rules and limits.

| Check | Actual local result |
| --- | --- |
| Backend regression | Final **254 passed** in 87.61 seconds with required PostgreSQL/pgvector and no skips. Includes the previous 213, 34 new support integration cases and 7 contact-configuration cases. An earlier full checkpoint passed 247 before the additional configuration cases. |
| Role/ownership | Farmer-only creation/own lists/details/messages/status; admin-only submitted inbox/replies/status; absent auth/advisors/wrong roles denied before target access. Another owner's/missing ticket is uniformly hidden. Service-level checks cannot be bypassed by omitting HTTP dependencies. Support permission still denies private farm access; support bodies stay out of account audit. |
| State/evidence | Open/In progress/Resolved, resolve/reopen, resolved-reply denial, stale/no-op status, two-admin conversation, literal messages, strict owner/role/farm-field rejection and bounded list/message projections pass. Generic recipient notices contain no subject/reply text. |
| Failures/concurrency | Eight immediate/deferred ticket/message/event/notification failure cases roll back version/message/event/notice before success. Failed creation leaves no empty ticket. Concurrent replies have one winner/event/notice. A reply waiting behind requester disablement is rejected; unavailable users receive no replies/notices, while admins can resolve their tickets. |
| Storage/contact | App message/event rewrites and ticket DELETE/TRUNCATE denied; identity/subject reassignment rejected; evidence blocks downgrade. Public contact works without auth/database, optional contact is honestly unset, and invalid/URI/header-injection/non-string addresses fail validation without delivery lookup. |
| Frontend | **72 passed** across 11 files: previous 64 plus 8 support cases for payload allowlist, no mutation replay, uncertain/stale drafts, status/draft coordination, literal rendering, admin route denial, late response/account-change privacy and public Help/contact fallback. ESLint and TypeScript/Vite production build pass. |
| Real browsers | All **20 passed** in 2.1 minutes using Edge at 1280×900 and 360×900 with real FastAPI/PostgreSQL. Four new support journeys cover public Help/login, farmer submission, admin inbox/status/reply, recipient notification, follow-up, resolution/reopening/reload, foreign links, stale replies and revocation without replay. All 16 prior account/farm/landing/lifecycle journeys remain green. |
| Visual scope | Synthetic Help, support request form, admin inbox and farmer/admin conversation captures are under ignored `frontend/test-results/`. Page/form width checks pass; desktop/mobile captures are reviewed locally. No farmer research, live staffing or agronomic review is implied. |

Commands run from the repository root:

```powershell
$supportCache = Join-Path (Get-Location) '.tools/pytest-cache-support'
.\scripts\uv.ps1 run pytest --require-database -o "cache_dir=$supportCache" --tb=short -q
.\scripts\uv.ps1 run ruff check . ../scripts/configure_local.py --config pyproject.toml
.\scripts\uv.ps1 run ruff format --check . ../scripts/configure_local.py --config pyproject.toml
.\scripts\uv.ps1 run alembic upgrade head
.\scripts\uv.ps1 run alembic check
.\scripts\uv.ps1 run alembic -x db=test check
.\scripts\uv.ps1 run alembic current
.\scripts\uv.ps1 run python -m app.worker --once
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run format:check
npm.cmd --prefix frontend run build
$env:PLAYWRIGHT_CHANNEL='msedge'
$env:E2E_API_PORT='18000'
$env:E2E_WEB_PORT='15173'
npm.cmd --prefix frontend run test:e2e
npm.cmd --prefix frontend run test:e2e -- support.spec.ts
```

The final focused support browser run captures the additional page/form/inbox layouts. Development was upgraded additively to 0007, preserving existing records without seeding support tickets. Migration/reset tests ran before browser tests; existing user services and Compose database are preserved. The optional public contact email is not invented or configured on the user's behalf; a monitored address/recovery policy remains an external-user gate. No email delivery, attachments, live chat, advisor cases, Admin Overview, external deployment, remote CI or real-user/provider evaluation is claimed. Earlier records below are historical checkpoints.

## Farm restore and workspace deletion - 19 November 2026

The user requested restore/delete options for archived farms. Migration `0006_farm_lifecycle` adds an append-only farm deletion marker and restore/delete audit operations, preserving existing snapshots/records. Owner-only restore clears only the farm archive. Workspace deletion requires archive, current version and farm-name confirmation; it retains storage evidence and excludes every farm/child/history/write/restore lookup. No physical erasure, cultivation restore/deletion or deleted-record browser is introduced. D28 and FARM_RECORDS.md define the semantics.

| Check | Actual local result |
| --- | --- |
| Full backend regression | **213 passed** in 102.38 seconds, with required PostgreSQL/pgvector and no skips. Includes the previous 191 cases plus 22 lifecycle/marker cases. The targeted farm suite first passed 151 tests. |
| Access/state | Existing all-route permission, foreign/missing-ID and session tests now include both new commands. Restore reopens inherited child archives while independently archived crops stay archived. Active restore is a current-version no-op; stale restore conflicts. Active-farm deletion, wrong/stale confirmation, missing/oversized/extra fields fail without effects. Deleted farms disappear from all statuses/counts, and all nested operations return generic 404 while another owner's records remain available. |
| Atomicity/concurrency | Ten immediate/deferred revision/audit/marker failure cases return safe 503 and roll back farm version, evidence and marker before success. Real lock waits verify restore→delete, delete→restore and duplicate delete have only one effect. |
| Persistence/migrations | Marker UPDATE/DELETE/TRUNCATE denied to the app; duplicate markers rejected. Upgrade from 0005 preserves farm snapshots. Downgrade refuses when lifecycle evidence exists. Existing base rebuild/rollback/grant tests remain green. Development upgraded to 0006 without seeding or deleting farms; development and `_test` Alembic checks report no new operations, and worker `--once` reports database ready. |
| Frontend/static | All **64 frontend tests** pass. Ruff check/format (52 Python files), ESLint, Prettier and TypeScript/Vite production build pass. No dependency/lockfile changes. |
| Browser regression | All **16 passed** in 2.2 minutes on Edge desktop 1280×900 and mobile 360×900, actual FastAPI/PostgreSQL with synthetic accounts. New journeys find Archived farms, restore with Escape/focus handling, re-archive, require typed name, cancel without effect, delete and verify farm/child links and home selector are inaccessible. Existing account, landing, conflicts, history, owner isolation and revocation cases remain green. |
| Visual evidence | Desktop/mobile delete confirmation screenshots inspected under ignored `frontend/test-results/`; dialog content, typed confirmation and controls fit the tested viewports. No farmer usability study or production-readiness claim is made. |

Commands run from the repository root:

```powershell
$farmCache = Join-Path (Get-Location) '.tools/pytest-cache-lifecycle'
.\scripts\uv.ps1 run pytest --require-database -o "cache_dir=$farmCache" --tb=short -q
.\scripts\uv.ps1 run ruff check . ../scripts/configure_local.py --config pyproject.toml
.\scripts\uv.ps1 run ruff format --check . ../scripts/configure_local.py --config pyproject.toml
.\scripts\uv.ps1 run alembic upgrade head
.\scripts\uv.ps1 run alembic check
.\scripts\uv.ps1 run alembic -x db=test check
.\scripts\uv.ps1 run alembic current
.\scripts\uv.ps1 run python -m app.worker --once
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run format:check
npm.cmd --prefix frontend run build
$env:PLAYWRIGHT_CHANNEL='msedge'
$env:E2E_API_PORT='18000'
$env:E2E_WEB_PORT='15173'
npm.cmd --prefix frontend run test:e2e
```

An initial development drift check correctly reported that the old schema needed upgrading; after the authorized additive upgrade both databases match metadata. Backend migration/reset tests and browser tests ran sequentially. Existing user services and the already running Compose database were left running; browser test child processes closed after completion. No remote CI, deployment, real-user data erasure, provider/AI evaluation or retention policy validation was performed. Stored historical data survives workspace deletion and backups; this feature must not be described as permanent data erasure.

## Landing-page farm entry correction - 19 November 2026

The user clarified that the farm entry belongs in the landing-page header/hero, with a prominent website action bar. Farmer login now returns to `/`; other roles open My Account. My Farms/Add a farm sit in the website navigation, with an Add Farm header button. The hero provides Add my farm for a new farmer, Get started/login for visitors, or a private farm selector and crop/observation continuation for returning farmers. The separate dashboard implementation/checklist and fixed mobile bottom bar were removed. Its old farmer URL redirects home.

Frontend component results: **64 passed**, 10 files. Existing record/location/account cases pass, with hero farm selection, saved-state continuation, list/nested-read failure, private late-response rejection after account switch, role-aware login, no private farmer queries for visitor/advisor/administrator and direct header/hero entry. New homepage notification mocks account for the additional farm reads; the actual API wrapper and owner enforcement remain unchanged.

Final ESLint, Prettier check and TypeScript/Vite production build pass. The same documented frontend commands and isolated Edge test-port commands below are used. No dependency, migration, backend domain/API or provider change was made. Device-location tests remain simulated and do not establish live GPS accuracy. Screenshots are synthetic visual evidence; usability with farmers and remote CI remain pending.

Final Edge browser regression: **14 passed** in 2.0 minutes across desktop 1280×900 and mobile 360×900, using actual FastAPI/PostgreSQL and synthetic accounts. Visitor hero entry reaches registration/login without private farm reads. Farmer login reaches the landing page, whose header action and hero Add my farm button are visible; the hero action is in the initial viewport on both sizes. Farm creation, optional simulated location, crop/first-observation continuation, private history, foreign-owner denial, conflicts, account changes and revocation/no replay remain covered. Empty and returning-farmer landing screenshots plus visitor screenshots are in ignored `frontend/test-results/`. Desktop/mobile captures were inspected visually. Existing development services and the running database were preserved; test child processes closed after the run, using isolated loopback ports 18000/15173 and only the guarded PostgreSQL `_test` database.

## Initial onboarding/location UX checkpoint - 19 November 2026 (dashboard superseded)

The user authorized beginner-friendly entry, navigation and location assistance. Farmer sign-in and restored-session login visits now open `/dashboard`; other roles open `/account`. The dashboard uses owned saved records to guide farm/crop/observation setup and keeps other/archived farms reachable. The form offers local district/village entry, legacy/custom location text, collapsed optional coordinates/area/timezone and explicit browser location. No schema, production API, dependency, map service or agricultural guidance was added.

| Check | Actual local result |
| --- | --- |
| Frontend components | **60 passed**, 10 files. Includes role-aware login, saved/empty/failed dashboard states, nested-read failures, dashboard role denial, onboarding observation intent/archived denial, exact legacy label/timezone preservation, district-label save without inferred coordinates, explicit location result, permission/unavailable/timeout paths, cancelled late lookup and paired-coordinate validation. Prior draft/history/account cases remain covered. |
| Real browser regression | **12 passed** in 1.4 minutes: existing account/admin and farm journeys on Edge desktop 1280×900 and mobile 360×900, actual FastAPI/PostgreSQL on guarded `_test` URLs. Onboarding follows saved state from first farm through crop and first observation; coordinates persist through normal versioned save, alongside history, conflicts, owner isolation and revocation/no-replay coverage. |
| Location evidence | Browser context supplies deterministic synthetic coordinates/accuracy and grants permission. Component tests simulate device errors/cancellation. These verify application handling, not live GPS accuracy, a real farm visit, district membership or agronomic applicability. |
| Static checks | Final ESLint, Prettier check and TypeScript/Vite production build pass. `git diff --check` passes. No manifest or lockfile changes. |
| Visual evidence | Empty/ready dashboard and expanded farm form screenshots plus cultivation/history/denial captures are under ignored `frontend/test-results/`. Desktop/mobile page and open-form width checks pass. Screenshots are synthetic local evidence, not farmer research. |
| Backend boundary | Only `tests/browser_server.py` changes: optional loopback ports and its explicit web origin. Ruff check/format pass for this harness. Existing domain code/schema are unchanged; previous 191-test backend evidence is historical, not rerun here. |

Commands run from the repository root:

```powershell
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run format:check
npm.cmd --prefix frontend run build
.\scripts\uv.ps1 run ruff check tests/browser_server.py --config pyproject.toml
.\scripts\uv.ps1 run ruff format --check tests/browser_server.py --config pyproject.toml
$env:PLAYWRIGHT_CHANNEL='msedge'
$env:E2E_API_PORT='18000'
$env:E2E_WEB_PORT='15173'
npm.cmd --prefix frontend run test:e2e
```

Default port 8000 was already occupied. The harness now accepts validated `E2E_API_PORT`/`E2E_WEB_PORT` overrides (defaults unchanged), selects its explicit origin and still refuses non-`_test` databases. The user's running services and already healthy Compose PostgreSQL were preserved. Browser runner child processes closed after the final successful run. Initial checks caught an outdated role-routing expectation after a test farmer became an advisor; the helper now checks the actual login role. Vite config imports use explicit TypeScript extensions. Colour-environment warnings remain informational. No remote CI, deployment, real-user/provider evaluation or region validation was run.

## FR-D connected screens verification - 18 November 2026

The user authorized My Farms, farm/cultivation details, observations, explicit stage confirmation, archive and history screens. FR-D reuses the existing theme, session client, fields/notices and native dialog. No dependency, database migration, provider, default development record or external publication was added.

| Check | Actual local result |
| --- | --- |
| Frontend behaviour | **41 tests passed** across 10 files: previous 30 tests plus 10 Farm Records component cases and one no-replay client case. Covers stale/uncertain saves, exact versions/decimal payloads, client validation, loading/retry/pagination, inaccessible/archived views, literal notes/history, preserved observation timestamp precision and late replies after account changes. These doubles prove UI behaviour, not server authorization. |
| Connected browser journeys | **All 12 passed** using headless Microsoft Edge at 1280x900 and 360x900 against the actual FastAPI app and guarded PostgreSQL/pgvector `_test` database. Six existing account journeys and six new Farm Records journeys passed. |
| Final form-layout check | The focused Farm Records suite then passed **all 6 cases** again, including explicit no-overflow checks while the farm, cultivation and observation creation forms are open. This rerun includes the final homepage availability/plural copy. |
| Manual workflow | Both sizes create/edit a farm, create a planned cultivation, create/edit an observation, read old text/provenance in history, confirm a stage, change planting date to invalidate it, archive cultivation/farm and read archived records/history. No browser storage or page errors were observed in the full journey. |
| Access/conflict/session | Real concurrent API edits produce 409 in the browser while its draft stays visible/disabled until explicit reload. Another owner's URL exposes no private record. Sign-out/account switch clears earlier records. Committed account disablement denies the next save, clears its draft, sends the browser to login and does not replay the mutation. Administrator farm navigation is denied. |
| Visual/accessibility | Actual My Farms, cultivation and observation-history desktop/mobile screenshots were inspected. Layouts fit their viewports without horizontal scrolling. Native archive dialog Escape, initial cancel focus and focus restoration passed. Full-page synthetic screenshots are ignored artifacts under frontend/test-results/. No farmer usability study is claimed. |
| Static/build | ESLint, Prettier and strict TypeScript/Vite production build pass. Homepage tests cover the Available Farm Records badge, two Planned AI/planning cards and farmer-only entry; illustrative sample labels stay intact. |
| Documentation | `git diff --check` passed; all 82 local links across 16 changed/new Markdown guides resolve and referenced SRS identifiers remain valid. |

Commands from the repository root:

```powershell
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run format:check
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run build
$env:PLAYWRIGHT_CHANNEL='msedge'
npm.cmd --prefix frontend run test:e2e
npm.cmd --prefix frontend run test:e2e -- farms.spec.ts
```

Docker's existing database service was started for verification; the browser harness applies migrations only to the guarded `_test` database and creates synthetic accounts using generated environment-only credentials. Initial browser checks found test-selector/menu-timing issues that were corrected. The sandboxed runner could not close its own test servers; only process IDs reported by that run were terminated, then the final suite ran with process-cleanup permission and completed all 12 tests/cleanup successfully. Node reported colour-environment warnings and npm printed an update notice; no package update was performed.

Farm POST/PATCH calls opt out of unauthorized-request replay. On 401, farm client handling forgets the token and clears private views; existing GET refresh behaviour remains. On 409, the draft remains until an explicit reload with a discard explanation. Uncertain network/503 creation offers record review rather than a retry. Device-local observation input and farm-timezone display are explicit; notes-only changes preserve the exact original instant. Server authority and transaction guarantees remain the unchanged FR-C implementation.

Backend migration/reset tests were not rerun concurrently with browser tests. Browser servers closed after the successful runs; the Compose database service was stopped afterward with its named volume preserved. No remote CI, deployment, source/AI evaluation, tasks, proposals, weather or advisor sharing was run or added. Evidence covers manual Farm Records only; full V0/AT01/AT02 and real-user operating/retention gates remain pending. All live data used here was synthetic local test data.

## FR-C owner-only services/API verification - 18 November 2026

The user authorized backend services/APIs, leaving screens and remote CI pending. FR-C adds DTOs, farm services, 19 operations on 13 paths and router registration, using the unchanged `0005_farm_records` schema. Tests exercise the actual ASGI app, JWT/session checks and real PostgreSQL transactions with synthetic data. No farmer permission, provider or database double establishes these results.

| Check | Actual local result |
| --- | --- |
| Full backend suite | **191 passed** in 48.43 seconds on the final run, no warnings. Includes 61 new FR-C API cases, 68 FR-B persistence cases and 62 existing account/foundation cases. |
| Access boundary | All farm operations reject absent auth and excluded advisor/admin roles. Foreign/missing IDs have uniform 404s; mixed parents, history, search/count/pagination and inactive/current-role cases cannot widen access. A direct service call also rejects administrator access without relying on route guards. |
| Manual lifecycle | Create farm/cultivation/observation, explicit stage confirmation, crop/date invalidation, no-op/paired/null PATCH, preserved observation/provenance history, archives and inherited read-only states pass. Planned dates use the farm timezone; observations normalize to UTC. |
| Input/privacy | Ownership/author/parent/confirmation mass assignment, invalid dates/coordinates/areas/units/timezone/crop/text and future/naive observations fail safely. Browser write protections and no-store/request IDs pass; responses omit raw private values and SQL failure details. |
| Concurrency | Real competing requests and PostgreSQL lock waits prove one winner for stale edits, safe archive-first/child-first ordering and denial of a writer waiting behind committed account disablement/revocation. |
| Transaction failure | Immediate/deferred revision/audit failure returns 503 before success and rolls back the new farm, revision and event. Existing persistence/account rollback regressions remain green. |
| Static/schema | Ruff lint/format pass. Both development/test `alembic check` report no new operations. No dependency, lockfile or schema migration was added for FR-C. |
| Contract/docs | Generated OpenAPI has 19 Farm Records operations on 13 paths with forbidden extra create fields and no client owner property. `git diff --check`, all 78 local Markdown links across 16 changed/new guides and SRS references pass. |

Commands actually run from the project root:

```powershell
$farmCache = Join-Path (Get-Location) '.tools/pytest-cache-frc'
.\scripts\uv.ps1 run pytest --require-database -o "cache_dir=$farmCache" --tb=short -q
.\scripts\uv.ps1 run ruff check . ../scripts/configure_local.py --config pyproject.toml
.\scripts\uv.ps1 run ruff format --check . ../scripts/configure_local.py --config pyproject.toml
.\scripts\uv.ps1 run alembic -x db=test check
.\scripts\uv.ps1 run alembic check
```

Initial targeted runs found and corrected a nullable-soil validator issue and a crop SELECT-only permission conflict from an unnecessary row lock. The final service preserves the read-only catalogue and checks crop assignment without expanding grants. Test fixture cleanup also removes operator-created synthetic catalogue variations between tests/reruns, in the guarded `_test` database only.

No frontend, farm browser journey, remote CI, deployment, AI/provider evaluation, case sharing or proposal/task execution was run or added. API evidence covers the manual-record/owner portions of AT01/AT02; full acceptance remains pending. Retention/account erasure and external-user operating gates remain unresolved. Refer to FR-B below for the prior development migration; FR-C leaves development records/schema unchanged. Docker Desktop and the previously stopped Compose database were started to run the PostgreSQL checks; the database service was stopped afterward with its named volume preserved.

## Farm Records planning checkpoint - 18 November 2026

[FARM_RECORDS.md](FARM_RECORDS.md) defines FR02/FR05-FR10, archive/history, audit-isolation and concurrency cases. At the original FR-A checkpoint only documentation existed; no farm migration/API/UI or authorization test had run. The subsequent FR-B record below supersedes its persistence status. Identity/persistence results do not establish the later HTTP ownership boundary or full AT01/AT02 completion.

Documentation verification: `git diff --check` passed. A local Python check resolved all 59 local Markdown links across the 11 changed/new documents, confirmed the plan's FR/DR/AT identifiers exist in the SRS, checked the FR-A through FR-E sequence, and confirmed changes are Markdown-only. Review compared the access/parent/archive/version rules against the existing identity/audit code and architecture; no farming runtime behaviour, database migration, browser journey or remote CI was executed in this documentation task.

## FR-B persistence verification - 18 November 2026

The user authorized the database layer after planning. Migration `0005_farm_records` adds eight tables, fixed supported chilli reference, immutable owner/parent/author identity triggers, per-entity revision/event uniqueness and restricted app grants. Tests use only the guarded dedicated PostgreSQL 18/pgvector database; no SQLite, real farmer records or providers are used.

| Check | Actual local result |
| --- | --- |
| Backend suite | 130 passed, no warnings on the final run; includes 68 Farm Records cases and the existing 62 account/foundation tests. |
| Domain constraints/history | Paired coordinates/area, finite dates, bounds/units, unknown soil/stage, planned dates, confirmation provenance, nonblank text, strict snapshot shape/identity and preserved observation revisions passed. |
| Permissions/references | App DELETE/TRUNCATE and revision/audit rewrites denied; crop catalogue is read-only. Owner/parent/author reassignment and mixed audit parent chains fail. Referenced-row deletion is blocked; account removal keeps tombstone-linked farm history. |
| Transactions/concurrency | Real concurrent duplicate revision/audit attempts produce one committed row. Immediate and deferred revision/audit failures roll back the record, revision and audit transaction. |
| Migrations | Upgrade from 0004 preserves existing users/notifications; downgrade/rebuild from base passes in the dedicated test database. Injected migration-transaction failure rolls back tables, seed, function and revision. |
| Local development | Upgraded from 0004 to 0005 without seeding farm records. `alembic current` reports 0005 head and `alembic check` reports no new operations. Worker `--once` reports database ready, still no business job handlers. |
| Static/docs | Ruff lint/format passed. Standalone test-database `alembic check` also reports no new operations. `git diff --check` and all 77 local links across 15 changed/new Markdown guides passed; SRS references resolve. |

Commands run from the repository root (the wrapper runs Python in backend/):

```powershell
.\scripts\uv.ps1 run alembic -x db=test upgrade head
$farmCache = Join-Path (Get-Location) '.tools/pytest-cache-frb'
.\scripts\uv.ps1 run pytest --require-database -o "cache_dir=$farmCache" --tb=short -q
.\scripts\uv.ps1 run ruff check . ../scripts/configure_local.py --config pyproject.toml
.\scripts\uv.ps1 run ruff format --check . ../scripts/configure_local.py --config pyproject.toml
.\scripts\uv.ps1 run alembic upgrade head
.\scripts\uv.ps1 run alembic current
.\scripts\uv.ps1 run alembic check
.\scripts\uv.ps1 run alembic -x db=test check
.\scripts\uv.ps1 run python -m app.worker --once
```

The absolute ignored cache path avoids an existing Windows pytest-cache write issue. Earlier default-cache checks reported warnings, and a relative path containing `..` failed cache initialization in the installed pytest; the final absolute-path run completed without warnings. Development data was not reset; destructive upgrade/downgrade/failure checks target `_test` only. The previously stopped Compose database was started for verification and stopped afterward with its named volume preserved. No farm service automatically creates revisions/audit yet: tests assemble transactions explicitly to verify persistence. Live owner/session enforcement, archive-versus-write races, optimistic service conflicts, browser journeys, frontend checks and remote CI were not implemented/run by FR-B. Do not mark AT01/AT02 or V0 complete.

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

At this M0 checkpoint the foundation exit criteria were met and user management was not yet implemented. The subsequent UM1 record below supersedes that identity status. M0 alone did not verify production hosting, OS servicing, private-user access, AI quality or later milestones.

## UM1 local verification record - 16 November 2026

The user requested the backend/frontend implementation after planning. The [UM1 contract](USER_MANAGEMENT.md) is now implemented with actual PostgreSQL-backed verification. Tests use synthetic farmers/advisors/administrators, not real account data or SQLite. The database fixture requires URLs ending in `_test`; integration tests truncate/rebuild only this dedicated test database. Do not point it at data you need to keep. Run backend and browser database suites sequentially, because the backend migration/reset checks rebuild the test schema.

| Check | Actual outcome |
| --- | --- |
| Backend | `pytest --require-database`: 38 passed, no skipped integration cases; includes the original foundation checks |
| Registration/validation | Generic new/duplicate outcomes, Argon2id storage, normalized email uniqueness, concurrent signup, strict DTO/mass-assignment and password redaction checks passed |
| Identity/session | Wrong/unknown/disabled login failures; tampered/wrong-algorithm/issuer/audience/expired tokens; unknown/revoked/expired sessions; rotation/replay/concurrent refresh and logout checks passed |
| Permissions/account writes | Own profile only, non-admin/advisor denial before target disclosure, stale versions, role/status revocation, re-enable requiring new login, self-management denial and concurrent administrator preservation passed |
| Atomicity/audit | Immediate audit-insert failure and a real deferred PostgreSQL commit-trigger failure both returned errors and rolled back account/session/audit writes; app audit UPDATE/DELETE denied |
| Abuse/browser boundaries | Missing/null/untrusted Origin and wrong client header denied; shared quotas, Retry-After, bucket expiry, registration/refresh caps and production Secure cookie checks passed |
| Migrations/metadata | Upgrade from M0 and test-database downgrade/rebuild through base to head passed; `alembic check` reported no new operations |
| Worker | Separate `python -m app.worker --once` reported database ready and exited successfully; no identity jobs invented |
| Frontend | 11 tests passed: foundation status, auth forms/confirmation/password masking, safe failures/retry, denied admin navigation, 429/empty-state retry, single-flight refresh, uncertain-response handling and memory-only tokens |
| Build/static | TypeScript production build, ESLint, Prettier and Ruff lint/format passed |
| Browser | Playwright 1.65.1 with installed headless Edge: all 6 tests passed (3 actual journeys at both 1280px and 360px) |
| Browser journeys | Farmer registration/login/profile/reload/denied-admin/logout; admin search/filter/detail/confirmed role/disable/re-enable with target-session revocation; concurrent real API edit yielding a stale UI decision and record reload |
| Accessibility/layout | Dialog Escape/focus restoration, password fields, accessible form navigation, no horizontal page scrolling and real session-cookie attributes checked; local screenshots inspected |
| Hash sample | Five sequential local Argon2id hash/verify runs: median 69.2ms hash, 69.4ms verify; parameters m=65536 KiB, t=3, p=4. This is a local sample, not a load/performance guarantee |
| Dependencies | Generated uv/npm locks include the selected libraries; npm installation audit reported zero findings |

The initial browser runs exposed overly broad test locators and a real React StrictMode dialog-focus restoration issue; those were corrected before the final green six-test run. Test traces/video are disabled to avoid recording token traffic; screenshots contain only synthetic account data and remain ignored. Browser server fixtures use fresh generated credentials, a guarded test DB and no default development administrator. They start API/Vite automatically and refuse to reuse existing servers. Stop normal API/Vite on 8000/5173 before running the suite.

From the project root, after normal locked setup and `docker compose up -d --wait`:

```powershell
.\scripts\uv.ps1 run ruff check . ../scripts/configure_local.py --config pyproject.toml
.\scripts\uv.ps1 run ruff format --check . ../scripts/configure_local.py --config pyproject.toml
.\scripts\uv.ps1 run alembic upgrade head
.\scripts\uv.ps1 run alembic check
.\scripts\uv.ps1 run pytest --require-database
.\scripts\uv.ps1 run python -m app.worker --once
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run format:check
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run build
```

For the default Chromium browser, install its matching Playwright binary once and then run the suite:

```powershell
Push-Location frontend
npm.cmd exec -- playwright install chromium
npm.cmd run test:e2e
Pop-Location
```

The local run used the already installed Edge instead of downloading Chromium:

```powershell
$env:PLAYWRIGHT_CHANNEL = 'msedge'
npm.cmd --prefix frontend run test:e2e
Remove-Item Env:PLAYWRIGHT_CHANNEL
```

Linux CI installs Chromium with `npx playwright install --with-deps chromium` and runs the same suite after backend/frontend jobs pass. That expanded remote workflow is configured, not executed for the current uncommitted UM1 changes. Real-user recovery/verification/privacy, deployed ingress, production security review, general farm/case authorization and full AT02 remain unverified. Browser tests and component doubles are distinguished above; no live-provider evaluation was performed.

## Public homepage follow-up - 16 November 2026

The user requested a homepage as the opening screen. `/` now renders a public React page outside the session provider, with no API request, and login/register/account header wordmarks link home. The new regression check renders the actual App route with an unavailable API, verifies the opening content and working account links, and checks that future features are labelled as roadmap items.

Frontend suite: 12 tests passed; ESLint, Prettier and strict TypeScript/production build passed. A separate local headless Edge check at 1280px and 360px blocked account API traffic and verified that home still rendered, login/register/home navigation worked, there were no page errors and there was no horizontal scrolling. Screenshots were visually inspected and remain ignored under `.tools/screenshots/home-*.png`; the smoke script is an ignored local QA helper, not an additional committed CI suite.

The regular frontend check commands above exercise the regression test. Backend code and account rules did not change, so backend tests and the six database-backed account browser journeys were not rerun for this frontend-only task. Their earlier results remain recorded separately. No dependencies, agricultural features, deployment or remote CI result were introduced by this follow-up.

## Homepage style revision - 16 November 2026

The user selected homepage first, bold/premium styling and real or generated imagery. The homepage now uses a locally generated photographic chilli-field hero, scoped forest/lime colours and heavy display typography. The built-in image_gen tool produced the original PNG; the served WebP is 1672 × 941 and 313,452 bytes. The [asset record](../frontend/public/images/README.md) contains the exact prompt and provenance. Alt text/footer disclose the generated nature, and future capabilities remain labelled as roadmap items.

Checks run: all 12 frontend tests passed, plus ESLint, Prettier and strict TypeScript/production build. Local headless Edge verified image loading, public home without API calls, login/register/home links and absence of horizontal scrolling or page errors; screenshots were inspected. The final header overlay improves text separation from the bright sky. Screenshot/script artifacts remain ignored under .tools. Backend/authentication behaviour and account styles are outside this visual task; no new dependencies, live-provider evaluation, deployment or remote CI result is claimed.

## Reference-led homepage refinement - 17 November 2026

The user approved adapting their supplied homepage screenshot. This homepage-only change adds a light header, photo hero, three planned feature previews, planned three-step workflow, trust/control principles, account CTA and grouped footer. It reuses the existing generated WebP without adding dependencies. Each feature has a Planned badge and an Illustrative preview label; the panels do not supply real agronomic advice or functional farm controls.

Commands run from frontend/: `npm.cmd run test` (12 tests in 6 files passed), `npm.cmd run lint`, `npm.cmd run format:check` and `npm.cmd run build` (strict TypeScript and Vite build) all passed. The homepage regression check verifies public rendering with an unavailable API, account-entry links, three planned/illustrative labels and valid section-anchor targets.

Local headless Edge smoke checks passed at 1280, 768, 360 and 320 pixels: HTTP 200, hero image loaded, no homepage API requests, keyboard skip link, all three header section anchors landing at their targets, login/register/home navigation, no horizontal scrolling and no JavaScript page errors. Desktop full-page and mobile hero screenshots were visually inspected. The local command `node .tools/reference-home-smoke.cjs` requires the frontend dev server at port 5173 and installed Edge; this ignored QA helper/screenshots are local evidence, not a committed CI suite. Normal frontend check commands above remain the repeatable repository checks.

Account styles, API, database and worker code were not changed in this task. Backend and full account E2E suites were not rerun for this homepage-only refinement. No remote CI, deployment, live provider evaluation or real-user usability validation is claimed.

## Merged design guide and creamy green homepage - 17 November 2026

The supplied Agro-Intelligence Editorial DESIGN.md was merged into UI_DESIGN.md, preserving the existing navigation, interaction, accessibility and product-safety requirements. The user requested a creamy green background, which replaces the reference's conflicting lavender surface tokens. The homepage now uses cream #f7f8ef, sage #edf2e5, warm-white cards, forest/sprout accents, finer borders and 24px card corners. It retains the existing section structure, image, working account links and planned/illustrative labels. Account styles and backend code were not changed.

Plus Jakarta Sans is bundled as an unmodified 27,348-byte Latin variable WOFF2, weights 400-800, with its full SIL Open Font License and [source/hash record](../frontend/public/fonts/plus-jakarta-sans/README.md). No font service request or new npm dependency is required at runtime.

From frontend/, `npm.cmd run test` passed all 12 tests in 6 files; `npm.cmd run lint`, `npm.cmd run format:check` and `npm.cmd run build` passed. Local headless Edge checks passed at 1280, 768, 360 and 320 pixels. Chromium platform-font inspection confirmed the custom Jakarta font supplied heading glyphs; checks also confirmed the cream/sage computed colours, loaded hero image, no homepage API/external requests, planned/illustrative labels, keyboard skip, section-anchor landing, login/register/home links, no horizontal overflow and no JavaScript page errors. Desktop full-page and mobile hero screenshots were visually inspected.

Sampled solid-background text pairs (body, card copy, accent action, planned badge and step numbers) meet at least 4.5:1 contrast. The initial step-number sample measured 4.18:1; its text was darkened before the passing final browser run. This sampling is not a full accessibility audit or a measured contrast guarantee across the photographic hero. The local QA helper `node .tools/creamy-home-smoke.cjs` requires the frontend dev server on port 5173 and installed Edge; helper/screenshots remain ignored local evidence rather than a committed CI suite.

No backend/full account E2E rerun, remote CI, deployment, AI evaluation or real-user usability study is claimed for this visual/documentation task.

## Shared creamy green theme across existing screens - 17 November 2026

The user extended the merged homepage visual style to the other existing parts. A single font-face/palette now lives in frontend/src/theme.css, consumed by homepage/account aliases. Updated screens are login/registration, account, administrator list/detail, native confirmation dialogs, shared states and /connection. Plus Jakarta Sans, creamy green/sage surfaces, rounded warm-white cards, pill navigation/actions, forest selected/save/confirm actions and sprout auth actions replace the former account serif/system theme. Desktop auth reuses the generated field photo; mobile remains form-first. No backend, API/session/permission logic, database or dependency change was made.

Verification completed:

- From frontend/: `npm.cmd run test` passed 12 tests in 6 files; `npm.cmd run lint`, `npm.cmd run format:check` and `npm.cmd run build` passed.
- Docker Desktop and the existing PostgreSQL container were started for the dedicated test databases. With normal API/Vite ports free, `$env:PLAYWRIGHT_CHANNEL='msedge'` then `npm.cmd --prefix frontend run test:e2e` passed all 6 existing real PostgreSQL-backed browser journeys (3 journeys at 1280px and 360px); remove the environment variable afterwards. Journeys cover registration/login/profile/reload/logout/denied admin access, administrator search/filter/role/disable/re-enable, session revocation, stale-edit recovery and dialog Escape/focus restoration. Only synthetic test accounts were used. Harmless NO_COLOR/FORCE_COLOR warnings appeared; no test failure remained.
- Additional local visual/state checks at 1280, 768, 360 and 320 pixels covered login, registration, account/mobile menu, administrator list/detail, dialog, access-denied, offline and connection views. Browser platform-font inspection confirmed local Jakarta glyph rendering; checks confirmed cream canvas, no external requests, no horizontal page scrolling, no overlapping role/status badges, password visibility toggles and dialog Escape/focus restoration. These use synthetic HTTP doubles for screenshots/state coverage and are **not** server authorization evidence; the six real journeys above supply separate integration evidence. Local helper: `node .tools/shared-theme-smoke.cjs` with the frontend dev server on port 5173 and installed Edge. Screenshots/helpers are ignored local artifacts, not another committed CI suite.
- `node .tools/creamy-home-smoke.cjs` passed again at all four widths after the shared-token/font move, including homepage API independence, actual local font rendering, sampled contrast, image loading, section anchors and account links.

Desktop registration/account and additional desktop login/mobile account/admin/dialog screenshots were visually inspected. Existing native dialog behaviour and server permission boundaries are preserved. Backend suites were not rerun for this visual-only task. No remote CI run, deployment, full accessibility audit or real-user usability study is claimed.

## Signup password policy - 17 November 2026

The user requested an 8-character minimum with at least one letter, number and symbol. Signup and the server Register DTO now require 8-128 characters, including a Unicode letter, decimal digit and punctuation/symbol character. Uppercase is optional; spaces are preserved but do not count as a symbol. The first-administrator CLI reuses Register and its prompt is updated. Login retains its prior input bounds and accepts existing stored passwords without the new composition check. Hashing/session controls and database schema are unchanged. Synthetic registration fixtures now satisfy the policy; browser fixture credentials guarantee a letter/number/symbol in addition to generated entropy.

Checks completed using the documented commands:

- `uv run ruff check` and Ruff format check passed through scripts/uv.ps1; `scripts/uv.ps1 run pytest --require-database` passed **54 tests** using the dedicated PostgreSQL/pgvector test database. New cases reject too-short/long passwords, each missing class, whitespace/format characters masquerading as symbols and verify safe 422/no user creation. Accepted cases cover exactly 8 characters, lowercase-only letters, Unicode letters/digits/symbols, the 128-character maximum and preservation of leading/trailing spaces. Existing passwords without the new composition still log in. Existing permission/session/audit/concurrency/migration tests remain green.
- From frontend/, `npm.cmd run test` passed **25 tests**; ESLint, Prettier and TypeScript/Vite production build passed. Form tests cover matching 8-character signup, each missing class/length failure before an API call, supported Unicode and untrimmed values, confirmation mismatch/password masking and existing-password login forwarding.
- After the backend suite completed (the suites share a disposable test DB), `$env:PLAYWRIGHT_CHANNEL='msedge'` plus `npm.cmd --prefix frontend run test:e2e` passed **all 6** real browser journeys at 1280px/360px; the environment variable was then removed. The registration journey now rejects each missing class locally without sending registration requests, then creates an account using a generated compliant password of exactly 8 characters and logs in successfully. Existing profile/admin/session/stale-edit/dialog journeys still pass. No default development account was added.

No remote CI, deployment, live provider evaluation or password-strength measurement is claimed. Ordinary signup/API validation remains independent of external providers.

## Account removal and password change - 18 November 2026

The user requested administrator account removal and a password-change option for users. Migration `0003_account_lifecycle` adds `users.deleted_at`. Admin DELETE checks actor/session, self-removal, expected version and active-admin safety; atomically scrubs the login email/name/password hash, disables and marks the account, revokes sessions and appends audit. Tombstones are hidden from ordinary lists and can be reviewed through `status=deleted`; audit/FK history stays intact. This is permanent removal of login identity in the UI, not physical deletion of the row or a declared retention policy for future farm/chat data. Own-password change requires the current password, reuses the 8-128 letter/number/symbol rule and shared login rate limits, advances the account version, retains the current session, revokes other sessions and audits without recording secrets.

- `.\scripts\uv.ps1 run pytest --require-database` passed **60 tests** against real local PostgreSQL 18/pgvector, including migration rebuild, non-admin/self-removal/stale-version denial, scrubbed listing/login denial/session revocation, concurrent admin removal preserving one admin, audit-failure rollback, wrong-current-password/policy checks, other-session revocation and successful new-password login.
- Frontend `npm.cmd test` passed **27 tests**. ESLint, Prettier check and TypeScript/Vite production build passed. Form coverage verifies password policy rejection before API submission and the current/new password request; user-list UI exposes the deleted filter.
- Playwright `$env:PLAYWRIGHT_CHANNEL='msedge'; npm.cmd run test:e2e` passed **all 6 desktop/mobile journeys**. Existing farmer profile journey now changes the password, reloads and signs in with the replacement. The administrator journey disables/re-enables, removes a synthetic account, verifies the deleted filter count and confirms the removed user cannot sign back in. Browser uses the separate guarded `_test` database.
- The Compose database service was started because it was stopped before verification, then stopped afterward with its named volume preserved. No volume deletion/reset or development-database migration was performed in the test suite.

Remote CI for these uncommitted changes, deployed behavior, real-user retention policy and account recovery remain unverified/out of scope. The database-removal behavior retains tombstones pending a broader retention decision; future farm/chat records must define their own privacy and retention handling before collection.

## Consistent brand mark - 17 November 2026

The user reported different logos on home and signup/account screens. The existing homepage leaf/sage-tile wordmark now comes from one Brand.tsx component and brand.css stylesheet, reused by the homepage header/footer, login/registration, account/admin headers and /connection. The previous W badges, duplicate styles and mobile rules hiding/resizing the logo were removed. Home navigation remains intact.

From frontend/, all 25 component tests passed, plus ESLint, Prettier and TypeScript/Vite production build. Local headless Edge checked /, /login, /register, /account, /admin/users and /connection at 1280, 768, 360 and 320 pixels. It compared the SVG path, icon/tile colour, dimensions, radius, wordmark/AI typography and visibility across routes/footer; all matched. Page-fit, login-to-home navigation and absence of JavaScript page errors passed. A 320px login screenshot was visually inspected. These focused UI checks use synthetic HTTP doubles, not authentication evidence; the earlier six real account journeys were not rerun for this logo-only change. The ignored local helper is `node .tools/brand-smoke.cjs`, requiring the frontend dev server at 5173 and installed Edge. No backend change, remote CI run or deployment is claimed.

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

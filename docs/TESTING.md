# Testing strategy

Status: M0 complete and UM1 account, audit-history, in-app notification and homepage session-navigation work verified locally. On 18 November 2026, account/audit changes passed 62 backend tests, 29 frontend tests and all 6 desktop/mobile browser journeys; migration/drift, lint, format and build checks passed. The subsequent homepage/login-navigation follow-up passed 30 frontend tests, lint, format and production build. Its browser rerun could not start because local port 8000 was already occupied; do not treat the earlier browser result as verification of the new redirect. Expanded CI has not run remotely for these local changes. Farming/AI release suites remain future work.

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

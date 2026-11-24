# Decision register

Last updated: 19 November 2026. M0 is complete. The user selected the warm green direction and explicitly requested the user-management backend/frontend implementation after planning. D19-D25 record local account/UI follow-ups; D26 records Farm Records FR-A planning through FR-D connected screens, and D27 records farmer onboarding/location assistance. Recovery, privacy and deployment decisions remain distinct from locally implemented controls.

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
| D05 | Code license and source repository/remote? | Repository setup/sharing | GitHub remote configured at Ushan-Srinuka/WagaMaga; code license remains unselected. |
| D06 | Exact V0 identity, acceptance and execution scope? | Before V0 mutations | Synthetic local records only; apply DR02 when tasks change |
| D07 | Supported area, evidence coverage and reuse rights? | Before publishing the corpus | Confirm chilli applicability and permissions |
| D08 | Parser, upload limits, scan mechanism and extraction fallback? | Before ingestion | Bound worker resources; local FM-Abhaya legacy text conversion selected for recognized fonts. OCR remains deferred. |
| D09 | LLM/embedding provider, model, dimensions, privacy and budget? | Before real AI evaluation | Compare using fixed questions; fake providers for ordinary tests |
| D10 | Routine/referred/blocked categories and qualified reviewer? | Before executable proposals/pilot | Review policy with an agricultural advisor; label simulated review |
| D11 | Session durations, hash library, recovery, rate limits, CSRF and CORS? | UM1 | D19-D23 are selected for the authorized implementation; recovery/email verification and real-user policy remain open. |
| D12 | Inaccessible-object policy, pagination and errors? | UM1 / later domains | Identity uses 401/403 before target lookup, then 404, bounded 20/100 pagination and safe 409/422/429/503 outcomes. Future private domain policy remains to be finalized. |
| D13 | Weather provider, precision, permissions, freshness and thresholds? | Live weather/review rules | Fixtures first; thresholds require domain validation |
| D14 | Retention, account deletion, reporting contact and provider terms? | Before real user data/external access | No durations/contact invented |
| D15 | Host, file storage, TLS, backup tooling and monthly budget? | Deployment planning | Preserve separate API/worker and private DB/storage |
| D16 | UI palette, typography, components and navigation? | UM1 | Warm green direction selected; the 17 November follow-up extends creamy green/sage surfaces, Plus Jakarta Sans, forest/sprout actions and rounded shared components across all existing screens. Plain CSS/accessible interactions remain. Future domain navigation remains open. |
| D17 | Testing, linting and formatting tools? | M0, expanded as features arrive | Accepted 15 November 2026: pytest/TestClient/HTTPX, Ruff; TypeScript compiler, ESLint, Prettier, Vitest/React Testing Library; Playwright when browser journeys exist. |
| D18 | Build user management early? | After M0 | Accepted sequence, then full backend/frontend UM1 implementation explicitly requested on 16 November 2026. This brings identity forward without marking M2 complete. |
| D19 | Password/JWT libraries and input policy? | UM1 | pwdlib 0.4.2 + Argon2id (argon2-cffi 25.1.0), PyJWT 2.15.1/HS256, email-validator 2.4.0; generated server key and strict DTOs. On 17 November the user selected 8-128 characters plus a letter, number and symbol for new passwords, superseding the initial 15-character minimum. |
| D20 | Browser session/refresh design? | UM1 | Selected/implemented: 15-minute memory-only access JWT, absolute 7-day families, hashed opaque refresh history, locked rotation/replay revocation and current actor/session checks. Same-origin browser proxy with exact Origin/client-header protections. |
| D21 | Administrator setup and lifecycle? | UM1 | Selected/implemented: restricted first-admin CLI, farmer-only signup, one role, own display-name editing, audited/versioned admin role/status writes and atomic revocation; self changes blocked and active administrator preserved. Recovery/deletion remain excluded. |
| D22 | Routing and reusable UI? | UM1 | Selected/implemented: React Router 8.5.1 declarative mode, existing Vite/React stack, plain CSS variables and shared fields/notices/native dialogs. No state manager or UI kit added. Playwright 1.65.1 added under D17. |
| D23 | Anti-abuse, recovery and data boundary? | UM1 / before real users | Implemented shared PostgreSQL fixed-window limits: 5 account failures/15min, 50 login IP attempts/15min, 5 registrations/IP/hour, 30 refreshes/IP and family/min. Keys are HMAC-derived; expired buckets are removed. Local synthetic use only; recovery, verification and retention remain open. |
| D24 | Account removal and password changes? | UM1 follow-up | Implemented identity scrub/tombstone and current-password-confirmed own change; future domain retention remains open. |
| D25 | Audit viewer and in-app notifications? | UM1 follow-up | Implemented account audit feed and recipient-owned account-security notices; no private farm access. |
| D26 | Farm Records scope, fields, ownership and history? | M1 Farm Records | FR-A through FR-D implemented locally with PostgreSQL and connected desktop/mobile evidence. Remote CI pending. |
| D27 | Beginner farmer entry and location input? | Farm Records UX | Accepted 19 November 2026: landing-page header/hero farm entry, local district reference and explicit optional browser geolocation. Existing API/schema and owner boundary retained. |
| D28 | Restore and delete archived farms? | Farm Records follow-up | Selected 19 November 2026: versioned owner-only restore and irreversible workspace deletion via an append-only tombstone; historical data is retained rather than erased. |
| D29 | Farmer Help and admin support? | Website support | Selected 19 November 2026: public Help, farmer-submitted requests, a scoped admin inbox and generic in-app notices. No blanket private-farm access or password recovery. |
| D30 | Administrator overview and farmer counts? | Admin reporting | Selected 19 November 2026: audited aggregate and per-farmer count metadata through dedicated endpoints. No private farm detail, observation, chat or action access. |

The solo developer owns engineering choices. Agricultural policy and evidence applicability require qualified domain input. These dependencies do not mean every routine implementation detail requires a separate approval.

## UM1 implementation choices - 16 November 2026

Homepage-only visual revision, 16 November 2026: the user selected bold/premium styling and real or generated imagery. D16's warm green account UI remains the account-page baseline; the homepage now uses a scoped forest/lime palette, heavy system sans-serif display text and a generated chilli-field image. The built-in image_gen tool was selected within the user's image preference; local PNG/WebP assets and exact prompt/provenance are recorded in frontend/public/images/README.md. This does not select a global UI kit, change the stack or imply the image depicts an actual farm.

Homepage reference refinement, accepted 17 November 2026: the user supplied a visual reference and approved adapting its layout for the homepage only. This supersedes the homepage's oversized uppercase/lime presentation above with sentence-case sans-serif headings, a light header, photo hero, bright green pill buttons, pale lavender surfaces and rounded cards. Add product vision/planned feature previews, a planned three-step workflow, trust principles, account CTA and footer section navigation. Reuse the existing local generated image and plain React/CSS; no additional package, provider or global design-system change. Mark future tools as Planned and sample panels as Illustrative preview. Do not reproduce unsupported privacy promises, agricultural advice, claimed citations or functional farm controls from the reference. Account-page styling, authentication and the agreed stack remain unchanged.

The user's request to create the user-management backend, frontend and related parts authorizes this bounded implementation. The earlier plan is now realized in [USER_MANAGEMENT.md](USER_MANAGEMENT.md), without a separate claim that each numeric default received individual user approval. D19-D23 were selected as documented implementation choices; no farming/AI feature or public deployment was added. D16's warm green direction was expressly selected by the user.

D19 uses [FastAPI's documented pwdlib/PyJWT approach](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/) with Argon2id, explicit HS256 validation and a generated server-only signing key. The existing Python/SQLAlchemy/Psycopg/Alembic stack is retained. Compatible versions are in generated uv.lock; public registration rejects role/status fields. Initially, passwords allowed 15-128 characters without composition requirements; the user-requested revision below supersedes that new-password policy. Spaces/password managers and exact untrimmed password values remain supported. Alternative external providers, legacy password stores and a different session architecture were unnecessary for this local milestone.

D20 retains memory-only access tokens plus rotated HttpOnly refresh cookies, rather than localStorage. Exact issuer/audience/expiry/signature and live account/session state are checked. Refresh races serialize on PostgreSQL user/family locks; reuse revokes the family. Cookies use host-only, auth-path, explicit SameSite=Lax and Secure in production. Exact Origin plus X-WagaMaga-Client protects browser auth POSTs; this follows the principles in [OWASP CSRF guidance](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html). [RFC 9700](https://www.rfc-editor.org/rfc/rfc9700.html#section-4.14) informed rotation/replay handling, without claiming a full OAuth server. A lost refresh response may require login; no automatic rotation retry is attempted. Current-state checks cost a database read but make revocation effective on subsequent requests.

D21 makes role/status, revocation and append-only audit writes atomic and commits before HTTP success. A real deferred PostgreSQL commit-failure test verifies that boundary. Administrator lifecycle changes take a transaction advisory lock, recheck the actor, block self-management and preserve an active administrator. The CLI requires local migration credentials and hidden password entry, and refuses repeated bootstrap once an administrator record exists. No default administrator or public elevation route exists.

D22 follows [React Router declarative routing](https://reactrouter.com/start/declarative/routing) inside Vite and keeps plain CSS, avoiding a new application server or UI/state framework. Shared semantic forms, notices and native dialogs establish the warm green layout. Actual 360px/1280px browser checks cover the connected screens and keyboard focus. Implementation followed the broad build request; a separate user wireframe-approval session is not claimed.

D23 uses shared PostgreSQL counters and expiry cleanup rather than adding Redis. Local Vite shares a proxy IP; the documented API command disables untrusted forwarded-header interpretation. Limits are configurable engineering defaults, not measured attack-resistance guarantees. Email ownership, account recovery, long-term retention, administrator MFA and external hosting remain decisions before real-user access. The original scope had no password/email change, hard deletion, impersonation or email service; password change and scrubbed account removal are added by D24.

Affected guides: USER_MANAGEMENT.md, ROADMAP.md, CODEX_WORKFLOW.md, DEVELOPMENT.md, API.md, DATABASE.md, UI_DESIGN.md, TESTING.md and SECURITY.md. Remote CI for UM1 is configured but not claimed to have run for these local changes.

## Merged homepage design foundations - 17 November 2026

Accepted within the user's request to combine their supplied DESIGN.md with the existing UI guide and use a creamy green background. [UI_DESIGN.md](UI_DESIGN.md) remains the single maintained design guide; merge the supplied editorial typography, forest/sprout accents, rounded shapes and fine borders with existing navigation, accessibility, evidence and farmer-control requirements. Resolve the supplied document's conflicting lavender front matter and warm cream prose in favour of the user's explicit creamy green direction: canvas #f7f8ef, sage sections #edf2e5, warm-white cards #fffef9 and forest #0f2d1f.

Use Plus Jakarta Sans for homepage headings/body, self-hosting the unmodified 27,348-byte Latin variable WOFF2 (weights 400-800) from Google Fonts with its SIL Open Font License and [source/hash record](../frontend/public/fonts/plus-jakarta-sans/README.md). This replaces the homepage system-font/lavender treatment above; account-page typography and colours remain their existing baseline. The alternative of a runtime Google Fonts stylesheet was unnecessary because local delivery avoids a third-party font request. No new npm package or global UI framework is needed. Review glyph coverage before adding languages beyond the current English homepage.

Reference telemetry, predictive diagnostics and gauges remain examples, not implemented or newly authorized features. Retain planned/illustrative labels and the existing generated image. API, authentication, database, worker, deployment and the agreed stack are outside this visual change.

## Shared visual theme expansion - 17 November 2026

Accepted through the user's request to use the same UI design in other parts. Extend the merged editorial/creamy green foundation to login, registration, own account, administrator list/detail, dialogs, shared states and the developer connection screen. This supersedes the earlier homepage-only restriction for visual styling. Register the existing local Jakarta font and palette once in frontend/src/theme.css; homepage/account aliases reference those tokens. Use warm-white cards, soft sage navigation, forest selected links/save/confirmation actions and sprout auth-entry actions. Desktop auth reuses the generated field photo with a dark text overlay; mobile remains form-first. Preserve warning colours and wording for destructive/disabled/error states.

No dependency, application feature, API/schema, authentication policy or deployment is added. Existing server-side permissions and session handling remain authoritative. Update UI_DESIGN.md and USER_MANAGEMENT.md and verify existing account journeys, responsive navigation and native dialog focus. Font binary/license/provenance remain unchanged; only their application scope is extended.

## New-password policy revision - 17 November 2026

Accepted through the user's explicit signup request: reduce the new-password minimum to 8 and require at least one letter, one number and one symbol; retain the 128-character maximum. Interpret letters as Unicode letter categories, numbers as decimal digits and symbols as Unicode punctuation/symbol categories. Whitespace or format/control characters alone do not satisfy the symbol requirement. Do not add an uppercase requirement or trim passwords.

Enforce the same rule in registration's SecretStr validator and the signup UI, including both password length fields and visible guidance. The controlled first-administrator CLI reuses Register, so its prompt follows this policy. Login continues checking existing stored hashes without enforcing the new composition rule; do not invalidate existing passwords or add a reset flow. Update synthetic test passwords and generate compliant browser fixture credentials. Argon2id, session/abuse controls, secret redaction, dependencies and database schema remain unchanged. API.md, SECURITY.md, DEVELOPMENT.md and USER_MANAGEMENT.md document the current contract; TESTING.md records actual verification separately.

## D24: account removal and password changes - 18 November 2026

Status: accepted from the user's explicit request to let administrators remove accounts and let users change their passwords. Scope stays inside UM1 identity; no farm/AI behavior is added.

Administrator removal is permanent from the product UI but uses a privacy-scrubbed tombstone, not a physical SQL row delete. In one transaction, verify administrator/session, reject self-removal and stale version, ensure an active administrator remains, replace email/name/password hash, mark disabled/deleted, revoke all sessions and append an audit event. Keep UUID/FK history intact; hide removed accounts from normal listing and offer an explicit deleted filter showing scrubbed records. The request requires a reason and optimistic version. An append-only audit failure rolls the entire mutation back. Future domain deletion/retention policy remains a separate design and must not cascade away evidence.

Users change their own password only after entering the current password. Reuse the accepted 8-128 letter/number/symbol rule. Rate-limit current-password attempts using the existing shared PostgreSQL limiter. In one transaction, update the Argon2id hash, increment account version, audit the change, revoke every other active session and keep the current session so the user can continue. No administrator password reset or forgotten-password flow is introduced.

Add migration `0003_account_lifecycle` with `users.deleted_at`; no new dependency. Update DEVELOPMENT, API, DATABASE, SECURITY, USER_MANAGEMENT, ROADMAP and TESTING. Verify with actual PostgreSQL/pgvector API tests, frontend tests, six desktop/mobile Playwright journeys, lint/format and build; remote CI remains a separate delivery check.

## D25: audit viewer and in-app notifications - 18 November 2026

Status: authorized by the user's request to implement audit-log viewing and in-app notifications. Keep both within the current account/security scope; no farming workflow or email service is introduced.

Add an administrator-only audit history page and `GET /admin/audit-logs`, with bounded pagination and action/account/date filters. Return action, actor/target UUID and current display name, changed values, reason, request ID and timestamp; never return email, password hashes, tokens or private farm/chat records. Record each audit-feed request in the append-only audit table with a fixed reason that contains no filter or private values. Keep the view distinct from operator/server diagnostics. Audit-log read access already exists for the app role; no new audit mutation privilege is added.

Add a PostgreSQL notifications table and recipient-owned inbox API/page. A user can list all/unread notifications, mark read or unread, and see a shared unread count; all queries and state changes derive recipient identity from the live session, and non-owner ID lookups return 404. Create trusted, fixed-format in-app notifications in the same transaction for active-user role changes, account re-enablement and the user's own password change. Do not create an unread alert for a disabled/removed account it cannot access. No arbitrary user-supplied message, email alert, general system-log screen, or automatic notification from future farm/advisor events is included. Add migration `0004_in_app_notifications` and grant the application role SELECT/INSERT/UPDATE only on the notifications table.

Update API, DATABASE, SECURITY, UI_DESIGN, USER_MANAGEMENT, DEVELOPMENT, ROADMAP and TESTING. Verify real PostgreSQL permission/transaction behavior, frontend tests and desktop/mobile browser flows. Email delivery, notification retention, and farm/advisor event definitions remain future decisions.

## D26: Farm Records planning defaults - 18 November 2026

Status: the initial documentation request produced [FARM_RECORDS.md](FARM_RECORDS.md), followed by explicit requests for FR-B persistence, FR-C owner-only APIs and FR-D connected screens. Defaults were selected within those requests; remote CI remains pending. No new tool/provider/dependency is selected and no separate numeric-default approval or agricultural validation is claimed.

Keep Farm Records within existing roadmap M1, preserving M1-M4 and SRS identifiers. Include manual farms, cultivations, observations, stage confirmation and archive/history; defer tasks, AI, weather, uploads and advisor sharing. Reuse UM1 authentication without bypass actors.

Propose required location label/optional paired coordinates, explicit farm timezone default Asia/Colombo, optional farm area/required cultivation area with ha/acre/m2 units and NUMERIC(18,6) precision. Seed chilli only. Allow future planting as planned, retain unknown soil/stage and expose owner-reported confirmation only. Crop/planting-date changes clear current stage metadata while immutable revisions retain provenance.

Require live active-farmer/session checks and farm ownership through every child/history query. Use 401 invalid session, 403 excluded role before lookup and uniform 404 non-owned/missing object. Collections use page 1-10000 and default 20/max 100 page_size, with ownership before counts. Keep private farm events/revisions separate from the existing account audit table/feed: its target_id references users and its administrator view is not a private farm viewer.

Archive makes descendants effectively read-only without erasing history. Require expected versions, consistent account/parent locks and atomic record/revision/audit writes. No restoration, ownership transfer, hard deletion, automatic POST retry or farm notifications. Retain synthetic local records with restricted FKs/grants; real-user retention/account deletion remains open under D14/DR04. Exact bounds, routes, races and acceptance cases are in FARM_RECORDS.md.

FR-A through FR-D are implemented locally; review/delivery and remote CI remain pending. Migration `0005_farm_records` adds the eight record/history/event tables, stable chilli seed, restricted grants, immutable owner/parent/author identity triggers and composite audit-parent FKs. Per-entity immutable snapshots permit later exact-context bindings. Refine the proposed NUMERIC(18,6) storage to unconstrained NUMERIC plus range/truncation CHECKs: PostgreSQL would otherwise round excess decimal places before a CHECK could reject them. The range and six-decimal domain are preserved, without silent rounding. No estimator is implemented and its nullable stage field is constrained to null until a future migration adds provenance support.

TESTING.md records actual PostgreSQL migration, grant, duplicate-insert, historical-account-reference and rollback evidence. Persistence alone cannot provide actor authorization, archive/version transitions or automatic revision/audit creation; FR-C now supplies those service rules as described below. Browser/remote CI evidence and full AT01/AT02 remain pending.

FR-C follow-up: the user explicitly authorized backend services/APIs with screens and remote CI pending. The implemented services now provide the actor/owner, archive/version and atomic revision/audit behaviour above. Typed DTOs reject ownership/provenance mass assignment and validate merged PATCH state; confirmations are explicit versioned events even when their label/clock repeats. Known crop reassignment and planting-date edits invalidate current stage metadata without erasing its revisions. Current-version archive repeats and active no-op edits add no effect. No new migration, package, provider or task execution was needed.

Use PostgreSQL's installed timezone catalogue for IANA identifier validation and local-date conversion, avoiding a new Windows timezone-data dependency. Preserve SELECT-only application access to crop_types; support is checked on assignment, and only controlled migrations/operators may change the catalogue with writers paused (OPERATIONS.md). FR-C's API tests verify cross-owner/mixed-parent denial, live role/session checks, duplicate/stale/archived writes, real lock serialization and immediate/deferred rollback. TESTING.md separates these local API results from FR-D browser evidence and future sharing/AI/remote CI gates.

FR-D follow-up: the user authorized the connected screens. Reuse React Router, plain CSS/shared theme, existing session memory and shared field/notice/native dialog components. My Farms and record forms/history now connect to the APIs; no package, migration, seed, provider or state manager is added. Native archive dialog labels are configurable while preserving existing account wording. Homepage farmer navigation links to records and its Farm Records card is Available; guidance/planning remain Planned and sample previews remain Illustrative.

Farm POST/PATCH calls opt out of automatic unauthorized-request replay; 401 clears the token/private views and returns to login. Read refresh behaviour is unchanged. Key the workspace outlet by user/role and ignore stale resource responses to avoid leaking previous account/URL data. Preserve decimal strings and full observation instants when only notes change. Device-local observation entry is explicit, with UTC transport and farm-timezone display. Stale drafts remain visible until explicit reload discards them; uncertain creation directs the user to review saved records. Coordinate draft/in-flight controls across parent edits, stage and observations. Browser/component evidence is local and synthetic; no claim of farmer usability research, agronomic validation or remote CI is made.

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

## Planner emphasis and deferred UI follow-ups - 18 November 2026

Status: accepted through the user's instruction to clarify the plan now and record extra features as later roadmap work. This is a product/UI sequencing decision, not a supporting-tool selection or authorization to implement farming/AI features now.

Use the planner as the main future farmer workspace, with chat supporting clarification, sourced explanations and proposals. Existing SRS farm records, seven-day proposals, evidence, required review, exact-version acceptance and safe execution remain unchanged. Add a combined cultivation diary after records/tasks and the first proposal journey work; add a missed-task revision entry point after safe proposal revision works. Keep these as bounded follow-ups, not new major releases or additional gates on the current Farm Records task.

Alternatives considered: expanding the current records slice to include all ideas would mix dependent work and delay verification; treating the application primarily as chat would obscure manual record/task management. The selected direction retains both chat and direct controls without changing the React/FastAPI/PostgreSQL/pgvector/private-storage/separate-worker architecture. It does not establish competitor uniqueness, farmer usability or agricultural validity.

Consequences and affected guides: [UI_DESIGN.md](UI_DESIGN.md#planned-farmer-experience-planner-supported-by-chat) explains the intended experience; [ROADMAP.md](ROADMAP.md#planned-planner-follow-ups) records dependencies and completion conditions. Preserve SRS IDs, current implementation evidence and release gates. No API, schema, code, provider or deployment change is made by this documentation decision.

## D27: farmer onboarding and location assistance - 19 November 2026

The user requested easier farm entry and location input, then explicitly corrected the initial separate-dashboard implementation: farm actions belong in the website landing-page header and hero, using a prominent action bar. Farmer login now returns home (`/`); other roles open My Account. The header exposes My Farms and Add Farm; a new farmer gets Add my farm in the hero, while a returning farmer can select an owned active farm and continue to its next crop/observation action. The separate dashboard checklist and fixed mobile bottom bar are removed. The old farmer `/dashboard` URL redirects home. Use the existing React Router, shared theme and owner-scoped APIs, preserving the accepted future planner direction without adding nonfunctional AI/task controls.

Bundle the 25 Sri Lankan administrative district names as a local display reference. Cross-checked on 19 November 2026 against the [Election Commission list](https://elections.gov.lk/en/download/download_LocalAuthoritiesDetals_E%20-%20Copy.html); English display aliases Kandy/Mahanuwara and Monaragala/Moneragala were compared with [DCS district atlases](https://www.statistics.gov.lk/Population/StaticalInformation/DistrictAtlases). No boundary geometries or private farm directory are included. A user-selected district plus village becomes the existing location label; a free-text alternative preserves old labels and other locations. This is a usability aid, not regional verification or an extension of agricultural support. Chilli/Anuradhapura guidance remains planned and subject to source/advisor validation under D07.

Use the browser's standard [Geolocation API](https://www.w3.org/TR/geolocation/) for an explicit one-time request. It needs a secure context and user permission, identifies the device rather than a verified farm, and may rely on browser/OS location services. Show accuracy and a farm-location check; keep the result in memory until normal save. Preserve existing coordinates on failure and invalidate late callbacks after cancellation/manual input/unmount. Manual input and omission remain available. No application map/geocoding provider, SDK, API key, dependency or new server endpoint is selected. Maps/search and reverse geocoding can be evaluated separately if needed.

Supporting verification: optional validated `E2E_API_PORT`/`E2E_WEB_PORT` select loopback ports for the existing Vite/Playwright and dedicated `_test` API harness. Defaults remain 8000/5173; the test server allows only its selected web origin. This lets checks coexist with the user's running development services without stopping them. It adds no deployed service or production setting. See [UI_DESIGN.md](UI_DESIGN.md), [DEVELOPMENT.md](DEVELOPMENT.md) and [TESTING.md](TESTING.md).

## D28: farm restore and workspace deletion - 19 November 2026

The user requested restore and delete after discussing archive behaviour. Restore clears only the farm's archive timestamp; inherited child archives become active again, while independently archived cultivations stay archived. An already active farm with the current version is a no-op; stale versions conflict. No cultivation restore or deletion action is added.

Delete is deliberately a workspace-removal command, not permanent data erasure: the app preserves immutable private revisions/audit and may later reference them in proposals. The UI explains retained storage and requires the current farm name. Only the owner of an archived farm can delete it. A new `farm_deletions` append-only marker hides that farm from every list/count/filter and makes all farm/child/history reads and writes return generic 404, including restore. There is no deleted-items browser or undo. Administrator/advisor status gives no access. The marker, version increment, final revision and `farm_deleted` event commit atomically under the same actor/session/farm locks as other writes. A repeated deleted request returns 404 without another effect; versioned restore/delete races serialize.

Migration `0006_farm_lifecycle` adds the marker and permits `farm_restored`/`farm_deleted` audit operations. Existing records and snapshot shapes are preserved. App grants on the marker are SELECT/INSERT only; physical DELETE/TRUNCATE, marker rewrites and history/audit rewrites remain unavailable. Downgrade refuses while lifecycle evidence exists, preventing schema rollback from silently re-exposing deleted records. Real erasure/retention periods remain a separate DR04 decision before real-user collection; this feature does not satisfy an erasure request. No new dependency/provider/worker is selected. See [FARM_RECORDS.md](FARM_RECORDS.md), [API.md](API.md), [DATABASE.md](DATABASE.md) and [TESTING.md](TESTING.md).

## D29: public Help and submitted support conversations - 19 November 2026

The user authorized Help + simple support requests + the admin inbox as the next build; Admin Overview follows separately. Reuse the modular monolith, PostgreSQL transactions/limits, current sessions, React Router, shared theme and native controls. Add `0007_support` for tickets and append-only messages/events, with strict owner/admin access and atomic generic notifications. No new provider, package, email transport, worker or real-time channel is selected. The [support specification](SUPPORT.md) defines requirements, contracts, locking, privacy and operational limits.

Support is explicit sharing of submitted text with administrators, separate from private farm records/AI chats and future assigned agricultural cases. Do not attach farm context, bypass recovery or execute farmer actions. Freeze ticket identity/category/subject and messages; version replies/status and record minimal events. Preserve generic account notifications without support subject/body; link to the owner's support list. Use per-actor creation/reply/status limits and disable automatic mutation replay. The existing record hooks now accept an explicit reader/error formatter so support reuses stale-response/draft protections with its own wording.

A public operator email is optional `SUPPORT_CONTACT_EMAIL`, validated by the already installed email-validator dependency and exposed by a no-database public contact endpoint. Display an honest unavailable state when unset; no placeholder, monitored staffing, email delivery or identity verification is implied. The contact address was requested from the user; no real address is invented. Retention/contact/recovery policies remain pre-pilot decisions, and support evidence blocks automatic schema downgrade. Other admin analytics and real-user operating gates remain separate.

## D30: count-only administrator reporting - 19 November 2026

The user explicitly approved Admin Overview after Help/support, following discussion of farmer/account totals and limited farmer farm/cultivation counts. Add a separate reporting service and count DTOs, using the existing PostgreSQL tables and audit mechanism. This is an explicit metadata permission; it does not make private farms/chats generally readable by administrators. [ADMIN_REPORTING.md](ADMIN_REPORTING.md) defines exact population, archive/delete, role/state and time-window semantics.

Use a single PostgreSQL count statement per response for internally consistent groups and a statement timestamp. Exclude workspace-deleted farms and removed/former-farmer owners; include disabled current farmers' retained records and count inherited crop archives. Account enabled state is not activity measurement. Support totals include retained submitted requests. No raw farm fields, private message content, charts, location grouping or exports are added. Audited views use a fixed reason and report kind, with no counts/private record IDs in audit; audit failure prevents a successful response.

Reuse current admin/session checks under locks, shared typed HTTP resources, React Router and theme. Admin login now opens Overview, farmer login stays on the landing page and advisor login stays on My Account. New account-page metadata requests are separate from the owner-only farm endpoints. No database migration, new privilege, dependency, provider or worker job is selected. Remote CI and real-user reporting/retention policies remain separate gates.

## D31: synthetic PDF extraction

Use [pypdf](https://pypi.org/project/pypdf/) in a bounded subprocess to extract selectable text locally without a provider. Keep the input file and durable queue state in one private PostgreSQL relation for this tightly capped demo. This makes upload acceptance atomic and avoids split database/file writes. The shared application role can read originals for processing. The HTTP interface returns plain text pages to active admins and exposes no raw PDF download.

Use one locked row per job. A complete processing result commits once, and interrupted transactions leave work queued. Review and publication apply to the original checksum and immutable extraction. Consider dedicated private file storage, screening, OCR and stronger cross-platform isolation separately before opening real-source ingestion.

## D32: Gemini for the local fictional answer preview

Use the [Gemini generateContent API](https://ai.google.dev/gemini-api/docs/generate-content/text-generation) with structured quotations, a server-only key and a configurable model. Keep provider traffic to the built-in fictional PDF and fixed questions while evaluating the unpaid service. The server checks the exact quotation, citation and current publication state before it returns an answer. Developer and CI tests use deterministic doubles and do not measure model quality. Real-source evaluation requires completed evidence review and a decision on external processing under the [Gemini terms](https://ai.google.dev/gemini-api/terms).

## D33: Sinhala legacy-font extraction

The DOA 2023 Sinhala guide renders correctly but its embedded FM-Abhaya text layer extracts as legacy Latin glyph codes. Use the pinned, pure-Python `sinhalanorm` converter only when PDF font metadata identifies FM-Abhaya, FM-Ababld, FM-Emanee or FM-Samantha, then index normalized Unicode. Preserve English and other unknown font runs unchanged. This does not claim support for sandaru-n, DL or other legacy fonts, image-only pages, or general Sinhala OCR; those require separate validation. The guide remains draft until its extracted passages are reviewed.

## D34: delete withdrawn knowledge PDFs

An administrator can delete a withdrawn PDF. In one transaction, change the source lifecycle to deleted, clear the stored original and full extracted page text, and append a lifecycle decision. Hide deleted versions from source lists and deny their page routes. Keep the source title/checksum and existing evaluation decisions, approved excerpts and audit history so prior review evidence remains traceable. This is removal of the uploaded file and full extracted pages, not complete erasure of every retained excerpt. Only ready/failed withdrawn PDF versions can be deleted; published sources must first be withdrawn. Database constraints and a trigger restrict the application role to the worker's single queued completion and this deletion transition. See [API.md](API.md) and [DATABASE.md](DATABASE.md).

## D35: published chilli research answers

Start the farmer research view with versioned summaries from the two CC BY 4.0 studies in [KNOWLEDGE_SOURCE_INVENTORY.md](KNOWLEDGE_SOURCE_INVENTORY.md). Use study-specific facts with page citations. Reuse the server-side Gemini adapter only for optional selection from the fixed summaries. Keep typed questions, farm details and uploaded documents outside these requests and verify the exact returned selection before displaying its Gemini label. A deterministic reference answer provides the same source when the provider fails. Farm-specific guidance remains subject to its existing separate release conditions.

The second reference set adds short English summaries of three sections of the Department of Agriculture's public chilli crop page. The answers cite the Sinhala section and stay inside the API. The source supports general checks for nursery siting, irrigation and soil testing. [Field crops – Chilli](https://doa.gov.lk/field-crops-chilli-si/)

## D36: manual Open-Meteo farm forecast

Use the [Open-Meteo daily forecast API](https://open-meteo.com/en/docs) for calendar dates, temperatures and precipitation. The API request starts with an owner action and shares two-decimal coordinates and the farm timezone. The [non-commercial service](https://open-meteo.com/en/terms) serves keyless local use. The customer endpoint uses the optional server key. Display provider credit and license beside the forecast.

Store one current snapshot per farm. Reuse a snapshot for 30 minutes and show it as stale after two hours or a change of local day. Keep stale data out of task rows. The owner can compare dates and use manual task editing. Agronomic thresholds and automated weather reviews remain part of D13's later work.

## D37: weather alerts and owner-reviewed date changes

Let the owner choose a precipitation threshold for each cultivation. Recheck pending tasks against current forecast dates, keeping one alert per task and due date. The threshold is a review preference. The owner selects the proposed date and approves the exact action. Bind that action to the task version, current forecast and rule version. Store the evidence with the plan and reference its resulting task event from the acceptance record.

## D38: synthetic PostgreSQL restore verification

Use `pg_dump` and `pg_restore` from the existing PostgreSQL/pgvector container so the tools match the database version. Seed the dedicated test database through the application integration test, restore to a temporary database and check restored data and grants before cleanup. Run the same drill in the backend workflow. [Testing guide](TESTING.md#chilli-questions-and-reliability)

## D39: farm weather opt-in and cultivation guidance

Use the existing worker and database for leased forecast checks. Owners opt in per farm and write rainfall thresholds per cultivation. A unique cultivation/date claim and the inbox entry commit with the forecast evidence. The owner continues to confirm individual date changes through the review flow.

Use structured farmer-reported soil moisture and confirmed stage for the three contextual chilli questions. Source facts come from the existing attributed public reference set. Use only an explicit Anuradhapura location label and observations from the last 24 hours for irrigation context. Questions use local rules and ask for missing field evidence where a source cannot justify plot-specific advice.

## D40: weekly planning and assigned advisor review

Show overdue pending tasks and the next seven farm-local days in the cultivation. Use the owner's rainfall setting to compare one pending task with the earliest later forecast day below that threshold in the same week. Retain the confirmed stage in the review evidence and require advisor clearance when the stage is missing or the task revision has been referred. Reuse the immutable task-plan action and execution receipt. Sharing is explicit and revocable, with an exact advisor account and a minimal case snapshot. Advisor clearance and farmer acceptance have independent, bound records.

## Recording an outcome

For each resolved decision, record ID, date, status, context, chosen option, alternatives, consequences and affected documents. Keep superseded outcomes with their replacement link. Never mark a decision resolved just because Codex generated a suggestion.

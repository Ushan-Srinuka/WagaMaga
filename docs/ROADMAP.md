# Build roadmap

Status: M0 complete, 16 November 2026. Remote foundation CI passed for published commit 62c6c62. A fresh Windows clone installed the locked dependencies and passed foundation checks and actual startup after correcting the Git line-ending policy. TESTING.md records the evidence and limits. V0 and later releases remain pending.

The original M0 checkpoint passed its clean-checkout and CI gates. The subsequent UM1 checkpoint now adds implemented identity/account behaviour, 38 passing backend tests, 11 frontend tests and 6 real-browser desktop/mobile journeys. Lint/format/build checks and local PostgreSQL/migration checks pass. Expanded UM1 CI is configured but not remotely executed for these local changes. Neither checkpoint establishes production readiness or a supported Windows servicing state.

UM1 user management was explicitly requested and is implemented locally, brought forward from M2. Its [milestone guide](USER_MANAGEMENT.md) defines the account scope, selected policies, structure and connected warm green screens. Complete review/publication and the expanded remote CI run before claiming all delivery gates; do not mark M2 complete. The V0/V1 sections below remain the subsequent product roadmap, not newly authorized work.

Authorized UI follow-up: a public homepage now opens at `/` with account entry links and clearly labelled roadmap content. It works without an API/session dependency. The frontend suite now has 12 passing tests and local desktop/mobile homepage smoke checks passed; TESTING.md separates these from the earlier UM1 evidence. No farming/AI capability was added with this page.

Homepage style revision: after the initial bold/premium version, the user approved a supplied reference on 17 November 2026. The page now pairs the existing generated photographic hero with a light header, softer backgrounds, rounded planned-feature cards, a three-step planned workflow and trust principles. Feature previews are explicitly illustrative. Asset provenance is retained locally. Account pages and the milestone sequence are outside this visual revision.

Further homepage refinement, 17 November 2026: the supplied DESIGN.md is merged into UI_DESIGN.md. The current homepage uses locally hosted Plus Jakarta Sans, creamy green/sage surfaces, forest/sprout actions, fine borders and larger card corners. This supersedes its previous lavender/system-font treatment without adding farming features or redesigning account pages. Font provenance/license are bundled; TESTING.md records checks separately.

Shared design follow-up, 17 November 2026: the user extended the same UI style to all existing parts. Login/registration, own account, administrator list/detail, dialogs, shared states and /connection now use one local font/palette in frontend/src/theme.css, with creamy green/sage surfaces and rounded controls/cards. Desktop auth reuses the generated field photo; mobile remains form-first. The previous homepage-only scope above is historical. No new domain feature or API/database change is introduced; TESTING.md records the current frontend and real account browser checks separately from visual doubles.

Password-policy follow-up, 17 November 2026: at the user's request, new passwords now use 8-128 characters with a letter, number and symbol. Signup UI/API and controlled admin bootstrap align; existing-password login remains compatible. Current local verification passed 54 backend, 25 frontend and 6 real desktop/mobile account browser tests. No new milestone, schema migration, dependency or reset/recovery flow was added. TESTING.md records the new cases and limitations.

Account-access follow-up, 18 November 2026: added current-password-confirmed self-service password change and confirmed administrator account removal. Removal scrubs email/name/password hash, revokes sessions and retains an auditable tombstone; list filtering, migration `0003_account_lifecycle`, API/UI guides and failure-path tests were added. Password changes retain the current session and revoke other sessions. Local PostgreSQL verification passed 60 tests, frontend tests passed 27, and all 6 real desktop/mobile account browser journeys passed; Ruff, ESLint, schema-drift check and production build passed. Remote CI remains pending, and this does not resolve real-user recovery or future farm/chat retention policy. See TESTING.md.

Audit and notification follow-up, 18 November 2026: added a filtered, paginated administrator audit-history screen/API that records each feed view, plus recipient-owned in-app notifications with unread count/read state and account-security event templates. Migration `0004_in_app_notifications` stores notices and restricts app-role grants; no email delivery or general system diagnostics view is included. PostgreSQL tests passed 62, frontend tests 29, all 6 desktop/mobile journeys reported passed, and lint/format/build/migration drift checks passed. Notification and audit retention/event policies remain unresolved; expanded remote CI has not run. See TESTING.md and D25.

Homepage account-status follow-up, 18 November 2026: the opening page now restores the live session and shows signed-in/signed-out state, account links and a recipient unread-notification badge. If the API cannot confirm session status, the page says so and offers retry. The main call to action and footer links follow the current account state. Frontend tests now cover both signed-out and signed-in homepage navigation; latest check passed 30 frontend tests, lint, formatting and production build. No backend/API behavior changed.

Login destination follow-up, 18 November 2026: successful sign-in and visits to the login page with an already active session now return to `/` instead of opening the account page. The landing page confirms the session and links to My account and Notifications. Auth component coverage, all 30 frontend tests, lint, formatting and production build passed. Browser rerun was blocked by an already occupied local port 8000; the previous browser result does not verify this redirect.

Farmer UX follow-up, 19 November 2026: at the user's request, sign-in returns to the website landing page, whose header and hero provide farm entry, owned-farm selection and crop/observation continuation. This supersedes the initial separate dashboard and mobile bottom bar after explicit user correction. District/village entry and optional explicit browser geolocation remain. The initial chilli/Anuradhapura guidance scope remains provisional; manual labels elsewhere do not expand agronomic support. Existing owner-only APIs/schema are reused, with no task/AI/planner/weather implementation. See D27, UI_DESIGN.md and TESTING.md. FR-E publication/remote CI and full M1 evidence gates remain pending.

Farm lifecycle follow-up, 19 November 2026 (D28): the user requested restore/delete for archived farms. Versioned owner-only farm restore and confirmed workspace deletion are implemented on `0006_farm_lifecycle`; protected historical data is retained and deleted links are inaccessible. Cultivation restore/deletion and permanent erasure remain excluded. This is bounded manual-record work; remote CI, full M1/V0 and real-user retention gates remain pending. See FARM_RECORDS.md and TESTING.md.

Help/support follow-up, 19 November 2026 (D29): the user authorized a public Help page, farmer requests and an admin support inbox. Submitted conversations, status/replies and generic notifications are implemented locally on `0007_support`; this grants no private farm access. The subsequent D30 implements separate count reporting. Password recovery, attachments, live chat, advisor cases, real-user policies and remote CI remain pending. [SUPPORT.md](SUPPORT.md) defines scope and TESTING.md records evidence.

Administrator reporting follow-up, 19 November 2026 (D30): Admin Overview and per-farmer record counts are implemented locally. Active administrators receive audited aggregate metadata without private farm details; existing farm APIs remain owner-only. Administrator login opens `/admin/overview`; farmer login still opens `/`. Schema remains `0007_support`. Local verification passed 266 backend tests, 77 frontend tests and 24 desktop/mobile browser journeys. [ADMIN_REPORTING.md](ADMIN_REPORTING.md) defines count populations and permissions. Next is final review/publication and remote CI, then the separately scoped M1 curated-source preparation. This does not complete M1/V0 or authorize AI/task implementation.

## M0: reproducible foundation - first build milestone

Scope: Git and ignore rules; selected supporting tools; manifests and locks; React/FastAPI entry points; separate worker entry point; PostgreSQL/pgvector setup; migration runner; safe configuration examples; foundation checks and CI.

Exit criteria:

- A clean checkout can follow DEVELOPMENT.md to start all local components.
- PostgreSQL/pgvector availability and the migration runner are verified.
- API liveness/readiness and frontend connectivity can be checked without model/weather keys.
- Worker starts independently; no fake claim of a durable business job implementation.
- Applicable backend checks, frontend checks/build and foundation verification pass in CI.
- Exact commands and required versions are documented; no secrets are committed.
- No farm, auth, chat, proposal or weather business features have been implemented in this milestone.

## UM1: early user management - implemented locally

Purpose: understand and exercise the application structure and refine a reusable UI before farming/AI features. Preserve M1-M4 identifiers and the SRS requirement IDs.

Implemented scope: farmer registration, login/logout, revocable sessions, own display-name editing, administrator list/detail and audited role/status actions. Current use is local/synthetic. Farmers/advisors do not gain administrator permissions; account administration adds no private farm/chat access. See [USER_MANAGEMENT.md](USER_MANAGEMENT.md) for current contracts and [DECISIONS.md](DECISIONS.md), D18-D23, for selected implementation choices.

Order: UM1-A decisions and visual review; UM1-B persistence/controlled initial administrator; UM1-C backend authentication/permissions; UM1-D connected React screens; UM1-E browser/CI verification and guides. Every implementation slice includes relevant tests.

Implementation checkpoint: UM1-B/C/D and local UM1-E checks are complete. Choices/styles are recorded for UM1-A; local screenshots were inspected, without claiming a separate user wireframe approval or farmer usability study. Expanded remote CI remains pending until these changes are committed/pushed. No default development administrator was created; use the restricted interactive setup documented in DEVELOPMENT.md.

Exit criteria: included account journeys work; server-side rules, token/session invalidation, last-administrator protection and atomic audit/revocation writes are verified; real PostgreSQL tests and mobile/desktop browser journeys pass; setup/contracts are documented and CI remains green. AT02's farm ownership and advisor case portions remain deferred.

Farms, cultivation, knowledge, AI, proposals, weather and case sharing stay outside UM1. Recovery/email verification, retention and real-user deployment requirements must be resolved before inviting real users; a synthetic local user-management demo does not complete those gates.

## M1: V0 evidence proof

Farm Records checkpoint, 18 November 2026: [FARM_RECORDS.md](FARM_RECORDS.md) defines FR-A requirements. FR-B provides schema `0005_farm_records`; FR-C provides owner-only APIs and atomic private history/audit. The authorized FR-D now connects My Farms, farm/cultivation details, observations, stage confirmation, archives and history to those APIs using the existing theme/session. Local component and real backend desktop/mobile journeys pass, including stale writes, foreign-record denial and revoked sessions. No migration/dependency, task, AI or weather flow was added. Next is FR-E review/publication and remote CI under the requested Git workflow; remote CI remains pending. This brings bounded manual records forward from M2 without completing M1/V0, M2 or full AT01/AT02. Preserve the identifiers and evidence-proof gates below; TESTING.md records actual results.

Suggested slices, each independently reviewed and tested:

1. Prepare synthetic farm/cultivation context, fixture metadata and a small source inventory. Confirm source reuse/applicability before indexing it as eligible evidence.
2. Establish the necessary local identity/context boundary and minimal record persistence. Reuse UM1 identity if completed; do not create a bypass authentication path. Use explicitly labelled synthetic actors; a local proof is not permission for public personal data.
3. Process curated document versions with provenance and review eligibility. Durable processing is needed when work must survive restart; do not represent in-process tasks as durable jobs.
4. Deliver a cited answer and source viewer; test missing evidence, unsupported claims and source-instruction injection.
5. Persist one bounded proposal, show current/proposed differences and bind acceptance to its exact version/hash.
6. If acceptance changes tasks, include atomic execution, precondition checks, evidence/decisions/audit persistence and duplicate prevention in this slice.
7. Demonstrate labelled weather fixtures and run the V0 evaluation and user journey.

Exit criteria: local synthetic records; curated documents; cited answers; at least 10 questions mapped to evidence including a missing-evidence case; one manual proposal and acceptance flow; labelled weather fixtures; evidence of applicable safety/failure checks. No public personal data. Record whether acceptance actually executes tasks.

## M2: V1 portfolio MVP

Complete all FR01-FR36 and DR requirements, with NFR baseline verification. Suggested order:

1. Reuse and verify completed UM1 registration/session/role handling; add ownership checks with each domain and implement case sharing. UM1 alone does not satisfy all FR02/FR04 or AT02 cases.
2. Complete farms, cultivations, observations, manual tasks and archive/history behaviour.
3. Knowledge administration and hybrid retrieval with measured lexical/vector/hybrid comparisons.
4. Advisor review, full proposal lifecycle, transactional execution and concurrency coverage.
5. Durable jobs/outbox, retries, leases, notifications and restart recovery.
6. Basic live weather adapter with visible data age and reviewed rules.
7. Complete responsive screens, deployed demo, evaluation and operating checks.

Some safety and persistence capabilities begin in V0 and expand here. Stable jobs, basic retries and duplicate-safe effects cannot all be deferred to V2. Automated weather polling is a V2 expansion; V1 can use manual live review.

Exit criteria: AT01-AT12 evidence; at least 30 labelled evaluation questions; Recall@5 >= 0.80 on answerable cases; target >= 90% supported material claims; no unsupported actionable treatment recommendation. Verify latency, timeout, security, usability and recovery requirements in a declared environment. Simulated advisor accounts are labelled.

## Planned planner follow-ups

Accepted for future planning on 18 November 2026, not implemented or authorized as the current coding task. The [UI direction](UI_DESIGN.md#planned-farmer-experience-planner-supported-by-chat) makes the planner the farmer's main workspace and chat its explanation/proposal assistant. Existing seven-day bounds, evidence requirements, advisor review, farmer acceptance and execution safeguards remain in scope under FR21-FR30; they are not new features to defer.

Continue the current Farm Records screens and verification first. Then build manual task management, cited answers and one complete proposal/review/acceptance journey. If that journey changes tasks, atomic execution, persisted evidence/decisions, precondition checks and duplicate prevention must work in that same slice. Bring forward supporting infrastructure when needed; these follow-ups do not reorder or replace the existing M1/M2 release gates.

### Combined cultivation diary

Status: planned UI follow-up after cultivation records, observations, manual task history and the first proposal journey work. Present the existing records together rather than introducing an independent source of farm facts. It is not an extra M0/UM1/Farm Records acceptance gate or a new major release.

Completion conditions for the later slice:

- An owner can view dated observations, task completion/cancellation and executed proposal changes for one cultivation in a combined history, with links to permitted details.
- Pending proposals remain visibly distinct from executed activities; farmer reports and estimates retain their provenance, and historical revisions remain intact.
- Another owner's history is denied. Administrator status alone grants no private diary access; any later advisor view requires submitted, assigned case scope.
- Verify record consistency, empty/error states and mobile/keyboard use with synthetic data. Define bounded history loading and reuse existing records before agreeing any API/schema additions.

### Missed-task proposal revision

Status: planned planner follow-up after manual task states and safe, versioned proposal revision/execution work. "I missed this task" starts a review request; it is not automatic rescheduling, a new task status or evidence that an activity was completed.

Completion conditions for the later slice:

- The owner can identify a pending task and optionally explain the delay. Load current authorized context and ask for missing information instead of assuming a later date is suitable.
- When supported, show a revised proposal with current/proposed differences, reasons, evidence and the existing maximum seven-day planning horizon. Missing evidence produces clarification or referral, not invented guidance.
- Leave tasks unchanged until required advisor clearance, fresh farmer acceptance bound to the revised version/hash and backend execution checks succeed. Completed/cancelled tasks and history cannot be silently overwritten.
- Verify ownership, stale task/proposal conflicts, fresh decision bindings, duplicate/concurrent requests and rollback. Define any new request contract in a separately scoped implementation task; reuse the existing revision lifecycle.

Schedule these as bounded follow-ups after dependency verification, without assigning them to a new major release or claiming completion of V0/V1. Specific controls, APIs and any data changes need design review with their future slice. They do not add sensors, image diagnosis, a marketplace or automatic agronomic decisions.

## M3: V2 reliability

Automated weather polling, broader evidence, expanded recovery tests and monitoring. Introduce Redis/Celery or more advanced vector indexing only when measurements justify a recorded architecture change.

## M4: V3 expansion

Additional crops, regions and evaluated languages. Image, voice and sensor features require separate requirements and validation.

## Completion evidence

For every milestone, record the commit/version, date, environment, dataset/model/prompt versions where relevant, commands run, outcomes, limitations and unresolved decisions. Use TESTING.md for requirement mapping and OPERATIONS.md for recovery evidence. A demo video or successful Swagger request alone does not satisfy a release gate.

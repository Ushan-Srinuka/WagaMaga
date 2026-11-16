# Build roadmap

Status: M0 complete, 16 November 2026. Remote foundation CI passed for published commit 62c6c62. A fresh Windows clone installed the locked dependencies and passed foundation checks and actual startup after correcting the Git line-ending policy. TESTING.md records the evidence and limits. V0 and later releases remain pending.

Local checkpoint: 12 backend tests and 2 frontend tests pass in the fresh clone; lint/format/build checks, actual PostgreSQL/pgvector readiness, migration/application-role checks, separate worker startup and responsive browser smoke checks pass. No business feature has been added. M0 completion does not establish production readiness or a supported Windows servicing state.

Next requested scope: user management only, brought forward from M2. Plan its authentication/session and account-management decisions and acceptance checks before implementation. Farms, cultivation, knowledge, AI, proposals and weather are outside that next task; advisor case sharing remains with the later case workflow. Completing identity early will not complete M2. The V0/V1 sections below remain the subsequent product roadmap.

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

## M1: V0 evidence proof

Suggested slices, each independently reviewed and tested:

1. Prepare synthetic farm/cultivation context, fixture metadata and a small source inventory. Confirm source reuse/applicability before indexing it as eligible evidence.
2. Establish the necessary local identity/context boundary and minimal record persistence. This may use explicitly labelled synthetic actors; it is not a public-auth implementation.
3. Process curated document versions with provenance and review eligibility. Durable processing is needed when work must survive restart; do not represent in-process tasks as durable jobs.
4. Deliver a cited answer and source viewer; test missing evidence, unsupported claims and source-instruction injection.
5. Persist one bounded proposal, show current/proposed differences and bind acceptance to its exact version/hash.
6. If acceptance changes tasks, include atomic execution, precondition checks, evidence/decisions/audit persistence and duplicate prevention in this slice.
7. Demonstrate labelled weather fixtures and run the V0 evaluation and user journey.

Exit criteria: local synthetic records; curated documents; cited answers; at least 10 questions mapped to evidence including a missing-evidence case; one manual proposal and acceptance flow; labelled weather fixtures; evidence of applicable safety/failure checks. No public personal data. Record whether acceptance actually executes tasks.

## M2: V1 portfolio MVP

Complete all FR01-FR36 and DR requirements, with NFR baseline verification. Suggested order:

1. Full registration/session handling, roles, object authorization and case sharing.
2. Complete farms, cultivations, observations, manual tasks and archive/history behaviour.
3. Knowledge administration and hybrid retrieval with measured lexical/vector/hybrid comparisons.
4. Advisor review, full proposal lifecycle, transactional execution and concurrency coverage.
5. Durable jobs/outbox, retries, leases, notifications and restart recovery.
6. Basic live weather adapter with visible data age and reviewed rules.
7. Complete responsive screens, deployed demo, evaluation and operating checks.

Some safety and persistence capabilities begin in V0 and expand here. Stable jobs, basic retries and duplicate-safe effects cannot all be deferred to V2. Automated weather polling is a V2 expansion; V1 can use manual live review.

Exit criteria: AT01-AT12 evidence; at least 30 labelled evaluation questions; Recall@5 >= 0.80 on answerable cases; target >= 90% supported material claims; no unsupported actionable treatment recommendation. Verify latency, timeout, security, usability and recovery requirements in a declared environment. Simulated advisor accounts are labelled.

## M3: V2 reliability

Automated weather polling, broader evidence, expanded recovery tests and monitoring. Introduce Redis/Celery or more advanced vector indexing only when measurements justify a recorded architecture change.

## M4: V3 expansion

Additional crops, regions and evaluated languages. Image, voice and sensor features require separate requirements and validation.

## Completion evidence

For every milestone, record the commit/version, date, environment, dataset/model/prompt versions where relevant, commands run, outcomes, limitations and unresolved decisions. Use TESTING.md for requirement mapping and OPERATIONS.md for recovery evidence. A demo video or successful Swagger request alone does not satisfy a release gate.

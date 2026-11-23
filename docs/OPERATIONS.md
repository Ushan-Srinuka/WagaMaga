# Deployment and operations

Status: M0 local infrastructure and UM1 account/session controls exist; no public host, deployed release, backup job or incident process has been configured. DEVELOPMENT.md owns startup/interactive administrator setup and TESTING.md owns actual checks. This guide retains future deployment/recovery requirements. Browser fixture servers refuse non-test databases and generate ephemeral synthetic credentials; do not use them as an application startup or account-recovery path.

Owner-only Farm Records APIs/screens now include farm restore/workspace deletion with website support on schema `0007_support`. Run the normal Alembic upgrade before API/worker startup; existing records/history are preserved. External release and remote CI remain pending. Keep synthetic local data until retention/account deletion and real-user operating gates are resolved.

Use `/farms` after farmer sign-in with the existing frontend/API startup commands. No demo records are seeded in development. Farm saves are single attempts; after an uncertain result inspect the list/history before creating again. A 401 clears private views and returns to login; a 409 retains the unsaved draft until explicit reload/review. Desktop/mobile browser checks launch their own test API/Vite processes and refuse development databases. On this Windows host the sandboxed runner could not terminate its child servers; rerunning with permission for its own process cleanup completed successfully. Never terminate unrelated user servers or reuse their ports for the test suite.

## Farm Records operations boundary

Manual tasks require schema `0016_manual_farm_tasks`. Include the task and task event tables in database backups and verify both current state and event history after a restore. Applying the migration preserves existing records. A downgrade with task history stops before removing either table.

The suggested plan demo requires `0017_suggested_task_plans`. Include `task_plans` and `task_plan_decisions` in database backups. After restoring, verify each accepted decision has its recorded task and there is one decision per plan. After a connection interruption, reload the latest plan and tasks to see the recorded outcome. Both plan tables are append-only and downgrading with plan history stops before removing data.

Demo weather uses a repeatable sample in the API process. No additional schema, worker, provider credential or forecast backup is required. Refresh the cultivation page to fetch the sample for the next local forecast date. The sample is for the portfolio walkthrough. It generates an inline review prompt and the farmer's manual edit uses normal task history and audit.

Live farm forecasts require migration `0018_live_farm_weather` and network access from the API to Open-Meteo. Use the keyless endpoint for non-commercial usage and the customer endpoint with `OPEN_METEO_API_KEY` for a licensed commercial deployment. Production keyless use requires `OPEN_METEO_NONCOMMERCIAL=true`. See [Open-Meteo terms](https://open-meteo.com/en/terms). Refresh is an explicit farmer action that sends rounded coordinates, timezone and dates. Use the existing private API logging settings so coordinates and the optional key do not enter logs.

Forecasts are cached per farm, reused for 30 minutes, and marked stale after two hours or at the next farm-local midnight. Outbound attempts are limited to two per farm per five minutes and twelve per farmer per hour. Provider or network failures leave the last saved forecast intact. The worker and application readiness do not depend on the weather provider.

Weather alerts and rescheduling require `0019_weather_task_review`. Include the rule, alert, plan, decision and task event tables in backups. After restoring, validate plan-to-event links and refresh a synthetic forecast to check alert deduplication. Stale forecasts suppress actionable alerts. After an interrupted decision, review the task and its plan history before retrying.

Keep the app database role restricted; perform crop catalogue changes with separate migration/operator credentials. The app can only read that catalogue, and checks eligibility on crop assignment. Pause writers before an operator changes supported crops or timezone data, then verify the catalogue and one synthetic record request before resuming. Do not grant catalogue UPDATE just to support row locking, or edit record ownership/history directly.

Every mutation uses consistent user/session/parent locks and a single record/revision/audit transaction. A 409 means reload and review; do not automatically replay the unchanged mutation. A 503/connection loss may leave a client unsure whether creation committed: inspect the owned list/history before retrying. There is no create idempotency contract or task execution in FR-C. Preserve the documented no-access-log startup: private locations, notes, bodies and account-search parameters must not enter operator logs. Retain only sanitized status/request IDs; database details never go into HTTP errors.

Restore/backup verification must include all farm/revision/event tables and user tombstone references. Never use test schema rebuilds as a development/production reset. Farm Restore reopens archived records in the app; it is separate from database backup restoration. Workspace deletion retains protected historical records and cannot be undone through the UI. Backups must include farm_deletions so restoration does not re-expose removed farms. Schema downgrade refuses while lifecycle evidence exists. No retention expiry, physical erasure, public sharing or production ownership certification is established by local tests.

Website support uses current schema `0007_support` with no new worker/provider. Include tickets, append-only messages/events and generic notices in database backups and retention planning. Downgrade refuses while support evidence exists; never reset real/development data with test rebuilds. Keep submitted text out of logs, account-audit feeds and public retrieval. Administrators operate only the submitted support conversation; they gain no farm/AI-chat access. Configure a monitored `SUPPORT_CONTACT_EMAIL` through the ignored environment before real-user use, define response/recovery responsibilities, and do not advertise password reset, email delivery or 24-hour staffing that does not exist. Support has per-actor limits (5 creates/30 replies/60 status actions per hour), with stale/uncertain results requiring review rather than automatic retry. See [SUPPORT.md](SUPPORT.md).

Admin count reports (D30) use existing services/schema `0007_support`; no new worker or provider is required. A report view appends minimal account audit, and reports fail closed if that evidence cannot commit. Counts are statement snapshots, not live usage monitoring; disabled/current roles, removed accounts, workspace deletion and parent archives follow [ADMIN_REPORTING.md](ADMIN_REPORTING.md). Existing private farm endpoints remain inaccessible to administrators. Configure no global farm-view shortcut to make counts work. Readiness/backup and real-user reporting/retention gates remain unchanged.

## Deployable units

React static build behind HTTPS; FastAPI API; separate worker/scheduler; PostgreSQL with pgvector; private document storage. Keep secrets server-side, database/storage private and origins explicit. Use separate development/test/deployed configuration.

PostgreSQL durable jobs are the initial design. FastAPI in-process BackgroundTasks is not the durable workflow store. Redis/Celery is optional future work only when justified by measured needs.

## Jobs and failure handling

Workers claim jobs with bounded leases, perform bounded work and persist outcomes. Expired leases allow restart recovery. Use capped transient-error retries and backoff; invalid sources or unsafe proposals need review. Insert outbox events with business changes and deduplicate downstream effects. Provide authorized users with pending/failure status.

Test worker interruption between claim/work/completion and transaction failure between related writes. Do not hold task/proposal locks during model or weather network calls.

## Health and observability

Separate liveness from readiness. Report database readiness and worker heartbeat/job age without making farm CRUD unavailable merely because the model provider is down. Correlate request, retrieval run, job, proposal and execution IDs.

Record request latency, provider latency, bounded retries, queue age/failures, AI usage and timeouts. Redact secrets and minimize personal text. Define actionable alerts when hosting is chosen; no monitoring or paging coverage currently exists.

## Deployment procedure to finalize

1. Run the milestone's CI checks and review the migration impact.
2. Verify backup availability and restore procedure.
3. Apply migrations using deployment credentials with the required limited scope.
4. Deploy compatible API/worker/frontend versions and validate configuration.
5. Smoke-test authentication where implemented, ownership, database readiness and one synthetic user journey.
6. Check worker progress and provider degradation behaviour.
7. Record release version, migration version, checks and any rollback/recovery action.

Document the real rollback strategy before deploying. Reverting application code may not reverse a data migration; destructive schema changes need an explicit recovery plan.

## Backup and restore

Back up both PostgreSQL and original document files, including enough versioned evidence to reconstruct decisions. Define access, encryption, schedule, retention and off-host storage with the chosen host.

Before a real pilot, restore into an isolated environment and verify database constraints, files/checksums, citations, task history and decision evidence. Check worker restart behaviour without duplicating effects. Measure recovery time and data loss rather than assuming backups are usable.

The [local restore drill](TESTING.md#chilli-questions-and-reliability) uses the synthetic test database in the Compose container. It restores into a temporary database and verifies pgvector, representative farm and task evidence, and application-role grants. The CI backend job runs the same drill. Production backup scheduling, document recovery and off-host retention require their own verification.

SRS pilot objectives: recovery point within 24 hours and recovery time within 4 hours. These are unmeasured targets, not service guarantees.

## Before real users

Resolve hosting/budget, reporting contact, source rights, provider terms, agronomic review policy, privacy/retention/account deletion and usage quotas. Verify HTTPS, session/cookie protections, explicit origins, audit grants, backup restoration and release gates. A deployed demo with synthetic actors does not establish production readiness or actual advisor coverage.
## Synthetic PDF processing

The public Chilli questions summaries are versioned with the API. The three Department of Agriculture summaries are served locally. With a Gemini key, the API can send the four fixed study summaries and a canonical study question, limited to six attempts per farmer per hour. Reference answers stay available if the provider is unavailable or its result fails validation. Farm guidance release and source withdrawal controls still apply to the separate uploaded PDF workflow.

Start the normal worker in development/test to process queued uploads. Use the Knowledge Sources list to check failures. Originals are stored in the private PostgreSQL relation and included in database backups. Restore tests should check both original checksums and numbered page text. The parser subprocess has a ten-second wall timeout and Linux CPU/address space limits. Windows uses the wall timeout. The demo requires selectable text and blocks production upload. Real-source rollout needs a separate upload screening and storage review.

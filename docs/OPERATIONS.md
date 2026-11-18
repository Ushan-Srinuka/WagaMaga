# Deployment and operations

Status: M0 local infrastructure and UM1 account/session controls exist; no public host, deployed release, backup job or incident process has been configured. DEVELOPMENT.md owns startup/interactive administrator setup and TESTING.md owns actual checks. This guide retains future deployment/recovery requirements. Browser fixture servers refuse non-test databases and generate ephemeral synthetic credentials; do not use them as an application startup or account-recovery path.

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

SRS pilot objectives: recovery point within 24 hours and recovery time within 4 hours. These are unmeasured targets, not service guarantees.

## Before real users

Resolve hosting/budget, reporting contact, source rights, provider terms, agronomic review policy, privacy/retention/account deletion and usage quotas. Verify HTTPS, session/cookie protections, explicit origins, audit grants, backup restoration and release gates. A deployed demo with synthetic actors does not establish production readiness or actual advisor coverage.

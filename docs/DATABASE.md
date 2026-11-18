# Database and migrations

Status: migrations `0001_foundation` through `0004_in_app_notifications` enable pgvector, add UM1 identity/session/rate-limit/audit tables, add privacy-scrubbed account removal and add recipient-owned notifications. The app role has notification SELECT/INSERT/UPDATE only; audit remains SELECT/INSERT. Compose initialization creates separate development/test databases and a restricted app role. Farm/AI tables and indexes remain unimplemented. The other logical entities below remain a future baseline.

## Storage boundaries

Use PostgreSQL for business state, full text search, pgvector embeddings, durable jobs and audit/decision references. Keep original source files in private document storage and reference storage keys/checksums from the database. Keep private farm records separate from the eligible public-knowledge retrieval scope.

## Entity groups

| Group | Entities |
| --- | --- |
| Identity | users, refresh_sessions |
| Farm context | farms, crop_types, cultivations, farm_observations |
| Work/review | farm_tasks, advisor_cases, ai_proposals/versions, proposal_actions, review_decisions, execution_records |
| Knowledge/advisory | knowledge_documents, document_versions, document_chunks, conversations/messages, retrieval_runs, run_evidence |
| Weather/notices | weather_snapshots, weather_events, notifications |
| Operations | jobs, outbox_events, audit_logs |

Use architecture field definitions as the baseline. Add tables when their slice needs them; M0 does not require the complete business schema.

## UM1 identity schema

[USER_MANAGEMENT.md](USER_MANAGEMENT.md) describes the implemented identity scope. `users` has UUID/unique case-insensitive normalized email, display_name, password_hash, checked role, disabled_at/deleted_at, version and UTC timestamps. Removed accounts are scrubbed tombstones so audit and future domain references remain valid; ordinary account rows are not hard-deleted. `refresh_sessions` stores stable user-owned families with absolute expiry/revocation; `refresh_tokens` stores unique hashes and consumption time, inheriting expiry/revocation from its family. Used hashes remain available to detect replay. `auth_rate_limits` stores keyed identifiers, fixed-window counts and expiry; expired buckets are removed during checks. `audit_logs` stores actor/target FKs, action, old/new values, reason, request ID and timestamp. `notifications` stores recipient FK, trusted account event type, title/body, creation time and nullable read time; its recipient/time index supports scoped inbox pagination. Notification retention is not yet defined. There are no farm, knowledge or task tables in UM1.

Database constraints enforce normalized-email and token-hash uniqueness, roles, positive versions and references. Session mutation locks user then family; administrator lifecycle operations also take a shared transaction advisory lock and recheck the actor. Role/status/removal changes, password-hash changes, session revocation and audit insertion commit or roll back together. Refresh replay revocation explicitly commits before its denial response. Real concurrent-connection, immediate/deferred audit-failure and migration-rebuild tests cover these rules. The app has identity DML and audit SELECT/INSERT, with no audit UPDATE/DELETE or schema-create access. Bootstrap/migration credentials remain separate. Long-term session/audit retention and real-user deletion policy remain unresolved; the implemented removal is an identity scrub/tombstone, not a retention policy or physical deletion.

## Integrity rules

- UUID primary keys, explicit foreign keys and UTC event timestamps.
- Store task dates as local dates with explicit farm timezone; derive reminder instants deliberately.
- Validate coordinates, positive areas with units, supported crops and date relationships.
- Use optimistic versions for mutable tasks/context and immutable versions for accepted proposal actions/document content.
- Preserve historical evidence and decision references; archive records instead of deleting their dependent history.
- Enforce execution/event/job/outbox uniqueness in the database, not only application memory.
- Restrict audit rows to append-only access for the normal application role; administrative migration/retention privileges are separate.

## Indexes

Index ownership and relationship filters, task cultivation/date/status, and notification recipient/read status. Use GIN for full text search. Record embedding model, dimensions and index version; never compare incompatible embeddings. Start with exact vector search for the small corpus and add approximate indexing only after measuring recall. See the [pgvector documentation](https://github.com/pgvector/pgvector).

## Migration workflow

Select the migration tool in M0, record the decision and add verified commands to DEVELOPMENT.md. Check migrations into source control. Review constraints, data transformations and deployment implications. Validate a fresh database build and the supported upgrade path against PostgreSQL/pgvector.

Do not use automatic table creation as a substitute for deployable migration history. Keep synthetic seeds explicit and repeatable. Reset scripts target disposable local/test data only and must not silently delete developer or deployed data.

## Task execution transaction

Lock the persisted proposal version and affected tasks, check owner/state/decisions/hash/expiry/evidence/context versions, claim the unique execution key, apply actions, insert execution/audit/outbox records, mark executed and commit. Roll back business writes on failure; record the safe failure separately. Provider requests happen outside held transaction locks.

Include the necessary tables and constraints in the first slice that changes tasks. Full business-schema breadth can arrive later; integrity for implemented flows cannot.

## Verification and lifecycle

Test migration upgrades, foreign keys, uniqueness, stale versions, concurrent execution, rollback and audit permissions using real PostgreSQL connections. Back up both database and document files and verify a combined restore. Retention/account deletion durations remain open; do not implement cascading deletion that destroys required approval evidence without a declared policy.

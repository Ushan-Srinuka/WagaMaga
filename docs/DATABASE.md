# Database and migrations

Status: migrations `0001_foundation` through `0007_support` enable pgvector, UM1 identity/accounts/notifications, farm persistence and append-only workspace deletion. Owner-only APIs/screens include farm restore/delete; AI tables remain unimplemented. Compose uses separate development/test databases and restricted application credentials. TESTING.md records actual evidence and remote CI limitations.

## Storage boundaries

Count reporting (D30) adds no schema change. Dedicated services read aggregate counts using one PostgreSQL statement snapshot per report, filtering workspace-deleted farms and removed/former-farmer owners and handling inherited crop archives. No raw farm fields are projected. A successful response commits a minimal `report_viewed` account-audit row; no counts, farm IDs, locations or message content enter that audit. Live admin checks/locks remain distinct from owner-only record services. See [ADMIN_REPORTING.md](ADMIN_REPORTING.md).

`0007_support` is the current head. It adds `support_tickets` (requester/category/subject/status/version/times), append-only `support_messages` (submitted text and author-role provenance) and `support_events` (minimal operation/status/version/request-ID evidence). Owner/update and status/update indexes support bounded queries; ticket-version uniqueness protects messages/events. Restricted FKs and a ticket identity trigger preserve context. The app has SELECT/INSERT/UPDATE on tickets, SELECT/INSERT only on messages/events, and no DELETE/TRUNCATE. Support notices add the allowed `support_updated` event without storing private text in notifications. There are no farm or AI-chat FKs; explicit sharing is limited to submitted messages. Downgrade refuses while requests/notices exist; real retention/erasure periods remain open. Services enforce owner/admin scope before every read/count or mutation and commit messages/events/notifications atomically. See [SUPPORT.md](SUPPORT.md).

Farm lifecycle migration `0006_farm_lifecycle` adds the `farm_deletions` table with a farm primary-key/FK, `deleted_by` user FK, finite UTC `deleted_at` and positive `entity_version`. The app can SELECT/INSERT markers only. Restore/delete add `farm_restored`/`farm_deleted` private audit operations without modifying existing snapshot shapes or rows. Owner services exclude marked farms before list counts and all parent-chain access. Delete atomically records the new farm version/revision/event and marker; records and child evidence stay stored. Downgrade refuses while markers or restore/delete evidence exist, so a schema rollback cannot resurrect a removed farm. This is workspace deletion, not physical data erasure or a retention policy; see D28.

Records schema: [FARM_RECORDS.md](FARM_RECORDS.md) and D26 define the implemented FR-B tables. Child ownership derives through farms.farmer_id; restricted FKs preserve user tombstones/history. Private revisions/events stay outside administrator account-audit viewing. Readiness expects `0007_support`; database readiness alone is not an owner-authorization check.

The subsequent FR-C services expose authorized routes using this schema. They recheck live actors/sessions, resolve full owner-scoped parent chains and lock user/session/parents consistently before applying optimistic/archival transitions. Actual mutations append the record revision and minimized farm audit event in the same transaction; function-scoped HTTP transactions commit before a success response. Read-only and no-op calls do not create evidence. Shared database credentials still have no row-level ownership guarantee; callers must use these services. Catalogue writes remain migration/operator-only, and timezone validation uses PostgreSQL's existing catalogue.

Use PostgreSQL for business state, full text search, pgvector embeddings, durable jobs and audit/decision references. Keep original source files in private document storage and reference storage keys/checksums from the database. Keep private farm records separate from the eligible public-knowledge retrieval scope.

## Entity groups

| Group | Entities |
| --- | --- |
| Identity | users, refresh_sessions |
| Farm context | farms, crop_types, cultivations, farm_observations, farm_revisions, cultivation_revisions, observation_revisions, farm_audit_events, farm_deletions |
| Website support | support_tickets, support_messages, support_events |
| Work/review | farm_tasks, advisor_cases, ai_proposals/versions, proposal_actions, review_decisions, execution_records |
| Knowledge/advisory | knowledge_documents, document_versions, document_chunks, conversations/messages, retrieval_runs, run_evidence |
| Weather/notices | weather_snapshots, weather_events, notifications |
| Operations | jobs, outbox_events, audit_logs |

Use architecture field definitions as the baseline. Add tables when their slice needs them; M0 does not require the complete business schema.

## UM1 identity schema

[USER_MANAGEMENT.md](USER_MANAGEMENT.md) describes the implemented identity scope. `users` has UUID/unique case-insensitive normalized email, display_name, password_hash, checked role, disabled_at/deleted_at, version and UTC timestamps. Removed accounts are scrubbed tombstones so audit and future domain references remain valid; ordinary account rows are not hard-deleted. `refresh_sessions` stores stable user-owned families with absolute expiry/revocation; `refresh_tokens` stores unique hashes and consumption time, inheriting expiry/revocation from its family. Used hashes remain available to detect replay. `auth_rate_limits` stores keyed identifiers, fixed-window counts and expiry; expired buckets are removed during checks. `audit_logs` stores actor/target FKs, action, old/new values, reason, request ID and timestamp. `notifications` stores recipient FK, trusted account event type, title/body, creation time and nullable read time; its recipient/time index supports scoped inbox pagination. Notification retention is not yet defined. There are no farm, knowledge or task tables in UM1.

Database constraints enforce normalized-email and token-hash uniqueness, roles, positive versions and references. Session mutation locks user then family; administrator lifecycle operations also take a shared transaction advisory lock and recheck the actor. Role/status/removal changes, password-hash changes, session revocation and audit insertion commit or roll back together. Refresh replay revocation explicitly commits before its denial response. Real concurrent-connection, immediate/deferred audit-failure and migration-rebuild tests cover these rules. The app has identity DML and audit SELECT/INSERT, with no audit UPDATE/DELETE or schema-create access. Bootstrap/migration credentials remain separate. Long-term session/audit retention and real-user deletion policy remain unresolved; the implemented removal is an identity scrub/tombstone, not a retention policy or physical deletion.

## FR-B farm persistence

`0005_farm_records` creates eight tables and seeds only the supported chilli catalogue row, using stable UUID `1e7402ea-35ab-4673-a8de-834c4bb70401`. ORM models register with Alembic metadata; no create_all or automatic farm/user seed is used. The test-only `farm_records` fixture creates two synthetic owners' farm/cultivation/observation chains, version-1 snapshots and audit evidence in the guarded `_test` database.

Constraints enforce nonblank labels/notes, text bounds, paired coordinates and optional farm area, coordinate ranges, positive versions, finite planting/observation dates, supported unit identifiers and all-or-none confirmation provenance. Area uses NUMERIC with range and `value = trunc(value,6)` checks, enforcing the intended 18/6 domain without implicit rounding. The estimator field must remain null until a separately specified estimator changes that constraint. FR-C services now enforce supported-crop assignment, timezone validation and future-observation rejection in addition to these database constraints.

Restricted FKs prevent deletion of referenced users, farms, crops, cultivations and observations. Identity triggers prevent owner/parent/author/created_at/ID reassignment. Composite FKs on farm audit entries enforce the farm/cultivation/observation chain; partial unique indexes allow only one successful event per target version. Revisions are unique per parent/version, contain only the exact allowlisted snapshot keys and require matching non-null snapshot ID/version. Their private JSONB data is separate from `audit_logs`, whose target is an account.

The app has SELECT/INSERT/UPDATE on farms/cultivations/observations, SELECT on crop_types and SELECT/INSERT on revisions/farm_audit_events. It cannot DELETE/TRUNCATE these tables or UPDATE revisions/audit. The separate migration role controls schema, seeds and any future retention process. Shared app credentials do not enforce row ownership: FR-C services scope every query, enforce optimistic/archival transitions and append complete revisions/audit in one transaction. PostgreSQL tests now cover both persistence and the API's immediate/deferred rollback boundary. No database row-level-security guarantee is claimed.

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

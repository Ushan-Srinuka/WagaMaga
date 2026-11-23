# Database and migrations

Migration `0015_knowledge_translations` extends the evidence review page range to 1–100. It stores an optional approved English translation in the same append-only decision as its exact source quote. A database constraint restricts translations to suitable decisions with a quote. Downgrade refuses while a translation or review past page 20 exists.

Migration `0012_chilli_pilot` adds an approved excerpt to each evidence decision and append-only evaluation runs. Run fingerprints bind the question, policy, model, review revision, candidates and approved excerpts. Only a matching current run can count toward pilot release.

Migration `0011_knowledge_eval` records append-only evidence labels by question and revision. Page labels bind to a PDF version and page, and case-level missing labels omit both. The app can select and insert decisions. Source identity, reviewer identity, reason, request and timestamp remain traceable. Downgrade is blocked when review decisions exist.

Migration `0010_discard_pdf` adds the discarded status and preserves the original file, version and decision history. Discarding updates the lifecycle revision and inserts its decision in one transaction. Only unpublished PDFs can be discarded through the admin API.

Migration `0008_knowledge_demo` adds synthetic guide versions and lifecycle decisions. The app role can update only the version's status and revision. Its content and checksum remain fixed, and decision rows are append-only through app grants. Downgrade is blocked while demonstration history exists.

Migration `0009_knowledge_pdf` adds the private `knowledge_source_pdfs` relation for originals, queued work and page extraction results. Upload and queue creation share one transaction. A worker claims a queued row with `FOR UPDATE SKIP LOCKED`. If the transaction rolls back, the row remains queued. Completed results are immutable and a PDF version's checksum covers original bytes.

Status: migrations `0001_foundation` through `0015_knowledge_translations` enable pgvector, accounts, private farm records, support and the synthetic knowledge lifecycle. Migration 0013 permits bounded source PDFs up to 6 MiB; migration 0014 adds withdrawn-PDF deletion. Compose uses separate development/test databases and restricted application credentials. TESTING.md records actual evidence and remote CI limitations.

## Storage boundaries

Count reporting (D30) adds no schema change. Dedicated services read aggregate counts using one PostgreSQL statement snapshot per report, filtering workspace-deleted farms and removed/former-farmer owners and handling inherited crop archives. No raw farm fields are projected. A successful response commits a minimal `report_viewed` account-audit row; no counts, farm IDs, locations or message content enter that audit. Live admin checks/locks remain distinct from owner-only record services. See [ADMIN_REPORTING.md](ADMIN_REPORTING.md).

`0007_support` adds `support_tickets` (requester/category/subject/status/version/times), append-only `support_messages` (submitted text and author-role provenance) and `support_events` (minimal operation/status/version/request-ID evidence). Owner/update and status/update indexes support bounded queries; ticket-version uniqueness protects messages/events. Restricted FKs and a ticket identity trigger preserve context. The app has SELECT/INSERT/UPDATE on tickets, SELECT/INSERT only on messages/events, and no DELETE/TRUNCATE. Support notices add the allowed `support_updated` event without storing private text in notifications. There are no farm or AI-chat FKs; explicit sharing is limited to submitted messages. Downgrade refuses while requests/notices exist; real retention/erasure periods remain open. Services enforce owner/admin scope before every read/count or mutation and commit messages/events/notifications atomically. See [SUPPORT.md](SUPPORT.md).

Farm lifecycle migration `0006_farm_lifecycle` adds the `farm_deletions` table with a farm primary-key/FK, `deleted_by` user FK, finite UTC `deleted_at` and positive `entity_version`. The app can SELECT/INSERT markers only. Restore/delete add `farm_restored`/`farm_deleted` private audit operations without modifying existing snapshot shapes or rows. Owner services exclude marked farms before list counts and all parent-chain access. Delete atomically records the new farm version/revision/event and marker; records and child evidence stay stored. Downgrade refuses while markers or restore/delete evidence exist, so a schema rollback cannot resurrect a removed farm. This is workspace deletion, not physical data erasure or a retention policy; see D28.

Records schema: [FARM_RECORDS.md](FARM_RECORDS.md) and D26 define the implemented FR-B tables. Child ownership derives through farms.farmer_id; restricted FKs preserve user tombstones/history. Private revisions/events stay outside administrator account-audit viewing. Readiness expects `0015_knowledge_translations`; database readiness alone is not an owner-authorization check.

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

### Manual cultivation tasks

Migration `0016_manual_farm_tasks` adds `farm_tasks` and `farm_task_events` with restricted foreign keys. Tasks store a cultivation, title, local calendar due date, status, version and UTC timestamps. Tasks are indexed by cultivation, due date and ID. The update trigger preserves the parent and creation time and permits only a single version increment from a pending task.

The event primary key is task ID and task version. An event stores the title and due date at the change, action, actor, request ID and UTC timestamp. The application role can append and read events and update only task state fields. It cannot remove tasks or rewrite events. A migration downgrade refuses to discard saved task history.

### Suggested task plan demo

Migration `0017_suggested_task_plans` adds two append-only tables. `task_plans` saves the fixed create action, title and due date, SHA-256 action hash, version, sample evidence code and text, parent versions, author, request ID and expiry. `task_plan_decisions` binds to the exact plan ID, version and hash with a composite foreign key. Its primary key allows one decision per plan. An accepted decision must reference its unique created task and a rejected decision has no task. The decision records the actor, request ID and time and serves as the execution receipt.

The application role receives SELECT and INSERT only for both tables. The plan service serializes decisions using the same owner and parent locks as manual task writes. Task creation, its task event and the execution receipt share one transaction. The migration refuses a downgrade while any plan exists, including an undecided plan.

### Live farm forecast cache

Migration `0018_live_farm_weather` adds `farm_forecasts` with one current snapshot per farm. It stores rounded coordinates, timezone, provider, UTC fetch time and three normalized daily measurements in JSONB. Cultivations on the same farm share the snapshot. The app role can read, insert and replace snapshot fields. It cannot change the farm key or delete the row. A cache entry for a different location or timezone is excluded from reads.

Refresh calls the provider before taking write locks. The service acquires the actor, session and parent locks, rechecks the location and day, and replaces the snapshot only after provider validation. This cache contains no proposal or task evidence links, so a schema downgrade can discard it without altering farm records or task history.

## Integrity rules

Migration `0019_weather_task_review` adds `weather_alert_rules` (one versioned setting per cultivation) and `weather_task_alerts` (one row per task and due date). A repeated check refreshes the stored evidence rather than adding another row. Rules and alert state can change under restricted column grants. Current reads require a pending task, active parent, qualifying threshold and matching fresh forecast.

Migration `0020_scheduled_weather` adds one `weather_refresh_schedules` row per opted-in farm, with version, next due time and recoverable lease. `weather_review_notices` claims one notification per cultivation and local due date, even when multiple tasks match. The claim, alert snapshot and `weather_review` inbox entry commit together. The application role can insert notice claims and cannot edit or delete them.

Migration `0021_guidance_observations` adds nullable soil moisture to `farm_observations`. Observation history allows this field only with the same three enumerated values. Revisions without a soil moisture value retain the original snapshot shape and historical rows stay readable. Downgrade refuses to discard recorded values or their history.

Weather date proposals reuse the append-only `task_plans` and `task_plan_decisions` tables. A date proposal stores the task ID/version, original and proposed dates, the applied threshold and a normalized snapshot of the forecast evidence. Each accepted decision points to a unique task event and version through a composite foreign key. Existing accepted example plans are backfilled to their original task creation event. Downgrade refuses while a weather date proposal exists.

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

Migration `0014_delete_withdrawn_pdf` lets an administrator delete a withdrawn PDF by clearing its original and extracted page JSON in one audited status transition. It keeps the source title/checksum, lifecycle decision rows and separate evaluation decisions/approved excerpts; the deleted version is hidden from source lists and page routes. A database trigger permits only the worker's one-time queued completion or the guarded delete state, and the application role receives only the columns needed for those transitions. Downgrade refuses after deletion evidence exists. This removes the PDF and full extracted pages but is not erasure of review excerpts or audit history.

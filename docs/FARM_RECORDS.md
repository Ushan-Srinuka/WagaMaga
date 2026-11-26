# Farm Records plan

Status: FR-A specification, FR-B persistence, FR-C owner-only services/APIs and FR-D connected screens are implemented locally, with a farmer-onboarding/location UX follow-up on 19 November 2026. Current schema is `0006_farm_lifecycle`, adding farm restore and append-only workspace deletion under D28. No new dependency is added. The farm/cultivation/observation, stage, archive and history journey has desktop/mobile browser evidence. Remote CI remains pending, and manual records do not establish agricultural validation. See D26-D28 in [DECISIONS.md](DECISIONS.md) and [TESTING.md](TESTING.md) for actual results and limits.

## Scope and roadmap

Farm Records is the first bounded workstream within roadmap M1, whose title remains "V0 evidence proof". The SRS also labels its Farm and Crop Management business module M1; that module is not a replacement for the roadmap release gates. Preserve M1-M4 and the stable SRS identifiers. Records alone do not complete V0 or M2.

Reuse UM1 accounts/live sessions, React, FastAPI's modular monolith, SQLAlchemy/Alembic and PostgreSQL/pgvector. Manual records need no new dependency, provider or worker job. Use local synthetic data only until DR04 retention/account-deletion policy is defined and displayed.

Included journey: sign in as a farmer, create a farm, add a cultivation, record observations, edit details, explicitly confirm a known stage, archive a cultivation/farm and read its history; restore an archived farm or delete it from the workspace with retained historical records.

Manual tasks were added separately under FR10 and FR30. A farmer can add and edit pending tasks, complete or cancel them, and view their task history on the cultivation history page. See the [manual task API contract](API.md#manual-cultivation-tasks).

Excluded from the Farm Records slice: calendar views, proposals/execution, AI/automatic stage estimation, weather, uploads, advisor sharing, crop administration, ownership transfers, cultivation restoration/deletion, permanent data erasure and farm notifications.

## Requirement traceability

UX follow-up, 19 November 2026: farmer login returns to `/`, with Add Farm in the website header and a hero action bar for adding a first farm, selecting an owned active farm and continuing to crops/observations. The initial separate dashboard is superseded; its old URL redirects farmers home. District/village entry is a UI aid over the existing location label; free-text/legacy labels remain available. Optional browser geolocation fills only a reviewed draft coordinate pair. It does not establish agricultural applicability or restrict the manual-record API to a district. The planned pilot remains chilli/Anuradhapura, subject to review. See [UI_DESIGN.md](UI_DESIGN.md#farmer-onboarding-follow-up---19-november-2026), D27 and the latest [TESTING.md](TESTING.md) record.

The [SRS](WagaMaga_AI_SRS.md) owns the identifiers and the [architecture](WagaMaga_AI_System_Architecture.md) owns the baseline design. The following refines the records slice.

| Requirement | Acceptance boundary |
| --- | --- |
| FR02, FR03 | Live account/session, farmer role and owner checks on every operation; identifiers cannot widen access. |
| FR04 | Sharing deferred; advisors receive no farm access before a separately implemented explicit case flow. |
| FR05 | Create, read, edit and archive owned farms with name, location and optional area/unit. |
| FR06 | Supported crop, planting date and positive cultivation area/unit; unknown soil remains null. |
| FR07 | Separate estimated and confirmed stages and provenance. Owner confirmation only here; case-scoped advisor confirmation deferred. |
| FR08 | Timestamped observations with author/notes; edits preserve immutable revisions from first implementation. |
| FR09 | Archives leave active lists, retain owner-readable history and block new activity. Later proposal execution must check farm and cultivation archive state. |
| FR10 | Bounded, filtered farm, cultivation, observation and task lists. Tasks are ordered by local due date. |
| FR30 | Owner creates and edits pending manual tasks, completes or cancels them and reads task history. |
| DR01, DR03, DR05 | Foreign keys, explicit dates/timezone, versioned private history and append-only audit. Future decisions bind immutable context. |
| DR04 | Synthetic local scope; retention/deletion periods remain open before real users. |

## Fields and validation

Server validation is authoritative; forms mirror it. Reject unknown request fields and client ownership, actor, server-managed creation/update/confirmation timestamps, archive or estimate metadata. The observation's observed_at is explicitly client-supplied. Updates accept an explicit allowlist plus `expected_version`.

### Farms

- `name`: trimmed, required, 1-120 characters; duplicate names allowed.
- `location`: required trimmed label, 1-200 characters. A label does not verify agronomic region/applicability.
- `latitude`, `longitude`: optional finite numeric pair, both supplied or both null; ranges -90 to 90 and -180 to 180. The UI can explicitly request the device location, show its accuracy and let the owner review/change/remove the pair before saving. No automatic collection, map, geocoder or district-centre coordinates.
- `timezone`: valid IANA identifier; default `Asia/Colombo`, stored on the farm.
- `area_value`, `area_unit`: optional pair, both null or a positive finite decimal and `ha`, `acre` or `m2`. FR-B refines the proposed `NUMERIC(18,6)` to unconstrained PostgreSQL NUMERIC with CHECKs enforcing `0 < value < 1000000000000` and equality with `trunc(value,6)`. This preserves the intended range/precision while rejecting excess decimals instead of PostgreSQL rounding them before validation.

### Cultivations

- `farm_id`: route-derived owned parent; immutable after creation.
- `crop_type_id`: required supported crop reference; seed stable `chilli` initially. Enabling records does not validate agricultural guidance.
- `planting_date`: required ISO local date. Future dates are allowed and labelled planned relative to the farm timezone. Dates do not establish stage or readiness.
- `area_value`, `area_unit`: required, using farm area validation. Do not impose summed cultivation area limits without a separate overlap/season model; farm area may be unknown.
- `soil_notes`: optional plain text, maximum 2000 characters; absent/blank becomes null. Do not infer soil type, pH or nutrient facts.
- `estimated_stage`: nullable/server-owned and null here. A future estimator must record source/rule version and estimation time before writing estimates.
- `confirmed_stage`: optional owner-reported label, trimmed, 1-80 characters, entered through an explicit confirmation command. Server sets `confirmed_by` and `confirmed_at`; all three are null or all present. This is reported context, not validated readiness.
- Changing crop or planting date clears current stage confirmation and any estimate in the same transaction; immutable history retains earlier provenance. A new confirmation is explicit. Area/soil edits do not silently change stage.

### Observations and common fields

- `observed_at`: required timezone-aware instant, stored UTC/displayed in farm timezone. Reject future instants relative to server time. Pre-planting observations are allowed; no end/completion date is introduced.
- `notes`: trimmed plain text, required, 1-4000 characters. Render as text, never executable HTML/instructions.
- `recorded_by`: server-derived creation actor, immutable; revisions separately record editor/time.
- Farm, cultivation and observation records have UUID keys, integer `version >= 1` and UTC created/updated timestamps. Farms/cultivations have nullable `archived_at`.

## Data model

Migration `0005_farm_records` installs the base tables and `0006_farm_lifecycle` adds `farm_deletions` and the restore/delete audit operations; [DATABASE.md](DATABASE.md) records constraints, grants and remaining service obligations. Only the supported chilli reference row is seeded outside tests; no farmer records are seeded on startup or in the development migration.

| Table | Relationships and purpose |
| --- | --- |
| `farms` | `farmer_id -> users.id`; fields above, archive state/version. No ownership transfer. |
| `crop_types` | UUID, unique stable code, display_name, supported flag; referenced rows cannot be deleted. |
| `cultivations` | `farm_id -> farms.id`, `crop_type_id -> crop_types.id`, nullable `confirmed_by -> users.id`, cultivation/stage/archive fields. |
| `farm_observations` | `cultivation_id -> cultivations.id`, immutable `recorded_by -> users.id`, observed_at, notes, version/timestamps; parent immutable. |
| `farm_revisions` | Farm FK, entity version, allowlisted full snapshot, changed_by user FK, changed_at; unique parent/version. |
| `cultivation_revisions` | Equivalent immutable cultivation snapshots including confirmation provenance, FK and unique parent/version. |
| `observation_revisions` | Equivalent immutable observation snapshots including author/editor, FK and unique parent/version. |
| `farm_deletions` | Append-only farm PK/FK, deleting actor, UTC time and final entity version. Excluded by all owner/parent-chain queries; not an erasure policy. |
| `farm_audit_events` | Actor/farm FKs, optional cultivation/observation FKs, operation, entity version, UTC time, request ID and outcome code. Check child references belong to the parent chain. No location/note payload. |

FR-C services create a revision for version 1 and every actual mutation. The snapshot helper serializes only mapped farm-record columns after flush; revision CHECKs require the exact key set and matching non-null entity ID/version. History reads check the current owner's full parent chain and project typed snapshots. Future proposals must persist/reference the exact context revisions used. Services append record/revision/audit inside the caller's transaction; the function-scoped HTTP transaction commits before returning success. Direct database writes are not equivalent to these services.

Use restricted FK deletion and preserve account tombstones/history; no cascading account/farm deletion. PostgreSQL enforces references, positive area/version, paired fields, coordinate ranges and revision uniqueness. Composite audit FKs reject mismatched parent chains. Triggers prevent changes to record IDs, owner/parent, original author and created_at. FR-C services additionally check supported crops on assignment, valid timezone, future observation times, current actor/owner and archive/version transitions. Database grants alone do not provide those service rules.

Index farms by farmer/archive/creation, cultivations by farm/archive/creation, observations by cultivation/observed time, revisions by parent/version and events by farm/time. Use stable UUID ordering tie-breakers. No private-record vector columns.

Application grants: SELECT/INSERT/UPDATE on mutable farm/cultivation/observation tables, SELECT on crop types, SELECT/INSERT on revisions/events; no DELETE, revision/audit UPDATE or schema privileges. Migration role handles DDL/crop seeds. Grants do not replace service ownership checks; this plan does not claim database row-level security.

## Owner-only rules

| Actor/state | Lists | Detail/history | Writes |
| --- | --- | --- | --- |
| Active farmer, owned records | Owned results/totals only | Allowed including archives | Only with active farm/relevant cultivation |
| Active farmer, another owner's/missing record | Never included | Generic 404 | Same generic 404; no effects |
| Advisor/administrator | 403 before target lookup | 403 before target lookup | 403 before target lookup |
| Missing/expired/revoked session, disabled/removed account | 401 | 401 | 401 |

Derive actor from UM1 validated authentication and check current account/session in PostgreSQL. Farm predicates include `farmer_id = actor.id`; child/history queries join to that farm. Nested URLs must match the full parent chain. Apply ownership before search, filters, totals, sorting or pagination; do not load a foreign row to produce a richer error.

Role changes do not transfer farms. A former farmer cannot access their records while an advisor/administrator; access requires an active farmer account again. Removed accounts retain inaccessible records under this synthetic-only plan. Administrator account rights grant no private farm access.

Reuse browser Origin/client-header/JSON write protections. Private responses use `Cache-Control: no-store`; errors omit raw inputs/private values/traces. Private snapshots and notes stay out of logs, administrator account projections/audit, account notifications, public retrieval indexes and providers. No administrator farm-audit endpoint. Database operators remain a separate infrastructure trust boundary.

## Archive, versions and atomic writes

Farm Restore clears only the farm archive timestamp. Independently archived cultivations remain archived; current-version restore of an active farm is a no-op. Delete requires an archived owned farm, `expected_version` and exact current `confirmation_name`. It appends `farm_deletions`, a final version/revision and `farm_deleted` event atomically; it does not physically erase stored data. All lists/counts and farm/child/history/write/restore lookups exclude this marker. There is no deleted-items view or undo. The UI explains retained data before confirmation. D28 retains the separate DR04 decision for real-user erasure/retention policy.

- Default lists show effective active records. A cultivation is effectively archived if its own or its farm's archived_at is set. Farm archive does not rewrite all child archive timestamps; history labels inherited state.
- Owner reads/history remain allowed. Archived parents block edits, new child records and stage confirmation. Observations inherit both parent states. Farm restore is supported with an explicit versioned command. Workspace-deleted farms are inaccessible, including history/children/restore; there is no physical-erasure route.
- PATCH, confirmation, archive, farm restore and workspace deletion require positive `expected_version`, checked after ownership. Mismatch returns 409. Current-version repeated archive returns the entity without duplicate event/revision; a stale repeat still returns 409. No-op PATCH likewise creates no version.
- Actual writes atomically advance version/timestamps, append revision and insert minimal farm audit. Any revision/audit/commit failure rolls back all business writes; success only after commit.
- Serialize writes with session revocation and parent archives. Lock actor user, session, farm, cultivation, observation as applicable, matching UM1 identity lock order. Recheck role/session, owner, archive and expected version under locks. A child write committed before archive remains valid; one obtaining the parent lock afterward is denied. Test with real concurrent connections.
- No network calls under locks. Manual POST creation is not claimed idempotent; after an uncertain response reload before retrying. Successful changes have transactional audit; denials use sanitized operational status/request-ID logging without private payload or partial records.
- Later task-changing flows still require DR02 persisted actions/decisions/evidence, precondition checks and execution uniqueness. This slice implements no task execution.

## Implemented API

Paths below are relative to `/api/v1`; all are implemented in FR-C. Routes own HTTP/DTOs; farms services own authorization/history/transitions. No public or administrator farm routes. Generated OpenAPI owns the full typed schemas; [API.md](API.md) documents contract details and examples.

| Methods/path | Purpose |
| --- | --- |
| `GET /crop-types` | Active farmer reads supported crop catalogue. |
| `POST /farms/{farm_id}/restore` | Versioned owner restore; independently archived cultivations remain archived. |
| `POST /farms/{farm_id}/delete` | Archived owner farm only; expected_version and confirmation_name. Hides access while retaining immutable history. |
| `GET/POST /farms` | Owned list or creation with server-derived owner. |
| `GET/PATCH /farms/{farm_id}` | Owned detail/edit. |
| `POST /farms/{farm_id}/archive` | Version-checked archive. |
| `GET/POST /farms/{farm_id}/cultivations` | Owned parent's list/create. |
| `GET/PATCH /farms/{farm_id}/cultivations/{cultivation_id}` | Detail/edit with matching parent chain. |
| `POST /farms/{farm_id}/cultivations/{cultivation_id}/archive` | Version-checked archive. |
| `POST /farms/{farm_id}/cultivations/{cultivation_id}/stage-confirmation` | Explicit reported stage and server-derived provenance. |
| `GET/POST /cultivations/{cultivation_id}/observations` | Owner-scoped list/create through containing farm. |
| `GET/PATCH /cultivations/{cultivation_id}/observations/{observation_id}` | Observation detail/edit with matching parent. |
| `GET .../{entity_id}/history` | Farm/cultivation/observation revisions appended to the corresponding detail path. |

All collections use page 1-10000, page_size default 20/max 100 and `{items,total,page,page_size}`. Farm/cultivation filters: `status=active|archived|all` default active; optional literal `q` name search up to 100 characters on farms, optional crop_type_id on cultivations. Cultivation filtering uses effective parent archive state. Observation filters: optional inclusive UTC from_date/to_date on observed_at; reject inverted ranges. Supported crop catalogue is paginated too.

Farm/cultivation ordering: created_at descending, UUID ascending. Observations: observed_at descending, UUID ascending. History: version descending. Responses use resource allowlists, effective archive/planned labels and no account email/session data; history returns owned snapshots/editor/time. No general farm-audit browser is needed.

Return 201 for creation and 200 for reads/PATCH/confirmation/archive. Use the access policy above, safe 422 validation, 409 stale/archived conflicts, and safe 503 storage unavailability. Preserve existing error envelope/request IDs and never reveal another owner's archive state. Stage confirmation accepts `{expected_version, stage}`; server supplies actor/time, and each explicit confirmation creates a new version even when the label/clock is unchanged. PATCH validates the merged record, supports paired-field removal only when the final pair is valid, rejects explicit null for required fields and treats version-only/unchanged edits as no-ops on active records.

Decimal coordinates/areas accept JSON numbers or decimal strings and serialize as strings without losing precision. Dates accept ISO local dates; observation instants require an offset and normalize to UTC. Timezone validation and current-date calculation use PostgreSQL's IANA timezone catalogue, including installed aliases such as UTC; no Windows timezone dependency is added. Crop catalogue writes remain migration/operator-only; coordinate supported-crop changes with paused writers as described in OPERATIONS.md.

## Implemented screens

FR-D reuses [UI_DESIGN.md](UI_DESIGN.md), the existing session client/theme and shared forms/notices/native dialog. Farmer-only My Farms navigation is available in the workspace and signed-in homepage. Home links directly to My Farms, the field-note form and the planner. Open Farm details on a farm to edit, archive or view its history.

- My Farms: own active/archived list, pagination, create form, empty state.
- Farm detail: location/area/timezone, edit/archive, cultivations/list/create.
- Cultivation detail: crop/date/planned label, area, unknown soil/stage labels, explicit stage confirmation and observation forms/list.
- History: owner-only revisions with actor/time/version and archive labels. Archive confirmation explains retained history and blocked activity.
- Each screen handles loading, empty, validation, unavailable, expired session, inaccessible and stale-version states. Offer reload/review on conflict; no silent overwrite or automatic mutation retry. Clear private screen state on logout/account switch. No fabricated estimates, forecasts or AI advice.

Farmer shortcuts include `/field-notes/new`, `/planner` and `/knowledge/chilli/crop`. Each uses the existing owner-only farm and crop lists. Record routes: `/farms`, `/farms/new`, `/farms/:farmId`, `/farms/:farmId/history`, `/farms/:farmId/cultivations/new`, `/farms/:farmId/cultivations/:cultivationId`, its `/history` page and `/observations/:observationId/history` under that cultivation. Farmer route guards improve navigation; the backend remains authoritative. The workspace outlet is keyed by current user/role; resource requests discard late responses after route/account changes. No records or drafts use browser storage.

Fields preserve decimal strings. Observation time entry explicitly uses the device timezone; UTC is sent to the API and timestamps display in the farm timezone. Notes-only edits preserve the original full observation timestamp, including sub-millisecond precision. History uses labelled fields, versions, actor/time and plain-text notes rather than raw JSON. UI crop selection loads up to 100 supported entries, sufficient for the initial single-chilli scope; expanding the catalogue needs its own selector review.

Farm writes disable the session client's automatic unauthorized-request replay. A 401 clears private state and returns to login; normal read refresh behaviour is unchanged. A 409 retains the draft, disables resubmission and offers explicit reload with a draft-discard explanation. Uncertain network/503 outcomes block replay and direct the user to review saved records. Parent edits, stage entry and observation drafts are coordinated so saving one does not silently discard another. Native archive confirmation explains retained history and read-only descendants; farm restore and typed-name workspace deletion are available on archived farms; cultivation restore/deletion and physical data erasure are not available.

## Delivery and acceptance

| Slice | Deliverable/gate |
| --- | --- |
| FR-A specification | Complete: plan, D26, aligned guides and documentation consistency checks. |
| FR-B persistence | Implemented locally: migration 0005, models, synthetic fixtures and restricted grants; real PostgreSQL migration/constraint/history/rollback evidence in TESTING.md. That slice was persistence-only. |
| FR-C services/API | Implemented locally: owner-scoped services/typed routes; PostgreSQL authorization, failure/concurrency and identity regression checks pass. Remote CI remains pending. |
| FR-D screens | Implemented locally: connected responsive screens, meaningful component checks and real backend mobile/desktop browser journeys; results in TESTING.md. |
| FR-E verification | Actual setup/check commands, results/limitations and current contracts; distinguish local evidence from remote CI. |

Implementation must verify:

1. Farmer A creates/edits farm, cultivation and observation, confirms a stage, archives and reads exact earlier revisions.
2. Farmer B's IDs, mixed parents, history IDs, searches, counts and archive filters reveal/mutate nothing. Reject spoofed owner/author/confirmation fields.
3. Excluded roles and invalid/expired/revoked/disabled/removed actors fail. Account/audit/notification views contain no private farm content.
4. Reject invalid/partial coordinates, mismatched units, zero/negative/nonfinite/overflow areas, unsupported crop, invalid timezone/date/time and empty/oversized text. Accept future planting as planned, valid pre-planting observations and unknown soil/stage.
5. Stale edits and writes under either archive level fail; repeated archive creates no duplicate effect. Crop/date edits clear current stage while history retains provenance.
6. Real concurrent PostgreSQL connections cover archive/create, stale-edit and revocation/write races. Inject revision/audit and deferred commit failures; assert rollback and no premature success. Verify no app-role revision/audit rewrite/delete or cascading history loss.
7. Real API/database mobile/desktop journeys cover inaccessible links, stale edits, safe text rendering, archived history and clearing account state. Mocks cannot establish authorization.

Use PostgreSQL/pgvector, never SQLite substitutes. Exact commands belong in [DEVELOPMENT.md](DEVELOPMENT.md) and [TESTING.md](TESTING.md) as implementation arrives; do not invent absent farm test commands. Report farm portions of AT01/AT02 only: proposal-execution blocking, advisor case rules and full V0/V1 gates remain unverified.

## Next delivery checkpoint

```text
Review the Farm Records diff and FR-E evidence in TESTING.md. Follow the
requested Git/publication workflow before running remote CI; do not claim
CI passed without the remote result. Resolve relevant findings and retain
the local/remote distinction. Do not expand into tasks, AI, weather, sharing
or deployment as part of closing these manual records slices. Full V0 and
AT01/AT02 gates still include later proposal/execution and advisor domains.
```

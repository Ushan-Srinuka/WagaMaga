# API guide

Status: M0 health, UM1 identity/accounts/audit/notifications and FR-C owner-scoped Farm Records endpoints are implemented locally. FR-D connects their screens. `GET /health/live` returns 200 for process liveness. `/health/ready` returns 200 only when PostgreSQL, pgvector and `0015_knowledge_translations` are ready, otherwise 503. These operational routes are outside `/api/v1`. OpenAPI/Swagger are available in development/test and disabled by default in production configuration.

## Contract ownership

Evidence review accepts `approved_excerpt` on suitable decisions and requires `english_translation` for a Sinhala quote. It checks the normalized original text against the cited page. The original and translation are each limited to 500 characters. Admin `GET /api/v1/admin/knowledge/evaluation/scores/summary` reports readiness and current passes. `POST /api/v1/admin/knowledge/evaluation/scores/{case_id}` records a check. Farmer endpoints under `/api/v1/knowledge/chilli` list the available pilot questions, accept an allowlisted `case_id` at `POST /answer`, and return the permitted extracted page at `GET /{case_id}/sources/{version_id}/pages/{number}`. Translated results return the approved English wording as `answer` and the original quote as `citation.excerpt`. All answer and page reads check the current pilot release and review. There are no free-form outbound prompts or attached farm records.

The admin evaluation screen uses `GET /api/v1/admin/knowledge/evaluation` to list the ten questions and `GET /api/v1/admin/knowledge/evaluation/{case_id}` for the fixed English and Sinhala keywords, current published candidate pages and labels. `POST /api/v1/admin/knowledge/evaluation/{case_id}/decisions` accepts `expected_revision`, `outcome` and an optional `note`. Outcomes `suitable` and `out_of_scope` require the retrieved `version_id` and `page_number` from 1 to 100. `missing` takes neither field and is available when no current retrieved page is marked suitable. Stale edits and pages no longer in the eligible result set return 409. These routes require an active administrator and use no provider.

To remove an unpublished PDF, an active administrator calls `POST /api/v1/admin/knowledge/sources/{version_id}/discard` with its `expected_revision`; the API hides the version and retains its original. To delete a withdrawn PDF, call the same action route with `/delete`. This clears the original and extracted pages, keeps the version title/checksum and append-only lifecycle history, records status `deleted`, and hides the version from the source list. Existing evaluation decisions and approved excerpts remain. Deletion is atomic and only allowed for withdrawn PDFs. Deleted/discarded page and mutation routes return 404.

Synthetic knowledge sources use `GET /api/v1/admin/knowledge/sources?page=1` (20 rows per page), `POST` to the same path with `{"template":"chilli-demo"}`, and `POST /api/v1/admin/knowledge/sources/{version_id}/{action}` with `expected_revision`. Actions include `review`, `publish` and `withdraw`; only unpublished PDFs can be `discard`ed, and only withdrawn PDFs can be `delete`d. A stale revision or invalid transition returns 409. These routes require a live administrator and use browser write protections. Each transition commits its decision alongside the status change.

In development and test, `POST /api/v1/admin/knowledge/sources/pdf` accepts raw `application/pdf` (up to 6 MiB, 100 pages and 120,000 extracted characters) and returns 201 with `processing: "queued"`. The source list shows `queued`, `ready` or `failed` and a safe failure code. Deleted uploads disappear from that list. `GET /api/v1/admin/knowledge/sources/{version_id}/pages` returns numbered plain text pages for successful extraction. Recognized FM-Abhaya, FM-Ababld, FM-Emanee and FM-Samantha legacy-font runs are converted to Unicode before indexing; other font runs are preserved without conversion. This is not general OCR or validated support for every Sinhala PDF. Review and publication return 409 while processing is queued or failed. Originals have no download route. The endpoint rejects production uploads.

An active administrator can use `GET /api/v1/admin/knowledge/sources/search?q=keywords`. It accepts up to 160 characters and returns up to ten ranked published PDF pages with `title`, `version_id`, `checksum`, `number` and a plain text `excerpt`. All parsed terms must occur on the same page. An empty result means no eligible page matched.

`GET /api/v1/admin/knowledge/evaluation/{case_id}/draft-matches?version_id={uuid}` lets an active administrator search one processed draft PDF using the fixed question’s Sinhala keywords. It returns `keywords` and up to ten `pages` in the same page match shape, including PDF pages 21–100 when present. Unknown cases or versions that are unavailable as processed drafts return 404. This preview sends no provider requests and creates no decisions or scores.

In development and test, an active administrator can call `POST /api/v1/admin/knowledge/evaluation/{case_id}/draft-answer` with `version_id`, `page_number`, `excerpt` and `english_translation`. The page must still match the question in a processed draft. The app checks the input quote against that exact page and returns the supplied draft translation as `answer`, with the original quote in `citation.excerpt`. Both text inputs are capped at 500 characters. The preview saves no reviews or scores and uses no provider. The browser origin must be permitted.

Chilli questions uses `GET /api/v1/knowledge/chilli/research` for examples and `POST /api/v1/knowledge/chilli/research/ask` with `{question}` of 1–240 characters. Both require an active farmer. A supported question returns `kind: "research"`, `method: "reference" | "gemini"`, a versioned summary, and its `citation`. Study citations return `title`, `url`, `publisher`, `authors`, `year`, `journal_page`, `pdf_page` and `license_url`. Public crop-page citations return `title`, `url`, `publisher` and `section` with `method: "reference"`. Unmatched questions return `no_evidence`. For study answers, the server optionally sends the canonical question and fixed study summaries to Gemini, verifies the exact selection and falls back to the reference result when unavailable. Typed text, farm data and the three crop-page summaries stay local. The six provider attempts per farmer per hour use a separate rate limit. These routes are available independently of the farm guidance release flag.

`POST /api/v1/farms/{farm_id}/cultivations/{cultivation_id}/chilli-guidance` accepts a `topic` of `nursery-setup`, `irrigation-checks` or `soil-test` and uses the normal browser write-origin check. It returns a reference answer and citation where applicable, plus `confirmed_stage`, `soil_moisture` (optional value and observed timestamp), `missing` checks and `timezone`. Unsupported crop or district yields a null answer and citation with reasons. The endpoint uses the reported Anuradhapura district, a confirmed stage if recorded, and the latest structured soil moisture within 24 hours for irrigation. The response contains no free-text observations. Observation create, patch and history return the optional `soil_moisture` field (`dry`, `moist`, `waterlogged` or null). Explicit null clears the value on edit and preserves the prior revision.

`GET` and `PATCH /api/v1/farms/{farm_id}/weather-schedule` read and change a versioned farm-wide opt-in. The PATCH body contains `{enabled, expected_version}` and uses the normal browser write-origin check. A farm with no preference starts at version 0, disabled. Both responses return `enabled`, `version`, `can_enable` and `can_disable`. Only current owners can access the preference. The worker writes recipient-only `weather_review` notifications when the forecast qualifies for at least one pending task for that cultivation and date. The existing alerts and task review endpoints remain the path for date changes.

The local farmer demo uses `GET /api/v1/knowledge/chilli/demo` to list example questions. `POST /api/v1/knowledge/chilli/demo/ask` accepts a `question` of 1–240 characters. A match returns the exact fictional answer, its citation and the matched `case_id`. Unsupported wording returns `no_evidence`. `POST /api/v1/knowledge/chilli/demo/answer` also supports the original `case_id` request. `GET /api/v1/knowledge/chilli/demo/{case_id}/sources/{version_id}/pages/{number}` only serves the page mapped to that case. These routes require an active farmer in development or test. The demo uses a server-owned sample and sends no provider requests, saves no typed questions and creates no scoring or release records.

The reviewed localhost workflow uses `GET /api/v1/knowledge/chilli/local` for its examples, `POST /api/v1/knowledge/chilli/local/ask` with a `question` of 1–240 characters, and `GET /api/v1/knowledge/chilli/local/{case_id}/sources/{version_id}/pages/{number}` for citations. It matches the supported nursery, irrigation and fertilizer questions to current `suitable` reviews on published, processed sources. Answers use the approved English wording and cite the exact source quote. Sinhala quotes require an English translation. Unmatched or unsupported questions return `no_evidence`. A page is accessible only while its review and publication remain current. Development or test and an active farmer session are required. The workflow sends no provider requests and creates no review, score or release records.

An operator can configure one pinned `LOCAL_NURSERY_REFERENCE` for the nursery question and `LOCAL_CHILLI_REFERENCES` for the irrigation (`CH-04`) and fertilizer (`CH-05`) questions in the ignored root `.env`. Draft references are development-only. If no approved answer is available, the app can return a configured draft translation as `reference_only: true` after matching the version, checksum, page and quote. The citation serves only the pinned quote. The reference becomes unavailable if the source leaves the draft state or the quote fails verification.

The local admin can create the fictional PDF with `POST /api/v1/admin/knowledge/sources` and `{"template":"gemini-preview-pdf"}`. After extraction, review and publication, `POST /api/v1/admin/knowledge/sources/answer` accepts a fixed `question` ID of `nursery`, `records` or `forecast`. It returns `{"status":"no_evidence"}` or an `answered` response with the exact excerpt and its citation. The endpoint uses the ordinary browser write checks. Only published versions of the built-in fixture qualify for outbound calls. Missing credentials or provider failure returns 503. Invalid quotations or citation IDs return 502. Outbound attempts are limited to eight per administrator per fixed hour.

Administrator reporting follow-up (D30): `GET /api/v1/admin/overview` returns a count snapshot, and `GET /api/v1/admin/users/{user_id}/farm-summary` returns counts for a current non-removed farmer. Both require a live administrator and successful minimal report-view audit. They reveal counts only; existing private farm/child/history routes still deny administrators. [ADMIN_REPORTING.md](ADMIN_REPORTING.md) defines populations, role/archive/delete handling and the exact response fields. No migration or farm access privilege is added; schema stays `0007_support`.

Help/support follow-up (D29), 19 November 2026: public `GET /api/v1/help/contact` returns only the configured support email (nullable), without auth or database access. Farmer-owned `/api/v1/support/tickets` and admin `/api/v1/admin/support/tickets` provide lists/details, paginated messages, versioned replies and status transitions. Only submitted text is shared with administrators; support grants no farm/chat access or recovery bypass. Strict bodies, role/owner checks, rate limits, atomic message/event/notification writes, no-store/request IDs and no mutation replay apply. [SUPPORT.md](SUPPORT.md) owns fields, limits and routes; OpenAPI owns exact schemas. Generic `support_updated` notices contain no subject/message text and link to the farmer's support list.

Farm lifecycle follow-up (D28), 19 November 2026: `POST /api/v1/farms/{id}/restore` accepts `{expected_version}` and returns the restored FarmOut (200). It clears only the farm archive; independently archived cultivations stay archived. A current-version repeat on an active farm is a no-op; stale commands return 409.

`POST /api/v1/farms/{id}/delete` accepts `{expected_version, confirmation_name}` and returns `{id, deleted: true, message}` (200). It requires an owned archived farm and the current name. Active farms return 409 `ARCHIVE_REQUIRED`; a mismatched name returns 422 `CONFIRMATION_MISMATCH`. It deletes access from the workspace, retaining historical data in storage. Removed farms are excluded from all list statuses/search/counts, and all their farm/child/history/mutation/restore URLs return generic 404. No deleted-items or permanent-erasure endpoint is added. Both commands retain live owner/session checks, strict input allowlists, browser write protections, atomic revision/audit/marker writes, optimistic versions and no automatic browser replay.

Farmer UX follow-up, 19 November 2026: The `/` landing-page hero composes existing owner-only Farm Records reads for signed-in farmers; `/dashboard` only redirects farmers to `/`. District/village selection builds the existing `location` label, and explicit browser geolocation fills the optional coordinate pair before normal save. There is no new location/geocoding endpoint, structured district field, region-eligibility flag or guidance coverage claim. Existing owner, version, validation and atomic history/audit contracts still apply.

Use `/api/v1` for application routes. Once implemented, FastAPI-generated OpenAPI describes actual request/response schemas; this guide explains conventions, permissions and workflows. Keep routes, generated schemas, examples and tests consistent. Do not manually maintain a second complete schema in Markdown.

The server derives the actor from validated authentication. It does not trust client owner IDs. Farm lookups enforce owner scope; future sources/jobs must enforce ownership or assigned case scope too. Farm policy is 403 for excluded roles before lookup and uniform 404 for non-owned/missing records.

## UM1 implemented account contract

The identity/account route set, request boundaries, permission matrix and error outcomes are listed in [USER_MANAGEMENT.md](USER_MANAGEMENT.md) and generated OpenAPI. D19-D25 record implementation choices under the user's account and notification requests. Existing public liveness behaviour is unchanged; readiness now expects migration `0007_support` after FR-B.

Implemented routes include display-name-only `PATCH /me`, self-service `POST /me/password`, `GET /admin/users`, `GET /admin/users/{id}`, `PATCH /admin/users/{id}/role` or `/status`, and `DELETE /admin/users/{id}`, alongside register/login/refresh/logout/me. Public registration cannot select an elevated role. Registration returns the same generic 200 acknowledgement for new/existing email, without user ID/tokens; this is a privacy exception to normal 201 creation responses. Login/refresh return `access_token`, `token_type`, `expires_in` and a safe `user` projection, plus an HttpOnly refresh cookie. Logout is an idempotent 204 for valid browser-origin/header requests. Responses never include password hashes or raw refresh tokens in JSON.

`GET /admin/audit-logs` is administrator-only and accepts action, account search `q`, UTC calendar `from_date`/`to_date`, page and page_size. It returns audit action, actor/target IDs and current display names, changed values, recorded reason, request ID and timestamp; email and credentials are omitted. Each feed request appends an `audit_viewed` record with a fixed reason and no query/private values. `GET /notifications` returns only the current user's notices with `unread_count`, pagination and optional `unread_only=true`; `PATCH /notifications/{id}` accepts `{ "read": true|false }`. Non-owner notification IDs return 404. Notifications are created transactionally for active-user role changes, account re-enablement and self-service password changes. No email is sent.

Browser auth and other protected browser writes require an exact configured Origin plus `X-WagaMaga-Client: web`; endpoints with bodies require JSON. Missing/null/untrusted Origin is rejected. Swagger exposes the client header; use the normal HTTP bearer authorization scheme after obtaining an access token. CORS permits explicit origins and GET/POST/PATCH/DELETE with Content-Type/Authorization/client headers, without enabling cross-origin credential cookies. Normal browser calls go through the same-origin Vite proxy. Use one hostname throughout the session; future cross-origin hosting requires its own reviewed cookie/CORS/CSRF contract.

Registration and password-change new passwords are 8-128 characters with at least one Unicode letter, one decimal digit and one punctuation/symbol character. Uppercase is optional; whitespace/format characters do not satisfy the symbol requirement. Passwords are not trimmed or truncated. Invalid passwords return the existing safe 422 envelope with a password field location and no raw input. OpenAPI describes the length/composition; the field validator enforces composition. Login retains its existing 1-128 input bound and checks the stored hash without applying the signup composition rule, preserving access for existing accounts. The local first-administrator CLI reuses Register validation. `POST /me/password` requires the current password, rate-limits attempts, keeps the current session and revokes other active sessions.

All protected endpoints check the current session and account role/status in PostgreSQL. Own-account PATCH accepts only `display_name` and `expected_version`. Admin role/status PATCH accepts the respective checked value, a 3-300 character reason and expected_version; it blocks self-management, checks stale versions and atomically records the account change, revocation and audit. DELETE requires the same reason/version body and browser Origin/header protection. It scrubs email, display name and password hash, marks the row disabled/deleted, revokes sessions and writes audit in one transaction. UUID/tombstone and referenced history remain; ordinary lists hide removed accounts, while `status=deleted` returns scrubbed tombstones. Self-removal and loss of the final active administrator are blocked. Transactions commit before a success response. Re-enabling never reactivates revoked sessions. There are no public arbitrary-user, recovery or impersonation endpoints.

User lists accept `q` (up to 100 characters), `role`, `status=enabled|disabled|deleted`, `page` (1-10000) and `page_size` (default 20, maximum 100). Results contain `items`, `total`, `page`, `page_size`, ordered by created_at descending then ID. User projections contain id, email, display_name, role, disabled_at, deleted_at, version and created_at. Deleted projections contain only scrubbed account identity. No farm/chat context is included.

Account errors use 401 for absent/invalid/revoked authentication, 403 for non-admin access before target lookup, 404 for an absent target after authorization, 409 for stale/self/last-admin conflicts, safe 422 validation, 429 plus Retry-After for limits and 503 for unavailable/unconfigured identity. Private/token responses use no-store. Validation errors omit raw inputs/context; stack traces and tokens are not returned. Refresh replay revokes the family and clears the cookie; concurrent refresh can therefore invalidate the first winner's token. Clients serialize refresh, do not automatically retry an uncertain rotation and return to login when reauthentication is required.

## FR-C implemented Farm Records contract

The [Farm Records specification](FARM_RECORDS.md) lists all 21 implemented operations across 15 paths, including nested cultivation/observation CRUD, confirmation, archives, farm restore/workspace deletion and owner-only history. Generated OpenAPI defines exact schemas. There is no administrator farm endpoint, ownership transfer, physical-erasure or advisor-sharing route. Cultivation restore/deletion remains excluded.

FR-D consumes this unchanged contract. Its frontend routes start at `/farms`; observation history includes the farm/cultivation context in the UI URL while using the corresponding authorized API parent path. Farm writes use the shared session client with unauthorized replay disabled: 401 clears private UI state and requires sign-in, while GET retains existing serialized refresh. A 409 retains the draft until explicit reload; uncertain 0/503 creation never automatically retries. Areas stay strings, device-local observation entry converts to UTC, and unchanged observation time is sent exactly when editing only notes. These are client interaction rules, not substitutes for server authorization.

Every service checks a live enabled farmer and session, independently of route guards. Parent queries enforce `farms.farmer_id`; non-owned/missing IDs and mismatched parent chains return the same `404 RECORD_NOT_FOUND`. Advisors/administrators receive 403 before lookup. Revoked/expired sessions and disabled/removed accounts return 401. All domain responses, including errors, use no-store and request IDs. Body validation errors omit raw private values.

Collections use `{items,total,page,page_size}`, page 1-10000 and page_size default 20/max 100; unknown query parameters are rejected. Owner filtering precedes totals, pagination and literal search. Farm filters: q and status active/archived/all. Cultivations: effective parent archive status and crop_type_id. Observations: inclusive UTC from_date/to_date, ordered by observed_at descending/UUID ascending. Farm/cultivation order is created_at descending/UUID ascending; history is version descending. The crop catalogue lists supported entries only. Existing account/audit pagination is unchanged.

Writes reuse the exact Origin/client-header/JSON protections. Create returns 201; PATCH, confirmation and archive return 200. PATCH/commands require a strict positive integer expected_version; stale requests return `409 RECORD_VERSION_CONFLICT`. Archived parents block writes with `409 RECORD_ARCHIVED`, while reads/history remain available. Farm archive makes descendants effectively archived without rewriting their own archive timestamp. Repeating an explicit archive with the current version returns the stored entity without another effect; stale repeats conflict. Active-record no-op PATCH does not increment versions or add evidence.

Record changes, immutable revision and private audit event commit together under actor-user/session/farm/cultivation/observation locks. A waiting writer rechecks live state after acquiring those locks. Commit-time database failure returns safe 503, with no partial record/history or premature success. Manual create POSTs have no idempotency-key contract; after an uncertain response reload rather than automatically retrying. Stage confirmation body is `{ "expected_version": 1, "stage": "Farmer-reported seedling" }`; provenance is server-derived and crop/planting-date changes clear current confirmation while preserving history.

Required fields/lengths and precision are in FARM_RECORDS.md/OpenAPI. Coordinates/area accept decimal strings or JSON numbers and serialize as strings. Dates are ISO local dates; observation timestamps require an offset, normalize to UTC and cannot be future. Timezone must exist in PostgreSQL's timezone catalogue. Unsupported/missing crop assignment returns safe 422, not a foreign-key trace. Soil unknown/blank is null, and no stage estimate is generated. Farm/cultivation/observation detail responses include effective_archived; cultivations also include planned relative to the farm timezone. History returns typed snapshots, revision IDs/versions and editor/time, without account email/session data.

Example creation bodies, using the selected supported crop UUID from `GET /crop-types`:

```json
{ "name": "Synthetic farm", "location": "Synthetic location", "timezone": "Asia/Colombo", "area_value": "2.5", "area_unit": "ha" }
```

```json
{ "crop_type_id": "1e7402ea-35ab-4673-a8de-834c4bb70401", "planting_date": "2027-01-15", "area_value": "1.25", "area_unit": "ha", "soil_notes": null }
```

```json
{ "observed_at": "2026-11-01T08:00:00+05:30", "notes": "Synthetic observation; no agricultural recommendation" }
```

### Manual cultivation tasks

All paths are relative to `/api/v1/farms/{farm_id}/cultivations/{cultivation_id}/tasks`. Only the current farmer owner can read tasks and task history or write changes. The full parent path must match. Archived parents allow reads and block writes. Workspace-deleted farms return the same 404 as missing or foreign records.

| Method and path | Contract |
| --- | --- |
| GET collection | Paginated tasks ordered by due date and UUID, plus the farm-local `farm_today` date. `status=pending\|completed\|cancelled\|all` defaults to pending. |
| POST collection | Create a pending task with `{title, due_date}` and return 201. Title is trimmed and limited to 120 characters. Due date is an ISO calendar date. |
| PATCH `/{task_id}` | Save both title and due date on a pending task with `{title, due_date, expected_version}`. An unchanged edit is a no-op. |
| POST `/{task_id}/status` | Complete or cancel a pending task with `{status, expected_version}`. The new status is final. |
| GET `/history` | Paginated immutable task events for this cultivation, newest first. Each event includes the task ID, version, title, due date, action and timestamp. |

Writes use the Farm Records origin and session checks. Stale versions, archived parents and changes to terminal tasks return 409. A successful mutation and its private history event commit together. On an uncertain create response, reload the list before retrying.

### Suggested task plan demo

All paths are relative to `/api/v1/farms/{farm_id}/cultivations/{cultivation_id}/task-plans`. They use the same owner, archive, workspace deletion and browser write rules as manual tasks.

| Method and path | Contract |
| --- | --- |
| GET collection | Read the newest plan as `{plan}`, or `{plan: null}` before the first review. |
| POST collection | Supply `{}` to save or retrieve a pending example. The server chooses the task and date, saves the sample evidence and context, and returns the plan. |
| POST `/{plan_id}/decision` | Send `Idempotency-Key` equal to the plan ID and `{expected_version, action_hash, outcome}`. Outcome is `accepted` or `rejected`. The response includes the saved outcome, decision time and task ID when accepted. |
| GET `/history` | Paginated accepted and rejected decisions with the saved title, due date and evidence. |

Acceptance adds the exact persisted task. The server rechecks the current parent versions, plan expiry, fixture eligibility, action hash, seven day date bound and any matching pending task. A conflicting submission returns 409. The plan ID is also the unique receipt key. A matching retry returns the original decision and task ID. The task, task history and decision commit together. The demo action is a fixed recordkeeping example and carries no agronomic recommendation or advisor requirement.

### Demo weather

`GET /api/v1/farms/{farm_id}/cultivations/{cultivation_id}/demo-weather` returns the built-in `sample-rain-v1` fixture to the current farmer owner. The response includes `source: "fixture"`, `fixture_version`, the farm's saved `location` and `timezone`, `forecast_date`, `condition`, `rainfall_mm` and `review_due_on`. The sample date is tomorrow in the farm timezone. Archived records return a null review date. Foreign, mismatched or workspace-deleted records return 404.

The UI offers task review for pending tasks whose due date matches `review_due_on`. The GET only reads data. Changing a task still uses the existing manual task PATCH contract.

### Live farm forecast

The current farmer owner reads `GET /api/v1/farms/{farm_id}/cultivations/{cultivation_id}/weather`. This reads the cache and never contacts a provider. The response has `status` (`needs_coordinates`, `unfetched`, `fresh`, `stale` or `provider_disabled`), `location`, `timezone`, `checked_at`, `can_refresh` and a nullable `forecast`. A forecast includes the provider, `fetched_at`, `fresh_until` and local dates with daily minimum and maximum in °C and expected precipitation in mm. Precipitation includes any liquid or frozen precipitation in the provider total.

`POST /weather/refresh` under the same cultivation accepts `{}` with the normal browser write checks. It requires active parents and saved coordinates. It reuses a matching forecast fetched less than 30 minutes ago. Otherwise it requests three dates from Open-Meteo, sends only the saved coordinates rounded to two decimals and the farm timezone, and saves the normalized forecast after rechecking access, location and date. Provider failure returns 503 and preserves the last forecast. Archived records can read existing forecasts. Foreign, mismatched or workspace-deleted records return 404.

### Weather alerts and task date review

These owner-only routes are relative to `/api/v1/farms/{farm_id}/cultivations/{cultivation_id}/weather/alerts`.

| Method and path | Contract |
| --- | --- |
| GET collection | Paginated current alerts for pending tasks, plus the threshold and its version, edit access and forecast freshness. |
| PATCH `/rule` | `{threshold_mm, expected_version}` with a whole number from 1 to 1000 mm or null to turn off alerts. Use version 0 for the first save. |
| POST `/tasks/{task_id}/reschedule` | `{proposed_due_date, expected_version, expected_rule_version, expected_forecast_fetched_at}`. Creates a review showing the saved task date, selected date and forecast evidence. |
| POST `/reschedules/{plan_id}/decision` | Send `Idempotency-Key` equal to the plan ID and `{expected_version, action_hash, outcome}`. Acceptance changes the date. Rejection records the decision with no task change. |

Refresh, setting changes and relevant task writes update the alert keyed by task and due date. A date review requires a fresh qualifying alert and a different farm-local date within seven days. Acceptance rechecks the latest review, exact action hash, task and parent versions, forecast freshness and threshold. Changed evidence or a superseded review returns 409. The task revision and execution receipt commit together. Identical decision retries return the original receipt. `GET /task-plans/history` includes the original and proposed dates for these decisions.

### Missed tasks

From the owned cultivation route, `POST /tasks/{task_id}/missed-review` takes `{expected_version, proposed_due_date, reason?}` for a pending task whose due date precedes `farm_today`. The optional reason is limited to 240 characters and retained with private plan evidence. The date must be between today and seven days from today on the farm calendar. The response has the review ID, version, action hash, original and proposed dates, evidence text, expiry and nullable `forecast_fetched_at`. It uses a matching current saved forecast when available.

`POST /task-plans/missed-reviews/{plan_id}/decision` accepts the same decision body and `Idempotency-Key` as the weather review. The farmer's decision binds to the exact current review. Changed task, parent or forecast evidence and superseded or expired reviews return 409. Acceptance commits the date, task revision and decision atomically. Keeping the date adds only a decision. Both appear in `/task-plans/history`.

### Weekly planner and assigned review

All cultivation paths below are relative to `/api/v1/farms/{farm_id}/cultivations/{cultivation_id}`. The server supplies the farm-local week start and end, including today and six following days.

| Route | Contract |
| --- | --- |
| `GET /week` | Paged overdue pending and in-week tasks with available forecast amounts and threshold alerts. |
| `GET /tasks?task_id={id}&status=all` | Opens the matching task within the same owned cultivation. |
| `GET /tasks/{id}/weekly-suggestion` | Latest persisted weekly suggestion for the task, or `plan: null`. |
| `POST /tasks/{id}/weekly-suggestion` | Accepts `{expected_version}`. Uses current qualifying weather and the earliest later forecast day below the saved threshold. Persists one date change for review. |
| `POST /task-plans/weekly/{id}/advisor` | Explicitly shares the suggestion with the active advisor identified by `advisor_email`. Send the plan's `expected_version` and `action_hash`. |
| `POST /task-plans/weekly/{id}/advisor/revoke` | Revokes access for this plan and assignment. Send the exact version and hash. |
| `POST /task-plans/weekly/{id}/revise` | Send the returned plan's version and hash plus `proposed_due_date`. Creates one linked revision for a different supported date and sends it to the same active advisor. Identical retries return that revision. |
| `POST /task-plans/weekly/{id}/decision` | Sends version, hash, outcome and `Idempotency-Key` equal to the plan ID. Unconfirmed stage or a referral requires active, assigned clearance for acceptance. Keeping the current date records the farmer decision. |
| `GET /task-plans/weekly-batch` and `/history` | Paged combined suggestions and a history of saved versions with advisor outcomes. |
| `POST /task-plans/weekly-batch/prepare` | Uses an empty body to prepare up to 20 candidate tasks from current forecast evidence. |
| `POST /task-plans/weekly-batch/accept` | Accepts `changes`, an array of up to 20 `{plan_id, expected_version, action_hash}` selections. Returns receipts. Duplicate tasks and stale or uncleared selections fail the transaction. Identical retries reuse the saved action receipts. |

`GET /api/v1/advisor/cases` returns current assigned, non-revoked case snapshots with task title, date comparison, confirmed stage and forecast figures. `POST /api/v1/advisor/cases/{plan_id}/decision` accepts version, hash, `outcome` (`cleared`, `declined`, `changes_requested`), and a reason up to 500 characters. Decisions are immutable and repeating the same decision returns its receipt while the case is accessible. The advisor cannot update the farm or task. All writes use the existing browser origin check. Changed evidence, superseded versions and closed access prevent execution. Farmer plan history includes a recorded advisor decision when present.

Review assignment, resubmission and first advisor decision each record a generic recipient update of type `advisor_review`. The `review_plan_id` on these notices opens `GET /api/v1/plan-reviews/{id}`. Farmers can open their own saved versions. Advisors can open current assigned cases. The link checks access on every request and exposes no farm details from the notification itself.

### Cultivation diary and task reminders

- `GET /api/v1/farms/{farm_id}/cultivations/{cultivation_id}/diary` returns the standard paginated result, newest first. Entries include an observation, task completion or cancellation, or executed plan action, with its timestamp and applicable due dates. Access follows cultivation history ownership and lifecycle rules.
- The existing notifications list includes recipient-owned `task_due` and `task_overdue` notices. The list, unread count and read-state changes all exclude notices that no longer match an active task, date or reminder type.

## Other route groups and future scope

Paths below are relative to `/api/v1`. Identity, farms/cultivations/observations and notifications are implemented as above. Remaining groups are representative future contracts, finalized with their own slice.

| Group | Representative routes | Scope |
| --- | --- | --- |
| Identity | `POST /auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`; `GET /me` | Farmer registration; admin-controlled elevated roles |
| Farms | `GET/POST /farms`; `GET/PATCH /farms/{id}`; `POST /farms/{id}/archive` | Owning farmer |
| Cultivations/observations | Analogous owner-scoped routes under their parent context | Validate parent ownership; retain required history |
| Tasks | `GET/POST /cultivations/{id}/tasks`; `PATCH /tasks/{id}`; `POST /tasks/{id}/complete`, `/cancel` | Owning farmer; version checks |
| Knowledge | `POST /knowledge/documents`; `GET /knowledge/documents/{id}/versions`; `POST /knowledge/versions/{id}/publish`, `/withdraw` | Authorized knowledge management/review |
| Sources | `GET /sources/{passage_id}` | Authorized source viewer; version and withdrawal labels |
| Advisory | `POST /conversations`; `POST /conversations/{id}/messages`; `GET/DELETE /conversations/{id}` | Owner; retention restrictions on deletion |
| Proposals | `POST /cultivations/{id}/proposals`; `GET /proposals/{id}/versions/{version}`; `POST .../revise`, `.../accept`, `.../reject` | Owner; exact version/hash and review policy |
| Advisor | `POST /cases`; `GET /advisor/cases`; `POST /cases/{id}/decisions` | Farmer submission; assigned advisor decisions |
| Weather/jobs | `GET /farms/{id}/weather`; `POST /cultivations/{id}/weather-review`; `GET /jobs/{id}` | Authorized farm/case context; fixture injection local/test only |
| Notifications | `GET /notifications`; `PATCH /notifications/{id}` | Recipient only |

## Request and response conventions

- Use UUID identifiers, UTC event timestamps and explicit local dates/timezones for scheduling.
- Bound pagination and filtering for collections. Exact parameter names, defaults and response envelope remain D12.
- Mutations carry the relevant expected entity/proposal version. Return 409 for stale task/proposal conflicts.
- Return 201 for creation and 202 with a job reference/status URL for queued work.
- Use 400/422 consistently for invalid requests, 401 for absent/invalid authentication, the chosen 403/404 policy for inaccessible objects, and 429 for rate limiting.
- Define a recoverable provider-error response without exposing provider secrets or internal traces.

Planned error shape; field details are illustrative:

```json
{
  "code": "TASK_VERSION_CONFLICT",
  "message": "The task changed. Review a revised proposal.",
  "request_id": "example-request-id",
  "field_errors": [],
  "retryable": false
}
```

Here `retryable: false` means repeating the unchanged request will not solve the conflict. A revised proposal requires new review and acceptance.

## Proposal commands and idempotency

Acceptance references the proposal version and action hash. The server loads persisted actions, verifies required decisions, checks expiry/evidence/context and applies a validated transaction. Clients do not send executable SQL or replacement action lists to the acceptance endpoint. Decide whether acceptance executes synchronously or queues a durable execution step and document that response explicitly.

Mutating approval commands accept `Idempotency-Key`. Persist the request payload hash and response; the same key with a different payload is rejected. Successful repeats return the stored result. Database execution uniqueness remains the final protection against duplicates, including requests using different HTTP keys.

## Swagger and API verification

FastAPI normally exposes Swagger UI at `/docs`, alternative documentation at `/redoc` and OpenAPI at `/openapi.json`. Those documentation paths are separate from the `/api/v1` business prefix unless configured otherwise. They become available after scaffolding; deployment exposure requires an explicit access policy.

For each implemented endpoint:

1. Open Swagger and inspect the schema and declared responses.
2. Authenticate using the configured mechanism; do not assume an OAuth password-flow button unless that scheme is actually configured.
3. Try a valid request, invalid input, missing authentication and another user's object ID using synthetic accounts.
4. Check status, response and persisted effects.
5. Automate those behaviours with pytest/API and PostgreSQL integration tests.

Swagger is manual exploration. Postman is optional; maintaining both is unnecessary initially. Neither replaces transaction, permission or regression tests.

See [FastAPI API documentation](https://fastapi.tiangolo.com/tutorial/first-steps/), [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/) and [TESTING.md](TESTING.md).

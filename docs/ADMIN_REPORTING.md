# Administrator count reporting

Status: explicitly authorized 19 November 2026 after Help/support. This adds Admin Overview and count summaries on farmer account pages. It does not add an administrator farm directory, private farm viewing, maps, observation/chat access, task control, exports or usage tracking. [DECISIONS.md](DECISIONS.md), D30, records the permission extension; [TESTING.md](TESTING.md) records verified local results. Schema remains `0007_support` with no migration or dependency change.

## Scope and permissions

- Active administrators may read platform aggregate counts and per-current-farmer farm/cultivation counts through dedicated reporting endpoints. Counts reveal activity metadata and are an explicit reporting permission, not anonymous data or general farm access.
- Farmers/advisors/anonymous callers cannot use these endpoints, including for their own IDs. Services independently recheck current administrator/session status under locks before reading.
- Existing `/farms`, cultivation, observation and history routes still reject administrators. Reports expose no farm/cultivation IDs, names, locations, coordinates, areas, field notes, support subjects/messages or private conversations.
- Farmer account pages retain the existing minimal account fields and add counts only. Removed/non-farmer target accounts return generic 404 for the summary endpoint; the screen hides the summary for those account states.
- Every successful report view appends a minimal `report_viewed` account-audit event with actor/target, report kind, time/request ID and a fixed reason. It records no counts, farm IDs or record text. If the audit cannot commit, the report does not return success.

Existing SRS FR02/FR03 server identity/permissions and DR01/DR03 integrity/provenance still apply. This explicitly narrows the administrator exception to count metadata; FR04 advisor case access and all private farm ownership rules remain unchanged. Real-user reporting/retention notices remain operating work before a pilot.

## Count definitions

| Group | Definition |
| --- | --- |
| Current accounts | All users without deleted_at, including disabled accounts. Role counts use current roles and sum to this total. |
| Enabled / disabled accounts | Non-removed accounts split by disabled_at. Enabled means access is allowed, not recent use or activity. |
| Removed accounts | User tombstones with deleted_at, shown separately and excluded from current/role/signup counts. |
| New farmer accounts, 30 days | Non-removed current farmer accounts created between statement time minus 30 days and statement time, inclusive, in UTC. No future dates or former-farmer accounts. |
| Farms | Non-workspace-deleted farms belonging to non-removed accounts whose current role is farmer, including disabled farmers. Active/archived splits use the farm's archive timestamp. Former-farmer and removed owners' retained records are excluded. |
| Cultivations | Cultivations under those same farms. Active requires both cultivation and farm unarchived; archived means either is archived. Workspace-deleted farm children are excluded. |
| Support | All retained submitted requests split by Open, In progress and Resolved, including requests whose owner is unavailable. Pending review is Open + In progress. |

Global and per-farmer definitions match. Each response computes all its count groups in a single PostgreSQL statement/statement snapshot using aggregate CTEs and emits a generated_at timestamp. This avoids mixed totals when records change concurrently. It does not claim live analytics, farmer presence, agronomic activity or a verified location. No region reports are built from free-text location labels.

## API and audit

Both routes are relative to `/api/v1`, use current active administrator authentication and return no-store/request-ID headers:

- `GET /admin/overview`: `{generated_at, accounts, farms, cultivations, support}`. Account metrics are total/enabled/disabled/farmers/advisors/administrators/new_farmers_30_days/removed; farm/cultivation metrics are total/active/archived; support metrics are total/open/in_progress/resolved.
- `GET /admin/users/{user_id}/farm-summary`: `{user_id, generated_at, farms, cultivations}` with the same record-count shapes. Target must currently be a non-removed farmer; disabled farmers are supported.

Read services lock only the current administrator user/session for authorization, read aggregate counts and append audit in the HTTP-owned transaction. No farm row mutation, ownership reassignment, history rewrite, privilege expansion or new table is introduced. Audit action filtering now accepts `report_viewed`; UI labels it Count summary viewed. The shared app DB role still has no row-level-security guarantee; every report and private-record route must enforce its own distinct contract.

Use 401 for invalid/revoked sessions, 403 for excluded roles, 404 for missing/non-farmer/removed summary targets, 422 for malformed IDs and safe 503 if storage/audit fails. No private values, SQL or guessed zero totals appear on failure. Ordinary report refresh is a read, not a farming operation.

## Interface

Admin login and visits to login with an active admin session now open `/admin/overview`. Farmers still return to `/`, and advisors to `/account`. Admin Overview is reachable from the account navigation and the signed-in administrator website header. It shows four highlights (farmers, farms, cultivations, pending support), account-state/role counts, detailed record splits, support statuses and the snapshot time. Links go to the existing farmer/user management and support inbox; count cards do not open private farms.

Farmer account detail shows Farm record summary with farm/cultivation totals/splits and an explicit privacy note. It reloads when the target/version changes. Shared request-state handling ignores late responses after route/principal changes, clears unavailable/stale totals during refresh, and displays real zero only after a successful count response. Loading, retry, denial and session expiry are explicit. The cream/sage/forest theme and responsive layout remain; no fabricated charts or metrics are added.

Local setup/check commands remain in [DEVELOPMENT.md](DEVELOPMENT.md) and [TESTING.md](TESTING.md). No new configuration is required. Farmer-facing Help/support remains separate under [SUPPORT.md](SUPPORT.md). Remote CI, real-user operating policies, knowledge management, advisor cases, weather and AI remain pending.

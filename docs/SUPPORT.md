# Help and website support

Status: authorized 19 November 2026 after the user requested a farmer help channel and admin improvements. This is a bounded Help/support-request/admin-inbox slice, not Admin Overview, broad farm reporting, account recovery or advisor case implementation. D29 in [DECISIONS.md](DECISIONS.md) records the decisions; [TESTING.md](TESTING.md) records actual local evidence. Keep synthetic local data until real-user retention, contact and operating policies are ready.

## Requirements and access

| ID | Accepted behaviour |
| --- | --- |
| SUP01 | Public Help explains farm setup, optional coordinates, archive/restore/workspace deletion, conflicts, privacy and the limits of website support. Reach it from website navigation, the account menu and login. |
| SUP02 | An active farmer explicitly submits category, subject and message; the server supplies the requester, role, IDs, status and timestamps. No farm IDs, observations, coordinates, credentials or AI-chat context are automatically attached. |
| SUP03 | Farmers list/read/reply to their own requests only. Another owner's/missing ticket or message collection returns uniform 404. Advisors cannot use farmer or admin support APIs. |
| SUP04 | Active administrators list/read submitted support conversations and reply/change status. This permission gives no farm, cultivation, observation, AI-chat or impersonation access. |
| SUP05 | Statuses are Open, In progress and Resolved. Farmers can resolve and reopen a resolved request; only support can mark In progress or reset an in-progress request to Open. Replies to resolved requests require explicit reopening. |
| SUP06 | Replies/status changes require expected_version. Each actual mutation atomically advances version/time and appends an immutable event; replies also append an immutable message. Concurrent stale actions have one winner. Current-version unchanged status is a no-op. |
| SUP07 | Admin replies/status changes create generic recipient-owned in-app notices for an available farmer. Subject, message body, farm data and employee details are absent from notification text. No email delivery or live chat is added. |
| SUP08 | Support creation/replies/status actions have per-actor rate limits and existing browser Origin/header/JSON protections. Failures preserve private drafts, block uncertain/stale replay and require explicit review. Messages render as plain text and are never executed. |
| SUP09 | Public Help displays only the configured, validated SUPPORT_CONTACT_EMAIL. When absent/unreachable it says so. Reading contact details needs no auth or database. There is no invented contact address, password-reset action or recovery bypass. |

SUP identifiers are local feature acceptance IDs, not replacements for SRS numbering. Existing FR01-FR03 identity/ownership, DR01/DR03 integrity/provenance and DR04 privacy/retention constraints continue to apply. Advisor case sharing under FR04 remains separate and unimplemented.

## Data and services

Migration `0007_support` creates:

- `support_tickets`: immutable ID/requester/category/subject/creation time, status, positive version and UTC update time; owner/update and status/update indexes.
- `support_messages`: ticket, server-derived author/role at send time, bounded body, ticket version and UTC time. Unique ticket/version. No edit or delete operation.
- `support_events`: ticket, actor, operation (created/replied/status_changed), previous/current status, ticket version, request ID/time. Unique ticket/version; no free-text message payload.

The app has SELECT/INSERT/UPDATE on tickets and SELECT/INSERT on messages/events. Restricted FKs and an identity trigger preserve context; no app DELETE/TRUNCATE, message/event rewrites or ownership reassignment. Notification constraints/types now allow `support_updated`. Downgrade refuses while tickets or support notices exist, rather than silently destroying evidence. This does not define retention periods or permanent erasure.

Routes handle HTTP/DTOs; support services independently enforce live role and ticket access. Farmer writes lock actor user → current session → ticket. Admin writes lock actor user → current session → requester user → ticket. Requester-before-ticket ordering serializes owner replies and account disablement without taking the ticket before the requester. An unavailable/deleted/former-farmer requester cannot receive replies; administrators can still resolve the ticket without sending a notification. HTTP transactions commit before a success response; message/event/notification failures roll back together. Account administration audit views never contain support bodies.

No source, farm, provider, upload, worker, email or external support integration is introduced. Support staff see the submitted conversation, not an automatic farm summary. Keep private text out of logs, public retrieval, account audit and notification content. The shared app database role is not PostgreSQL row-level security; services remain authoritative.

## API

Paths are relative to `/api/v1`. Public `GET /help/contact` returns `{email: string|null}`. All ticket routes require a current session.

| Actor | Routes |
| --- | --- |
| Farmer | GET/POST `/support/tickets`; GET `/support/tickets/{id}`; GET/POST `/support/tickets/{id}/messages`; POST `/support/tickets/{id}/status` |
| Administrator | GET `/admin/support/tickets`; GET `/admin/support/tickets/{id}`; GET/POST `/admin/support/tickets/{id}/messages`; POST `/admin/support/tickets/{id}/status` |

Creation accepts category (account/farm_records/technical/feedback), trimmed subject 1–120 and body 1–4000 characters. Reply accepts body and positive expected_version. Status accepts the three supported states and expected_version. Extra properties are rejected. Lists support status/category, bounded page 1–10000 and page_size 1–100 (default 20); ownership precedes filters/counts. Messages return newest version first with pagination, displayed chronologically within each page. Ticket projections include current requester name/availability, not email or private farm data; message projections omit author IDs and employee details.

Creation is limited to 5 attempts per actor/hour; replies 30 and status changes 60. Existing PostgreSQL HMAC-keyed rate-limit storage records no message text. 401 denotes invalid/revoked sessions; 403 excluded roles/actions; uniform 404 unavailable tickets; 409 stale, resolved, unavailable requester or unsupported owner transition; 422 invalid input; 429 rate limiting; 503 unavailable storage. Errors retain no-store and request IDs. Mutations never automatically replay after 401 or an uncertain response. Creation has no idempotency-key contract: review saved requests after connection loss.

## Screens and operation

Public `/help` restores session-aware navigation but keeps FAQs and contact available when signed out or the database is unavailable. `SUPPORT_CONTACT_EMAIL` is optional, public and operator-configured through the existing environment; it sends no email. Do not put an unmonitored placeholder into the live configuration. Without it, login help explicitly says the public contact channel is not configured; a monitored contact and recovery policy remain required operating decisions before real farmers are invited.

Farmer `/support`, `/support/new` and `/support/{id}` provide filters, submission, private conversation, replies, resolve/reopen, loading/empty/error and explicit draft-discard refresh. Admin `/admin/support` and `/admin/support/{id}` expose the same submitted conversations plus support status actions. Busy/draft coordination prevents a status change or refresh from silently discarding a reply. Notification links lead to My support requests. Login/help does not offer a nonfunctional reset link. The current shared cream/sage/forest theme and website-first landing entry remain.

Run the migration/start/check commands in [DEVELOPMENT.md](DEVELOPMENT.md) and [TESTING.md](TESTING.md). API/worker readiness expects `0007_support`. No default accounts or support tickets are seeded in development. All verification uses synthetic local data. Admin Overview and limited count metadata are a separate implemented follow-up in [ADMIN_REPORTING.md](ADMIN_REPORTING.md). Knowledge management, attachments, real-time chat, advisor support and remote CI remain pending.

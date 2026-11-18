# API guide

Status: M0 health, UM1 identity/account, administrator audit history and recipient-scoped in-app notification endpoints are implemented locally. Farming/advisory/planning routes remain planned. `GET /health/live` returns 200 for process liveness; `/health/ready` returns 200 only when PostgreSQL, pgvector and `0004_in_app_notifications` are ready, otherwise 503. These public operational routes are outside `/api/v1`. OpenAPI/Swagger are available in development/test and disabled by default in production configuration.

## Contract ownership

Use `/api/v1` for application routes. Once implemented, FastAPI-generated OpenAPI describes actual request/response schemas; this guide explains conventions, permissions and workflows. Keep routes, generated schemas, examples and tests consistent. Do not manually maintain a second complete schema in Markdown.

The server derives the actor from validated authentication. It does not trust client owner IDs. Every protected object lookup checks ownership or assigned case scope, including sources and job status. Define a consistent 403/404 policy before the first domain API.

## UM1 implemented account contract

The identity/account route set, request boundaries, permission matrix and error outcomes are listed in [USER_MANAGEMENT.md](USER_MANAGEMENT.md) and generated OpenAPI. D19-D25 record implementation choices under the user's account and notification requests. Existing public liveness behaviour is unchanged; readiness now expects migration `0004_in_app_notifications`.

Implemented routes include display-name-only `PATCH /me`, self-service `POST /me/password`, `GET /admin/users`, `GET /admin/users/{id}`, `PATCH /admin/users/{id}/role` or `/status`, and `DELETE /admin/users/{id}`, alongside register/login/refresh/logout/me. Public registration cannot select an elevated role. Registration returns the same generic 200 acknowledgement for new/existing email, without user ID/tokens; this is a privacy exception to normal 201 creation responses. Login/refresh return `access_token`, `token_type`, `expires_in` and a safe `user` projection, plus an HttpOnly refresh cookie. Logout is an idempotent 204 for valid browser-origin/header requests. Responses never include password hashes or raw refresh tokens in JSON.

`GET /admin/audit-logs` is administrator-only and accepts action, account search `q`, UTC calendar `from_date`/`to_date`, page and page_size. It returns audit action, actor/target IDs and current display names, changed values, recorded reason, request ID and timestamp; email and credentials are omitted. Each feed request appends an `audit_viewed` record with a fixed reason and no query/private values. `GET /notifications` returns only the current user's notices with `unread_count`, pagination and optional `unread_only=true`; `PATCH /notifications/{id}` accepts `{ "read": true|false }`. Non-owner notification IDs return 404. Notifications are created transactionally for active-user role changes, account re-enablement and self-service password changes. No email is sent.

Browser auth and other protected browser writes require an exact configured Origin plus `X-WagaMaga-Client: web`; endpoints with bodies require JSON. Missing/null/untrusted Origin is rejected. Swagger exposes the client header; use the normal HTTP bearer authorization scheme after obtaining an access token. CORS permits explicit origins and GET/POST/PATCH/DELETE with Content-Type/Authorization/client headers, without enabling cross-origin credential cookies. Normal browser calls go through the same-origin Vite proxy. Use one hostname throughout the session; future cross-origin hosting requires its own reviewed cookie/CORS/CSRF contract.

Registration and password-change new passwords are 8-128 characters with at least one Unicode letter, one decimal digit and one punctuation/symbol character. Uppercase is optional; whitespace/format characters do not satisfy the symbol requirement. Passwords are not trimmed or truncated. Invalid passwords return the existing safe 422 envelope with a password field location and no raw input. OpenAPI describes the length/composition; the field validator enforces composition. Login retains its existing 1-128 input bound and checks the stored hash without applying the signup composition rule, preserving access for existing accounts. The local first-administrator CLI reuses Register validation. `POST /me/password` requires the current password, rate-limits attempts, keeps the current session and revokes other active sessions.

All protected endpoints check the current session and account role/status in PostgreSQL. Own-account PATCH accepts only `display_name` and `expected_version`. Admin role/status PATCH accepts the respective checked value, a 3-300 character reason and expected_version; it blocks self-management, checks stale versions and atomically records the account change, revocation and audit. DELETE requires the same reason/version body and browser Origin/header protection. It scrubs email, display name and password hash, marks the row disabled/deleted, revokes sessions and writes audit in one transaction. UUID/tombstone and referenced history remain; ordinary lists hide removed accounts, while `status=deleted` returns scrubbed tombstones. Self-removal and loss of the final active administrator are blocked. Transactions commit before a success response. Re-enabling never reactivates revoked sessions. There are no public arbitrary-user, recovery or impersonation endpoints.

User lists accept `q` (up to 100 characters), `role`, `status=enabled|disabled|deleted`, `page` (1-10000) and `page_size` (default 20, maximum 100). Results contain `items`, `total`, `page`, `page_size`, ordered by created_at descending then ID. User projections contain id, email, display_name, role, disabled_at, deleted_at, version and created_at. Deleted projections contain only scrubbed account identity. No farm/chat context is included.

Account errors use 401 for absent/invalid/revoked authentication, 403 for non-admin access before target lookup, 404 for an absent target after authorization, 409 for stale/self/last-admin conflicts, safe 422 validation, 429 plus Retry-After for limits and 503 for unavailable/unconfigured identity. Private/token responses use no-store. Validation errors omit raw inputs/context; stack traces and tokens are not returned. Refresh replay revokes the family and clears the cookie; concurrent refresh can therefore invalidate the first winner's token. Clients serialize refresh, do not automatically retry an uncertain rotation and return to login when reauthentication is required.

## Planned route groups

Paths below are relative to `/api/v1`. Identity is implemented as above; the other groups remain representative planned contracts. Exact schemas and omitted CRUD details are finalized when their slice is built.

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

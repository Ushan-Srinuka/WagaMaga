# API guide

Status: M0 health endpoints are implemented; business contracts below remain planned from architecture section 8. `GET /health/live` returns 200 for process liveness. `GET /health/ready` returns 200 only when the configured PostgreSQL database, pgvector and Alembic revision are ready, otherwise 503. These public local operational routes are outside `/api/v1`; no identity/farm/advisory/planning endpoints exist yet. OpenAPI/Swagger are available in development/test and disabled by default in production configuration.

## Contract ownership

Use `/api/v1` for application routes. Once implemented, FastAPI-generated OpenAPI describes actual request/response schemas; this guide explains conventions, permissions and workflows. Keep routes, generated schemas, examples and tests consistent. Do not manually maintain a second complete schema in Markdown.

The server derives the actor from validated authentication. It does not trust client owner IDs. Every protected object lookup checks ownership or assigned case scope, including sources and job status. Define a consistent 403/404 policy before the first domain API.

## Planned route groups

Paths below are relative to `/api/v1`. The architecture uses representative contracts; exact schemas and omitted CRUD details are finalized when their slice is built.

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

# UM1: user management plan

Status: UM1 implemented locally, with account-removal, password-change, audit-history and in-app notification follow-up through 18 November 2026. M0 remains complete. D19-D25 in [DECISIONS.md](DECISIONS.md) record the implementation choices. Tests and remaining remote CI/real-user limits are recorded in TESTING.md.

## Outcome and scope

A farmer can register, sign in, see and edit their display name, change their password, and sign out. An administrator can find accounts, inspect account details, change roles, disable/re-enable accounts and permanently remove accounts. Advisors can sign in and manage their own display name and password; their case workflow comes later. All roles use the same login page. Public registration creates farmers only.

The milestone establishes a reusable React application shell, accessible forms, consistent errors and backend identity boundaries. It does not claim full product authorization: farm ownership and advisor assignment must accompany their later domain endpoints.

Included: local synthetic accounts, sessions and revocation, protected account endpoints, administrator account actions and audit viewer, recipient-scoped in-app account notifications, minimal anti-abuse controls, responsive screens and relevant tests. The administrator audit feed can filter actions, actor/account and UTC dates; reading it is recorded. It excludes general server logs and email addresses. Administrator removal scrubs account email/name and credentials, disables the account and retains its tombstone and audit references; it cannot be undone in the UI. It does not delete dependent farm/chat evidence in future modules. Users can change their own password after supplying the current password; other sessions are revoked, while the current session stays active. Notifications are generated for account role changes, account re-enablement and self-service password changes; recipients can list/filter and mark them read/unread. Excluded: farms, cultivation, documents, AI, proposals, weather, advisor case sharing, public deployment, social login, MFA, email delivery/alerts, avatars, administrator impersonation, password recovery and email verification. Recovery and email verification need separate decisions before external users; do not display working-looking links for absent functionality.

## Requirement mapping

| Baseline | UM1 responsibility | Boundary |
| --- | --- | --- |
| FR01 | Farmer registration, authentication, logout and administrator-only role assignment | First administrator is bootstrapped outside HTTP |
| FR02 | Own-account access; administrator-only account administration | Farm/chat/source/job object checks remain unimplemented until those routes exist |
| FR03 | Signature, issuer, audience and expiry validation; session revocation; generic authentication failures | Do not infer current privileges from stale token role claims |
| FR04 | Preserve the future assignment boundary | Case submission and assignment are deferred |
| DR01 / DR05 | UUID/FK/UTC identity data; append-only audit evidence for account administration | No cascading deletion of historical evidence |
| NFR01 / NFR03 / NFR09 / NFR10 | Password/session protections, responsive forms, redaction, meaningful checks and CI | No production-security or usability-study claim |
| AT02 | Identity/role-denial portion only | Full cross-farm and assigned-case acceptance remains pending |

## Implemented user journeys

1. Register with display name, email, password and password confirmation. The server accepts only account fields and always assigns farmer; reject attempts to supply role, status or ownership fields. Do not automatically log in after registration. Use a generic acknowledgement for both a new account and an existing email, without saying an email was sent. Continue to login.
2. Login with email/password. Return the same safe failure for an unknown email, wrong password or disabled account. Farmers return to Home, or directly to Chilli AI after choosing Log in to ask. Advisors open the Advisor inbox and administrators open Admin Overview.
3. Reload a protected page. Restore the session through a rotated refresh cookie before rendering private account data. An expired/revoked session returns the user to login with a clear explanation.
4. Edit the signed-in user's display name or change the password after verifying the current password. The new password uses the signup rule; other sessions are revoked and this session remains active. Email changes and recovery remain unavailable.
5. An administrator searches a bounded, paginated user list, filters role/status, opens an account and confirms a role/status change or permanent removal with a reason. Removal scrubs sign-in identifiers/credentials, revokes sessions, leaves an audit-preserving tombstone and is excluded from ordinary account results. The deleted filter shows only scrubbed tombstones. Self-removal and removal that would eliminate the final active administrator are rejected. Show stale-write conflicts and refresh the record before retrying.
6. Logout revokes the current session and clears browser state/cookie. Role changes, disablement, account removal and password changes revoke affected sessions atomically. Re-enabling an account does not reactivate old sessions.

## Permission matrix

D30 follow-up: administrator login opens Admin Overview, farmers return to the website landing page and advisors open the Advisor inbox. Dedicated reporting endpoints allow audited count-only aggregate/per-farmer metadata. This adds no general private-record permission: farm names, coordinates, observations, chats and owner actions remain inaccessible to administrators. Current farmer account pages show only record counts, excluding workspace-deleted farms. [ADMIN_REPORTING.md](ADMIN_REPORTING.md) defines the scope.

Website-support follow-up (D29): Help is public. Farmers can create/read/reply/resolve/reopen their own submitted requests; administrators can handle those conversations through Support inbox, but cannot open farms or private AI chats. Advisors are excluded from both support APIs. Generic support notices remain recipient-owned. Public contact email is separately configured, and support does not reset passwords or replace identity verification. See [SUPPORT.md](SUPPORT.md).

| Operation | Anonymous | Farmer/advisor | Administrator |
| --- | --- | --- | --- |
| Register a farmer / login | Allowed with abuse controls | Public form remains available; no elevation | Same public form cannot create elevated roles |
| Read/update own account | Denied | Own display name only | Own display name only |
| List/read other accounts | Denied | Denied | Minimal account fields and account audit history |
| Read or change another user's notification state | Denied | Denied | Denied; inbox is recipient-owned |
| Change another account's role/status | Denied | Denied | Allowed with fresh authorization, version check and audit |
| Remove another account | Denied | Denied | Allowed with reason/version, privacy scrub, session revocation and audit |
| Change own password | Denied | Allowed after current-password check; revokes other sessions | Same |
| Change own role / disable self / remove self | Denied | Denied | Denied; use another administrator |
| Read private farms/chats or impersonate a user | No access in UM1 | No such route in UM1 | Account administration adds no private-data permission |

Preserve at least one active administrator. Serialize administrator lifecycle changes, recheck the actor after acquiring the lock, and test concurrent attempts to disable/demote administrators. Hiding a button is only a UI convenience; enforce every rule on the server.

## Authentication implementation

Keep the architecture's memory-only JWT access token and rotated HttpOnly refresh cookie. D19-D21/D23 record the selected local implementation:

- Use `pwdlib[argon2]` with Argon2id for passwords and PyJWT for signed access tokens. Resolve compatible versions against CPython 3.14 and commit generated locks only in implementation. Benchmark hash cost without weakening the selected hashing cost merely to meet a demo speed target. At the user's request on 17 November 2026, new passwords use 8-128 characters with at least one letter, one decimal digit and one symbol (Unicode punctuation/symbol categories). Uppercase is not required. Spaces are permitted and preserved but do not satisfy the symbol rule; paste/password managers remain allowed. Never silently trim or truncate passwords. Signup UI, server registration and first-admin bootstrap share this policy; login does not reapply composition rules to existing accounts. Use a dummy hash verification for nonexistent accounts to reduce login timing differences, alongside generic responses and abuse limits.
- Use 15-minute access tokens and an absolute 7-day session lifetime initially, with no remember-me option. Require `sub`, `sid`, `iss`, `aud`, `iat` and `exp`, an explicit allowed algorithm (HS256) and a generated server-only key of at least 256 bits. Tokens carry no email or private record data. Recheck current user role/status and the session on every protected request; logout, disablement and role changes therefore invalidate otherwise unexpired tokens.
- Generate high-entropy opaque refresh tokens, store only their hashes, rotate atomically and retain used-token records until the session can no longer be replayed. Reuse revokes the session family. Database locking must prevent two concurrent refreshes from producing two valid successors. The client coordinates refresh requests and never automatically retries a refresh after an uncertain response; a lost rotation response may require login again in this first design.
- Use host-only refresh cookies with HttpOnly, explicit SameSite=Lax, a narrow auth path and expiry aligned with the server session. Require Secure outside explicit localhost HTTP development. Clear cookies with the same path/domain attributes. Access tokens are never saved to localStorage/sessionStorage, URLs or logs.
- Use one browser origin through the existing Vite API proxy locally and a suitable reverse proxy if deployed later. Validate the exact allowed Origin on registration, login, refresh and logout; reject missing, null and untrusted origins on these browser POSTs. Require the application header `X-WagaMaga-Client: web` on them and JSON content for endpoints with request bodies; expose that header in OpenAPI for manual exploration. SameSite and CORS alone are not the CSRF policy. A separate cross-origin deployment would require revisiting this design, credentialed CORS and browser tests.
- PostgreSQL-backed, expiring rate-limit buckets cover login/registration/refresh across API processes/restarts. Initial settings: 5 failed logins per normalized-account key per 15 minutes plus 50 attempts per IP per 15 minutes; 5 registrations per IP/hour; 30 refreshes per IP and session/minute. These are tunable defaults, not measured attack-resistance guarantees. Keys are HMAC-derived and expired buckets are removed. Rate-limit errors use generic 429 plus Retry-After. No Redis was added.

First-administrator setup is a restricted local console operation, not a public endpoint, startup seed or committed default password. It prompts without echo, serializes the initial check and refuses another bootstrap once any administrator record exists. The interactive command is documented in DEVELOPMENT.md. Account recovery remains outside this milestone.

## Persistence implementation

Use the existing SQLAlchemy/Psycopg/Alembic setup and real PostgreSQL/pgvector tests. Add only identity-related tables, with reviewed application-role grants:

| Table | Responsibility |
| --- | --- |
| `users` | UUID, unique normalized email, display name, password hash, one checked role, disabled_at/deleted_at, UTC timestamps and optimistic version |
| `refresh_sessions` | Stable session/family ID referenced by JWT sid, user FK, absolute expiry and revocation metadata |
| `refresh_tokens` | Unique token hash, session FK, created/consumed timestamps; expiry and revocation inherit from the session family. Retained used hashes enable replay detection. |
| `auth_rate_limits` | HMAC-derived fixed-window bucket key, count and expiry; no plaintext account/IP/password/token values |
| `audit_logs` | Actor, target, action, previous/new role or status, reason, request ID and UTC timestamp; application role cannot UPDATE/DELETE |

The supporting tables refine the architecture’s logical session design and are implemented by migrations 0002_identity and 0003_account_lifecycle. Treat emails as case-insensitive identifiers for this application, apply one normalization rule everywhere, and enforce uniqueness in PostgreSQL. Removed accounts remain as tombstones because append-only audit rows and future domain records may reference their UUID; scrub the email, display name and password hash instead of deleting the row. Validate bounded display names and input sizes. Reject unsupported role/status values and mass assignment.

Role/status changes, session revocation and the associated audit insert share one transaction. If any step fails, none of them commit. Use expected entity versions for admin/profile writes and a consistent lock order for user/session operations. The normal app role receives necessary identity access and insert-only audit grants; bootstrap/migration privileges remain separate. Synthetic fixtures are explicit and contain no working default administrator password.

## Implemented API surface

All paths below are implemented under `/api/v1`. Pydantic DTOs and generated OpenAPI define exact schemas. Swagger exposes HTTP bearer authorization for access-token exploration; login uses JSON rather than an OAuth password-flow form.

| Method/path | Purpose | Response |
| --- | --- | --- |
| `POST /auth/register` | Display name/email/password only; always farmer | 200 generic acknowledgement for new/existing email, no token/user ID; deliberate privacy exception to normal creation responses |
| `POST /auth/login` | Issue access token and refresh cookie | 200, or uniform 401 for invalid/disabled login |
| `POST /auth/refresh` | Rotate refresh token and issue access token | 200; expired/reused/revoked token gives 401 and clears cookie |
| `POST /auth/logout` | Revoke current session; safe repeat clears cookie | 204 for an otherwise valid origin/header request |
| `GET /me` | Current account projection | 200; no password hash/session secrets |
| `PATCH /me` | Display name plus expected version only | 200 or 409 on a stale write |
| `POST /me/password` | Current password and policy-valid new password | 200 safe account projection; current session retained, other sessions revoked |
| `GET /admin/users` | Bounded account list, email/name search and role/status filters | 200; default page size 20, maximum 100, stable ordering; removed records hidden unless `status=deleted` |
| `GET /admin/users/{id}` | Minimal account detail | 200 or 404 for absent target after admin authorization |
| `PATCH /admin/users/{id}/role` | Checked role, reason and expected version | 200; revokes target sessions and audits atomically |
| `PATCH /admin/users/{id}/status` | Enable/disable, reason and expected version | 200; disablement revokes sessions atomically |
| `DELETE /admin/users/{id}` | Reason and expected version; self/last-active-admin protections | 200 scrubbed tombstone; sessions revoked and audit retained atomically |
| `GET /admin/audit-logs` | Filtered, paginated account security/administrative history; each read is audited | 200; account names/IDs, action, values, reason, request ID and time; no emails/secrets |
| `GET /notifications` | Current recipient's paginated notifications, optional unread filter | 200 items and unread count |
| `PATCH /notifications/{id}` | Mark one of the current recipient's notifications read or unread | 200; another recipient's ID returns 404 |

Identity errors: 401 for missing/invalid/revoked authentication; 403 for an authenticated non-admin on admin routes, checked before target lookup; 404 for a missing target after authorization; 409 for stale versions, already-removed account or self/last-admin conflicts; 400 for an incorrect current password; 422 for safe input validation; 429 for throttling. Redact request-body passwords/tokens from validation errors and logs. Use no-store for token/private account responses and the shared safe error envelope. Removal retains UUID, role, timestamps and audit references while scrubbing login identity and credentials; it is permanent in this UI and not a hard row deletion.

## Implemented project structure

These module paths now contain the implementation:

| Location | Responsibility |
| --- | --- |
| `backend/app/modules/identity/models.py` / `schemas.py` | Identity persistence models and explicit input/output DTOs |
| `backend/app/modules/identity/routes.py` / `service.py` | HTTP boundaries and account/session business rules |
| `backend/app/modules/identity/security.py` / `dependencies.py` | Hash/token adapters, current actor and role checks |
| `backend/app/modules/identity/cli.py` | Controlled initial administrator setup |
| `backend/app/db/` / `backend/migrations/` | Shared session lifecycle and reviewed migrations |
| `frontend/src/app/` | Router, session provider and application shell |
| `frontend/src/features/auth/` | Registration/login and session restoration UI |
| `frontend/src/features/account/` | Own-account screen and display-name form |
| `frontend/src/features/users/` | Administrator user list/detail and confirmed role/status actions |
| `frontend/src/components/` | Button, labelled field, alert, badge, dialog and layout primitives |
| `frontend/src/lib/` | Small shared HTTP/error handling; no password or token persistence |

Routes validate and call services. Services enforce authorization, manage transactions and use models; cryptographic operations stay behind small adapters. The API and worker retain one Python project. The worker remains a separate foundation process, with no invented identity background job or email service. Do not add a repository abstraction, state framework or microservice solely to demonstrate layers.

## UI direction and screens

The initial warm green direction was selected on 16 November 2026. On 17 November the user extended the merged homepage design to the other existing screens. Shared font/colour tokens now live in frontend/src/theme.css: creamy canvas `#f7f8ef`, warm-white surface `#fffef9`, forest `#0f2d1f`, sprout `#38d46a`, ink `#172f24` and sage borders `#dce4d5`. Self-hosted Plus Jakarta Sans replaces Georgia/system typography. Account cards/dialogs have 24px corners, fields use 16px corners and at least 48px height, while buttons/badges/navigation use pill shapes. Desktop auth uses the existing generated field photo in a dark story panel; mobile keeps the form first. [UI_DESIGN.md](UI_DESIGN.md) owns the combined visual foundation. Account rules, API contracts, accessible field/password/dialog behaviour and role boundaries remain unchanged. Plain CSS and shared React components with React Router declarative routing remain selected; no component kit, Tailwind migration or new state manager was added.

| Screen | Layout and content |
| --- | --- |
| `/` | Short introduction to Chilli AI, sign-in, registration and Help. Home restores the session to show role-specific actions. |
| `/login` | Simple brand header, centered form, email/password, show-password control, login button and register link |
| `/` after farmer login | Home offers Ask Chilli AI, Add a field note, My Farms and Planner. Staff see their own workspace entry. The old farmer `/dashboard` URL redirects home. |
| `/register` | Matching form with display name/email/password/confirmation and clear farmer-only registration wording |
| `/account` | Responsive signed-in header/menu, own name/email/role/status, editable display name, current-password-confirmed password change and sign-out action |
| `/admin/users` | Reusable app shell, user count for the filtered list, search, role/status filters including removed records and paginated rows; stacked account cards on mobile |
| `/admin/users/:id` | Account detail with role/status/removal controls, impact explanation and confirmation dialog; removed accounts display scrubbed tombstone state; no private farming content |
| Shared states | Session restoration, loading, empty results, validation failure, generic login failure, rate limit, access denied, stale write, offline/retry and session expiry |

The signed-in shell uses a compact header and role-specific navigation. On mobile use an accessible menu; forms fit the viewport and content reflows without horizontal page scrolling. Do not add placeholder farm/AI navigation. Preserve the existing M0 health screen as a developer connection page or test route; it is not the signed-in product home.

Use visible labels, password-manager autocomplete, keyboard focus, text with status colours, announced validation errors and a dialog that traps/restores focus. A submitting form prevents accidental duplicate actions. Confirmations explain session revocation; removal explicitly explains identity scrubbing and irreversibility. Version conflicts retain context and require a fresh decision. Do not show raw API traces or conflate a disabled account with a removed one.

## Implementation slices and verification

| Slice | Deliverable | Evidence before proceeding |
| --- | --- | --- |
| UM1-A: choices and style | D19-D23 selected for the broad authorized implementation; warm green direction retained | Connected screens/screenshots reviewed locally; no separate user wireframe approval or usability study claimed |
| UM1-B: persistence and bootstrap | Identity/session/token/rate-limit/audit migrations and restricted bootstrap | Fresh/upgrade migration tests, uniqueness/grants, initial-admin concurrency and rollback |
| UM1-C: backend identity | Registration/login/refresh/logout/me and administrator account actions | API and real PostgreSQL permission, revocation, reuse, concurrency and failure-path tests |
| UM1-D: React journey | Shared style primitives, auth/session shell, account and administrator screens connected to the actual API | Component tests for form validation, loading/errors, denied roles, confirmation and stale-state handling |
| UM1-E: close milestone | End-to-end journeys, CI and updated setup/API/UI/database guides | Real-browser mobile/desktop, keyboard and cookie checks; existing M0 checks stay green |

Tests belong in every slice, not only UM1-E. Document exact executable commands in DEVELOPMENT.md/TESTING.md when the commands exist. Swagger supports manual request exploration; automated pytest and browser checks establish repeatable behaviour. A Playwright suite and CI browser setup now cover these journeys; ordinary checks remain offline/provider-independent.

Minimum backend cases: concurrent duplicate-email registration creates one user; client-supplied elevated roles are rejected; correct/incorrect/unknown/disabled login responses are safe; token tampering/algorithm/issuer/audience/expiry checks fail; unknown/revoked sid fails; logout/disable/role-change/removal prevents both old access and refresh; password change checks current password/policy, retains only the current session and audits without secrets; refresh replay/concurrency and lost-response behaviour; CSRF/CORS/cookie flags; throttle limits across API instances; profile mass assignment and user-ID substitution; non-admin access denial before target disclosure; stale admin writes; concurrent administrator removal leaves one active administrator; removal scrubs identity and rolls back if audit fails; append-only grants; no secrets in responses/logs.

Minimum UI/browser cases: farmer registration to login to account to logout; administrator search/filter/detail/role/status actions; protected direct URL and reload; expired session and one refresh attempt; non-admin visiting an admin URL; offline and 409/429 messages; password masking/autocomplete; keyboard/dialog focus; 360px and 1280px layouts without horizontal page scrolling. Use synthetic accounts and actual PostgreSQL-backed browser journeys; component doubles are not end-to-end evidence.

UM1 is complete only when these included journeys and failure paths work, the accepted contract and migrations are documented, relevant checks/CI pass and no excluded domain feature has been added. AT02 remains partially satisfied until the later ownership/case workflows exist. Retention, recovery, verified email ownership, HTTPS/hosting and any MFA requirement must be resolved before a real-user pilot; this initial milestone uses local synthetic data.

## Run and review this milestone

Follow DEVELOPMENT.md for locked setup, migration, hidden-password first-administrator bootstrap and local API/frontend/worker startup. The app opens on its public homepage, with links to login/registration; /connection retains the M0 developer screen. Register synthetic farmers and use an authorized administrator for role/status changes. TESTING.md owns exact commands and actual outcomes. Browser fixtures use only guarded test databases and generated credentials, without adding a default development administrator.

The backend, frontend and browser checks pass locally. Expanded remote CI is configured and awaits a push; no deployment was performed. Full AT02 and the farming/AI milestones remain pending. Recovery, email ownership, privacy/retention and real-user operating policies are unresolved. Review further account changes as a bounded task.

## References for the implementation choices

Reviewed 16 November 2026: [FastAPI password hashing and JWT guide](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/) supports the pwdlib/PyJWT candidates; [OWASP authentication](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html) and [password storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html) inform the password/failure controls; [OWASP CSRF guidance](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html) informs browser-origin protections; [RFC 9700 refresh-token guidance](https://www.rfc-editor.org/rfc/rfc9700.html#section-4.14) informs rotation/reuse handling, without claiming this custom login is an OAuth authorization server; [React Router declarative setup](https://reactrouter.com/start/declarative/installation) supports adding browser routing to the existing Vite client. Lifetimes, thresholds, layouts and schema details are selected project defaults, not values mandated by these sources.

# Security and privacy

Status: UM1 account/session controls are implemented and verified locally as recorded in TESTING.md. Farming, upload and AI controls below remain requirements for future slices. Derived from SRS FR01-FR04, FR11-FR29, DR01-DR05 and NFR01-NFR02/NFR09; this is not a production-security certification.

## Reporting a vulnerability

A private reporting contact and response process have not been configured. Before inviting external users or contributors, the maintainer must publish a private reporting route and supported deployment versions. Do not post credentials, exploit details involving real users or personal information in a public issue. No response-time SLA is currently promised.

## Identity and permissions

- Validate JWT signature, issuer, audience and expiry; keep access tokens in browser memory.
- Rotate refresh sessions using Secure HttpOnly cookies outside local HTTP development. Store refresh token hashes and revoke sessions on logout or account disablement.
- Define SameSite, CSRF/origin checks, explicit CORS origins and rate limits. Use modern password hashing and non-enumerating authentication errors.
- Derive identity from the session; never trust a client-supplied owner or role.
- Enforce ownership on reads, writes, jobs, citations and source files. Advisor access requires explicit farmer submission, assignment and sharing scope.
- Administrator role management does not authorize private conversations or acceptance on a farmer's behalf.

## UM1 implementation boundary

The early [user-management milestone](docs/USER_MANAGEMENT.md) implements the architecture's JWT/rotated-refresh boundary. D19-D23 record selected libraries, 15-minute access and absolute 7-day sessions, HttpOnly cookies, origin/header checks, atomic rotation/replay revocation, shared expiring limits and controlled first administrator setup. Tokens remain memory-only in the browser. Production cookies require Secure; localhost HTTP is the explicit development exception.

Current user/session checks invalidate old access and refresh after logout, role change, disablement, removal or password change. Account administration and audit/revocation share a transaction that commits before success is sent; removal keeps a scrubbed UUID tombstone to preserve audit and future references. Users prove their current password before changing it; attempts use the shared account/IP rate limits, the current session stays active and other sessions are revoked. The first administrator uses a restricted local command with no default password/public elevation route. Public signup is farmer-only, and role assignment does not validate an advisor's professional qualification. Keep real credentials out of CLI arguments, fixtures, UI bundles and logs; browser fixtures use generated test-only credentials and guarded test databases.

The administrator audit viewer exposes account-action history only, never general server diagnostics. It returns actor/target IDs and display names, action, changed values, reason, request ID and time, with no email or credentials. Reading the feed is itself recorded with a fixed audit event. Audit rows remain append-only for the application role. Notifications are recipient-scoped: every list/read-state query derives the recipient from the live session, and a notification ID belonging to another user returns 404. Notification content is generated from fixed account/security templates and contains no passwords or tokens. No email notifications are sent.

New-password policy, selected by the user on 17 November 2026: 8-128 characters with at least one letter, one decimal digit and one punctuation/symbol character. Uppercase is optional; spaces are allowed but do not count as a symbol. Signup, self-service password change and administrator bootstrap enforce the same rule. Argon2id storage, password secrecy, rate limits and generic/redacted errors are retained. Passwords are never trimmed or truncated. Existing passwords remain valid at login; no forced reset or forgotten-password recovery is implemented.

This milestone uses local synthetic accounts. Administrator removal is permanent in the UI but does not physically delete the row: email/name/password hash are scrubbed, the account is disabled and marked deleted, and the UUID plus audit references remain. Future farm/chat retention and deletion rules are still unresolved and must be designed before those records exist. Email ownership verification, recovery, external access and any required MFA remain unresolved before real-user use. The administrator list exposes minimal account details and never confers private farm/chat access. TESTING.md separates actual identity checks from future full ownership/assignment coverage. Keep the documented no-proxy-headers local startup setting; real ingress/IP attribution and multi-origin deployments require their own reviewed configuration.

## Data and infrastructure

Keep database and storage private. Keep server secrets out of React bundles, fixtures, logs and source control. Use separate development, test and deployed configurations. Restrict the application database role so it cannot update or delete existing audit rows; use a separate controlled retention process.

Minimize private context sent to model providers and location precision sent to weather providers. Decide provider retention terms, account deletion rules and evidence retention before collecting real user data. Store UTC event times and explicit local scheduling dates/timezones.

## Upload and AI boundaries

- Quarantine uploads; validate allowed type and size, inspect content and scan before parsing. Parse in a resource-bounded worker. Select scanner/parser tools before enabling uploads.
- Publish only successfully processed and reviewed document versions. Keep passage locators, provenance and versioned evidence.
- Treat document instructions as data. The model has no unrestricted SQL, shell, network or mutation tool.
- Validate structured output, source IDs, context authorization and result sizes. A valid schema or citation does not establish agronomic correctness.
- Block or refer treatment, precise chemical/nutrient quantities, uncertain symptom conclusions and unsupported actions under a reviewed policy.

## Approval and transaction controls

Bind each decision to the immutable proposal version and action hash. Recheck owner, state, expiry, evidence withdrawal, task versions and material weather freshness before applying persisted actions. Use database transactions, locks and uniqueness to prevent partial or duplicate effects. Do not hold database locks during provider calls.

These controls apply to the first implemented task-changing flow, including V0. A locally simulated account or advisor is labelled as simulated.

## Required verification

- A different farmer's IDs cannot expose farms, tasks, chats, sources or jobs.
- Unassigned advisors are denied; advisor clearance alone cannot execute changes.
- Expired/revoked sessions cannot continue obtaining access; cookie endpoints enforce the chosen CSRF/origin policy.
- Uploaded prompt injection cannot authorize tools or disclose secrets.
- Withdrawn evidence, stale versions, changed actions and duplicate/concurrent requests fail safely or return the prior result.
- Logs and responses omit tokens, stack traces and another user's private details.

See [TESTING.md](docs/TESTING.md) for traceability and [OPERATIONS.md](docs/OPERATIONS.md) for deployment/recovery controls.

## Open security decisions

Authentication library and password hash configuration; token/session durations; account recovery; rate limits; inaccessible-object response policy; upload scanner and limits; private reporting contact; retention/deletion durations; provider terms; production origins and hosting. Track outcomes in [DECISIONS.md](docs/DECISIONS.md).

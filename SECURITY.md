# Security and privacy

Status: required design controls, not a claim of implemented security. Derived from SRS FR01-FR04, FR11-FR29, DR01-DR05 and NFR01-NFR02/NFR09.

## Reporting a vulnerability

A private reporting contact and response process have not been configured. Before inviting external users or contributors, the maintainer must publish a private reporting route and supported deployment versions. Do not post credentials, exploit details involving real users or personal information in a public issue. No response-time SLA is currently promised.

## Identity and permissions

- Validate JWT signature, issuer, audience and expiry; keep access tokens in browser memory.
- Rotate refresh sessions using Secure HttpOnly cookies outside local HTTP development. Store refresh token hashes and revoke sessions on logout or account disablement.
- Define SameSite, CSRF/origin checks, explicit CORS origins and rate limits. Use modern password hashing and non-enumerating authentication errors.
- Derive identity from the session; never trust a client-supplied owner or role.
- Enforce ownership on reads, writes, jobs, citations and source files. Advisor access requires explicit farmer submission, assignment and sharing scope.
- Administrator role management does not authorize private conversations or acceptance on a farmer's behalf.

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

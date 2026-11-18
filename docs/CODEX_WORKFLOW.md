# Building WagaMaga AI with Codex

Status: M0 complete and [UM1 user management](USER_MANAGEMENT.md) implemented locally, 16 November 2026, following the user's explicit backend/frontend request. D19-D23 record selected implementation choices and the warm green UI is connected. TESTING.md records actual results; expanded remote CI remains pending. V0 stages below remain future templates rather than permission to add domains.

Codex recognizes repository instructions in AGENTS.md. Other filenames here are project conventions; they are not all automatically loaded as instructions. Name the relevant guide in each task. Keep durable rules in AGENTS.md and specific acceptance details in the task. This follows [official AGENTS.md guidance](https://learn.chatgpt.com/docs/agent-configuration/agents-md) and [OpenAI's workflow example](https://developers.openai.com/cookbook/examples/codex/iterating-development-workflows-with-codex).

## 1. Open the project and establish context

Open the WagaMaga folder in Codex. The root README and docs/README.md index the guides. The SRS and architecture remain the baseline. Use this context prompt at the start of substantial work or a new chat:

```text
We are building WagaMaga AI. Read AGENTS.md, README.md and the relevant
sections of docs/WagaMaga_AI_SRS.md and docs/WagaMaga_AI_System_Architecture.md.
Inspect the current project and docs/ROADMAP.md. Keep React, FastAPI,
PostgreSQL/pgvector, private document storage and a separate worker.
Summarize what is implemented, what remains and the next bounded task.
Do not implement features in this context-review task.
```

Do not ask Codex to build the entire application in one request. Keep related code, tests and documentation together in a coherent slice.

## 2. Resolve the M0 tooling choices

Current project checkpoint: completed on 15 November 2026. The user accepted D01-D04 and D17. The prompt below is retained as a workflow template for future reconsideration, not an instruction to reopen accepted choices. Read DEVELOPMENT.md for the prerequisite audit before planning installation or scaffolding.

Before installing dependencies, choose runtime versions, package managers, React language/build tool, database access/migrations and local PostgreSQL setup. Candidates are listed in DECISIONS.md; they are not agreed merely because a previous answer mentioned them.

```text
Read docs/DECISIONS.md and docs/DEVELOPMENT.md. Recommend one simple M0
tooling setup for this Windows project within the agreed stack. Explain
the runtime, frontend, database/migration and local database choices.
Record recommendations as proposed decisions. Do not scaffold or install yet.
```

Review the proposal and tell Codex which choices to use, or explicitly delegate those reversible choices in the next task. No provider or pilot decision needs to block unrelated foundation work.

## 3. Build M0 only: reproducible foundation

Once the supporting choices are settled, use:

```text
Implement M0 from docs/ROADMAP.md using the selected decisions in
docs/DECISIONS.md. Initialize Git if needed, add ignore rules, scaffold
React and FastAPI, configure PostgreSQL/pgvector and the migration runner,
and add a separate worker entry point, safe environment examples and CI.
Add meaningful foundation checks and verified setup/check commands to
docs/DEVELOPMENT.md and docs/TESTING.md. Keep external providers optional.
Do not implement authentication, farm CRUD, RAG, proposals or live weather.
Run the available checks and report what passed, failed or was not run.
```

Inspect the diff and verify that the documented local startup works. Resolve missing prerequisites or environment permissions explicitly; do not claim unavailable checks passed.

## Next after M0: UM1 user management only

Read USER_MANAGEMENT.md for the implemented scope. The earlier planning-only task was followed by an explicit request to implement the backend/frontend. Choices were selected within that scope and connected screens are now available for review. Current follow-up work is review/publication and remote CI; do not rerun the historical implementation prompt against already implemented tables or bootstrap a default account.

UM1-B persistence/bootstrap, UM1-C backend identity and UM1-D connected screens exist. Local UM1-E tests pass, with expanded remote CI still unverified. Full AT02 remains pending until farm, case, source and job domains exist. Do not add those features just to demonstrate identity or mistake component mocks for server authorization.

Historical first-slice prompt, retained as a template rather than the next task:

```text
Read AGENTS.md, docs/USER_MANAGEMENT.md and accepted UM1 decisions.
Implement only UM1-B: identity/session/refresh-token/rate-limit/audit
persistence, reviewed grants and controlled first-administrator bootstrap.
Include real PostgreSQL migration, uniqueness, privilege, concurrency and
rollback checks. Record verified commands in DEVELOPMENT.md/TESTING.md.
Do not add HTTP authentication, UI, farms, AI, providers or deployment yet.
```

The numbered V0 workflow below resumes after this early identity milestone. Reuse UM1 identity rather than adding an authentication bypass for seeded demonstrations.

## 4. Prepare the V0 evidence and evaluation cases

```text
Prepare the V0 source inventory, synthetic cultivation/weather fixture
definitions and at least 10 evidence-mapped evaluation cases following
docs/KNOWLEDGE_EVALUATION.md. Include a missing-evidence case. Verify source
rights and applicability where possible; mark unknowns explicitly.
Do not invent agricultural guidance or represent unreviewed material as
approved. Keep live provider calls and real farmer data out of this task.
```

If reusable evidence is unavailable, narrow the workflow or record the blocker. Synthetic responses can verify plumbing but cannot prove agronomic quality.

## 5. Establish minimal V0 context and persistence

```text
Implement the minimal V0 synthetic identity/context and cultivation
persistence needed for the evidence proof. Use docs/DATABASE.md and the
SRS validation rules. Keep it local and label simulated actors. Add
migrations, repeatable synthetic seeds and meaningful validation/history
tests. Do not claim full public authentication or all farm CRUD is complete.
Update setup commands and the roadmap with actual results.
```

Reuse UM1 identity if implemented. Real multi-user access must still wait for object authorization and resolved privacy/operating gates. The V0 exception is a local synthetic demo, not permission to expose private records publicly.

## 6. Build curated ingestion and cited advisory

Split ingestion and advisory into separate tasks if either becomes large. Example ingestion task:

```text
Implement the V0 curated-source processing slice from the architecture.
Preserve document versions, checksums, provenance and page/section locators.
Keep unreviewed, failed and withdrawn content ineligible for new retrieval.
Use bounded processing and durable jobs when the work must survive restart.
Test parse failure, publication eligibility and historical source access.
Follow the repository security policy in SECURITY.md at the project root.
```

Example advisory task:

```text
Implement the minimum V0 cited-question flow and authorized source viewer.
Follow docs/API.md, docs/UI_DESIGN.md and docs/KNOWLEDGE_EVALUATION.md.
Use server-side model/embedding adapters and bounded requests. Test
missing evidence, invalid citations, private context isolation and source
prompt injection. Ordinary tests use deterministic provider doubles.
Report real evaluation separately; do not call a mocked run AI-quality proof.
```

V1 requires full hybrid retrieval and comparison against lexical/vector baselines. It may be introduced here if it fits the bounded slice; do not silently mark V1 retrieval acceptance complete.

## 7. Build one safe proposal and acceptance flow

```text
Implement one bounded V0 proposal and acceptance journey. Persist immutable
actions, evidence and the reviewed version/hash. Show current versus
proposed tasks. Block unsupported/high-risk actions under the available
review policy. If acceptance changes tasks, include the DR02 data and
atomic execution, precondition checks, audit records and database uniqueness
in this task. Test stale versions, changed tasks, duplicate/concurrent
requests and injected rollback. Never execute arbitrary model instructions.
Label simulated review and document whether acceptance actually executes.
```

Do not defer transaction integrity for an already implemented mutation to a later release. This clarification is recorded in DECISIONS.md.

## 8. Verify and close V0

```text
Verify the V0 gate in docs/ROADMAP.md against the actual code. Run relevant
API/integration/browser checks and the evidence-mapped questions. Demonstrate
labelled weather fixtures, cited answers and one proposal acceptance journey.
Record versions, results and limitations. Identify missing evidence honestly;
do not mark V0 complete unless its exit criteria are met.
```

Use Swagger to explore APIs and browser tests to demonstrate the journey. Use dataset/human review for AI quality. Each answers a different verification question.

## 9. Expand to V1 in bounded slices

Follow ROADMAP.md: full identity/roles/ownership; farm and task lifecycle;
knowledge administration and hybrid retrieval; advisor cases and full proposal
states; durable jobs/outbox/notifications; basic live weather; complete UI and
operating evidence. Bring required durable infrastructure forward whenever an
earlier implemented workflow needs it.

Use this template for each slice:

```text
Implement [one observable behaviour] for [actor]. Read [relevant guides]
and SRS [requirement IDs]. Acceptance examples: [happy path], [permission
failure], [invalid/stale input] and [recovery/duplicate behaviour if relevant].
Keep the agreed stack. Include the needed migration, API, UI states and
meaningful tests. Use synthetic data and deterministic external providers
for ordinary tests. Run relevant checks, review the diff and update docs.
Do not expand into [specific unrelated scope]. Report actual outcomes.
```

## 10. Review every completed slice

```text
Review this slice against its SRS requirements and acceptance examples.
Prioritize authorization, stale decisions, partial writes, duplicate
effects, source applicability and private-data exposure. Check meaningful
test coverage and API/UI consistency. Report actionable findings with
file/line references and residual verification gaps. Do not add new features.
```

Inspect Codex's diff and reported commands yourself. Fix material findings and rerun affected checks before marking the slice complete. Use focused commits as checkpoints once Git is initialized. Publishing a remote, opening a PR and deploying are separate tasks when needed.

## 11. Evaluate and deploy the V1 demo

Run AT01-AT12, the 30-question evaluation, frontend/browser checks, measured latency and recovery procedures. Follow OPERATIONS.md for deployment and restoration. Resolve real-user privacy, source rights, reviewer availability, thresholds and budget before a pilot. Do not describe simulated advisors as real agricultural review.

## 12. Keep the project state readable

At each checkpoint, update the roadmap with actual completion/evidence and the decision register with resolved choices. Update the API/UI/database/setup guides when contracts change. A new Codex chat should be able to determine the current state from the repository and tests without relying on hidden conversation history.

Current checkpoint: M0 is complete and UM1 implemented/verified locally. Use DEVELOPMENT.md to run it and create the first administrator interactively; inspect TESTING.md for the real 38 backend/11 frontend/6 browser results and outstanding remote CI. Review the account UI and any remaining account-policy needs as bounded follow-ups. Case sharing and farm/AI workflows remain later work and require their own request. The historical prerequisite audit is dated evidence, not current installed-tool state.

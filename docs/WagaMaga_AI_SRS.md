# WagaMaga AI Software Requirements Specification

Project requirements

## 1 Project purpose and scope

WagaMaga AI helps Sri Lankan farmers turn agricultural guidance and farm information into reviewed cultivation activities. This Software Requirements Specification defines the initial product, its release boundaries and the acceptance evidence needed before implementation is considered complete.

Document version 0.1 | 14 November 2026 | Requirements baseline for review. The product owner is the solo developer. Farmer interviews, agricultural validation and operating measurements remain release gates, rather than completed findings.

### Product definition

The product combines a farming knowledge assistant with farm and cultivation records, an activity calendar and weather related task review. AI explains information and prepares proposals. Authorized users make decisions; backend services enforce rules and execute accepted changes.

### Initial boundaries

| Area | Initial definition |
| --- | --- |
| Crop and area | Chilli cultivation in Anuradhapura; confirm source applicability before fixing the supported area. |
| Language and clients | English responsive React web application for mobile and desktop browsers. |
| Actors | Farmer, Agricultural Advisor and Administrator. Advisor access is limited to assigned, voluntarily submitted cases. |
| Knowledge | Curated, approved cultivation guides and advisories with explicit source and version metadata. |
| Weather | One provider adapter; labelled recorded test events in V0 and basic live integration in V1. |

### Business objectives

- Help the farmer locate applicable evidence and understand its limits.
- Convert a reviewed proposal into manageable, traceable tasks.
- Keep explanations, proposed changes and executed changes distinct.
- Demonstrate full stack implementation, hybrid retrieval, authorization, evaluation and failure recovery.

### Exclusions

Initial releases exclude image diagnosis, autonomous treatment decisions, invented fertilizer quantities, automatic irrigation equipment, yield or price forecasting, a marketplace, voice and native mobile clients. The platform is not a substitute for agricultural officers. HARTI price data is outside the initial workflow.

## 2 Business modules users and screens

| Module | Operations and business behaviour |
| --- | --- |
| M1 Farm and Crop Management | Create farms, cultivations and observations; read current details and history; update permitted fields; archive records. Preserve prior task and approval history. |
| M2 Advisory and Knowledge | Create conversations and candidate document versions; read cited answers and sources; update document metadata through versioned review; archive documents or delete eligible chats. Search, evidence selection and publication are business operations. |
| M3 Planner and Alerts | Create manual tasks and proposed plans; read calendars, alerts and review queues; update task status and revise proposals; cancel tasks or reject proposals. Approval and atomic execution are business operations. |

### Roles and access

| Role | Allowed scope |
| --- | --- |
| Farmer | Own farms, cultivations, observations, conversations and tasks; submit cases; accept or reject own proposals. |
| Advisor | Read only assigned case information; request clarification; clear, reject or request revision; review knowledge candidates. Cannot provide farmer consent. |
| Administrator | Manage accounts, role assignment, knowledge publication and system health. Administrative status does not automatically grant access to private farm conversations or approval on behalf of a farmer. |

### Required screens

| Actor | Screens |
| --- | --- |
| Farmer | Dashboard; My Farms; Farm and Cultivation Details; Ask WagaMaga; Planner; Recommendations and Proposal Details; Notifications; Profile and Settings. |
| Advisor | Review Queue; Assigned Case Details; Knowledge Review. |
| Administrator | User Management; Knowledge Documents; Document Processing; System Overview. |
| Shared | Register; Login; account recovery where configured; access denied and not found states. |

Weather and alerts appear on the dashboard. Crops are managed inside farm details. Citations open an authorized source viewer. All screens show loading, empty and error states; cancelled or archived objects are clearly labelled.

## 3 Identity farms and cultivation requirements

Requirements use stable identifiers. Unless explicitly marked V0 or V2, functional requirements are required for V1. Shall states a testable obligation.

### Identity and permissions

- FR01 The system shall register farmer accounts, authenticate users and support logout. Advisor and administrator roles shall be assigned only through an authorized administrative process.
- FR02 The API shall enforce role and object ownership checks for every protected read or mutation. A farmer changing an object identifier shall not gain access to another farmer's records.
- FR03 The system shall validate access token signature, issuer, audience and expiry. Revoked sessions shall not obtain new access tokens. Failed authentication shall not disclose whether an account exists.
- FR04 The farmer shall explicitly submit a case before an advisor receives its required farm context. Assignment and access shall be recorded and revocable for future access.

### Farm and crop records

- FR05 Farmers shall create, view, edit and archive their farms, including name, location and optional area. Coordinates shall be validated and area values shall include units.
- FR06 Farmers shall create cultivation records with farm, supported crop type, planting date and cultivation area. Unknown soil information shall remain unknown rather than being inferred as fact.
- FR07 The system shall distinguish estimated crop stage from a stage confirmed by a farmer or advisor, recording the confirmation actor and time.
- FR08 Farmers shall record observations with observation time and notes. Editing shall retain change history where a record has supported an approved decision.
- FR09 Archive shall hide a farm or cultivation from active lists without removing historical decisions. New proposals shall not execute against archived cultivations.
- FR10 Farm and task lists shall support relevant filters and bounded pagination. Default task ordering shall be by scheduled date in the farmer's configured timezone.

### Validation and history

Reject malformed coordinates, unsupported crop identifiers, impossible date ordering and nonpositive areas. A future planting date represents a planned cultivation. Dates alone shall not establish readiness for an agronomic action. Audit records identify the actor, operation, object, timestamp and outcome without storing credentials or hidden model reasoning.

## 4 Knowledge and hybrid RAG requirements

- FR11 Only authorized knowledge managers shall upload candidate sources with publisher, title, URL or file, language, crop applicability, publication date and validity information. Unknown dates shall be explicitly marked.
- FR12 Uploaded content shall remain unavailable to farmer retrieval until file checks, parsing, indexing and content approval have completed. Extraction failures shall be visible to the manager.
- FR13 Replacing content shall create an immutable document version. Superseded or withdrawn versions shall be excluded from new retrieval; permitted historical citations shall remain resolvable.
- FR14 Each indexed passage shall retain its document version, passage identifier, text and page or section locator. Embeddings shall record their model and index version.
- FR15 V1 shall retrieve evidence using both PostgreSQL full text search and vector similarity, combine ranked candidates and apply authorization and applicability filters before evidence reaches the model.
- FR16 The assistant shall answer cultivation questions using eligible sources, attach references to material agricultural claims and expose supporting passages in a source viewer.
- FR17 When evidence or farm context is insufficient or conflicting, the assistant shall ask for clarification, explain the gap or refer the case. It shall not fabricate sources, diagnoses, quantities or forecast certainty.
- FR18 Follow up questions shall use only the owner's conversation context. Instructions inside uploaded documents shall be treated as untrusted content, not as permission to call tools or bypass policy.
- FR19 Private farm records and current forecasts shall be retrieved through authorized structured queries or adapters, rather than trusted as facts from a vector match.
- FR20 Farmers shall view and delete eligible conversations. Deletion shall not erase approval evidence or audit records that must be retained; the user shall see the applicable retention explanation.

### Knowledge administration

Knowledge managers shall see upload, processing, review, publication, withdrawal and failure status. Publishing means the source was reviewed for inclusion; it does not establish that every generated answer is correct. Source management shall record review identity and timestamp.

### Language boundary

V1 shall support English input and evaluated English evidence. Sinhala and Tamil material may be inventoried but shall not be advertised as supported retrieval until language specific extraction, retrieval, translation and answer evaluation are completed.

## 5 Planning review and execution requirements

- FR21 The farmer shall request a bounded activity plan for a cultivation, with an initial maximum horizon of seven days. Missing information needed for a proposal shall produce clarification rather than guessed farm conditions.
- FR22 A proposal shall contain its version, cultivation, action list, affected task identifiers and versions, proposed dates, explanations, evidence references, context timestamp, expiry and review requirement.
- FR23 The backend shall validate structured output, ownership, supported action types, date ranges and evidence identifiers. Agronomic correctness shall be evaluated separately; schema validity alone shall not imply correctness.
- FR24 Routine task proposals may proceed to farmer review. Treatment, precise nutrient or chemical quantities, uncertain symptom conclusions and unsupported actions shall not execute through the routine path; they shall be blocked or referred under an advisor approved policy.
- FR25 Assigned advisors shall clear, reject or request revision of referred proposal versions with a recorded reason. Advisor clearance shall not substitute for farmer consent.
- FR26 Farmers shall compare current and proposed tasks, inspect evidence, and accept or reject the exact proposal version. Any changed action list shall require new review and acceptance.
- FR27 Before execution, the backend shall recheck permissions, proposal state, required decisions, expiry, source withdrawal, task versions and available forecast freshness where weather is material.
- FR28 Approved task changes, the execution result and audit entries shall be committed atomically. Repeated approval or execution requests shall not create duplicate task changes.
- FR29 A conflict or failed check shall leave tasks unchanged and return a clear outcome. Partial database writes shall roll back. Stale proposals shall require revision rather than automatic acceptance.
- FR30 Farmers shall create manual tasks, edit pending tasks, mark completion and cancel tasks. Completed or cancelled task history shall be retained; subsequent AI proposals shall not silently overwrite it.

### Approval states

Draft moves to Pending advisor or Pending farmer. Advisor clearance moves to Pending farmer. Farmer acceptance moves to Approved. A validated transaction moves to Executed. Rejected, Superseded and Expired are terminal for that version. Blocked or Failed records the reason; retry requires renewed precondition checks. Revision creates a new version and invalidates prior approval bindings.

## 6 Weather notifications and data requirements

### Weather and reminders

- FR31 The system shall obtain forecast data through a provider adapter and record provider, farm location, issue time where supplied, fetched time, forecast interval, units and provenance.
- FR32 V0 shall use explicitly labelled weather fixtures. V1 shall support a manual or scheduled live weather review with visible data age. Seasonal advisory text shall not be represented as a local daily forecast.
- FR33 Configurable, reviewed event rules shall identify tasks for review. Rainfall thresholds, freshness limits and agronomic interpretations shall be configuration requiring domain validation, not unlabelled model guesses.
- FR34 A weather event shall create a review notice or proposal, not directly reschedule farm tasks. Reprocessing the same event for the same cultivation shall not duplicate notices or proposals.
- FR35 Notifications shall persist in the application and support unread and read states. A reminder shall be derived from an active task and suppressed if the task has been completed or cancelled.
- FR36 On provider outage, malformed responses or stale data, the system shall show the limitation and suppress unsupported weather based proposals. Existing manual tasks and farm records shall remain usable.

### Data integrity and lifecycle

- DR01 Store business entities with primary and foreign keys, UTC event timestamps and explicit local dates or timezone where relevant. Use Asia/Colombo as the initial display timezone.
- DR02 Keep proposal actions, evidence references, decisions, forecast snapshots and execution uniqueness in the first release that changes tasks.
- DR03 Preserve immutable evidence text or a versioned source sufficient to reconstruct a historical decision. Withdrawn evidence shall be labelled when viewed and shall block new execution dependent on it.
- DR04 Define and display retention and account deletion policy before collecting real user data. Separate farm location, private conversation text and public knowledge access.
- DR05 Admins shall not silently edit audit history. Application database credentials shall have no permission to update or delete existing audit rows. Retention deletion requires a separate controlled process.

The logical data model and proposed API contracts are defined in the companion System Architecture document. Exact provider, model, retention periods and domain thresholds remain decisions to resolve before a real pilot.

## 7 Quality security and operating requirements

The following are proposed engineering targets, not measured results or service guarantees. Verify them on the documented test environment and revise the baseline explicitly if necessary.

| ID | Requirement and verification |
| --- | --- |
| NFR01 Security | Use HTTPS outside local development, modern password hashing, short lived signed access tokens, protected refresh sessions, explicit CORS origins and rate limits. Test expiry, revocation, ownership and role escalation. |
| NFR02 AI isolation | No credentials, unrestricted SQL, shell execution or direct mutation tools for the model. Constrain tool inputs and output size; test malicious document and user instructions. |
| NFR03 Usability | Support 360 px mobile and 1280 px desktop layouts without horizontal page scrolling. Primary forms shall have labels, keyboard access, clear errors and visible proposal status. |
| NFR04 Latency | On a declared dataset of up to 5000 passages and 10 concurrent test users, target p95 non AI CRUD responses below 1 second, excluding file transfer. Report AI end to end p50 and p95 separately. |
| NFR05 AI bounds | Initial interactive generation timeout 60 seconds; show pending status and a recoverable timeout response. Enforce bounded model calls, context size and per request usage. |
| NFR06 Reliability | No partial task updates and no duplicate effects in repeated or concurrent approval tests. Pending jobs shall be visible and recoverable after worker restart. |
| NFR07 Evidence quality | Evaluate at least 30 labelled questions, including answerable, unanswerable, outdated and conflicting evidence cases. Initial target: evidence Recall at 5 at least 0.80 for answerable cases; report baseline comparison. |
| NFR08 Answer quality | All citations shall resolve to permitted passages. Human review shall judge claim support and applicability; target at least 90 percent supported material claims on the defined evaluation set. Any unsupported actionable treatment recommendation fails the release gate. |
| NFR09 Observability | Correlate request, retrieval run, job, proposal and execution IDs. Record latency, failures, retries and model usage; redact secrets and minimize personal text in logs. |
| NFR10 Delivery | CI shall run backend checks, frontend build and relevant tests. Provide reproducible local setup, migrations, seed data and dependency configuration without committed secrets. |
| NFR11 Recovery | Before a real pilot, demonstrate restoration of database and document files from backup. Initial pilot objectives: recovery point within 24 hours and recovery time within 4 hours. These require deployment validation. |

## 8 Acceptance scenarios and traceability

Use deterministic integration tests for business rules and permissions. Use labelled evidence plus human review for retrieval and answer quality; an LLM judge alone is insufficient. Acceptance evidence shall identify release, data version and execution date.

| Test | Scenario and expected outcome | Requirements |
| --- | --- | --- |
| AT01 | Farmer creates a farm, cultivation and observation, then archives it; history remains readable and new execution is blocked. | FR05 to FR10 |
| AT02 | Farmer substitutes another owner's object IDs; reads, source access and mutations are denied. Advisor without assignment is denied. | FR01 to FR04 |
| AT03 | Upload a valid guide and a parsing failure; neither is retrieved before review. Publishing exposes only the valid approved version. | FR11 to FR14 |
| AT04 | Evaluate exact crop terms and paraphrased questions using keyword only, vector only and hybrid runs on the same corpus. Inspect citations and applicability. | FR15 to FR19; NFR07 to NFR08 |
| AT05 | Ask a question without evidence and inject a tool bypass instruction in a source; assistant states the gap and makes no unauthorized call. | FR17 to FR18; NFR02 |
| AT06 | Generate a valid weekly proposal, review its task differences, accept it and confirm exactly the accepted tasks and audit records exist. | FR21 to FR28 |
| AT07 | Refer a proposal; farmer cannot bypass required clearance. Advisor clearance alone cannot execute it. | FR24 to FR26 |
| AT08 | Revise an approved proposal or edit an affected task before execution; old acceptance does not execute the changed actions. | FR26 to FR29 |
| AT09 | Submit duplicate and concurrent approval requests and inject a transaction failure; produce one successful effect or no partial effect. | FR27 to FR30; NFR06 |
| AT10 | Replay a weather event; create one review notice. Supply stale or unavailable weather; show limitation without unsupported rescheduling. | FR31 to FR36 |
| AT11 | Delete an eligible conversation; required approval evidence remains under the declared retention policy. | FR20; DR03 to DR05 |
| AT12 | Run mobile, latency, timeout, restart and restore checks; record measurements and unresolved failures. | NFR03 to NFR11 |

### Core user stories

As a farmer, I can register a cultivation, ask a cited question, review a proposed weekly plan, accept its changes and mark tasks complete. As an assigned advisor, I can clear or return a referred case. As a knowledge manager, I can publish a reviewed document version and withdraw obsolete evidence.

## 9 Release gates assumptions and references

| Release | Scope and exit gate |
| --- | --- |
| V0 Evidence proof | Local seeded records; curated documents; cited answers; one manual proposal and acceptance flow; labelled weather fixtures. No public personal data. At least 10 sample questions mapped to evidence, including a missing evidence case. |
| V1 Portfolio MVP | All FR01 to FR36 and DR requirements, plus NFR baseline verification. Hybrid retrieval, authenticated roles, advisor referral, atomic task execution, basic live weather and deployed demo. Real advisor review must not be claimed for simulated accounts. |
| V2 Reliability | Automated weather polling, broader corpus, expanded failure recovery and operational monitoring. V1 already requires durable job status, basic retries and duplicate safe effects. |
| V3 Expansion | Additional crops, regions and evaluated languages. Image, voice and sensor features require separate requirements and validation. |

### Decisions required before a pilot

- Confirm the target farmer workflow through interviews and an agricultural advisor; the present scope is a product hypothesis.
- Verify source coverage, language, dates and reuse permissions. Confirm whether available chilli material supports the selected area and proposed activity horizon.
- Select the weather provider, location precision, permitted usage, freshness rules and event thresholds. Define approval policy with a qualified advisor.
- Select the LLM and embedding model using evaluation, privacy terms and an agreed operating budget. Set model specific context and usage limits.
- Choose hosting, retention periods and backup procedures. Do not claim offline or push notification support without implementation.

### Dependencies and major risks

Limited evidence may require a narrower workflow. Model and weather outages shall degrade to manual management. Incorrect or stale applicability can produce misleading recommendations despite valid citations. Human review capacity may limit real deployment. English V1 does not establish usability for Sinhala or Tamil speaking farmers.

### Terminology and references

RAG means retrieval augmented generation. Hybrid retrieval combines keyword and vector candidates. A proposal is a versioned suggestion; clearance is advisor review; acceptance is farmer consent; execution is a backend transaction. An idempotent operation has no additional effect when repeated.

Product requirements originate from the WagaMaga planning discussion. Technical companion: WagaMaga AI System Architecture, version 0.1. Candidate source directory: Department of Agriculture agro met advisories, https://doa.gov.lk/agro-met-advisory-si/ (accessed 14 November 2026). Availability does not establish reuse rights or crop specific adequacy. No agricultural recommendation is established by this specification.

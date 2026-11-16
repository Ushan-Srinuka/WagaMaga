# UI design guide

Status: the M0 React connection screen is implemented with loading, readiness and retry states. Business screens and user validation do not exist yet. The requirements and proposed visual direction below guide later implementation; final product design choices remain D16.

## Audience and product behaviour

Build an English responsive interface for farmers using mobile/desktop browsers, with separate advisor and administrator navigation. Begin with one validated chilli workflow. Show unknown information as unknown; planting dates alone do not establish readiness for an agronomic action.

The interface must distinguish an AI explanation, a proposed task change, advisor clearance, farmer acceptance and completed backend execution. Do not imply a task changed while a proposal is merely pending or approved.

## Screens and navigation

| Audience | Screens | Primary work |
| --- | --- | --- |
| Farmer | Dashboard, My Farms, Farm/Cultivation Details | Current context, observations and active records |
| Farmer | Ask WagaMaga, authorized source viewer | Ask questions, inspect citations and evidence gaps |
| Farmer | Planner, Recommendations/Proposal Details | Manual tasks, current/proposed comparison, acceptance/rejection |
| Farmer | Notifications, Profile/Settings | Read notices, timezone and account settings |
| Advisor | Review Queue, Assigned Case Details, Knowledge Review | Review only submitted and assigned context |
| Administrator | User Management, Knowledge Documents, Document Processing, System Overview | Roles, publication and operating status |
| Shared | Register, Login, configured recovery, Access Denied, Not Found | Identity and navigation outcomes |

Keep weather and alerts on the dashboard. Manage cultivations inside farm details. Suggested mobile primary navigation is Dashboard, Farms, Ask and Planner, with notifications/profile accessible from the header or menu. Final navigation remains a design decision.

## Suggested visual direction

Use a calm agricultural palette with a restrained green accent, neutral surfaces, readable typography and generous form spacing. Prioritize clear text and task status over decorative charts. Treat this as a starting proposal, not a validated brand identity. Select typography, tokens and a component library before building reusable components.

Use consistent buttons, form fields, status badges, evidence cards, task rows, alerts and confirmation dialogs. No UI library is currently agreed.

## Required interaction details

- Every data screen supports loading, empty, error and retry states.
- Forms have labels, unit-bearing area fields, inline validation and clear save outcomes.
- Archived farms and completed/cancelled tasks remain visibly labelled in history.
- Citations open the exact authorized passage with source/version and page/section locator; withdrawn historical evidence is labelled.
- AI responses show missing context and evidence limitations. A citation is not displayed as a guarantee of correctness.
- Proposal details show existing versus proposed dates/actions, rationale, evidence, version, expiry and review requirement.
- Acceptance sends the exact reviewed version/hash. A conflict explains what changed and requires revision rather than silently accepting updates.
- Advisor clearance is presented separately from farmer acceptance. Referred proposals cannot appear executable before clearance.
- Queued work shows pending/running/failure states from persisted job status. Poll initially; no streaming or push support is promised.
- Weather shows fixture/live provenance and data age. Outages or stale data do not disable manual task management.
- Deletion explains applicable retention; archive and irreversible deletion use distinct wording.

## Accessibility and responsive checks

Verify at 360 px and 1280 px without horizontal page scrolling. Use keyboard-accessible controls, visible focus, semantic headings, usable dialogs and descriptive validation. Status must be understandable without colour alone. Prefer touch targets around 44 px where practical as a proposed usability convention.

Test forms and proposal actions using accessible names in React Testing Library. Use browser tests for navigation, keyboard interaction, citation viewing and mobile/desktop layouts. Capture screenshots for significant visual changes; do not treat screenshots alone as behaviour tests.

## UI implementation order

After M0, build the minimum screens for the V0 journey: seeded cultivation context, question/source display, proposal comparison and acceptance result. Expand to full role-based screens and record management in V1. Pair UI work with its API contract and failure states rather than building all static screens first.

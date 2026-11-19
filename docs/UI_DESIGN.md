# UI design guide

Status: M0 connection, UM1 account screens, administrator audit history and in-app notifications are implemented locally. On 17 November 2026 the user requested merging their supplied DESIGN.md with this guide, then extending its creamy green design to the other existing screens. The shared font/palette cover home, login, registration, account, administrator list/detail/audit, notifications, dialogs, shared states and the developer connection page. [USER_MANAGEMENT.md](USER_MANAGEMENT.md) lists account boundaries. D16/D22/D25 retain the plain CSS/React Router approach. Farmer research and real-user usability validation remain pending.

## Design sources and scope

Connected Farm Records screens are specified in [FARM_RECORDS.md](FARM_RECORDS.md): farmer-only My Farms, farm/cultivation details, observations, explicit stage confirmation and labelled revision/archive history. FR-D connects the FR-C APIs using the shared creamy green theme, warm-white cards, local font and native confirmation dialog. Desktop/mobile layouts reflow into single-column cards/forms without horizontal scrolling. My Farms appears only for farmers in the workspace and signed-in homepage. Farm Records is marked Available on the homepage; its sample remains Illustrative, with guidance/planning still Planned.

Archive keeps details/history readable and removes write controls. Unknown soil/stage stays explicitly unknown; planned dates never imply agronomic readiness. Stage confirmation shows actor/time. Observation input states its device timezone and saved display uses the farm timezone; decimal strings are preserved. History renders labelled fields and plain text, never HTML or raw implementation JSON. Record requests and drafts are not stored in localStorage/sessionStorage.

On 409 retain the draft and block resubmission until explicit reload, explaining that reload discards the draft. An uncertain creation offers review of existing records and never claims success or automatically replays the POST. In-flight edits and parent/child drafts disable conflicting actions. Farm mutations do not automatically replay after 401; session expiry/logout/account changes clear private views. All screens include loading, empty, denied/not-found, validation and recoverable error states. Existing account dialog wording is retained by default; farm archive supplies domain-specific labels and preserves native Escape/focus behaviour. TESTING.md distinguishes component doubles from real connected browser evidence.

This guide combines the supplied **Agro-Intelligence Editorial** DESIGN.md with the existing WagaMaga navigation, accessibility, interaction and product-safety rules. Keep one maintained UI guide rather than a second competing DESIGN.md. The attached reference mixes blue/lavender front-matter surfaces with warm cream prose; the user's explicit creamy green preference resolves that conflict. Adopt its Plus Jakarta Sans typography, forest/sprout greens, generous spacing, rounded cards and restrained depth, while keeping the previously approved homepage structure.

The reference's telemetry, predictive metrics, disease diagnostics, gauges and camera overlays are visual examples, not implemented capabilities or authorization to build them. Do not use colour, glows or sample panels to imply measured crop health, verified guidance or live data. Existing ownership, proposal-review and evidence rules still apply. Shared theme tokens and the local font face live in frontend/src/theme.css, loaded at the application entry point; existing homepage/account styles consume these tokens. The user's follow-up authorizes styling existing screens, without adding business features or changing authentication contracts.

## Audience and product behaviour

Build an English responsive interface for farmers using mobile/desktop browsers, with separate advisor and administrator navigation. Begin with one validated chilli workflow. Show unknown information as unknown; planting dates alone do not establish readiness for an agronomic action.

The interface must distinguish an AI explanation, a proposed task change, advisor clearance, farmer acceptance and completed backend execution. Do not imply a task changed while a proposal is merely pending or approved.

## Planned farmer experience: planner supported by chat

Direction accepted on 18 November 2026: make the cultivation planner the main working experience for the planned farming product. Ask WagaMaga supports it by explaining guidance, asking for missing details and preparing proposals. Farmers must also be able to enter records and manage manual tasks without using chat or waiting for an AI provider. This clarifies existing SRS FR05-FR08 and FR16-FR30; it does not add an implementation task or claim that a planner exists today.

The intended journey is: record cultivation context and observations; inspect current tasks; request an explanation or a plan of at most seven days; inspect reasons and sources; obtain required advisor clearance; accept the exact proposal; see the backend execution outcome; record progress. Show unknown context as unknown and never infer agronomic readiness from planting dates alone. Proposal changes continue to require fresh review/acceptance and server-side precondition checks.

As the relevant features are implemented, provide direct controls for recording observations, completing tasks, inspecting a suggestion's reason/source and requesting advisor review. These are entry points to existing permission-checked workflows, not generic AI write tools. Final navigation placement remains a later UI detail.

A combined cultivation diary and an "I missed this task" revision entry point are [planned follow-ups in ROADMAP.md](ROADMAP.md#planned-planner-follow-ups). Their screen details and completion conditions are deferred until their dependencies work. Do not add those controls to the current Farm Records slice or expose nonfunctional farming actions on the homepage.

## Screens and navigation

### Farmer onboarding follow-up - 19 November 2026

The user's correction supersedes the initial separate dashboard: farmer entry belongs in the website landing-page header and hero. Farmer login and restored-session login visits return to `/`; administrators open `/admin/overview` and advisors `/account`. `/dashboard` remains only a farmer-protected redirect home. The workspace logo and Home link return to the website. Remove the dashboard checklist, farm preview grid and fixed mobile bottom navigation.

The homepage retains its green field-photo hero and public product sections. Its header now exposes My Farms and Add a farm in the navigation and a prominent Add Farm action beside account controls. The hero headline is “Your farm. All in one place.” A wide cream action bar with a green edge places farm entry directly beneath the introduction. New farmers get Add my farm; visitors get Get started and a login link. Account restoration/offline states stay explicit and do not query private farms before authentication. On mobile the action bar stacks and the website navigation remains accessible without a bottom app bar.

For signed-in farmers, the hero loads up to 100 owned active farms into a labelled selector. Selecting a farm remounts its next-action reader; it reads the first active cultivation and its observation count, then links to Add what you are growing, Record first observation or Open crop records. Loading/failure falls back to Open farm rather than claiming a setup milestone. List failure has retry and a direct records link; archived and additional records stay available through View all farm records. Over 100 farms uses that paginated records page. Key private hero state by user ID and ignore late responses on account/selection changes. No checklist completion or agricultural readiness is inferred.

New cultivation creation and the hero observation action open the existing observation form using a consumed `observe=1` intent. Parent editing/archive controls stay disabled while that draft is open. Archived cultivations never gain a write form from this URL. The planned planner-first direction still applies when those features exist.

New farm forms start with a name chosen by the farmer, a district selector with no default district and a village/town field. A free-text location mode supports existing descriptions and other locations. The 25-district reference is bundled locally, with provenance in D27; choosing a district never supplies coordinates or establishes guidance eligibility. District mode saves `village, district District, Sri Lanka` in the existing location label, bounded to 200 characters. Editing begins with the exact existing label and timezone; unrelated edits do not reformat them.

Exact location is collapsed and optional. Use my current location requests browser permission only after an explicit click, fills the optional pair in the draft, shows accuracy and asks the farmer to verify they are at the farm. It never auto-saves, reverse-geocodes or changes district/village. Permission errors/timeouts/unsupported contexts preserve existing coordinates and allow manual entry or omission. Pending lookup disables submission; cancellation/manual edits invalidate late callbacks. Clearing coordinates clears both. Additional optional area and timezone controls are collapsed; new farms default to Asia/Colombo. Visible scope notes explain that chilli is the initial crop and the planned Anuradhapura guidance pilot still requires agricultural review. Manual records outside that location are not a claim of agricultural support.

### Public landing page

The public opening page is `/`, implemented after UM1 at the user's request. Its reference-led layout has a light header, generated chilli-field photo hero, forest text, sprout green pill buttons, creamy green canvas, sage-tinted sections and rounded warm-white cards. Plus Jakarta Sans now supplies homepage headings and body text. The page follows a product-vision section with three feature previews, a three-step planned workflow, trust/control principles, an account invitation and grouped footer links. Section navigation wraps to a second header row on smaller screens, and cards stack on mobile. Farm Records is Available, guidance/planning remain Planned, and all sample panels retain Illustrative preview labels; previews contain no working farming controls, fabricated source citations or agronomic recommendations. Home restores the current session before rendering account navigation: signed-in users see their name, My account, Notifications with an unread badge and farmer-only My Farms; signed-out users see Log in and Create account. A temporary API outage is labelled as unknown and offers retry, rather than falsely showing signed out. Hero and footer account links follow the same session state; protected URLs retain their server checks.

The local hero is an illustrative AI-generated image, disclosed in the footer and alt text, without a claim that it documents a real farm. The original PNG and an optimized 313,452-byte WebP are in frontend/public/images/; its [provenance and exact prompt](../frontend/public/images/README.md) record the built-in image-generation mode. CSS controls responsive crops and contrast. The new font is self-hosted with its license; there is no runtime external image/font host or new package dependency.

| Audience | Screens | Primary work |
| --- | --- | --- |
| Farmer | Landing-page header/hero, My Farms, Farm/Cultivation Details | Direct farm entry, current context, observations and active records |
| Farmer | Ask WagaMaga, authorized source viewer | Ask questions, inspect citations and evidence gaps |
| Farmer | Planner, Recommendations/Proposal Details | Manual tasks, current/proposed comparison, acceptance/rejection |
| Farmer | Notifications, Profile/Settings | Read notices, timezone and account settings |
| Advisor | Review Queue, Assigned Case Details, Knowledge Review | Review only submitted and assigned context |
| Administrator | User Management, Knowledge Documents, Document Processing, System Overview | Roles, publication and operating status |
| Shared | Register, Login, configured recovery, Access Denied, Not Found | Identity and navigation outcomes |

Manage cultivations inside farm details. Current farmer entry stays in the website header/hero on desktop and mobile. Weather, alerts, Ask and Planner navigation remain future work, to be placed when their workflows are implemented; do not add an empty dashboard or nonfunctional navigation for them.

## Combined visual foundations

Aim for a calm editorial presentation: clear hierarchy, useful whitespace, biological greens and warm light surfaces. Keep the photographic hero and dark account invitation as the strongest visual anchors. Avoid decorative textures, glowing fake live indicators and heavy card shadows.

### Shared palette

These variables in frontend/src/theme.css are the implemented source of truth. Homepage `--home-*` and account `--canvas`/`--surface`/`--ink` aliases reference them rather than duplicating palette values. They adapt the supplied palette to the user's creamy green request rather than retaining its blue/lavender surfaces.

| Token | Value | Use |
| --- | --- | --- |
| `--color-canvas` | `#f7f8ef` | Creamy green page canvas |
| `--color-soft` | `#edf2e5` | Soft sage sections, sidebar, footer and preview wells |
| `--color-inset` | `#e6eddd` | Nested accents, icon tiles, profile monograms and trust strip |
| `--color-surface` | `#fffef9` | Warm-white cards, fields, headers and dialogs |
| `--color-forest` | `#0f2d1f` | Structural actions, selected navigation and dark anchors |
| `--color-ink` | `#172f24` | Primary text |
| `--color-green` | `#176b3b` | Links and focus on light backgrounds |
| `--color-sprout` | `#38d46a` | Homepage/auth account CTA with forest text |
| `--color-muted` | `#526052` | Descriptions and secondary text |
| `--color-line` | `#dce4d5` | Fine card borders and separators |

Keep white text on dark forest/photo zones with a dark overlay. Use dark forest text on sprout buttons; bright green is an accent rather than small text on cream. Status always needs words/icons alongside colour. The reference's lime `#a3e635` remains an optional future accent, not another homepage action colour or a crop-health claim.

### Typography

Brand consistency: use frontend/src/components/Brand.tsx and its shared brand.css for every rendered wordmark. The homepage's leaf icon in a sage tile, forest WagaMaga text and green AI label now appear on home/header/footer, login, registration, account/admin headers and /connection. Remove the earlier W badges and per-page/mobile logo overrides; keep the leaf visible at narrow widths. Existing home links remain intact. Plain text references to the product are not separate logos.

Use **Plus Jakarta Sans**, upright variable weights 400-800, for body text, headings, forms, navigation and dialogs across existing screens. Body text is generally 15px/24px; descriptions may use 16-17px for hierarchy. Use 700 for headings/actions and 800 for display text. Keep heading tracking around -0.025em to -0.035em. Homepage hero type scales to 48px on desktop and 28-36px on narrow screens; workspace headings scale 30-44px, auth card headings 27-30px and account panel headings 24px. Preview metadata is smaller and must remain secondary to readable feature descriptions. This replaces the former account Georgia/system-font pairing.

The [self-hosted Latin font record](../frontend/public/fonts/plus-jakarta-sans/README.md) includes source URLs, SHA-256 and the bundled SIL Open Font License. The unmodified variable WOFF2 is 27,348 bytes, served locally with font-display: swap and a Segoe UI/Arial fallback. No Google Fonts request is made at runtime. Current screens are English; review character coverage before adding other languages.

### Layout, shape and depth

Use a consistent 4/8px spacing rhythm, 24px desktop card gaps and a 1200px maximum homepage wrapper. Outer margins are 48px desktop, 32px tablet and 20px mobile. Homepage feature/workflow/trust groups use three equal columns on desktop and stack below 700px; the supplied 12/8/4-column scheme remains a broader layout reference, not a claim that every current section implements that grid.

Use 24px card radii/padding, 16px inner panels, 32px desktop account-invitation corners and full-pill actions/badges. Cards have a fine sage border; dark invitation elevation uses a subtle forest-tinted ambient shadow. Avoid hover transforms that move nearby content, respect reduced motion and retain visible focus. Homepage account actions are at least 48px high, with the compact desktop header action at least 44px.

### Components and future screens

Structural save/confirmation actions use forest/white; homepage and auth account-entry actions use sprout/forest. Ghost actions over the photo need a visible edge and white text. Existing fields use at least 48px height, 16px corners, visible boundaries and a clear focus outline; password toggles retain accessible names and 44px targets without overlapping input text. Search, buttons, role badges and navigation use pill shapes. Destructive controls and disabled-account states retain their warning colours/wording. Planned badges and illustrative panels remain distinct from functional controls. Do not add gauges, forecasts or photo-diagnostic components merely to demonstrate this design language.

### Account and shared-screen layouts

Login and registration pair a dark, generated-field-image story panel with a rounded warm-white form on desktop. The image is labelled illustrative/AI-generated in its alt text and reuses the homepage asset. Mobile hides the story panel and puts the form first. Profile and administrator screens use warm-white cards over the creamy canvas; the sidebar uses soft sage with a forest/white selected link. A compact header and accessible mobile Menu retain only existing account/admin navigation. User lists reflow to mobile cards. Dialogs, notices, empty/offline/denied states and /connection share typography, colours and rounded surfaces. Native dialog focus, keyboard behaviour and existing forms/actions remain intact. Plain CSS and small React components remain selected; no UI kit or CSS framework was added.

Use consistent buttons, form fields, status badges, evidence cards, task rows, alerts and confirmation dialogs as those screens are built. Preserve the interaction rules below when applying any visual direction.

## Required interaction details

Admin Overview (D30) is the administrator login destination `/admin/overview`. The website still opens `/` for farmers; advisors open `/account`. Use four sage summary cards, account-state/role counts, farm/cultivation splits and support statuses with a snapshot time, useful management links and explicit count/privacy definitions. Show real zero only after successful reads; loading/failure/denial never invent totals. The farmer account page adds count-only Farm record summary; removed/non-farmer accounts have no summary. Count cards do not open private farms. Enabled accounts are not advertised as active visitors, and no fabricated charts or live health indicators are added. Admin Overview is reachable through account navigation and the administrator website header. See [ADMIN_REPORTING.md](ADMIN_REPORTING.md).

Help/support (D29): add Help to the website header/footer, account navigation and login; `/help` uses the existing cream/green theme with a short getting-started guide, accessible FAQ disclosure controls and a public contact section. Signed-in farmers get Contact support/My support requests; administrators get Support inbox. The public contact email is configured, never invented, and an unavailable state is explicit. No fake password-reset or advisor action is shown.

Support list/new/detail pages use the existing workspace, filters and forms. Submission explains that administrators read only the submitted conversation and that farm context is not attached. Category/subject/message are bounded and labelled. Conversation messages render literal text, show farmer/support provenance and device-local time, and page newest groups chronologically. A draft blocks status changes/refresh; resolve/reopen are explicit reversible actions. Stale/uncertain failures retain the draft and require review before resubmission. Generic support notifications link to My support requests. Role/owner/private-response safeguards remain on the server. Public contact/Help work without a signed-in session; no database is needed for the contact endpoint.

Farm lifecycle controls (D28): archived farm detail exposes Restore farm and Delete farm beside history. Archive confirmation tells farmers where to find archived farms and that restoration is available. Restore confirmation explains that separately archived crops remain archived. Delete is available only after archive; its dialog explains loss of workspace access, retained historical storage and no undo, and requires the current farm name before enabling confirmation. The existing native dialog contains the field and keeps busy/error/cancel handling. Only a successful server response navigates to the archived list with a success notice; hidden/deleted direct links use the generic unavailable view. A stale or uncertain result blocks replay until explicit record review. This does not add cultivation restore/deletion, permanent erasure or a deleted-records screen.

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

## UM1 user-management screens

Implemented screens are login, farmer registration, own account/profile and password editing, administrator list/detail/removal, and denied/expired/offline states. One login serves all roles. Navigation follows the actual signed-in account: My Account and administrator-only User Management. Farm/AI navigation remains later work; registration offers no role selector.

Signup guidance now states 8-128 characters with at least one letter, one number and one symbol; uppercase is optional and spaces do not count as symbols. Both password fields use the 8-character minimum. Signup reports composition failures before sending a request, while the backend also validates them. Login does not apply signup composition rules to existing passwords. See USER_MANAGEMENT.md for the complete policy and API boundary.

The [screen/layout table and component boundaries](USER_MANAGEMENT.md) cover desktop/mobile behaviour. Shared fields support visible labels, autocomplete and password visibility; notices announce safe results. The account page asks for the current password, new password and confirmation; it explains that other sessions will end. Administrator role/status/removal confirmations explain impact, use native modal focus containment and restore focus when cancelled. Removed accounts are visibly distinct from disabled accounts and can be filtered in the admin list. Audit history uses filters, readable event cards and expandable request/account references. Notifications show unread status and provide read/unread actions; the shared workspace nav displays the unread count. Loading, empty results, retry, stale-write and rate-limit states are implemented; unavailable recovery links are omitted.

Current paths are /login, /register, /account, /admin/users and /admin/users/:id; the M0 connection screen is /connection. Screens use real account APIs and server authorization. Browser tests cover desktop/mobile reflow, reload, denied access, stale decisions and dialog keyboard/focus behaviour. Screenshots use synthetic accounts. A separate user wireframe-approval session did not occur; implementation followed the user's broad build instruction and selected style, and remains available for visual review.

## UI implementation order

After M0, complete the early UM1 scope and its review/check gates. The later V0 journey adds cultivation context, question/source display, proposal comparison and acceptance result. Expand to complete domain screens in V1. Pair UI work with its API contract and failure states; a visual prototype alone does not establish working authentication or permissions.
# Landing-page Help entry — 19 November 2026

The landing page includes a simple sage panel immediately above the footer, with “Need a hand with your farm records?” and two actions. Visit Help Centre opens `/help`; Contact Support opens `/support/new` for signed-in farmers and `/help#sign-in` for other visitors. Actions sit beside the text when space permits and stack on mobile. Existing header/footer Help links remain available.

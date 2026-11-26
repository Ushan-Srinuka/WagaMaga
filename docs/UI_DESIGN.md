# UI design guide

Status: M0 connection, UM1 account screens, administrator audit history and in-app notifications are implemented locally. On 17 November 2026 the user requested merging their supplied DESIGN.md with this guide, then extending its creamy green design to the other existing screens. The shared font/palette cover home, login, registration, account, administrator list/detail/audit, notifications, dialogs, shared states and the developer connection page. [USER_MANAGEMENT.md](USER_MANAGEMENT.md) lists account boundaries. D16/D22/D25 retain the plain CSS/React Router approach. Farmer research and real-user usability validation remain pending.

## Design sources and scope

Connected Farm Records screens are specified in [FARM_RECORDS.md](FARM_RECORDS.md): farmer-only My Farms, farm/cultivation details, observations, explicit stage confirmation and labelled revision/archive history. FR-D connects the FR-C APIs using the shared creamy green theme, warm-white cards, local font and native confirmation dialog. Desktop/mobile layouts reflow into single-column cards/forms without horizontal scrolling. My Farms appears only for farmers in the workspace and signed-in homepage. Home links to the connected farmer tools.

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

The combined cultivation diary and **I missed this task** are available inside the cultivation workspace. See the [planner follow-ups](ROADMAP.md#planner-follow-ups).

### Cultivation diary and reminders

The crop page shows the farm name, planting date and links to Field notes, Planner and, for chilli crops, Ask Chilli AI. The planner starts with today’s tasks, followed by overdue work and the coming days. Pending tasks have a Mark done button. Forecast and threshold controls are under Weather and alerts. The overview also provides the crop record, diary and reviewed sources.

Open **Cultivation history** to see the diary first, with farm-local timestamps and links to detail views. Manual edits show the previous and saved dates when the date changed. Weather decisions distinguish a kept date from an executed reschedule. Pending suggestions remain under weekly review. **Notifications** shows due-soon and overdue task reminders for the farmer. Completed, cancelled and moved tasks stop showing outdated reminders.

In a chilli cultivation, **Farm tasks → Ask about my tasks** answers supported English questions about the next seven farm-local days, pending overdue tasks and the reason for a saved date suggestion. The answer shows the saved forecast and the suggestion’s current state. **Review date options** opens the same forecast-based review controls as the seven-day planner.

### Manual tasks

Open a cultivation and use **Farm tasks** to add a title and due date, edit pending work, mark it complete or cancel it. The list defaults to pending tasks and can show completed, cancelled or all tasks. **Cultivation history** shows task changes with their saved title, due date and time. Archived cultivations keep the list and history readable.

Within **Farm tasks**, **Suggested plans** shows a labelled portfolio example beside the existing tasks. The review shows the proposed addition, local due date, checklist text and review deadline. **Accept and add task** immediately refreshes the pending list. **Reject suggestion** leaves the list as it was. **Plan decisions** in cultivation history shows both outcomes. Expired or stale examples can be replaced with a fresh review.

**Demo weather** shows a simulated rain forecast with the saved farm location, timezone and date. Only open tasks due on the sample date offer **Review this task**. That action opens the manual editor with the saved date. **Keep task date** closes the editor without saving, and **Save task** applies the farmer's edits. Archived tasks and tasks on other dates show no weather review action. If the sample fails to load, the task controls stay available.

**Weather forecast** shows the farm location, three dates, minimum and maximum temperatures, precipitation, provider attribution and fetch time. The fetch control explains that it shares approximate coordinates. Farms without coordinates link back to the farm record. Fresh forecast values appear beside pending tasks on matching dates. Stale forecasts stay labelled in the forecast card and are removed from the task rows. The existing editor lets farmers choose whether to change a date. The sample is shown through a separate development control.

**Weather alerts** lets the farmer save or turn off a precipitation threshold per cultivation. Matching pending tasks show the due date, forecast amount and threshold. **Review task date** starts a date comparison. **Confirm new date** saves the reviewed date and **Keep current date** records a rejection. The task and plan histories retain the result and the weather evidence. When the forecast or task changes, the farmer reloads the alerts before starting another review.

## Screens and navigation

### Farmer home and navigation

Farmer entry is in the website landing-page header and hero. Farmers sign in to `/`, administrators to `/admin/overview`, and advisors to `/advisor`. `/dashboard` redirects farmers home. The workspace logo and Home link return to the website.

The Advisor inbox links to pending plan and PDF assignments. Each full list has Needs review and Recently reviewed filters. Recently reviewed covers the past 30 days within current assignment access. Both detail screens require an outcome, a reason and explicit submission. The recorded outcome, reason and timestamp appear on the detail screen. PDF reviewers can jump to a page and keep their draft reason while navigating extracted text.

Signed-in farmers see **Ask Chilli AI**, **Add a field note**, **My Farms**, and **Planner** on Home. The first action opens general questions without requiring farm setup. **Ask about my crop** opens the private chilli crop chat. The AI screens have a visible Home link.

Field notes, Planner and crop chat share a paginated chooser for the farmer’s active farms and crops. A single farm and crop open directly. Crop chat only offers chilli plantings. A farmer with no farm or crop sees the corresponding setup action. Failed reads show a retry. My Farms lists crops before the collapsible Farm details controls.

A field-note shortcut opens the existing observation form with the note box focused. The device supplies the initial date and time. Farmers can change the time or record soil moisture before saving. Archive rules, version checks and history still apply.

New farm forms start with a name chosen by the farmer, a district selector with no default district and a village/town field. A free-text location mode supports existing descriptions and other locations. The 25-district reference is bundled locally, with provenance in D27; choosing a district never supplies coordinates or establishes guidance eligibility. District mode saves `village, district District, Sri Lanka` in the existing location label, bounded to 200 characters. Editing begins with the exact existing label and timezone; unrelated edits do not reformat them.

Exact location is collapsed and optional. Use my current location requests browser permission only after an explicit click, fills the optional pair in the draft, shows accuracy and asks the farmer to verify they are at the farm. It never auto-saves, reverse-geocodes or changes district/village. Permission errors/timeouts/unsupported contexts preserve existing coordinates and allow manual entry or omission. Pending lookup disables submission; cancellation/manual edits invalidate late callbacks. Clearing coordinates clears both. Additional optional area and timezone controls are collapsed; new farms default to Asia/Colombo. Visible scope notes explain that chilli is the initial crop and the planned Anuradhapura guidance pilot still requires agricultural review. Manual records outside that location are not a claim of agricultural support.

### Public landing page

The public home page has one sentence about the app, a chilli-field image and account entry links. **Log in to ask** returns a farmer to the question box. Normal farmer sign-in opens Home. The header links to Help. Home waits for the restored session and provides retry on connection failure.

The local hero is an illustrative AI-generated image, documented with the image asset, without a claim that it documents a real farm. The original PNG and an optimized 313,452-byte WebP are in frontend/public/images/; its [provenance and exact prompt](../frontend/public/images/README.md) record the built-in image-generation mode. CSS controls responsive crops and contrast. The new font is self-hosted with its license; there is no runtime external image/font host or new package dependency.

| Audience | Screens | Primary work |
| --- | --- | --- |
| Farmer | Landing-page header/hero, My Farms, Farm/Cultivation Details | Direct farm entry, current context, observations and active records |
| Farmer | Ask WagaMaga, authorized source viewer | Ask questions, inspect citations and evidence gaps |
| Farmer | Planner, Recommendations/Proposal Details | Manual tasks, current/proposed comparison, acceptance/rejection |
| Farmer | Notifications, Profile/Settings | Read notices, timezone and account settings |
| Advisor | Review Queue, Assigned Case Details, Knowledge Review | Review only submitted and assigned context |
| Administrator | User Management, Knowledge Documents, Document Processing, System Overview | Roles, publication and operating status |
| Shared | Register, Login, configured recovery, Access Denied, Not Found | Identity and navigation outcomes |

Choose a farm under My Farms to open its crops. Open Farm details to edit the farm, archive it or view its history.

## Combined visual foundations

Use large labelled actions, the existing chilli-field photo, and warm light surfaces. Put daily actions before the photo on phones.

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

The home page uses a full-width chilli-field hero with a dark overlay behind the controls. The two main actions take a full row each. My Farms and Planner share the following row. The homepage and account pages use white and mint for hero headings and sprout green with forest text for primary actions. Field notes uses soft sage. My Farms and Planner use forest green with light borders. Below the hero are Chilli AI with an example question, three farm tool cards and a Getting started guide. The header and footer link to all three sections. The mobile header uses a labelled Menu button. The footer links to the Help centre and offers Contact support to signed-in farmers.

Use 24px card radii/padding, 16px inner panels, 32px desktop account-invitation corners and full-pill actions/badges. Cards have a fine sage border; dark invitation elevation uses a subtle forest-tinted ambient shadow. Avoid hover transforms that move nearby content, respect reduced motion and retain visible focus. Homepage account actions are at least 48px high, with the compact desktop header action at least 44px.

### Components and future screens

Structural save/confirmation actions use forest/white; primary actions on the homepage and account-entry pages use sprout and forest. Ghost actions over the photo need a visible edge and white text. Existing fields use at least 48px height, 16px corners, visible boundaries and a clear focus outline; password toggles retain accessible names and 44px targets without overlapping input text. Search, buttons, role badges and navigation use pill shapes. Destructive controls and disabled-account states retain their warning colours/wording. Planned badges and illustrative panels remain distinct from functional controls. Do not add gauges, forecasts or photo-diagnostic components merely to demonstrate this design language.

### Account and shared-screen layouts

Login and registration pair a dark, generated-field-image story panel with a rounded warm-white form on desktop. The image is labelled illustrative/AI-generated in its alt text and reuses the homepage asset. Mobile hides the story panel and puts the form first. Profile and administrator screens use warm-white cards over the creamy canvas; the sidebar uses soft sage with a forest/white selected link. A compact header and accessible mobile Menu retain only existing account/admin navigation. User lists reflow to mobile cards. Dialogs, notices, empty/offline/denied states and /connection share typography, colours and rounded surfaces. Native dialog focus, keyboard behaviour and existing forms/actions remain intact. Plain CSS and small React components remain selected; no UI kit or CSS framework was added.

Use consistent buttons, form fields, status badges, evidence cards, task rows, alerts and confirmation dialogs as those screens are built. Preserve the interaction rules below when applying any visual direction.

## Required interaction details

Admin Overview (D30) is the administrator login destination `/admin/overview`. The website still opens `/` for farmers; advisors open `/advisor/cases`. Use four sage summary cards, account-state/role counts, farm/cultivation splits and support statuses with a snapshot time, useful management links and explicit count/privacy definitions. Show real zero only after successful reads; loading/failure/denial never invent totals. The farmer account page adds count-only Farm record summary; removed/non-farmer accounts have no summary. Count cards do not open private farms. Enabled accounts are not advertised as active visitors, and no fabricated charts or live health indicators are added. Admin Overview is reachable through account navigation and the administrator website header. See [ADMIN_REPORTING.md](ADMIN_REPORTING.md).

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
## Landing-page Help entry — 19 November 2026

The home footer includes the WagaMaga wordmark, a short product description and links to Chilli AI, Farm tools, Getting started and the Help centre. Contact support opens `/support/new` for signed-in farmers.

## Knowledge Sources

In production the administrator form requests the source URL, reuse basis and applicability metadata. The version card shows screening and extraction status. On a ready draft, open **Advisor review** to assign, reassign or revoke access before a decision. Advisors open **Knowledge review** from their account navigation, page through extracted text and record approval or requested changes with a reason. The administrator completes review and publication after approval.

Source details display the full version ID alongside the checksum and metadata. Reference answers offer a keyboard-operable supporting passage disclosure with a retry path for temporary errors. The chilli pilot route shows the Anuradhapura scope and the release status returned by the API.

**Ask about my crop** opens private crop chat from a chilli cultivation. The farmer can reopen it from **Saved conversations**, inspect the cited page, or confirm deletion. The answer form makes the Gemini choice explicit and shows the local district and crop stage separately from the answer.

**Published chilli references** shows the corpus version, source locator and English paraphrase for each passage. In the local PDF workflow, set a source title or start from **Upload replacement PDF** on a published version. The publish dialog identifies the effect on the previous version. On farmer answers, **Show supporting passage** expands the cited source note on demand.

The signed-in **Chilli questions** screen starts with nursery site, irrigation and soil testing questions, followed by published study questions. It accepts typed variants. Practical answers show the relevant Department of Agriculture section and link to the public Sinhala crop page. Research answers show the study attribution, journal and PDF page, DOI and license. The selection label identifies Gemini only when the server verified its choice against the source summary. **Chilli farm guidance** opens the separate gated advice screen.

**Chilli guidance for this cultivation** appears on active chilli cultivation records. It offers three questions and shows the confirmed crop stage, a recent recorded irrigation observation when applicable, the cited source and the checks the record cannot answer. The observation editor includes optional soil moisture and keeps it in private history.

**Automatic weather alerts** sits in the cultivation forecast panel and applies to the whole farm. The control explains the sharing of approximate coordinates before opt-in. The owner can turn it off from the same panel. The notification inbox links to My Farms so the owner can open the cultivation and review any date change.

An overdue pending task in **Farm tasks** shows **I missed this task**. The owner selects a date and can record why the task was missed. The comparison shows the existing date, proposed date and any matching current forecast. **Confirm new date** and **Keep current date** both appear in **Cultivation history → Plan decisions**.

**Seven-day planner** shows the seven farm-local days with readable dates and a separate overdue list. Rain alerts sit next to the affected task and its review action. A task opens in the same cultivation's task controls. **Review suggestion** compares the current and proposed dates with rainfall evidence and the recorded stage. The sharing form explains which fields the named advisor receives. **Assigned plan reviews** is visible to advisor accounts and offers clearance, decline or a request for changes with a reason. The farmer sees the advisor decision before confirming the task change.

After **Request changes**, the farmer sees the advisor's reason and can use **Revise suggested date** to send another date back. Each version is visible in **Weekly suggestion history**. Review notifications open the specific suggestion for the recipient. **Review weekly changes** compares several proposed date changes and lets the farmer select ready changes. The result lists the dates saved in that transaction.

Administrators can open **Knowledge Sources** in the workspace menu. Each synthetic guide card displays the saved status, version identifier, content and checksum. Review, publish and withdraw actions require confirmation.

The PDF form accepts a synthetic document and explains size, page and text limits. Queued versions explain how to refresh. A failed extraction shows the reason where available. A ready version opens a plain text preview with PDF page numbers.

**Search published PDFs** accepts keywords and shows a brief excerpt, PDF page number and version for each result. Expand **Citation details** for the complete version ID and checksum. Empty searches that have been submitted display **No evidence found** when no eligible page matches.

**Remove PDF** is available on unpublished PDF cards, including queued and failed uploads. Confirming hides the card and retains the stored original and decision history. Published cards use **Withdraw**.

The **Review the 10 chilli questions** link opens an admin page with a question selector, ranked candidate pages, expandable page text, a short review note and evidence labels. Decisions persist across reloads. Refresh the case if its sources or labels changed while reviewing.

The admin **Gemini scoring** screen shows per-case readiness and the latest result for current evidence. The farmer workspace links to **Chilli questions**. While review is pending it displays the pilot status. After release it offers the fixed questions, a cited answer and an expandable page preview.

The development frontend adds **Try the local demo** to **Chilli questions**. The demo lets the farmer type a question or insert an example. Its citation control opens the matched page of the fictional PDF. Example questions cover nursery labels, irrigation logs, fertilizer logs and a forecast with no evidence.

**Search reviewed excerpts locally** is a second development entry from **Chilli questions**. Its examples use the nursery-site, irrigation and fertilizer review questions. An answer shows the approved English wording and the original quote when it differs from the answer. **Read cited page** opens the extracted page while its review and publication are current.

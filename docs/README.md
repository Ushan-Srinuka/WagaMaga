# Documentation index

Status: M0 complete and UM1 user management implemented locally, 16 November 2026. TESTING.md distinguishes M0 remote CI from current local account/browser results and pending UM1 remote CI. DEVELOPMENT.md covers startup and controlled administrator setup. Farming/AI features remain unimplemented. The earlier PDF is a dated snapshot, not a live mirror.

Start with [How to explain WagaMaga AI in simple English](PROJECT_EXPLAINED.md) for presentation answers, technology choices, Markdown documentation, architecture, testing and an honest account of current progress.

That presentation guide predates the UM1 implementation. Use the current status above and TESTING.md for the account features and their actual verification evidence.

## Requirements and design

| Document | Purpose |
| --- | --- |
| [SRS](WagaMaga_AI_SRS.md) | Product scope, FR/DR/NFR identifiers, AT01-AT12 and release gates |
| [Architecture](WagaMaga_AI_System_Architecture.md) | Components, trust boundaries, retrieval, transactions, logical data and API baseline |
| [Decision register](DECISIONS.md) | Agreed constraints, proposed clarifications and unresolved choices |
| [UI design](UI_DESIGN.md) | Shared editorial foundations, creamy green palette/typography across existing screens, interaction states and accessibility |
| [API guide](API.md) | Route conventions, identity, errors, jobs, versioning and Swagger use |
| [Database guide](DATABASE.md) | Entity groups, integrity, migrations, indexes and isolation |

## Building and verifying

| Document | Purpose |
| --- | --- |
| [Development](DEVELOPMENT.md) | Intended folder layout, local setup and configuration |
| [Testing](TESTING.md) | Tools, requirement mapping, deterministic suites and release evidence |
| [Knowledge and evaluation](KNOWLEDGE_EVALUATION.md) | Source review, dataset design, retrieval and answer-quality gates |
| [Roadmap](ROADMAP.md) | M0 foundation, V0 proof and V1/V2/V3 completion criteria |
| [Codex workflow](CODEX_WORKFLOW.md) | Ordered build tasks and reusable prompts |
| [User management](USER_MANAGEMENT.md) | UM1 account scope, implemented contracts/structure/security, warm green UI and test gates |
| [Operations](OPERATIONS.md) | Deployment, job recovery, monitoring, backup and restoration |

## Repository policies

- [Project entry point](../README.md)
- [Codex repository instructions](../AGENTS.md)
- [Contribution workflow](../CONTRIBUTING.md)
- [Security and privacy](../SECURITY.md)

## Maintaining these files

The SRS owns requirements; the architecture owns baseline technical design. Other guides explain those decisions without changing them silently. Record deviations in DECISIONS.md and update the affected baseline when agreed. Keep exact runnable commands in DEVELOPMENT.md and TESTING.md rather than duplicating them throughout the docs.

API.md distinguishes implemented health/account routes from later planned contracts. Generated OpenAPI describes current HTTP schemas. Tests verify implementation against requirements; neither generated documentation nor this index alone proves feature completion.

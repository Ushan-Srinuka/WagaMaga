# Documentation index

Status: M0 foundation complete, 16 November 2026. Remote CI and fresh Windows checkout verification are recorded in TESTING.md. Business features remain unimplemented; the next requested scope is user management only. DEVELOPMENT.md has startup commands. The earlier exported PDF is a dated snapshot, not a live mirror of these files.

## Requirements and design

| Document | Purpose |
| --- | --- |
| [SRS](WagaMaga_AI_SRS.md) | Product scope, FR/DR/NFR identifiers, AT01-AT12 and release gates |
| [Architecture](WagaMaga_AI_System_Architecture.md) | Components, trust boundaries, retrieval, transactions, logical data and API baseline |
| [Decision register](DECISIONS.md) | Agreed constraints, proposed clarifications and unresolved choices |
| [UI design](UI_DESIGN.md) | Screens, navigation, interaction states and accessibility |
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
| [Operations](OPERATIONS.md) | Deployment, job recovery, monitoring, backup and restoration |

## Repository policies

- [Project entry point](../README.md)
- [Codex repository instructions](../AGENTS.md)
- [Contribution workflow](../CONTRIBUTING.md)
- [Security and privacy](../SECURITY.md)

## Maintaining these files

The SRS owns requirements; the architecture owns baseline technical design. Other guides explain those decisions without changing them silently. Record deviations in DECISIONS.md and update the affected baseline when agreed. Keep exact runnable commands in DEVELOPMENT.md and TESTING.md rather than duplicating them throughout the docs.

API.md currently documents planned contracts. Generated OpenAPI will describe implemented HTTP schemas once FastAPI exists. Tests verify implementation against requirements; neither generated documentation nor this index proves feature completion.

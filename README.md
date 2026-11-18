# WagaMaga AI

WagaMaga AI helps Sri Lankan farmers find cited cultivation guidance and review proposed activities before the backend changes tasks.

## Current status

M0 foundation is complete. UM1 user management is implemented locally: farmer registration, login/logout, rotated revocable sessions, own-account display-name editing and administrator account search/detail/role/status actions. Existing React screens now share the selected creamy green/sage theme, local Plus Jakarta Sans typography, rounded cards and forest/sprout actions. Farming, RAG, proposals, advisor case review and weather remain unimplemented. See TESTING.md for current local evidence; the expanded UM1 CI workflow is configured but has not run remotely for these uncommitted changes.

A public homepage opens at `/`, introduces the product and links to registration/login. Its reference-led layout uses a generated chilli-field photo hero, creamy green/sage surfaces, forest/sprout accents, rounded cards and locally hosted Plus Jakarta Sans. Product vision, planned features, the future workflow and trust principles explain the direction; sample panels are labelled illustrative. The combined design foundations are in docs/UI_DESIGN.md. Home remains available without an API connection.

## Stack

- React + strict TypeScript + Vite, Node.js 24 and npm 11.
- FastAPI, CPython 3.14 and uv; synchronous SQLAlchemy/Psycopg and Alembic.
- PostgreSQL 18 with pgvector in Docker; API/frontend/worker run directly on Windows initially.
- Private local document directory for future ingestion; no provider keys are needed for M0.

## Quick start on Windows

Prerequisites: Git, Node/npm, uv (global or the existing ignored project-local copy) and a running Docker Desktop Linux engine. Keep the existing Python installation; uv uses the pinned 3.14 interpreter. No Windows update or global Node/Python replacement is part of this scaffold.

From the project root:

```powershell
.\scripts\uv.ps1 sync --locked
.\scripts\uv.ps1 run python ../scripts/configure_local.py
npm.cmd --prefix frontend ci
docker compose up -d --wait
.\scripts\uv.ps1 run alembic upgrade head
```

Start each application process in its own terminal from the project root:

```powershell
# Terminal 1: API
.\scripts\uv.ps1 run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --no-proxy-headers --no-access-log
```

```powershell
# Terminal 2: frontend
npm.cmd --prefix frontend run dev
```

```powershell
# Terminal 3: worker foundation heartbeat
.\scripts\uv.ps1 run python -m app.worker
```

Open the [homepage](http://127.0.0.1:5173) for the public introduction, then choose Create account or Sign in. The homepage works without an API connection; account actions require the API/database. Use [Swagger](http://127.0.0.1:8000/docs) for API exploration and [/connection](http://127.0.0.1:5173/connection) for the original foundation status screen. Readiness at `/health/ready` returns 503 until PostgreSQL, pgvector and migration `0002_identity` are available. The worker reports readiness; durable job handlers are future work.

To create the first administrator, run the following in your own terminal after setup/migration and enter the requested name, email and password. The password is hidden; no default administrator is installed. Once an administrator exists, this command refuses further bootstrap attempts. See DEVELOPMENT.md for account and recovery limits.

```powershell
.\scripts\uv.ps1 run python -m app.modules.identity.cli
```

The setup script generates ignored local credentials and adds an authentication signing key if the existing `.env` has none, preserving other settings and existing credentials. Do not commit `.env`, `.tools`, `.data` or uploads. Docker initialization runs only for a new database volume; editing passwords later does not change existing database roles. UM1 is a local synthetic-account milestone; recovery, email verification and real-user privacy/deployment gates remain unresolved.

## Documentation

- [Explain the project in simple English](docs/PROJECT_EXPLAINED.md)
- [Development setup and exact commands](docs/DEVELOPMENT.md)
- [Testing and verification record](docs/TESTING.md)
- [Roadmap](docs/ROADMAP.md) and [Codex workflow](docs/CODEX_WORKFLOW.md)
- [SRS](docs/WagaMaga_AI_SRS.md), [architecture](docs/WagaMaga_AI_System_Architecture.md) and [decisions](docs/DECISIONS.md)
- [Complete documentation index](docs/README.md), [contribution guide](CONTRIBUTING.md) and [security](SECURITY.md)

The exported PDF in `output/pdf/` is a dated documentation snapshot from before scaffolding. Current Markdown and code are authoritative. [Foundation CI passed for the initial published commit](https://github.com/Ushan-Srinuka/WagaMaga/actions/runs/43828618767); TESTING.md records the separate clean-checkout evidence and remaining product/operating limits.

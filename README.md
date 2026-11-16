# WagaMaga AI

WagaMaga AI helps Sri Lankan farmers find cited cultivation guidance and review proposed activities before the backend changes tasks.

## Current status

M0 foundation scaffold, 15 November 2026: React connection screen, FastAPI health/OpenAPI endpoints, a separate worker entry point, PostgreSQL/pgvector, Alembic, locked dependencies and GitHub Actions configuration. Authentication, farms, RAG, proposals, advisor review and weather features are not implemented.

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
.\scripts\uv.ps1 run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```powershell
# Terminal 2: frontend
npm.cmd --prefix frontend run dev
```

```powershell
# Terminal 3: worker foundation heartbeat
.\scripts\uv.ps1 run python -m app.worker
```

Open the [frontend](http://127.0.0.1:5173), [Swagger](http://127.0.0.1:8000/docs) or [liveness check](http://127.0.0.1:8000/health/live). Readiness at `/health/ready` returns 503 until PostgreSQL, pgvector and the current migration are available. The worker reports readiness; durable job handlers are future work.

The setup script generates ignored local credentials and preserves an existing `.env`. Do not commit `.env`, `.tools`, `.data` or uploads. Docker initialization runs only for a new database volume; editing passwords later does not change existing database roles.

## Documentation

- [Development setup and exact commands](docs/DEVELOPMENT.md)
- [Testing and verification record](docs/TESTING.md)
- [Roadmap](docs/ROADMAP.md) and [Codex workflow](docs/CODEX_WORKFLOW.md)
- [SRS](docs/WagaMaga_AI_SRS.md), [architecture](docs/WagaMaga_AI_System_Architecture.md) and [decisions](docs/DECISIONS.md)
- [Complete documentation index](docs/README.md), [contribution guide](CONTRIBUTING.md) and [security](SECURITY.md)

The exported PDF in `output/pdf/` is a dated documentation snapshot from before scaffolding. Current Markdown and code are authoritative. CI is configured; a local verification result is not a claim that a remote GitHub Actions run has occurred.

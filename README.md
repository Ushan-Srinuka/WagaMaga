# WagaMaga AI

WagaMaga AI helps Sri Lankan farmers find cited cultivation guidance and review proposed activities before the backend changes tasks.

## Current status

- **Farmer workspace.** Sign in to the homepage and open **Ask about growing chilli** for published references and citations. The same page provides **My Farms**, **Add farm** and the next crop or observation action. Private records include farms, cultivations, crop stages, observations and history, with archive and farm restore controls.
- **Daily planning.** Cultivation pages put **Add observation**, **Add task** and **This week** below the crop heading. The seven-day planner separates overdue work and shows rainfall warnings beside affected tasks. Farmers can manage tasks, use optional forecasts and alerts, and review suggested changes before accepting them.
- **Questions and sources.** Within a chilli cultivation, **Ask about growing chilli** uses eligible reviewed PDFs and **Ask about my tasks** reads that cultivation’s planner. Administrators manage source versions, and assigned advisors can review source drafts. The real-farmer Anuradhapura advisory pilot remains disabled pending approved-source evaluation and independent review of answer support and applicability.
- **Roles and support.** Advisors sign in to **Assigned plan reviews** and can act on assigned snapshots. Administrators land on a count-only overview and manage accounts, knowledge sources and submitted support conversations. Public Help remains available at `/help`.
- **Verification.** The [testing record](docs/TESTING.md) distinguishes local checks using synthetic accounts from CI for published candidates and from evaluation required for the real-farmer pilot. Missing account recovery and real-user retention decisions remain release limitations.

## Stack

- React + strict TypeScript + Vite, Node.js 24 and npm 11.
- FastAPI, CPython 3.14 and uv; synchronous SQLAlchemy/Psycopg and Alembic.
- PostgreSQL 18 with pgvector in Docker; API/frontend/worker run directly on Windows initially.
- Private PDF storage and a separate worker for extraction, queued questions, weather checks and reminders.

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
# Terminal 3: background worker
.\scripts\uv.ps1 run python -m app.worker
```

Open the [homepage](http://127.0.0.1:5173) for the public introduction, then choose Create account or Sign in. The homepage works without an API connection; account actions require the API/database. Use [Swagger](http://127.0.0.1:8000/docs) for API exploration and [/connection](http://127.0.0.1:5173/connection) for the original foundation status screen. Readiness at `/health/ready` returns 503 until PostgreSQL, pgvector and the current migration head are available. The worker processes queued jobs and scheduled checks.

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

"""Short, bounded database checks; connection failures never expose credentials."""

from dataclasses import asdict, dataclass
from typing import Literal

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import Settings

SCHEMA_REVISION = "0019_weather_task_review"


@dataclass(frozen=True)
class Readiness:
    status: Literal["ready", "not_ready"]
    database: Literal["ready", "unavailable", "not_configured"]
    schema: str | None = None
    pgvector: str | None = None

    def payload(self) -> dict[str, str | None]:
        return asdict(self)


class Database:
    def __init__(self, settings: Settings):
        self.engine: Engine | None = None
        if settings.database_url is not None:
            self.engine = create_engine(
                settings.database_url.get_secret_value(),
                pool_pre_ping=True,
                pool_size=2,
                max_overflow=2,
                hide_parameters=True,
                connect_args={"connect_timeout": 3, "options": "-c statement_timeout=3000"},
            )

    def check_ready(self) -> Readiness:
        if self.engine is None:
            return Readiness("not_ready", "not_configured")
        try:
            with self.engine.connect() as connection:
                vector_version = connection.execute(
                    text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
                ).scalar_one_or_none()
                revision = connection.execute(
                    text("SELECT version_num FROM public.alembic_version")
                ).scalar_one_or_none()
        except SQLAlchemyError:
            return Readiness("not_ready", "unavailable")
        ready = vector_version is not None and revision == SCHEMA_REVISION
        return Readiness("ready" if ready else "not_ready", "ready", revision, vector_version)

    def close(self) -> None:
        if self.engine is not None:
            self.engine.dispose()

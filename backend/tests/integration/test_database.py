from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ProgrammingError

from app.core.config import Settings
from app.db.database import SCHEMA_REVISION
from app.main import create_app

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def database_settings(request):
    settings = Settings()
    if settings.test_database_url is None or settings.test_migration_database_url is None:
        if request.config.getoption("--require-database"):
            pytest.fail("Dedicated test database URLs are required")
        pytest.skip("No dedicated PostgreSQL/pgvector test database configured")
    for url in (settings.test_database_url, settings.test_migration_database_url):
        if not (make_url(url.get_secret_value()).database or "").endswith("_test"):
            pytest.fail("Integration checks require a database name ending in _test")
    migration_engine = create_engine(settings.test_migration_database_url.get_secret_value())
    try:
        with migration_engine.begin() as connection:
            config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
        yield settings.model_copy(update={"database_url": settings.test_database_url})
    finally:
        migration_engine.dispose()


def test_migration_extension_and_readiness(database_settings):
    with TestClient(create_app(database_settings)) as client:
        response = client.get("/health/ready")
        assert response.status_code == 200
        assert response.json()["schema"] == SCHEMA_REVISION
        assert response.json()["pgvector"] is not None


def test_app_role_cannot_change_schema_or_revision(database_settings):
    engine = create_engine(database_settings.database_url.get_secret_value())
    try:
        with engine.connect() as connection:
            privileges = connection.execute(
                text(
                    "SELECT rolsuper, rolcreatedb, rolcreaterole "
                    "FROM pg_roles WHERE rolname=current_user"
                )
            ).one()
            assert privileges == (False, False, False)
        with engine.begin() as connection, pytest.raises(ProgrammingError):
            connection.execute(text("UPDATE public.alembic_version SET version_num='tampered'"))
        with engine.begin() as connection, pytest.raises(ProgrammingError):
            connection.execute(text("CREATE TABLE public.forbidden_foundation_probe (id integer)"))
    finally:
        engine.dispose()


def test_real_postgres_vector_and_full_text_capabilities(database_settings):
    engine = create_engine(database_settings.database_url.get_secret_value())
    try:
        with engine.connect() as connection:
            version = int(connection.execute(text("SHOW server_version_num")).scalar_one())
            assert 180000 <= version < 190000
            assert connection.execute(
                text("SELECT '[1,0,0]'::vector <=> '[1,0,0]'::vector")
            ).scalar_one() == pytest.approx(0)
            assert (
                connection.execute(
                    text(
                        "SELECT to_tsvector('english', 'cultivation guidance') "
                        "@@ plainto_tsquery('english', 'cultivation')"
                    )
                ).scalar_one()
                is True
            )
    finally:
        engine.dispose()

import pytest

from app.modules.identity.security import passwords

SYNTHETIC_PASSWORD = "a synthetic growing season password 1!"
SYNTHETIC_HASH = passwords.hash(SYNTHETIC_PASSWORD)


def pytest_addoption(parser):
    parser.addoption(
        "--require-database",
        action="store_true",
        default=False,
        help="Fail instead of skip if integration DB configuration is missing",
    )


@pytest.fixture
def isolated_settings(monkeypatch):
    for name in (
        "DATABASE_URL",
        "MIGRATION_DATABASE_URL",
        "TEST_DATABASE_URL",
        "TEST_MIGRATION_DATABASE_URL",
    ):
        monkeypatch.delenv(name, raising=False)
    from app.core.config import Settings

    return Settings(_env_file=None, app_env="test")


@pytest.fixture(scope="session")
def identity_engines(request):
    from pathlib import Path

    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine
    from sqlalchemy.engine import make_url

    from app.core.config import Settings

    settings = Settings()
    urls = (settings.test_database_url, settings.test_migration_database_url)
    if any(url is None for url in urls):
        if request.config.getoption("--require-database"):
            pytest.fail("Dedicated PostgreSQL test URLs are required")
        pytest.skip("Dedicated PostgreSQL test URLs are not configured")
    for url in urls:
        if not (make_url(url.get_secret_value()).database or "").endswith("_test"):
            pytest.fail("Refusing to run identity integration tests outside an _test database")
    app_engine, owner_engine = [
        create_engine(url.get_secret_value(), hide_parameters=True) for url in urls
    ]
    with owner_engine.begin() as connection:
        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
    yield settings, app_engine, owner_engine
    app_engine.dispose()
    owner_engine.dispose()


@pytest.fixture
def accounts(identity_engines):
    from pydantic import SecretStr
    from sqlalchemy import text
    from sqlalchemy.orm import Session

    from app.modules.identity.models import User

    settings, engine, owner = identity_engines
    with owner.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE notifications, audit_logs, refresh_tokens, refresh_sessions, "
                "auth_rate_limits, users"
            )
        )
    settings = settings.model_copy(
        update={
            "database_url": settings.test_database_url,
            "app_env": "test",
            "auth_signing_key": SecretStr(
                "synthetic-test-only-signing-key-never-use-for-real-data-at-least-64-bytes"
            ),
            "auth_registration_attempts": 100,
            "auth_login_ip_attempts": 1000,
            "auth_refresh_attempts": 1000,
        }
    )
    people = {}
    with Session(engine, expire_on_commit=False) as db, db.begin():
        for name, role in (
            ("admin", "administrator"),
            ("second-admin", "administrator"),
            ("farmer", "farmer"),
            ("other-farmer", "farmer"),
            ("advisor", "advisor"),
        ):
            person = User(
                email=f"{name}@example.com",
                display_name=name.title(),
                role=role,
                password_hash=SYNTHETIC_HASH,
            )
            db.add(person)
            db.flush()
            people[name] = person.id
    return settings, engine, owner, people


@pytest.fixture
def account_client(accounts):
    from fastapi.testclient import TestClient

    from app.main import create_app

    with TestClient(
        create_app(accounts[0]),
        headers={
            "Origin": "http://127.0.0.1:5173",
            "X-WagaMaga-Client": "web",
        },
    ) as client:
        yield client

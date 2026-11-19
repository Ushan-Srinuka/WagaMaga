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
                "TRUNCATE support_events, support_messages, support_tickets, "
                "farm_deletions, farm_audit_events, observation_revisions, "
                "cultivation_revisions, "
                "farm_revisions, farm_observations, cultivations, farms, "
                "notifications, audit_logs, refresh_tokens, refresh_sessions, "
                "auth_rate_limits, users"
            )
        )
        # Operator-only catalogue variations in a test must not leak into later tests/reruns.
        connection.execute(text("DELETE FROM crop_types WHERE code <> 'chilli'"))
        connection.execute(text("UPDATE crop_types SET supported=true WHERE code='chilli'"))
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


@pytest.fixture
def farm_records(accounts):
    """Explicit synthetic records for two owners; never seeds the development database."""
    from datetime import UTC, date, datetime
    from decimal import Decimal
    from uuid import NAMESPACE_URL, uuid5

    from sqlalchemy.orm import Session

    from app.modules.farms.history import record_snapshot
    from app.modules.farms.models import (
        CHILLI_ID,
        Cultivation,
        CultivationRevision,
        Farm,
        FarmAuditEvent,
        FarmObservation,
        FarmRevision,
        ObservationRevision,
    )

    seeds = {}
    with Session(accounts[1]) as db, db.begin():
        for owner in ("farmer", "other-farmer"):
            actor = accounts[3][owner]
            farm = Farm(
                id=uuid5(NAMESPACE_URL, f"wagamaga-synthetic-farm-{owner}"),
                farmer_id=actor,
                name=f"SYNTHETIC-PRIVATE-FARM-{owner}",
                location="Synthetic location, not a real farm",
                latitude=Decimal("8.3"),
                longitude=Decimal("80.4"),
                area_value=Decimal("2"),
                area_unit="acre",
            )
            db.add(farm)
            db.flush()
            cultivation = Cultivation(
                id=uuid5(NAMESPACE_URL, f"wagamaga-synthetic-cultivation-{owner}"),
                farm_id=farm.id,
                crop_type_id=CHILLI_ID,
                planting_date=date(2026, 1, 10),
                area_value=Decimal("1.25"),
                area_unit="acre",
            )
            db.add(cultivation)
            db.flush()
            observation = FarmObservation(
                id=uuid5(NAMESPACE_URL, f"wagamaga-synthetic-observation-{owner}"),
                cultivation_id=cultivation.id,
                recorded_by=actor,
                observed_at=datetime(2026, 1, 2, 8, tzinfo=UTC),
                notes=f"SYNTHETIC-PRIVATE-NOTE-{owner}: pre-planting record only",
            )
            db.add(observation)
            db.flush()
            for record, revision, parent, operation in (
                (farm, FarmRevision, "farm_id", "farm_created"),
                (cultivation, CultivationRevision, "cultivation_id", "cultivation_created"),
                (observation, ObservationRevision, "observation_id", "observation_created"),
            ):
                db.add(
                    revision(
                        **{parent: record.id},
                        version=1,
                        snapshot=record_snapshot(record),
                        changed_by=actor,
                    )
                )
                db.add(
                    FarmAuditEvent(
                        actor_id=actor,
                        farm_id=farm.id,
                        cultivation_id=cultivation.id if record is not farm else None,
                        observation_id=observation.id if record is observation else None,
                        operation=operation,
                        entity_version=1,
                        request_id=str(uuid5(NAMESPACE_URL, f"synthetic-{owner}-{operation}")),
                    )
                )
            seeds[owner] = {
                "farm": farm.id,
                "cultivation": cultivation.id,
                "observation": observation.id,
            }
    return seeds

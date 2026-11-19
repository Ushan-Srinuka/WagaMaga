"""FR-B PostgreSQL evidence. These tests do not establish the future HTTP owner boundary."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import func, select, text, update
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.orm import Session

from app.db.database import SCHEMA_REVISION
from app.modules.farms.history import record_snapshot
from app.modules.farms.models import (
    CHILLI_ID,
    CropType,
    Cultivation,
    Farm,
    FarmAuditEvent,
    FarmDeletion,
    FarmObservation,
    FarmRevision,
    ObservationRevision,
)
from app.modules.identity.models import User
from app.modules.notifications.models import Notification

pytestmark = pytest.mark.integration
MUTABLE = ("farms", "cultivations", "farm_observations")
APPEND_ONLY = (
    "farm_revisions",
    "cultivation_revisions",
    "observation_revisions",
    "farm_audit_events",
)


def migration_config(connection):
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    config.attributes["connection"] = connection
    return config


def test_synthetic_roundtrip_units_unknowns_dates_and_history(accounts, farm_records):
    with Session(accounts[1]) as db:
        crop = db.get(CropType, CHILLI_ID)
        assert (crop.code, crop.supported) == ("chilli", True)
        assert db.scalar(select(func.count()).select_from(CropType)) == 1
        for owner, ids in farm_records.items():
            farm = db.get(Farm, ids["farm"])
            cultivation = db.get(Cultivation, ids["cultivation"])
            observation = db.get(FarmObservation, ids["observation"])
            assert farm.farmer_id == accounts[3][owner]
            assert farm.timezone == "Asia/Colombo"
            assert (farm.area_value, farm.area_unit) == (Decimal("2"), "acre")
            assert cultivation.area_value == Decimal("1.25")
            assert cultivation.soil_notes is cultivation.estimated_stage is None
            assert cultivation.confirmed_stage is cultivation.confirmed_by is None
            assert observation.observed_at.utcoffset() == timedelta(0)
            assert observation.observed_at.date() < cultivation.planting_date
            revision = db.scalar(
                select(ObservationRevision).where(
                    ObservationRevision.observation_id == observation.id
                )
            )
            assert revision.snapshot == record_snapshot(observation)
            assert revision.changed_by == observation.recorded_by == farm.farmer_id
        assert db.scalar(select(func.count()).select_from(FarmAuditEvent)) == 6


@pytest.mark.parametrize(
    "changes",
    [
        {"latitude": Decimal("90.01")},
        {"longitude": Decimal("-180.01")},
        {"latitude": None},
        {"latitude": Decimal("NaN")},
        {"longitude": Decimal("Infinity")},
        {"area_value": Decimal("0")},
        {"area_value": Decimal("-1")},
        {"area_value": Decimal("NaN")},
        {"area_value": Decimal("Infinity")},
        {"area_value": Decimal("1000000000000")},
        {"area_value": Decimal("0.0000001")},
        {"area_unit": None},
        {"area_value": None},
        {"area_unit": "bad"},
        {"name": " \t\n"},
        {"location": ""},
        {"version": 0},
        {"farmer_id": uuid4()},
    ],
)
def test_farm_database_constraints_reject_invalid_values(accounts, farm_records, changes):
    with pytest.raises(IntegrityError), Session(accounts[1]) as db, db.begin():
        db.execute(update(Farm).where(Farm.id == farm_records["farmer"]["farm"]).values(**changes))


@pytest.mark.parametrize(
    "changes",
    [
        {"area_value": Decimal("0")},
        {"area_value": Decimal("1.1234567")},
        {"area_value": Decimal("NaN")},
        {"area_unit": "bad"},
        {"soil_notes": "x" * 2001},
        {"confirmed_stage": "reported"},
        {"confirmed_by": uuid4()},
        {"estimated_stage": "guessed"},
        {"crop_type_id": uuid4()},
        {"version": 0},
    ],
)
def test_cultivation_database_constraints(accounts, farm_records, changes):
    with pytest.raises(IntegrityError), Session(accounts[1]) as db, db.begin():
        db.execute(
            update(Cultivation)
            .where(Cultivation.id == farm_records["farmer"]["cultivation"])
            .values(**changes)
        )


def test_optional_farm_area_coordinates_and_future_planting_are_supported(accounts, farm_records):
    with Session(accounts[1]) as db, db.begin():
        farm = db.get(Farm, farm_records["farmer"]["farm"])
        farm.area_value = farm.area_unit = farm.latitude = farm.longitude = None
        cultivation = db.get(Cultivation, farm_records["farmer"]["cultivation"])
        cultivation.planting_date = date(2099, 1, 1)
        cultivation.area_value = Decimal("0.000001")
        cultivation.area_unit = "m2"
        cultivation.confirmed_stage = "Owner-reported seedling"
        cultivation.confirmed_by = accounts[3]["farmer"]
        cultivation.confirmed_at = datetime.now(UTC)
    with Session(accounts[1]) as db:
        farm = db.get(Farm, farm_records["farmer"]["farm"])
        cultivation = db.get(Cultivation, farm_records["farmer"]["cultivation"])
        assert farm.area_value is farm.area_unit is None
        assert cultivation.planting_date == date(2099, 1, 1)
        assert cultivation.area_value == Decimal("0.000001")


@pytest.mark.parametrize("notes", ["", " \t\n", "x" * 4001])
def test_observation_notes_constraints(accounts, farm_records, notes):
    with pytest.raises(IntegrityError), Session(accounts[1]) as db, db.begin():
        db.execute(
            update(FarmObservation)
            .where(FarmObservation.id == farm_records["farmer"]["observation"])
            .values(notes=notes)
        )


@pytest.mark.parametrize(
    "table, field, cast",
    [
        ("cultivations", "planting_date", "date"),
        ("farm_observations", "observed_at", "timestamptz"),
    ],
)
def test_infinite_dates_are_not_valid_records(accounts, farm_records, table, field, cast):
    with pytest.raises(IntegrityError), accounts[1].begin() as connection:
        connection.execute(text(f"UPDATE {table} SET {field}='infinity'::{cast}"))


def test_observation_revisions_preserve_original_text_and_author(accounts, farm_records):
    ids = farm_records["farmer"]
    new_notes = "Synthetic corrected observation, no agricultural claim"
    with Session(accounts[1]) as db, db.begin():
        observation = db.get(FarmObservation, ids["observation"])
        observation.notes = new_notes
        observation.version = 2
        observation.updated_at = datetime.now(UTC)
        db.flush()
        db.add(
            ObservationRevision(
                observation_id=observation.id,
                version=2,
                snapshot=record_snapshot(observation),
                changed_by=accounts[3]["farmer"],
            )
        )
        db.add(
            FarmAuditEvent(
                actor_id=accounts[3]["farmer"],
                farm_id=ids["farm"],
                cultivation_id=ids["cultivation"],
                observation_id=observation.id,
                operation="observation_updated",
                entity_version=2,
                request_id=str(uuid4()),
            )
        )
    with Session(accounts[1]) as db:
        revisions = list(
            db.scalars(
                select(ObservationRevision)
                .where(ObservationRevision.observation_id == ids["observation"])
                .order_by(ObservationRevision.version)
            )
        )
        assert [item.version for item in revisions] == [1, 2]
        assert revisions[0].snapshot["notes"].startswith("SYNTHETIC-PRIVATE-NOTE")
        assert revisions[1].snapshot["notes"] == new_notes
        assert all(item.snapshot["recorded_by"] == str(accounts[3]["farmer"]) for item in revisions)


@pytest.mark.parametrize(
    "table, field, target",
    [
        ("farms", "farmer_id", "other-farmer"),
        ("cultivations", "farm_id", "farm"),
        ("farm_observations", "cultivation_id", "cultivation"),
        ("farm_observations", "recorded_by", "other-farmer"),
    ],
)
def test_database_blocks_owner_parent_author_reassignment(
    accounts, farm_records, table, field, target
):
    target_id = (
        accounts[3][target] if target == "other-farmer" else farm_records["other-farmer"][target]
    )
    with pytest.raises(IntegrityError), accounts[1].begin() as connection:
        connection.execute(text(f"UPDATE {table} SET {field}=:target"), {"target": target_id})


@pytest.mark.parametrize("table", (*MUTABLE, *APPEND_ONLY, "crop_types"))
def test_app_database_grants_are_restricted(accounts, farm_records, table):
    expected = {"SELECT"}
    if table in MUTABLE:
        expected |= {"INSERT", "UPDATE"}
    elif table in APPEND_ONLY:
        expected |= {"INSERT"}
    with accounts[1].connect() as connection:
        for privilege in (
            "SELECT",
            "INSERT",
            "UPDATE",
            "DELETE",
            "TRUNCATE",
            "REFERENCES",
            "TRIGGER",
        ):
            assert connection.scalar(
                text("SELECT has_table_privilege(current_user, :table, :privilege)"),
                {"table": table, "privilege": privilege},
            ) == (privilege in expected)
    denied_statements = [f"DELETE FROM {table} WHERE false", f"TRUNCATE {table}"]
    if table not in MUTABLE:
        denied_statements.append(f"UPDATE {table} SET id=id WHERE false")
    if table == "crop_types":
        denied_statements.append("INSERT INTO crop_types SELECT * FROM crop_types WHERE false")
    for statement in denied_statements:
        with pytest.raises(ProgrammingError), accounts[1].begin() as connection:
            connection.execute(text(statement))


@pytest.mark.parametrize(
    "mutation", ["extra", "missing", "id", "version", "null_id", "null_version"]
)
def test_revision_snapshot_shape_and_identity(accounts, farm_records, mutation):
    with Session(accounts[1]) as db:
        farm = db.get(Farm, farm_records["farmer"]["farm"])
        snapshot = record_snapshot(farm) | {"version": 2}
    if mutation == "extra":
        snapshot["provider_payload"] = "not permitted in history"
    elif mutation == "missing":
        del snapshot["location"]
    elif mutation == "id":
        snapshot["id"] = str(uuid4())
    elif mutation == "version":
        snapshot["version"] = 99
    else:
        snapshot[mutation.removeprefix("null_")] = None
    with pytest.raises(IntegrityError), Session(accounts[1]) as db, db.begin():
        db.add(
            FarmRevision(
                farm_id=farm.id, version=2, snapshot=snapshot, changed_by=accounts[3]["farmer"]
            )
        )


@pytest.mark.parametrize("wrong_parent", ["farm", "cultivation", "missing_cultivation"])
def test_farm_audit_parent_chain_cannot_be_mixed(accounts, farm_records, wrong_parent):
    own, other = farm_records["farmer"], farm_records["other-farmer"]
    with pytest.raises(IntegrityError), Session(accounts[1]) as db, db.begin():
        db.add(
            FarmAuditEvent(
                actor_id=accounts[3]["farmer"],
                farm_id=other["farm"] if wrong_parent == "farm" else own["farm"],
                cultivation_id=(
                    None
                    if wrong_parent == "missing_cultivation"
                    else other["cultivation"]
                    if wrong_parent == "cultivation"
                    else own["cultivation"]
                ),
                observation_id=own["observation"],
                operation="observation_updated",
                entity_version=2,
                request_id=str(uuid4()),
            )
        )


@pytest.mark.parametrize("kind", ["revision", "audit"])
def test_concurrent_duplicate_history_and_audit_are_unique(accounts, farm_records, kind):
    farm_id = farm_records["farmer"]["farm"]
    with Session(accounts[1]) as db:
        snapshot = record_snapshot(db.get(Farm, farm_id)) | {"version": 2}
    barrier = Barrier(2)

    def attempt(_):
        try:
            with Session(accounts[1]) as db, db.begin():
                barrier.wait(timeout=10)
                if kind == "revision":
                    db.add(
                        FarmRevision(
                            farm_id=farm_id,
                            version=2,
                            snapshot=snapshot,
                            changed_by=accounts[3]["farmer"],
                        )
                    )
                else:
                    db.add(
                        FarmAuditEvent(
                            actor_id=accounts[3]["farmer"],
                            farm_id=farm_id,
                            operation="farm_updated",
                            entity_version=2,
                            request_id=str(uuid4()),
                        )
                    )
            return "created"
        except IntegrityError as error:
            assert error.orig.sqlstate == "23505"
            return "duplicate"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(attempt, range(2))) == ["created", "duplicate"]


@pytest.mark.parametrize("target", ["farm_revisions", "farm_audit_events"])
@pytest.mark.parametrize("deferred", [False, True])
def test_history_and_audit_failures_roll_back_record_transaction(
    accounts, farm_records, target, deferred
):
    owner = accounts[2]
    farm_id = farm_records["farmer"]["farm"]
    with owner.begin() as connection:
        connection.execute(
            text("""
            CREATE FUNCTION public.frb_test_failure() RETURNS trigger
            LANGUAGE plpgsql AS $$ BEGIN
                RAISE EXCEPTION 'Synthetic farm persistence failure' USING ERRCODE = '23514';
            END; $$
        """)
        )
        mode = "DEFERRABLE INITIALLY DEFERRED" if deferred else ""
        connection.execute(
            text(
                f"CREATE CONSTRAINT TRIGGER frb_test_failure AFTER INSERT ON {target} "
                f"{mode} FOR EACH ROW EXECUTE FUNCTION public.frb_test_failure()"
            )
        )
    reached_commit = False
    try:
        with pytest.raises(IntegrityError), Session(accounts[1]) as db, db.begin():
            farm = db.get(Farm, farm_id)
            farm.name = "Synthetic replacement must roll back"
            farm.version = 2
            db.flush()
            db.add(
                FarmRevision(
                    farm_id=farm_id,
                    version=2,
                    snapshot=record_snapshot(farm),
                    changed_by=accounts[3]["farmer"],
                )
            )
            db.add(
                FarmAuditEvent(
                    actor_id=accounts[3]["farmer"],
                    farm_id=farm_id,
                    operation="farm_updated",
                    entity_version=2,
                    request_id=str(uuid4()),
                )
            )
            db.flush()
            reached_commit = True
        assert reached_commit is deferred
        with Session(accounts[1]) as db:
            farm = db.get(Farm, farm_id)
            assert farm.version == 1
            assert farm.name == "SYNTHETIC-PRIVATE-FARM-farmer"
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(FarmRevision)
                    .where(FarmRevision.farm_id == farm_id)
                )
                == 1
            )
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(FarmAuditEvent)
                    .where(
                        FarmAuditEvent.farm_id == farm_id, FarmAuditEvent.cultivation_id.is_(None)
                    )
                )
                == 1
            )
    finally:
        with owner.begin() as connection:
            connection.execute(text(f"DROP TRIGGER frb_test_failure ON {target}"))
            connection.execute(text("DROP FUNCTION public.frb_test_failure()"))


def test_restricted_foreign_keys_preserve_owner_and_history(accounts, farm_records):
    ids = farm_records["farmer"]
    for table, identifier in (
        ("users", accounts[3]["farmer"]),
        ("farms", ids["farm"]),
        ("cultivations", ids["cultivation"]),
        ("farm_observations", ids["observation"]),
        ("crop_types", CHILLI_ID),
    ):
        with pytest.raises(IntegrityError), accounts[2].begin() as connection:
            connection.execute(text(f"DELETE FROM {table} WHERE id=:id"), {"id": identifier})


def test_private_farm_events_do_not_enter_administrator_account_feed(
    accounts, farm_records, account_client
):
    login = account_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "a synthetic growing season password 1!"},
    )
    assert login.status_code == 200
    response = account_client.get(
        "/api/v1/admin/audit-logs",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert response.status_code == 200
    assert response.json()["items"] == []
    assert "SYNTHETIC-PRIVATE" not in response.text
    with Session(accounts[1]) as db:
        assert db.scalar(select(func.count()).select_from(FarmAuditEvent)) == 6


def test_account_removal_retains_private_farm_references(accounts, farm_records, account_client):
    farmer_id = accounts[3]["farmer"]
    login = account_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "a synthetic growing season password 1!"},
    )
    assert login.status_code == 200
    response = account_client.request(
        "DELETE",
        f"/api/v1/admin/users/{farmer_id}",
        json={"expected_version": 1, "reason": "Synthetic owner removal persistence check"},
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert response.status_code == 200
    with Session(accounts[1]) as db:
        assert db.get(User, farmer_id).deleted_at is not None
        assert db.get(Farm, farm_records["farmer"]["farm"]).farmer_id == farmer_id
        assert (
            db.get(FarmObservation, farm_records["farmer"]["observation"]).recorded_by == farmer_id
        )
        assert db.scalar(select(func.count()).select_from(FarmRevision)) == 2


def test_upgrade_preserves_accounts_and_notifications_and_matches_metadata(accounts):
    user_id = accounts[3]["farmer"]
    notice_id = uuid4()
    with Session(accounts[1]) as db, db.begin():
        db.add(
            Notification(
                id=notice_id,
                recipient_id=user_id,
                event_type="password_changed",
                title="Synthetic existing notice",
                body="Synthetic account event",
            )
        )
    with accounts[2].begin() as connection:
        config = migration_config(connection)
        command.downgrade(config, "0004_in_app_notifications")
        assert connection.scalar(text("SELECT to_regclass('public.farms')")) is None
        command.upgrade(config, "head")
        command.check(config)
    with Session(accounts[1]) as db:
        assert db.get(User, user_id).email == "farmer@example.com"
        assert db.get(Notification, notice_id).recipient_id == user_id
        assert db.scalar(select(func.count()).select_from(CropType)) == 1
        assert db.get(CropType, CHILLI_ID).supported
    with accounts[1].connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == SCHEMA_REVISION


def test_failed_migration_rolls_back_schema_seed_and_revision(accounts):
    owner = accounts[2]
    with owner.begin() as connection:
        command.downgrade(migration_config(connection), "0004_in_app_notifications")
    try:
        with (
            pytest.raises(RuntimeError, match="Synthetic migration rollback"),
            owner.begin() as conn,
        ):
            command.upgrade(migration_config(conn), "head")
            raise RuntimeError("Synthetic migration rollback")
        with owner.connect() as conn:
            assert conn.scalar(text("SELECT version_num FROM alembic_version")) == (
                "0004_in_app_notifications"
            )
            assert conn.scalar(text("SELECT to_regclass('public.crop_types')")) is None
            assert (
                conn.scalar(text("SELECT to_regprocedure('public.farm_record_identity_guard()')"))
                is None
            )
    finally:
        with owner.begin() as connection:
            command.upgrade(migration_config(connection), "head")


def test_lifecycle_upgrade_preserves_farm_snapshots(accounts, farm_records):
    farm_id = farm_records["farmer"]["farm"]
    with Session(accounts[1]) as db:
        before = db.scalar(select(FarmRevision).where(FarmRevision.farm_id == farm_id)).snapshot
    with accounts[2].begin() as conn:
        config = migration_config(conn)
        command.downgrade(config, "0005_farm_records")
        assert conn.scalar(text("SELECT to_regclass('public.farm_deletions')")) is None
        command.upgrade(config, "head")
        command.check(config)
    with Session(accounts[1]) as db:
        assert db.get(Farm, farm_id).version == 1
        assert (
            db.scalar(select(FarmRevision).where(FarmRevision.farm_id == farm_id)).snapshot
            == before
        )


def test_lifecycle_marker_append_only_constraints_and_downgrade_guard(accounts, farm_records):
    farm_id = farm_records["farmer"]["farm"]
    with Session(accounts[1]) as db, db.begin():
        db.add(FarmDeletion(farm_id=farm_id, deleted_by=accounts[3]["farmer"], entity_version=1))
    for sql in (
        "UPDATE farm_deletions SET entity_version=2 WHERE false",
        "DELETE FROM farm_deletions WHERE false",
        "TRUNCATE farm_deletions",
    ):
        with pytest.raises(ProgrammingError), accounts[1].begin() as conn:
            conn.execute(text(sql))
    with pytest.raises(IntegrityError), Session(accounts[1]) as db, db.begin():
        db.add(FarmDeletion(farm_id=farm_id, deleted_by=accounts[3]["farmer"], entity_version=2))
    with pytest.raises(RuntimeError, match="lifecycle evidence"), accounts[2].begin() as conn:
        command.downgrade(migration_config(conn), "0005_farm_records")
    with accounts[1].connect() as conn:
        assert conn.scalar(text("SELECT version_num FROM alembic_version")) == SCHEMA_REVISION

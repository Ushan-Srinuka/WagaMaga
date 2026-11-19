"""FR-C real PostgreSQL authorization, lifecycle, failure and serialization evidence."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier, Event
from time import monotonic
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.modules.farms import service
from app.modules.farms.models import (
    CHILLI_ID,
    CropType,
    Farm,
    FarmAuditEvent,
    FarmDeletion,
    FarmRevision,
)
from app.modules.identity import service as identity
from app.modules.identity.models import RefreshSession, User
from app.modules.identity.security import IdentityError

pytestmark = pytest.mark.integration
PREFIX = "/api/v1"
PASSWORD = "a synthetic growing season password 1!"
FARM = {
    "name": "Synthetic API farm",
    "location": "Synthetic location",
    "area_value": "2",
    "area_unit": "ha",
    "latitude": "8.3",
    "longitude": "80.4",
}
CULTIVATION = {
    "crop_type_id": str(CHILLI_ID),
    "planting_date": "2099-01-01",
    "area_value": "1.25",
    "area_unit": "ha",
}
OBSERVATION = {"observed_at": "2026-01-01T10:30:00+05:30", "notes": "Synthetic field note"}


def login(client, name="farmer"):
    response = client.post(
        f"{PREFIX}/auth/login",
        json={
            "email": f"{name}@example.com",
            "password": PASSWORD,
        },
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def path(ids):
    return (
        f"/farms/{ids['farm']}",
        f"/farms/{ids['farm']}/cultivations/{ids['cultivation']}",
        f"/cultivations/{ids['cultivation']}/observations/{ids['observation']}",
    )


def operations(ids):
    farm, cultivation, observation = path(ids)
    return [
        ("GET", farm, None),
        ("PATCH", farm, {"name": "Attempted edit", "expected_version": 1}),
        ("POST", farm + "/archive", {"expected_version": 1}),
        ("POST", farm + "/restore", {"expected_version": 1}),
        ("POST", farm + "/delete", {"expected_version": 1, "confirmation_name": "Synthetic"}),
        ("GET", farm + "/history", None),
        ("GET", farm + "/cultivations", None),
        ("POST", farm + "/cultivations", CULTIVATION),
        ("GET", cultivation, None),
        ("PATCH", cultivation, {"soil_notes": "Attempted edit", "expected_version": 1}),
        ("POST", cultivation + "/archive", {"expected_version": 1}),
        ("POST", cultivation + "/stage-confirmation", {"stage": "Reported", "expected_version": 1}),
        ("GET", cultivation + "/history", None),
        ("GET", f"/cultivations/{ids['cultivation']}/observations", None),
        ("POST", f"/cultivations/{ids['cultivation']}/observations", OBSERVATION),
        ("GET", observation, None),
        ("PATCH", observation, {"notes": "Attempted edit", "expected_version": 1}),
        ("GET", observation + "/history", None),
    ]


def call(client, method, route, headers, data=None, **kwargs):
    response = client.request(
        method,
        PREFIX + route,
        headers=headers,
        **({"json": data} if data is not None else {}),
        **kwargs,
    )
    assert response.headers["cache-control"] == "no-store"
    assert response.headers.get("x-request-id")
    return response


def test_full_manual_record_journey_and_exact_history(account_client, accounts):
    client = account_client
    headers = login(client)
    farm = call(client, "POST", "/farms", headers, FARM)
    assert farm.status_code == 201, farm.text
    farm = farm.json()
    assert farm["farmer_id"] == str(accounts[3]["farmer"])
    assert farm["timezone"] == "Asia/Colombo" and farm["version"] == 1
    f = f"/farms/{farm['id']}"
    cultivation = call(client, "POST", f + "/cultivations", headers, CULTIVATION)
    assert cultivation.status_code == 201, cultivation.text
    cultivation = cultivation.json()
    assert cultivation["planned"] and cultivation["soil_notes"] is None
    assert cultivation["estimated_stage"] is cultivation["confirmed_stage"] is None
    c = f + f"/cultivations/{cultivation['id']}"
    observation = call(
        client, "POST", f"/cultivations/{cultivation['id']}/observations", headers, OBSERVATION
    )
    assert observation.status_code == 201, observation.text
    observation = observation.json()
    assert observation["observed_at"].startswith("2026-01-01T05:00:00")
    o = f"/cultivations/{cultivation['id']}/observations/{observation['id']}"
    stage = call(
        client,
        "POST",
        c + "/stage-confirmation",
        headers,
        {"expected_version": 1, "stage": " Farmer-reported seedling "},
    )
    assert stage.status_code == 200, stage.text
    assert stage.json()["confirmed_by"] == str(accounts[3]["farmer"])
    assert stage.json()["confirmed_stage"] == "Farmer-reported seedling"
    assert stage.json()["confirmed_at"] and stage.json()["version"] == 2
    changed = call(
        client, "PATCH", c, headers, {"expected_version": 2, "planting_date": "2099-01-02"}
    )
    assert changed.status_code == 200 and changed.json()["confirmed_stage"] is None
    versions = call(client, "GET", c + "/history", headers).json()
    assert [item["version"] for item in versions["items"]] == [3, 2, 1]
    assert versions["items"][1]["snapshot"]["confirmed_at"] == stage.json()["confirmed_at"]
    updated = call(client, "PATCH", o, headers, {"expected_version": 1, "notes": "Corrected note"})
    assert (
        updated.status_code == 200 and updated.json()["recorded_by"] == observation["recorded_by"]
    )
    history = call(client, "GET", o + "/history", headers).json()
    assert [r["snapshot"]["notes"] for r in history["items"]] == [
        "Corrected note",
        OBSERVATION["notes"],
    ]
    archived = call(client, "POST", f + "/archive", headers, {"expected_version": 1})
    assert archived.status_code == 200 and archived.json()["effective_archived"]
    assert call(client, "GET", "/farms", headers).json()["total"] == 0
    assert call(client, "GET", "/farms?status=archived", headers).json()["total"] == 1
    assert call(client, "GET", c, headers).json()["effective_archived"]
    assert call(client, "GET", o, headers).json()["effective_archived"]
    assert call(client, "GET", f + "/cultivations", headers).json()["total"] == 0
    assert call(client, "GET", f + "/cultivations?status=archived", headers).json()["total"] == 1
    assert call(client, "POST", f + "/cultivations", headers, CULTIVATION).status_code == 409
    assert (
        call(client, "PATCH", o, headers, {"expected_version": 2, "notes": "Blocked"}).status_code
        == 409
    )
    with Session(accounts[1]) as db:
        assert db.scalar(select(func.count()).select_from(FarmAuditEvent)) == 7
        assert db.scalar(select(func.count()).select_from(FarmRevision)) == 2


def test_foreign_and_missing_ids_are_uniformly_hidden(account_client, accounts, farm_records):
    headers = login(account_client)
    unknown = {key: uuid4() for key in ("farm", "cultivation", "observation")}
    for foreign, missing in zip(
        operations(farm_records["other-farmer"]), operations(unknown), strict=True
    ):
        responses = [
            call(account_client, method, route, headers, data)
            for method, route, data in (foreign, missing)
        ]
        assert [r.status_code for r in responses] == [404, 404]
        assert responses[0].json()["code"] == responses[1].json()["code"] == "RECORD_NOT_FOUND"
        assert responses[0].json()["message"] == responses[1].json()["message"]
    for suffix in ("", "?status=all", "?q=SYNTHETIC-PRIVATE-FARM-other-farmer"):
        result = call(account_client, "GET", "/farms" + suffix, headers).json()
        assert result["total"] == (0 if "?q=" in suffix else 1)
        assert all(item["farmer_id"] == str(accounts[3]["farmer"]) for item in result["items"])
    with Session(accounts[1]) as db:
        assert db.scalar(select(func.count()).select_from(FarmAuditEvent)) == 6


@pytest.mark.parametrize("role", [None, "advisor", "admin"])
def test_all_routes_require_live_farmer_role(account_client, farm_records, role):
    headers = login(account_client, role) if role else {}
    all_ops = operations(farm_records["farmer"]) + [
        ("GET", "/farms", None),
        ("POST", "/farms", FARM),
        ("GET", "/crop-types", None),
    ]
    for method, route, data in all_ops:
        assert call(account_client, method, route, headers, data).status_code == (
            403 if role else 401
        )


def test_mixed_parent_chains_including_two_owned_farms_fail(account_client, farm_records):
    headers = login(account_client)
    own, foreign = farm_records["farmer"], farm_records["other-farmer"]
    second = call(account_client, "POST", "/farms", headers, FARM).json()["id"]
    for wrong_farm in (foreign["farm"], second):
        base = f"/farms/{wrong_farm}/cultivations/{own['cultivation']}"
        for method, suffix, data in [
            ("GET", "", None),
            ("GET", "/history", None),
            ("PATCH", "", {"expected_version": 1, "soil_notes": "Attempt"}),
            ("POST", "/archive", {"expected_version": 1}),
            ("POST", "/stage-confirmation", {"expected_version": 1, "stage": "Attempt"}),
        ]:
            assert call(account_client, method, base + suffix, headers, data).status_code == 404
    base = f"/cultivations/{own['cultivation']}/observations/{foreign['observation']}"
    assert call(account_client, "GET", base, headers).status_code == 404
    assert call(account_client, "GET", base + "/history", headers).status_code == 404
    assert (
        call(
            account_client, "PATCH", base, headers, {"expected_version": 1, "notes": "Attempt"}
        ).status_code
        == 404
    )


@pytest.mark.parametrize("state", ["revoked", "expired", "disabled", "deleted", "role_changed"])
def test_current_account_and_session_state_is_checked_on_every_route(
    account_client, accounts, farm_records, state
):
    headers = login(account_client)
    with Session(accounts[2]) as db, db.begin():
        user = db.get(User, accounts[3]["farmer"])
        session = db.scalar(select(RefreshSession).where(RefreshSession.user_id == user.id))
        if state == "revoked":
            session.revoked_at = datetime.now(UTC)
        elif state == "expired":
            session.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        elif state == "disabled":
            user.disabled_at = datetime.now(UTC)
        elif state == "deleted":
            user.deleted_at = datetime.now(UTC)
        else:
            user.role = "advisor"  # Even an unrevoked stale JWT cannot restore farmer rights.
    for method, route, data in operations(farm_records["farmer"]) + [("POST", "/farms", FARM)]:
        assert call(account_client, method, route, headers, data).status_code == (
            403 if state == "role_changed" else 401
        )


@pytest.mark.parametrize(
    "invalid",
    [
        {"farmer_id": str(uuid4())},
        {"name": " \t "},
        {"name": None},
        {"name": 12},
        {"location": "x" * 201},
        {"location": "private\x00payload"},
        {"latitude": "91"},
        {"longitude": None},
        {"latitude": "NaN"},
        {"area_value": "Infinity"},
        {"area_value": "0"},
        {"area_value": "-1"},
        {"area_value": "0.0000001"},
        {"area_value": "1000000000000"},
        {"area_unit": "acres"},
        {"area_unit": None},
        {"timezone": "Imaginary/Zone"},
        {"archived_at": "2026-01-01T00:00:00Z"},
        {"version": 99},
        {"confirmed_by": str(uuid4())},
    ],
)
def test_create_validation_is_safe_and_has_no_effect(account_client, accounts, invalid):
    headers = login(account_client)
    response = call(account_client, "POST", "/farms", headers, FARM | invalid)
    assert response.status_code == 422, response.text
    assert "private" not in response.text and "payload" not in response.text
    with Session(accounts[1]) as db:
        assert db.scalar(select(func.count()).select_from(Farm)) == 0
        assert db.scalar(select(func.count()).select_from(FarmAuditEvent)) == 0


@pytest.mark.parametrize(
    "target, invalid",
    [
        ("cultivation", {"planting_date": "2026-02-30"}),
        ("cultivation", {"planting_date": 123}),
        ("cultivation", {"crop_type_id": str(uuid4())}),
        ("cultivation", {"soil_notes": "x" * 2001}),
        ("cultivation", {"estimated_stage": "guessed"}),
        ("cultivation", {"confirmed_stage": "spoofed"}),
        ("observation", {"observed_at": "2099-01-01T00:00:00Z"}),
        ("observation", {"observed_at": "2026-01-01T00:00:00"}),
        ("observation", {"observed_at": 123}),
        ("observation", {"notes": " "}),
        ("observation", {"notes": "x" * 4001}),
        ("observation", {"recorded_by": str(uuid4())}),
    ],
)
def test_child_validation(account_client, farm_records, target, invalid):
    headers = login(account_client)
    ids = farm_records["farmer"]
    route = (
        f"/farms/{ids['farm']}/cultivations"
        if target == "cultivation"
        else f"/cultivations/{ids['cultivation']}/observations"
    )
    body = (CULTIVATION if target == "cultivation" else OBSERVATION) | invalid
    assert call(account_client, "POST", route, headers, body).status_code == 422


def test_patch_pairs_nulls_and_noops(account_client, accounts, farm_records):
    headers = login(account_client)
    f, c, o = path(farm_records["farmer"])
    for route, body in [
        (f, {"name": None}),
        (f, {"latitude": None}),
        (f, {"area_value": None}),
        (c, {"area_value": None}),
        (c, {"planting_date": None}),
        (o, {"notes": None}),
    ]:
        assert (
            call(
                account_client, "PATCH", route, headers, body | {"expected_version": 1}
            ).status_code
            == 422
        )
    assert call(account_client, "PATCH", f, headers, {"expected_version": True}).status_code == 422
    for route in (f, c, o):
        assert (
            call(account_client, "PATCH", route, headers, {"expected_version": 1}).json()["version"]
            == 1
        )
    changed = call(
        account_client,
        "PATCH",
        f,
        headers,
        {
            "expected_version": 1,
            "latitude": None,
            "longitude": None,
            "area_value": None,
            "area_unit": None,
        },
    )
    assert changed.status_code == 200 and changed.json()["version"] == 2
    assert changed.json()["latitude"] is changed.json()["area_value"] is None
    with Session(accounts[1]) as db:
        assert db.scalar(select(func.count()).select_from(FarmAuditEvent)) == 7


def test_provenance_and_parent_fields_cannot_be_mass_assigned(account_client, farm_records):
    headers = login(account_client)
    f, c, o = path(farm_records["farmer"])
    for route, values in [
        (f, {"farmer_id": str(uuid4())}),
        (f, {"id": str(uuid4())}),
        (f, {"created_at": "2026-01-01T00:00:00Z"}),
        (c, {"farm_id": str(uuid4())}),
        (c, {"confirmed_stage": "Spoofed"}),
        (c, {"confirmed_by": str(uuid4())}),
        (o, {"recorded_by": str(uuid4())}),
        (o, {"cultivation_id": str(uuid4())}),
    ]:
        assert (
            call(
                account_client, "PATCH", route, headers, {"expected_version": 1} | values
            ).status_code
            == 422
        )
    assert (
        call(
            account_client,
            "POST",
            c + "/stage-confirmation",
            headers,
            {
                "expected_version": 1,
                "stage": "Reported",
                "confirmed_by": str(uuid4()),
            },
        ).status_code
        == 422
    )


def test_stage_reconfirmation_and_crop_revision_history(
    account_client, accounts, farm_records, monkeypatch
):
    headers = login(account_client)
    _, c, o = path(farm_records["farmer"])
    fixed = datetime(2026, 11, 18, tzinfo=UTC)
    monkeypatch.setattr(service, "now", lambda: fixed)
    for version in (1, 2):
        confirmed = call(
            account_client,
            "POST",
            c + "/stage-confirmation",
            headers,
            {"expected_version": version, "stage": "Owner-reported stage"},
        )
        assert confirmed.status_code == 200 and confirmed.json()["version"] == version + 1
    # Soil edits retain confirmation; choosing a different supported crop invalidates it.
    edited = call(
        account_client, "PATCH", c, headers, {"expected_version": 3, "soil_notes": " Unknown "}
    )
    assert (
        edited.status_code == 200
        and edited.json()["confirmed_at"] == confirmed.json()["confirmed_at"]
    )
    alternative = uuid4()
    with Session(accounts[2]) as db, db.begin():
        db.add(
            CropType(
                id=alternative,
                code="synthetic_crop",
                display_name="Synthetic test crop",
                supported=True,
            )
        )
    changed = call(
        account_client,
        "PATCH",
        c,
        headers,
        {"expected_version": 4, "crop_type_id": str(alternative)},
    )
    assert changed.status_code == 200 and changed.json()["confirmed_by"] is None
    assert changed.json()["estimated_stage"] is None
    for route in (c, o):
        stale = call(account_client, "PATCH", route, headers, {"expected_version": 999})
        assert stale.status_code == 409
    history = call(account_client, "GET", c + "/history", headers).json()
    assert history["total"] == 5 and history["items"][1]["snapshot"]["confirmed_by"]


def test_filters_pagination_order_and_utc_bounds(account_client, farm_records):
    headers = login(account_client)
    ids = farm_records["farmer"]
    f, c, o = path(ids)
    assert (
        call(account_client, "GET", "/crop-types", headers).json()["items"][0]["code"] == "chilli"
    )
    result = call(account_client, "GET", "/farms?page_size=1&page=2", headers).json()
    assert result["items"] == [] and result["total"] == 1
    assert call(account_client, "GET", "/farms?q=%25", headers).json()["total"] == 0
    for query in ("page=0", "page=10001", "page_size=101", "status=deleted", "owner_id=spoofed"):
        assert call(account_client, "GET", "/farms?" + query, headers).status_code == 422
    route = f"/cultivations/{ids['cultivation']}/observations"
    before = call(account_client, "GET", route + "?to_date=2026-01-01", headers).json()
    assert before["total"] == 0
    on_date = call(
        account_client, "GET", route + "?from_date=2026-01-02&to_date=2026-01-02", headers
    ).json()
    assert on_date["total"] == 1
    assert (
        call(
            account_client, "GET", route + "?from_date=2026-01-03&to_date=2026-01-02", headers
        ).status_code
        == 422
    )
    assert call(account_client, "GET", o + "/history?page_size=1", headers).json()["total"] == 1


def test_unsupported_crop_and_timezone_planned_label(
    account_client, accounts, farm_records, monkeypatch
):
    headers = login(account_client)
    unsupported = uuid4()
    with Session(accounts[2]) as db, db.begin():
        db.add(
            CropType(
                id=unsupported,
                code="synthetic_unsupported",
                display_name="Synthetic",
                supported=False,
            )
        )
    ids = farm_records["farmer"]
    f, c, _ = path(ids)
    assert (
        call(
            account_client,
            "POST",
            f + "/cultivations",
            headers,
            CULTIVATION | {"crop_type_id": str(unsupported)},
        ).status_code
        == 422
    )
    assert (
        call(
            account_client,
            "PATCH",
            c,
            headers,
            {"expected_version": 1, "crop_type_id": str(unsupported)},
        ).status_code
        == 422
    )
    monkeypatch.setattr(service, "now", lambda: datetime(2026, 1, 9, 19, tzinfo=UTC))
    # Colombo is already January 10; UTC is still January 9.
    assert not call(account_client, "GET", c, headers).json()["planned"]
    assert (
        call(
            account_client, "PATCH", f, headers, {"expected_version": 1, "timezone": "UTC"}
        ).status_code
        == 200
    )
    assert call(account_client, "GET", c, headers).json()["planned"]
    with Session(accounts[2]) as db, db.begin():
        db.get(CropType, CHILLI_ID).supported = False
    # Historical records remain readable/editable, but even reassigning the same
    # now-unsupported crop ID is invalid input.
    assert call(account_client, "GET", c, headers).status_code == 200
    assert (
        call(
            account_client,
            "PATCH",
            c,
            headers,
            {"expected_version": 1, "crop_type_id": str(CHILLI_ID)},
        ).status_code
        == 422
    )
    assert (
        call(
            account_client,
            "PATCH",
            c,
            headers,
            {"expected_version": 1, "soil_notes": "Synthetic historical context"},
        ).status_code
        == 200
    )


def test_version_archive_repeats_and_inherited_readonly(account_client, accounts, farm_records):
    headers = login(account_client)
    f, c, o = path(farm_records["farmer"])
    archived = call(account_client, "POST", c + "/archive", headers, {"expected_version": 1})
    assert archived.status_code == 200 and archived.json()["version"] == 2
    assert (
        call(account_client, "POST", c + "/archive", headers, {"expected_version": 1}).status_code
        == 409
    )
    assert (
        call(account_client, "POST", c + "/archive", headers, {"expected_version": 2}).status_code
        == 200
    )
    for method, route, body in [
        ("PATCH", c, {"expected_version": 2, "soil_notes": "Blocked"}),
        ("POST", c + "/stage-confirmation", {"expected_version": 2, "stage": "Blocked"}),
        ("PATCH", o, {"expected_version": 1, "notes": "Blocked"}),
        (
            "POST",
            f"/cultivations/{farm_records['farmer']['cultivation']}/observations",
            OBSERVATION,
        ),
    ]:
        assert call(account_client, method, route, headers, body).status_code == 409
    assert call(account_client, "GET", o + "/history", headers).status_code == 200
    assert (
        call(account_client, "GET", f + "/cultivations?status=archived", headers).json()["total"]
        == 1
    )
    with Session(accounts[1]) as db:
        assert db.scalar(select(func.count()).select_from(FarmAuditEvent)) == 7


@pytest.mark.parametrize(
    "method, route, body",
    [
        ("POST", "/farms", FARM),
        ("PATCH", "/farms/{farm}", {"expected_version": 1, "name": "Blocked"}),
        ("POST", "/farms/{farm}/archive", {"expected_version": 1}),
    ],
)
def test_browser_write_protection(account_client, farm_records, method, route, body):
    headers = login(account_client) | {"Origin": "https://untrusted.example"}
    assert (
        call(
            account_client, method, route.format(**farm_records["farmer"]), headers, body
        ).status_code
        == 403
    )


@pytest.mark.parametrize("target", ["farm_revisions", "farm_audit_events"])
@pytest.mark.parametrize("deferred", [False, True])
def test_http_commit_and_insert_failures_never_report_success(
    account_client, accounts, farm_records, target, deferred
):
    headers = login(account_client)
    with accounts[2].begin() as conn:
        conn.execute(
            text("""
            CREATE FUNCTION public.frc_test_failure() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN RAISE EXCEPTION 'Synthetic private farm failure' USING ERRCODE='23514'; END; $$
        """)
        )
        mode = "DEFERRABLE INITIALLY DEFERRED" if deferred else ""
        conn.execute(
            text(
                f"CREATE CONSTRAINT TRIGGER frc_test_failure AFTER INSERT ON {target} "
                f"{mode} FOR EACH ROW EXECUTE FUNCTION public.frc_test_failure()"
            )
        )
    try:
        result = call(account_client, "POST", "/farms", headers, FARM)
        assert result.status_code == 503
        assert "Synthetic" not in result.text and "INSERT" not in result.text
        with Session(accounts[1]) as db:
            assert db.scalar(select(func.count()).select_from(Farm)) == 2
            assert db.scalar(select(func.count()).select_from(FarmRevision)) == 2
            assert db.scalar(select(func.count()).select_from(FarmAuditEvent)) == 6
    finally:
        with accounts[2].begin() as conn:
            conn.execute(text(f"DROP TRIGGER frc_test_failure ON {target}"))
            conn.execute(text("DROP FUNCTION public.frc_test_failure()"))


def test_concurrent_stale_edits_have_one_effect(account_client, accounts, farm_records):
    headers = login(account_client)
    f, _, _ = path(farm_records["farmer"])
    barrier = Barrier(2)

    def edit(index):
        barrier.wait(timeout=10)
        return call(
            account_client,
            "PATCH",
            f,
            headers,
            {"expected_version": 1, "name": f"Synthetic edit {index}"},
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(edit, range(2))) == [200, 409]
    with Session(accounts[1]) as db:
        assert db.get(Farm, farm_records["farmer"]["farm"]).version == 2
        assert db.scalar(select(func.count()).select_from(FarmRevision)) == 3


def wait_for_database_lock(owner):
    deadline = monotonic() + 5
    while monotonic() < deadline:
        with owner.connect() as conn:
            if conn.scalar(
                text(
                    "SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() "
                    "AND pid <> pg_backend_pid() AND wait_event_type='Lock'"
                )
            ):
                return
        Event().wait(0.02)
    pytest.fail("The concurrent request never waited on a real PostgreSQL lock")


@pytest.mark.parametrize("first", ["archive", "observation"])
def test_archive_and_child_creation_serialize_in_either_order(
    account_client, accounts, farm_records, monkeypatch, first
):
    headers = login(account_client)
    ids = farm_records["farmer"]
    f, _, _ = path(ids)
    entered, release = Event(), Event()
    original = service.retain
    first_operation = "farm_archived" if first == "archive" else "observation_created"

    def paused(db, record, actor_id, operation, *args, **kwargs):
        if operation == first_operation:
            entered.set()
            assert release.wait(timeout=10)
        return original(db, record, actor_id, operation, *args, **kwargs)

    monkeypatch.setattr(service, "retain", paused)

    def archive():
        return call(account_client, "POST", f + "/archive", headers, {"expected_version": 1})

    def observe():
        return call(
            account_client,
            "POST",
            f"/cultivations/{ids['cultivation']}/observations",
            headers,
            OBSERVATION,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        pending = pool.submit(archive if first == "archive" else observe)
        try:
            assert entered.wait(timeout=10)
            second = pool.submit(observe if first == "archive" else archive)
            wait_for_database_lock(accounts[2])
        finally:
            release.set()
        assert pending.result(timeout=10).status_code == (200 if first == "archive" else 201)
        assert second.result(timeout=10).status_code == (409 if first == "archive" else 200)


def test_disable_committing_before_waiting_farm_write_revokes_it(
    account_client, accounts, farm_records, monkeypatch
):
    farmer_headers = login(account_client)
    admin_headers = login(account_client, "admin")
    entered, release = Event(), Event()
    original = identity.write_audit

    def paused(*args, **kwargs):
        original(*args, **kwargs)
        entered.set()
        assert release.wait(timeout=10)

    monkeypatch.setattr(identity, "write_audit", paused)
    with ThreadPoolExecutor(max_workers=2) as pool:
        disable = pool.submit(
            call,
            account_client,
            "PATCH",
            f"/admin/users/{accounts[3]['farmer']}/status",
            admin_headers,
            {"enabled": False, "expected_version": 1, "reason": "Synthetic disable"},
        )
        try:
            assert entered.wait(timeout=10)
            create = pool.submit(call, account_client, "POST", "/farms", farmer_headers, FARM)
            wait_for_database_lock(accounts[2])
        finally:
            release.set()
        assert disable.result(timeout=10).status_code == 200
        assert create.result(timeout=10).status_code == 401
    with Session(accounts[1]) as db:
        assert db.scalar(select(func.count()).select_from(Farm)) == 2


def test_services_also_enforce_identity_without_route_dependencies(
    account_client, accounts, farm_records
):
    login(account_client, "admin")
    with Session(accounts[1]) as db:
        session = db.scalar(
            select(RefreshSession).where(RefreshSession.user_id == accounts[3]["admin"])
        )
        with pytest.raises(IdentityError) as error:
            service.get_farm(db, (session.user_id, session.id), farm_records["farmer"]["farm"])
        assert error.value.status == 403


def test_farm_restore_reopens_inherited_children_but_keeps_independent_archives(
    account_client, accounts, farm_records
):
    headers = login(account_client)
    f, c, _ = path(farm_records["farmer"])
    second = call(account_client, "POST", f + "/cultivations", headers, CULTIVATION).json()
    second_path = f + f"/cultivations/{second['id']}"
    assert (
        call(account_client, "POST", c + "/archive", headers, {"expected_version": 1}).status_code
        == 200
    )
    assert (
        call(account_client, "POST", f + "/archive", headers, {"expected_version": 1}).status_code
        == 200
    )
    assert call(account_client, "GET", second_path, headers).json()["effective_archived"]
    restored = call(account_client, "POST", f + "/restore", headers, {"expected_version": 2})
    assert restored.status_code == 200 and restored.json()["version"] == 3
    assert restored.json()["archived_at"] is None and not restored.json()["effective_archived"]
    assert call(account_client, "GET", c, headers).json()["effective_archived"]
    assert not call(account_client, "GET", second_path, headers).json()["effective_archived"]
    assert (
        call(account_client, "POST", f + "/restore", headers, {"expected_version": 3}).json()[
            "version"
        ]
        == 3
    )
    assert (
        call(account_client, "POST", f + "/restore", headers, {"expected_version": 2}).status_code
        == 409
    )
    assert (
        call(
            account_client,
            "PATCH",
            f,
            headers,
            {"expected_version": 3, "name": "Restored synthetic farm"},
        ).status_code
        == 200
    )
    assert (
        call(
            account_client,
            "POST",
            f"/cultivations/{second['id']}/observations",
            headers,
            OBSERVATION,
        ).status_code
        == 201
    )
    revisions = call(account_client, "GET", f + "/history", headers).json()["items"]
    assert [r["version"] for r in revisions] == [4, 3, 2, 1]
    assert revisions[1]["snapshot"]["archived_at"] is None
    assert revisions[2]["snapshot"]["archived_at"] is not None
    with Session(accounts[1]) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(FarmAuditEvent)
                .where(
                    FarmAuditEvent.farm_id == farm_records["farmer"]["farm"],
                    FarmAuditEvent.operation == "farm_restored",
                )
            )
            == 1
        )


def test_farm_delete_hides_every_child_link_and_retains_atomic_evidence(
    account_client, accounts, farm_records
):
    headers = login(account_client)
    ids = farm_records["farmer"]
    f, _, _ = path(ids)
    name = call(account_client, "GET", f, headers).json()["name"]
    command = {"expected_version": 1, "confirmation_name": name}
    assert call(account_client, "POST", f + "/delete", headers, command).status_code == 409
    call(account_client, "POST", f + "/archive", headers, {"expected_version": 1})
    assert call(account_client, "POST", f + "/delete", headers, command).status_code == 409
    command["expected_version"] = 2
    assert (
        call(
            account_client, "POST", f + "/delete", headers, command | {"confirmation_name": "wrong"}
        ).status_code
        == 422
    )
    removed = call(account_client, "POST", f + "/delete", headers, command)
    assert removed.status_code == 200 and removed.json()["deleted"] is True
    assert "Historical records are retained" in removed.json()["message"]
    for status in ("active", "archived", "all"):
        page = call(account_client, "GET", f"/farms?status={status}&page_size=1", headers).json()
        assert page["total"] == 0 and page["items"] == []
    for method, route, data in operations(ids):
        assert call(account_client, method, route, headers, data).status_code == 404
    other = login(account_client, "other-farmer")
    assert call(account_client, "GET", "/farms?status=all", other).json()["total"] == 1
    with Session(accounts[1]) as db:
        deletion = db.get(FarmDeletion, ids["farm"])
        assert deletion.deleted_by == accounts[3]["farmer"] and deletion.deleted_at
        assert deletion.entity_version == db.get(Farm, ids["farm"]).version == 3
        assert (
            db.scalar(
                select(func.count())
                .select_from(FarmRevision)
                .where(FarmRevision.farm_id == ids["farm"])
            )
            == 3
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(FarmAuditEvent)
                .where(
                    FarmAuditEvent.farm_id == ids["farm"],
                    FarmAuditEvent.operation == "farm_deleted",
                )
            )
            == 1
        )
        assert db.scalar(select(func.count()).select_from(Farm)) == 2


@pytest.mark.parametrize(
    "body",
    [
        {"expected_version": 1},
        {"expected_version": 0, "confirmation_name": "Synthetic"},
        {"expected_version": 1, "confirmation_name": " "},
        {"expected_version": 1, "confirmation_name": "x" * 121},
        {"expected_version": 1, "confirmation_name": "Synthetic", "deleted_by": str(uuid4())},
    ],
)
def test_delete_command_allowlist_and_required_confirmation(
    account_client, accounts, farm_records, body
):
    headers = login(account_client)
    f, _, _ = path(farm_records["farmer"])
    assert call(account_client, "POST", f + "/delete", headers, body).status_code == 422
    with Session(accounts[1]) as db:
        assert db.scalar(select(func.count()).select_from(FarmDeletion)) == 0
        assert db.get(Farm, farm_records["farmer"]["farm"]).version == 1


@pytest.mark.parametrize(
    "action,target",
    [
        ("restore", "farm_revisions"),
        ("restore", "farm_audit_events"),
        ("delete", "farm_revisions"),
        ("delete", "farm_audit_events"),
        ("delete", "farm_deletions"),
    ],
)
@pytest.mark.parametrize("deferred", [False, True])
def test_lifecycle_failure_rolls_back_before_http_success(
    account_client, accounts, farm_records, action, target, deferred
):
    headers = login(account_client)
    ids = farm_records["farmer"]
    f, _, _ = path(ids)
    call(account_client, "POST", f + "/archive", headers, {"expected_version": 1})
    with accounts[2].begin() as conn:
        conn.execute(
            text(
                "CREATE FUNCTION public.lifecycle_test_failure() RETURNS trigger "
                "LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Synthetic lifecycle failure' "
                "USING ERRCODE='23514'; END; $$"
            )
        )
        mode = "DEFERRABLE INITIALLY DEFERRED" if deferred else ""
        conn.execute(
            text(
                f"CREATE CONSTRAINT TRIGGER lifecycle_test_failure AFTER INSERT ON {target} "
                f"{mode} FOR EACH ROW EXECUTE FUNCTION public.lifecycle_test_failure()"
            )
        )
    try:
        command = {"expected_version": 2}
        if action == "delete":
            command["confirmation_name"] = "SYNTHETIC-PRIVATE-FARM-farmer"
        result = call(account_client, "POST", f + f"/{action}", headers, command)
        assert result.status_code == 503 and "Synthetic" not in result.text
        with Session(accounts[1]) as db:
            assert db.get(Farm, ids["farm"]).version == 2
            assert db.get(Farm, ids["farm"]).archived_at is not None
            assert db.get(FarmDeletion, ids["farm"]) is None
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(FarmRevision)
                    .where(FarmRevision.farm_id == ids["farm"])
                )
                == 2
            )
    finally:
        with accounts[2].begin() as conn:
            conn.execute(text(f"DROP TRIGGER lifecycle_test_failure ON {target}"))
            conn.execute(text("DROP FUNCTION public.lifecycle_test_failure()"))


@pytest.mark.parametrize(
    "first_action,second_action",
    [("restore", "delete"), ("delete", "restore"), ("delete", "delete")],
)
def test_restore_and_delete_serialize_with_one_effect(
    account_client, accounts, farm_records, monkeypatch, first_action, second_action
):
    headers = login(account_client)
    ids = farm_records["farmer"]
    f, _, _ = path(ids)
    call(account_client, "POST", f + "/archive", headers, {"expected_version": 1})
    entered, release = Event(), Event()
    original = service.retain
    operation = "farm_restored" if first_action == "restore" else "farm_deleted"

    def paused(db, record, actor_id, actual, *args, **kwargs):
        if actual == operation:
            entered.set()
            assert release.wait(timeout=10)
        return original(db, record, actor_id, actual, *args, **kwargs)

    monkeypatch.setattr(service, "retain", paused)

    def command(action):
        body = {"expected_version": 2}
        if action == "delete":
            body["confirmation_name"] = "SYNTHETIC-PRIVATE-FARM-farmer"
        return call(account_client, "POST", f + f"/{action}", headers, body)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(command, first_action)
        try:
            assert entered.wait(timeout=10)
            second = pool.submit(command, second_action)
            wait_for_database_lock(accounts[2])
        finally:
            release.set()
        assert first.result(timeout=10).status_code == 200
        assert second.result(timeout=10).status_code == (409 if first_action == "restore" else 404)
    with Session(accounts[1]) as db:
        assert db.get(Farm, ids["farm"]).version == 3
        assert (db.get(FarmDeletion, ids["farm"]) is not None) == (first_action == "delete")

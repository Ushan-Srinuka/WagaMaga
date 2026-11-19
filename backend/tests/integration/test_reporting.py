"""Count-only administrator reporting, privacy, audit and lifecycle evidence."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Event
from time import monotonic
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text, update
from sqlalchemy.orm import Session

from app.modules.farms.models import CHILLI_ID, Farm
from app.modules.identity import service as identity
from app.modules.identity.models import AuditLog, RefreshSession, User
from app.modules.identity.security import IdentityError
from app.modules.reporting import service

pytestmark = pytest.mark.integration
ROOT = "/api/v1"


def login(client, who="admin"):
    response = client.post(
        ROOT + "/auth/login",
        json={"email": f"{who}@example.com", "password": "a synthetic growing season password 1!"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def call(client, method, path, headers, data=None):
    result = client.request(
        method, ROOT + path, headers=headers, **({"json": data} if data is not None else {})
    )
    assert result.headers["cache-control"] == "no-store" and result.headers.get("x-request-id")
    return result


def test_overview_counts_are_allowlisted_not_private_record_projections(
    account_client, accounts, farm_records
):
    admin, farmer, other = (
        login(account_client),
        login(account_client, "farmer"),
        login(account_client, "other-farmer"),
    )
    own, foreign = farm_records["farmer"], farm_records["other-farmer"]
    crop = call(
        account_client,
        "POST",
        f"/farms/{own['farm']}/cultivations",
        farmer,
        {
            "crop_type_id": str(CHILLI_ID),
            "planting_date": "2026-01-01",
            "area_value": "1",
            "area_unit": "ha",
        },
    ).json()
    call(
        account_client,
        "POST",
        f"/farms/{own['farm']}/cultivations/{crop['id']}/archive",
        farmer,
        {"expected_version": 1},
    )
    call(account_client, "POST", f"/farms/{own['farm']}/archive", farmer, {"expected_version": 1})
    call(
        account_client, "POST", f"/farms/{foreign['farm']}/archive", other, {"expected_version": 1}
    )
    removed = call(
        account_client,
        "POST",
        f"/farms/{foreign['farm']}/delete",
        other,
        {"expected_version": 2, "confirmation_name": "SYNTHETIC-PRIVATE-FARM-other-farmer"},
    )
    assert removed.status_code == 200
    for index, owner in enumerate((farmer, farmer, other)):
        ticket = call(
            account_client,
            "POST",
            "/support/tickets",
            owner,
            {
                "category": "technical",
                "subject": f"Private synthetic subject {index}",
                "body": "Private synthetic body",
            },
        ).json()
        if index:
            call(
                account_client,
                "POST",
                f"/admin/support/tickets/{ticket['id']}/status",
                admin,
                {"expected_version": 1, "status": "in_progress" if index == 1 else "resolved"},
            )
    response = call(account_client, "GET", "/admin/overview", admin)
    assert response.status_code == 200
    report = response.json()
    assert set(report) == {"generated_at", "accounts", "farms", "cultivations", "support"}
    assert report["accounts"] == {
        "total": 5,
        "enabled": 5,
        "disabled": 0,
        "farmers": 2,
        "advisors": 1,
        "administrators": 2,
        "new_farmers_30_days": 2,
        "removed": 0,
    }
    assert report["farms"] == {"total": 1, "active": 0, "archived": 1}
    assert report["cultivations"] == {"total": 2, "active": 0, "archived": 2}
    assert report["support"] == {"total": 3, "open": 1, "in_progress": 1, "resolved": 1}
    assert "SYNTHETIC-PRIVATE" not in response.text and "Private synthetic" not in response.text
    assert '"latitude"' not in response.text and '"longitude"' not in response.text
    assert str(own["farm"]) not in response.text and str(foreign["farm"]) not in response.text
    call(account_client, "POST", f"/farms/{own['farm']}/restore", farmer, {"expected_version": 2})
    summary = call(
        account_client, "GET", f"/admin/users/{accounts[3]['farmer']}/farm-summary", admin
    ).json()
    assert summary["farms"] == {"total": 1, "active": 1, "archived": 0}
    assert summary["cultivations"] == {"total": 2, "active": 1, "archived": 1}
    assert set(summary) == {"user_id", "generated_at", "farms", "cultivations"}
    for suffix in ("", "/history", f"/cultivations/{own['cultivation']}"):
        assert (
            call(account_client, "GET", f"/farms/{own['farm']}" + suffix, admin).status_code == 403
        )
    with Session(accounts[1]) as db:
        assert db.scalar(select(func.count()).select_from(Farm)) == 2
        events = db.scalars(select(AuditLog).where(AuditLog.action == "report_viewed")).all()
        assert len(events) == 2
        assert {e.new_value for e in events} == {"overview", "farmer_summary"}
        assert all(
            e.reason == "Administrator viewed count summary" and e.request_id for e in events
        )


@pytest.mark.parametrize("who", [None, "farmer", "advisor"])
def test_reports_require_live_admin_before_target_lookup(account_client, accounts, who):
    headers = login(account_client, who) if who else {}
    for route in (
        "/admin/overview",
        f"/admin/users/{accounts[3]['farmer']}/farm-summary",
        f"/admin/users/{uuid4()}/farm-summary",
    ):
        assert call(account_client, "GET", route, headers).status_code == (
            401 if who is None else 403
        )
    with Session(accounts[1]) as db:
        assert (
            db.scalar(
                select(func.count()).select_from(AuditLog).where(AuditLog.action == "report_viewed")
            )
            == 0
        )


def test_zero_counts_are_real_and_old_or_future_signups_are_not_new(account_client, accounts):
    with Session(accounts[2]) as db, db.begin():
        db.execute(
            update(User)
            .where(User.id == accounts[3]["farmer"])
            .values(created_at=datetime.now(UTC) - timedelta(days=31))
        )
        db.execute(
            update(User)
            .where(User.id == accounts[3]["other-farmer"])
            .values(created_at=datetime.now(UTC) + timedelta(days=1))
        )
    report = call(account_client, "GET", "/admin/overview", login(account_client)).json()
    assert report["accounts"]["new_farmers_30_days"] == 0
    assert report["farms"] == report["cultivations"] == {"total": 0, "active": 0, "archived": 0}
    assert report["support"] == {"total": 0, "open": 0, "in_progress": 0, "resolved": 0}


def test_disabled_farmers_remain_in_record_counts_but_removed_or_former_farmers_do_not(
    account_client, accounts, farm_records
):
    admin = login(account_client)
    call(
        account_client,
        "PATCH",
        f"/admin/users/{accounts[3]['farmer']}/status",
        admin,
        {"enabled": False, "expected_version": 1, "reason": "Synthetic count definition"},
    )
    report = call(account_client, "GET", "/admin/overview", admin).json()
    assert report["accounts"]["disabled"] == 1 and report["accounts"]["enabled"] == 4
    assert report["farms"]["total"] == 2
    call(
        account_client,
        "PATCH",
        f"/admin/users/{accounts[3]['other-farmer']}/role",
        admin,
        {"role": "advisor", "expected_version": 1, "reason": "Synthetic count definition"},
    )
    assert call(account_client, "GET", "/admin/overview", admin).json()["farms"]["total"] == 1
    assert (
        call(
            account_client, "GET", f"/admin/users/{accounts[3]['other-farmer']}/farm-summary", admin
        ).status_code
        == 404
    )
    call(
        account_client,
        "DELETE",
        f"/admin/users/{accounts[3]['farmer']}",
        admin,
        {"expected_version": 2, "reason": "Synthetic count definition"},
    )
    final = call(account_client, "GET", "/admin/overview", admin).json()
    assert final["accounts"]["removed"] == 1 and final["accounts"]["total"] == 4
    assert final["farms"]["total"] == 0 and final["cultivations"]["total"] == 0
    assert (
        call(
            account_client, "GET", f"/admin/users/{accounts[3]['farmer']}/farm-summary", admin
        ).status_code
        == 404
    )


@pytest.mark.parametrize("path", ["/admin/overview", "/admin/users/{farmer}/farm-summary"])
@pytest.mark.parametrize("deferred", [False, True])
def test_report_is_not_returned_if_view_audit_cannot_commit(
    account_client, accounts, path, deferred
):
    admin = login(account_client)
    with accounts[2].begin() as conn:
        conn.execute(
            text(
                "CREATE FUNCTION public.report_test_failure() RETURNS trigger "
                "LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Synthetic report failure' "
                "USING ERRCODE='23514'; END; $$"
            )
        )
        mode = "DEFERRABLE INITIALLY DEFERRED" if deferred else ""
        conn.execute(
            text(
                "CREATE CONSTRAINT TRIGGER report_test_failure AFTER INSERT ON audit_logs "
                f"{mode} FOR EACH ROW EXECUTE FUNCTION public.report_test_failure()"
            )
        )
    try:
        response = call(account_client, "GET", path.format(farmer=accounts[3]["farmer"]), admin)
        assert response.status_code == 503 and "Synthetic" not in response.text
        assert "farms" not in response.json()
        with Session(accounts[1]) as db:
            assert db.scalar(select(func.count()).select_from(AuditLog)) == 0
    finally:
        with accounts[2].begin() as conn:
            conn.execute(text("DROP TRIGGER report_test_failure ON audit_logs"))
            conn.execute(text("DROP FUNCTION public.report_test_failure()"))


def test_reporting_service_also_enforces_admin_permissions(account_client, accounts):
    login(account_client, "farmer")
    with Session(accounts[1]) as db:
        session = db.scalar(
            select(RefreshSession).where(RefreshSession.user_id == accounts[3]["farmer"])
        )
        with pytest.raises(IdentityError) as denied:
            service.overview(db, (session.user_id, session.id), str(uuid4()))
        assert denied.value.status == 403


def test_report_waiting_behind_admin_revocation_returns_no_counts(
    account_client, accounts, monkeypatch
):
    admin, other = login(account_client), login(account_client, "second-admin")
    entered, release = Event(), Event()
    original = identity.write_audit

    def paused(*args, **kwargs):
        original(*args, **kwargs)
        entered.set()
        assert release.wait(timeout=10)

    monkeypatch.setattr(identity, "write_audit", paused)
    with ThreadPoolExecutor(max_workers=2) as pool:
        disabled = pool.submit(
            call,
            account_client,
            "PATCH",
            f"/admin/users/{accounts[3]['admin']}/status",
            other,
            {"enabled": False, "expected_version": 1, "reason": "Synthetic report revocation"},
        )
        try:
            assert entered.wait(timeout=10)
            response = pool.submit(call, account_client, "GET", "/admin/overview", admin)
            deadline = monotonic() + 5
            waiting = False
            while monotonic() < deadline:
                with accounts[2].connect() as conn:
                    waiting = conn.scalar(
                        text(
                            "SELECT EXISTS (SELECT 1 FROM pg_stat_activity "
                            "WHERE datname=current_database() AND pid<>pg_backend_pid() "
                            "AND wait_event_type='Lock')"
                        )
                    )
                if waiting:
                    break
                Event().wait(0.02)
            assert waiting
        finally:
            release.set()
        assert disabled.result(timeout=10).status_code == 200
        assert response.result(timeout=10).status_code == 401

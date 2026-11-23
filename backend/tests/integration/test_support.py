"""Real PostgreSQL support permissions, evidence, notification and race coverage."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier, Event
from time import monotonic
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.main import create_app
from app.modules.identity import service as identity
from app.modules.identity.models import AuditLog, RefreshSession
from app.modules.identity.security import IdentityError
from app.modules.notifications.models import Notification
from app.modules.support import schemas as dto
from app.modules.support import service
from app.modules.support.models import SupportEvent, SupportMessage, SupportTicket

pytestmark = pytest.mark.integration
ROOT = "/api/v1"
BASE = "/support/tickets"
ADMIN = "/admin/support/tickets"
BODY = {
    "category": "farm_records",
    "subject": "Synthetic support question",
    "body": "Synthetic private message <b>plain text</b>",
}


def login(client, who="farmer"):
    result = client.post(
        ROOT + "/auth/login",
        json={"email": f"{who}@example.com", "password": "a synthetic growing season password 1!"},
    )
    assert result.status_code == 200
    return {"Authorization": f"Bearer {result.json()['access_token']}"}


def call(client, method, path, headers, data=None):
    response = client.request(
        method, ROOT + path, headers=headers, **({"json": data} if data is not None else {})
    )
    assert response.headers["cache-control"] == "no-store"
    assert response.headers.get("x-request-id")
    return response


def create(client, headers, **overrides):
    response = call(client, "POST", BASE, headers, BODY | overrides)
    assert response.status_code == 201, response.text
    return response.json()


def test_support_lifecycle_keeps_messages_events_and_notices_atomic(account_client, accounts):
    farmer, admin = login(account_client), login(account_client, "admin")
    ticket = create(account_client, farmer)
    own, office = BASE + f"/{ticket['id']}", ADMIN + f"/{ticket['id']}"
    assert ticket["status"] == "open" and ticket["version"] == 1
    assert (
        call(
            account_client,
            "POST",
            office + "/status",
            admin,
            {"status": "in_progress", "expected_version": 1},
        ).json()["version"]
        == 2
    )
    assert (
        call(
            account_client,
            "POST",
            own + "/messages",
            farmer,
            {"body": "Farmer follow-up", "expected_version": 2},
        ).json()["version"]
        == 3
    )
    assert (
        call(
            account_client,
            "POST",
            office + "/messages",
            admin,
            {"body": "Private support answer", "expected_version": 3},
        ).json()["version"]
        == 4
    )
    assert (
        call(
            account_client,
            "POST",
            own + "/status",
            farmer,
            {"status": "resolved", "expected_version": 4},
        ).json()["version"]
        == 5
    )
    assert (
        call(
            account_client,
            "POST",
            office + "/messages",
            admin,
            {"body": "Blocked", "expected_version": 5},
        ).status_code
        == 409
    )
    assert (
        call(
            account_client,
            "POST",
            own + "/status",
            farmer,
            {"status": "open", "expected_version": 5},
        ).json()["version"]
        == 6
    )
    second_admin = login(account_client, "second-admin")
    assert (
        call(
            account_client,
            "POST",
            office + "/messages",
            second_admin,
            {"body": "Second support answer", "expected_version": 6},
        ).json()["version"]
        == 7
    )
    resolved = call(
        account_client,
        "POST",
        office + "/status",
        admin,
        {"status": "resolved", "expected_version": 7},
    )
    assert resolved.json()["version"] == 8
    assert (
        call(
            account_client,
            "POST",
            office + "/status",
            admin,
            {"status": "resolved", "expected_version": 8},
        ).json()["version"]
        == 8
    )
    messages = call(account_client, "GET", own + "/messages?page_size=2", farmer).json()
    assert messages["total"] == 4 and [item["ticket_version"] for item in messages["items"]] == [
        7,
        4,
    ]
    assert all("author_id" not in item and "email" not in item for item in messages["items"])
    notices = call(account_client, "GET", "/notifications", farmer)
    assert "Private support answer" not in notices.text and BODY["subject"] not in notices.text
    assert len([n for n in notices.json()["items"] if n["event_type"] == "support_updated"]) == 4
    with Session(accounts[1]) as db:
        assert db.scalar(select(func.count()).select_from(SupportEvent)) == 8
        assert db.scalar(select(func.count()).select_from(SupportMessage)) == 4
        assert db.scalar(select(func.count()).select_from(AuditLog)) == 0


def test_other_owner_and_missing_support_links_are_uniform(account_client, accounts):
    farmer = login(account_client)
    other = login(account_client, "other-farmer")
    ticket = create(account_client, other, subject="Other owner's support request")
    create(account_client, farmer)
    for suffix, method, data in (
        ("", "GET", None),
        ("/messages", "GET", None),
        ("/messages", "POST", {"body": "Attempt", "expected_version": 1}),
        ("/status", "POST", {"status": "resolved", "expected_version": 1}),
    ):
        responses = [
            call(account_client, method, BASE + f"/{identifier}" + suffix, farmer, data)
            for identifier in (ticket["id"], uuid4())
        ]
        assert [r.status_code for r in responses] == [404, 404]
        assert responses[0].json()["message"] == responses[1].json()["message"]
        assert "Other owner" not in responses[0].text
    for query in ("", "?status=open&page_size=1", "?category=farm_records"):
        result = call(account_client, "GET", BASE + query, farmer).json()
        assert result["total"] == 1
        assert result["items"][0]["farmer_id"] == str(accounts[3]["farmer"])


@pytest.mark.parametrize("who", [None, "advisor", "admin"])
def test_farmer_routes_exclude_other_roles(account_client, who):
    headers = login(account_client, who) if who else {}
    identifier = uuid4()
    for method, path, body in (
        ("GET", BASE, None),
        ("POST", BASE, BODY),
        ("GET", BASE + f"/{identifier}", None),
        ("GET", BASE + f"/{identifier}/messages", None),
        ("POST", BASE + f"/{identifier}/messages", {"body": "Attempt", "expected_version": 1}),
        ("POST", BASE + f"/{identifier}/status", {"status": "open", "expected_version": 1}),
    ):
        assert call(account_client, method, path, headers, body).status_code == (
            401 if who is None else 403
        )


@pytest.mark.parametrize("who", [None, "farmer", "advisor"])
def test_admin_routes_exclude_other_roles(account_client, who):
    headers = login(account_client, who) if who else {}
    identifier = uuid4()
    for method, suffix, body in (
        ("GET", "", None),
        ("GET", f"/{identifier}", None),
        ("GET", f"/{identifier}/messages", None),
        ("POST", f"/{identifier}/messages", {"body": "Attempt", "expected_version": 1}),
        ("POST", f"/{identifier}/status", {"status": "in_progress", "expected_version": 1}),
    ):
        assert call(account_client, method, ADMIN + suffix, headers, body).status_code == (
            401 if who is None else 403
        )


def test_farmer_status_scope_and_version_conflicts(account_client, accounts):
    farmer, admin = login(account_client), login(account_client, "admin")
    ticket = create(account_client, farmer)
    own, office = BASE + f"/{ticket['id']}", ADMIN + f"/{ticket['id']}"
    assert (
        call(
            account_client,
            "POST",
            own + "/status",
            farmer,
            {"status": "in_progress", "expected_version": 1},
        ).status_code
        == 403
    )
    call(
        account_client,
        "POST",
        office + "/status",
        admin,
        {"status": "in_progress", "expected_version": 1},
    )
    assert (
        call(
            account_client,
            "POST",
            own + "/status",
            farmer,
            {"status": "open", "expected_version": 2},
        ).status_code
        == 409
    )
    assert (
        call(
            account_client,
            "POST",
            own + "/messages",
            farmer,
            {"body": "Stale", "expected_version": 1},
        ).status_code
        == 409
    )
    assert (
        call(
            account_client, "GET", ADMIN + "?status=in_progress&category=farm_records", admin
        ).json()["total"]
        == 1
    )
    assert call(account_client, "GET", ADMIN + "?status=resolved", admin).json()["total"] == 0


@pytest.mark.parametrize(
    "changes",
    [
        {"body": " "},
        {"subject": "x" * 121},
        {"body": "x" * 4001},
        {"category": "agricultural_advice"},
        {"farmer_id": str(uuid4())},
        {"farm_id": str(uuid4())},
        {"status": "resolved"},
        {"author_role": "administrator"},
    ],
)
def test_ticket_input_allowlist(account_client, accounts, changes):
    headers = login(account_client)
    result = call(account_client, "POST", BASE, headers, BODY | changes)
    assert result.status_code == 422
    assert BODY["body"] not in result.text
    with Session(accounts[1]) as db:
        assert db.scalar(select(func.count()).select_from(SupportTicket)) == 0


def test_browser_write_protection_and_creation_limit(account_client):
    headers = login(account_client)
    denied = account_client.post(
        ROOT + BASE, headers=headers | {"Origin": "https://untrusted.example.com"}, json=BODY
    )
    assert denied.status_code == 403
    for _ in range(5):
        create(account_client, headers)
    assert call(account_client, "POST", BASE, headers, BODY).status_code == 429


@pytest.mark.parametrize(
    "target", ["support_tickets", "support_messages", "support_events", "notifications"]
)
@pytest.mark.parametrize("deferred", [False, True])
def test_support_reply_failures_roll_back_message_version_event_and_notification(
    account_client, accounts, target, deferred
):
    farmer, admin = login(account_client), login(account_client, "admin")
    ticket = create(account_client, farmer)
    with accounts[2].begin() as conn:
        conn.execute(
            text(
                "CREATE FUNCTION public.support_test_failure() RETURNS trigger "
                "LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Synthetic private support failure' "
                "USING ERRCODE='23514'; END; $$"
            )
        )
        mode = "DEFERRABLE INITIALLY DEFERRED" if deferred else ""
        verb = "UPDATE" if target == "support_tickets" else "INSERT"
        conn.execute(
            text(
                f"CREATE CONSTRAINT TRIGGER support_test_failure AFTER {verb} ON {target} "
                f"{mode} FOR EACH ROW EXECUTE FUNCTION public.support_test_failure()"
            )
        )
    try:
        response = call(
            account_client,
            "POST",
            ADMIN + f"/{ticket['id']}/messages",
            admin,
            {"body": "Must roll back", "expected_version": 1},
        )
        assert response.status_code == 503 and "Synthetic" not in response.text
        with Session(accounts[1]) as db:
            assert db.get(SupportTicket, ticket["id"]).version == 1
            assert db.scalar(select(func.count()).select_from(SupportMessage)) == 1
            assert db.scalar(select(func.count()).select_from(SupportEvent)) == 1
            assert db.scalar(select(func.count()).select_from(Notification)) == 0
    finally:
        with accounts[2].begin() as conn:
            conn.execute(text(f"DROP TRIGGER support_test_failure ON {target}"))
            conn.execute(text("DROP FUNCTION public.support_test_failure()"))


def test_support_create_failure_never_leaves_an_empty_ticket(account_client, accounts, monkeypatch):
    farmer = login(account_client)
    original = service.event

    def fail(*args, **kwargs):
        original(*args, **kwargs)
        raise IntegrityError("Synthetic failure", {}, Exception("Synthetic"))

    monkeypatch.setattr(service, "event", fail)
    assert call(account_client, "POST", BASE, farmer, BODY).status_code == 503
    with Session(accounts[1]) as db:
        assert db.scalar(select(func.count()).select_from(SupportTicket)) == 0
        assert db.scalar(select(func.count()).select_from(SupportMessage)) == 0
        assert db.scalar(select(func.count()).select_from(SupportEvent)) == 0


def test_concurrent_replies_have_one_message_event_and_notice(account_client, accounts):
    farmer, admin = login(account_client), login(account_client, "admin")
    ticket = create(account_client, farmer)
    barrier = Barrier(2)

    def send(index):
        barrier.wait(timeout=10)
        return call(
            account_client,
            "POST",
            ADMIN + f"/{ticket['id']}/messages",
            admin,
            {"body": f"Reply {index}", "expected_version": 1},
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(send, range(2))) == [200, 409]
    with Session(accounts[1]) as db:
        assert db.get(SupportTicket, ticket["id"]).version == 2
        assert db.scalar(select(func.count()).select_from(SupportMessage)) == 2
        assert db.scalar(select(func.count()).select_from(SupportEvent)) == 2
        assert db.scalar(select(func.count()).select_from(Notification)) == 1


def test_disabled_requester_cannot_receive_replies_but_admin_can_resolve(account_client, accounts):
    farmer, admin = login(account_client), login(account_client, "admin")
    ticket = create(account_client, farmer)
    response = call(
        account_client,
        "PATCH",
        f"/admin/users/{accounts[3]['farmer']}/status",
        admin,
        {"enabled": False, "expected_version": 1, "reason": "Synthetic support account test"},
    )
    assert response.status_code == 200
    office = ADMIN + f"/{ticket['id']}"
    assert (
        call(
            account_client,
            "POST",
            office + "/messages",
            admin,
            {"body": "Blocked", "expected_version": 1},
        ).status_code
        == 409
    )
    assert (
        call(
            account_client,
            "POST",
            office + "/status",
            admin,
            {"status": "resolved", "expected_version": 1},
        ).status_code
        == 200
    )
    assert call(account_client, "GET", BASE, farmer).status_code == 401
    with Session(accounts[1]) as db:
        assert db.scalar(select(func.count()).select_from(Notification)) == 0


def test_support_permissions_do_not_open_farms_or_account_audit_messages(
    account_client, farm_records
):
    farmer, admin = login(account_client), login(account_client, "admin")
    ticket = create(account_client, farmer)
    assert call(account_client, "GET", ADMIN + f"/{ticket['id']}", admin).status_code == 200
    assert (
        call(account_client, "GET", f"/farms/{farm_records['farmer']['farm']}", admin).status_code
        == 403
    )
    feed = call(account_client, "GET", "/admin/audit-logs", admin)
    assert BODY["body"] not in feed.text and BODY["subject"] not in feed.text


def test_messages_events_and_ticket_identity_are_immutable(accounts, account_client):
    ticket = create(account_client, login(account_client))
    for sql in (
        "UPDATE support_messages SET body=body WHERE false",
        "DELETE FROM support_messages WHERE false",
        "TRUNCATE support_events",
        "DELETE FROM support_tickets WHERE false",
        "UPDATE support_events SET status=status WHERE false",
    ):
        with pytest.raises(ProgrammingError), accounts[1].begin() as conn:
            conn.execute(text(sql))
    with pytest.raises(IntegrityError), accounts[1].begin() as conn:
        conn.execute(
            text("UPDATE support_tickets SET farmer_id=:owner WHERE id=:ticket"),
            {"owner": accounts[3]["other-farmer"], "ticket": ticket["id"]},
        )
    with pytest.raises(IntegrityError), accounts[1].begin() as conn:
        conn.execute(
            text("UPDATE support_tickets SET subject='Changed' WHERE id=:ticket"),
            {"ticket": ticket["id"]},
        )
    with accounts[2].begin() as conn:
        config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
        config.attributes["connection"] = conn
        with pytest.raises(RuntimeError, match="support evidence"), conn.begin_nested():
            command.downgrade(config, "0006_farm_lifecycle")


def test_public_help_contact_works_without_database_or_auth():
    settings = Settings().model_copy(
        update={
            "database_url": None,
            "auth_signing_key": None,
            "support_contact_email": "help@example.com",
        }
    )
    with TestClient(create_app(settings)) as client:
        response = client.get(ROOT + "/help/contact")
        assert response.status_code == 200 and response.json() == {"email": "help@example.com"}


def test_service_permissions_apply_without_http_dependencies(account_client, accounts):
    login(account_client, "advisor")
    with Session(accounts[1]) as db:
        session = db.scalar(
            select(RefreshSession).where(RefreshSession.user_id == accounts[3]["advisor"])
        )
        ids = (session.user_id, session.id)
        with pytest.raises(IdentityError) as denied:
            service.create_ticket(db, ids, dto.Create(**BODY), str(uuid4()))
        assert denied.value.status == 403


def test_reply_waiting_behind_requester_disablement_is_rejected(
    account_client, accounts, monkeypatch
):
    farmer, admin = login(account_client), login(account_client, "admin")
    other_admin = login(account_client, "second-admin")
    ticket = create(account_client, farmer)
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
            f"/admin/users/{accounts[3]['farmer']}/status",
            admin,
            {"enabled": False, "expected_version": 1, "reason": "Synthetic support serialization"},
        )
        try:
            assert entered.wait(timeout=10)
            response = pool.submit(
                call,
                account_client,
                "POST",
                ADMIN + f"/{ticket['id']}/messages",
                other_admin,
                {"body": "Must not send after disable", "expected_version": 1},
            )
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
        assert response.result(timeout=10).status_code == 409
    with Session(accounts[1]) as db:
        assert db.get(SupportTicket, ticket["id"]).version == 1
        assert db.scalar(select(func.count()).select_from(Notification)) == 0

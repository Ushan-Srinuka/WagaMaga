from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.db.database import SCHEMA_REVISION
from app.main import create_app
from app.modules.identity import service
from app.modules.identity.models import AuditLog, RateLimit, RefreshSession, RefreshToken, User
from app.modules.identity.schemas import Register
from app.modules.identity.security import COOKIE_NAME, IdentityError, now, passwords, token_hash

pytestmark = pytest.mark.integration
PASSWORD = "a synthetic growing season password 1!"
HEADERS = {"Origin": "http://127.0.0.1:5173", "X-WagaMaga-Client": "web"}


def login(client, name="farmer"):
    response = client.post(
        "/api/v1/auth/login", json={"email": f"{name}@example.com", "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    return response.json()


def bearer(result):
    return {"Authorization": f"Bearer {result['access_token']}"}


def test_registration_privacy_hashing_and_field_boundaries(account_client, accounts):
    data = {"email": "New.Farmer@example.com", "display_name": "New farmer", "password": PASSWORD}
    first = account_client.post("/api/v1/auth/register", json=data)
    second = account_client.post(
        "/api/v1/auth/register", json={**data, "email": data["email"].upper()}
    )
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert "access_token" not in first.text and "email" not in first.text
    with Session(accounts[1]) as db:
        user = db.scalar(select(User).where(User.email == "new.farmer@example.com"))
        assert user.role == "farmer" and user.password_hash.startswith("$argon2id$")
        assert user.password_hash != PASSWORD
    response = account_client.post("/api/v1/auth/register", json={**data, "role": "administrator"})
    assert response.status_code == 422
    assert PASSWORD not in response.text and "$argon2" not in response.text
    invalid = account_client.post(
        "/api/v1/auth/register", json={**data, "password": "private-short"}
    )
    assert invalid.status_code == 422 and "private-short" not in invalid.text


@pytest.mark.parametrize(
    "password",
    [
        "Abcd1!x",
        "1234567!",
        "abcdefg!",
        "abcdefg1",
        "Abcdef1 ",
        "Abcdef1\u200b",
        "        ",
        "a" * 127 + "1!",
    ],
    ids=[
        "too-short",
        "no-letter",
        "no-number",
        "no-symbol",
        "space-not-symbol",
        "format-not-symbol",
        "spaces-only",
        "too-long",
    ],
)
def test_registration_rejects_password_policy_failures_without_creating_user(
    account_client, accounts, password
):
    response = account_client.post(
        "/api/v1/auth/register",
        json={"email": "policy@example.com", "display_name": "Policy test", "password": password},
    )
    assert response.status_code == 422
    assert password not in response.text
    assert response.headers["cache-control"] == "no-store"
    assert any(item["field"] == "body.password" for item in response.json()["field_errors"])
    with Session(accounts[1]) as db:
        assert db.scalar(select(User).where(User.email == "policy@example.com")) is None


@pytest.mark.parametrize(
    "password",
    ["Abcdef1!", "abcdef1!", "අbcdef1!", "Abcdef١!", "Abcdef1€", "a" * 126 + "1!", " abcd1! "],
    ids=[
        "eight-characters",
        "lowercase-allowed",
        "unicode-letter",
        "unicode-decimal",
        "unicode-symbol",
        "maximum-length",
        "spaces-preserved",
    ],
)
def test_registration_accepts_policy_passwords_and_login_preserves_them(
    account_client, accounts, password
):
    response = account_client.post(
        "/api/v1/auth/register",
        json={"email": "policy@example.com", "display_name": "Policy test", "password": password},
    )
    assert response.status_code == 200
    assert "access_token" not in response.json()
    with Session(accounts[1]) as db:
        user = db.scalar(select(User).where(User.email == "policy@example.com"))
        assert user.role == "farmer" and passwords.verify(password, user.password_hash)
    signed_in = account_client.post(
        "/api/v1/auth/login", json={"email": "policy@example.com", "password": password}
    )
    assert signed_in.status_code == 200


def test_existing_passphrase_without_new_composition_can_still_log_in(account_client, accounts):
    legacy_password = "a synthetic growing season password"
    with Session(accounts[1]) as db, db.begin():
        db.get(User, accounts[3]["farmer"]).password_hash = passwords.hash(legacy_password)
    response = account_client.post(
        "/api/v1/auth/login", json={"email": "farmer@example.com", "password": legacy_password}
    )
    assert response.status_code == 200


def test_login_failures_are_uniform_and_disabled_account_denied(account_client, accounts):
    with Session(accounts[1]) as db, db.begin():
        db.get(User, accounts[3]["farmer"]).disabled_at = now()
    bodies = []
    for email, password in (
        ("unknown@example.com", PASSWORD),
        ("advisor@example.com", "wrong"),
        ("farmer@example.com", PASSWORD),
    ):
        response = account_client.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
        assert response.status_code == 401
        bodies.append((response.json()["code"], response.json()["message"]))
    assert len(set(bodies)) == 1


def test_session_cookie_rotation_replay_and_logout(account_client, accounts):
    result = login(account_client)
    first = account_client.cookies.get(COOKIE_NAME)
    assert first and first not in result["access_token"]
    assert account_client.get("/api/v1/me", headers=bearer(result)).status_code == 200
    assert (
        account_client.get("/api/v1/me", headers=bearer(result)).headers["cache-control"]
        == "no-store"
    )
    rotated = account_client.post("/api/v1/auth/refresh")
    assert rotated.status_code == 200
    successor = account_client.cookies.get(COOKIE_NAME)
    assert successor != first
    cookie = rotated.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie and "Path=/api/v1/auth" in cookie
    with Session(accounts[1]) as db:
        stored = db.scalars(select(RefreshToken)).all()
        assert len(stored) == 2 and all(
            item.token_hash not in {first, successor} for item in stored
        )
        assert token_hash(first) in {item.token_hash for item in stored}
    replay = account_client.post(
        "/api/v1/auth/refresh", headers={"Cookie": f"{COOKIE_NAME}={first}"}
    )
    assert replay.status_code == 401
    assert account_client.get("/api/v1/me", headers=bearer(result)).status_code == 401
    assert (
        account_client.post(
            "/api/v1/auth/refresh", headers={"Cookie": f"{COOKIE_NAME}={successor}"}
        ).status_code
        == 401
    )
    fresh = login(account_client)
    assert account_client.post("/api/v1/auth/logout").status_code == 204
    assert account_client.post("/api/v1/auth/logout").status_code == 204
    assert account_client.get("/api/v1/me", headers=bearer(fresh)).status_code == 401


@pytest.mark.parametrize(
    "change",
    ["signature", "issuer", "audience", "expired", "algorithm", "sid", "sid-type", "missing"],
)
def test_access_token_validation(account_client, accounts, change):
    result = login(account_client)
    payload = jwt.decode(result["access_token"], options={"verify_signature": False})
    key = accounts[0].auth_signing_key.get_secret_value()
    algorithm = "HS256"
    if change == "signature":
        key = "a-different-synthetic-key-at-least-32-characters"
    elif change == "issuer":
        payload["iss"] = "wrong"
    elif change == "audience":
        payload["aud"] = "wrong"
    elif change == "expired":
        payload["exp"] = now() - timedelta(seconds=1)
    elif change == "algorithm":
        algorithm = "HS512"
    elif change == "sid":
        payload["sid"] = str(uuid4())
    elif change == "sid-type":
        payload["sid"] = 123
    else:
        del payload["exp"]
    token = jwt.encode(payload, key, algorithm=algorithm)
    assert (
        account_client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"}).status_code
        == 401
    )


def test_profile_ownership_admin_permission_and_pagination(account_client, accounts):
    farmer = login(account_client)
    for target in (accounts[3]["other-farmer"], uuid4()):
        assert (
            account_client.get(f"/api/v1/admin/users/{target}", headers=bearer(farmer)).status_code
            == 403
        )
    assert account_client.get("/api/v1/me").status_code == 401
    assert (
        account_client.patch(
            "/api/v1/me",
            headers=bearer(farmer),
            json={
                "display_name": "Changed",
                "expected_version": 1,
                "role": "administrator",
            },
        ).status_code
        == 422
    )
    changed = account_client.patch(
        "/api/v1/me",
        headers=bearer(farmer),
        json={
            "display_name": "Changed",
            "expected_version": 1,
        },
    )
    assert changed.status_code == 200 and changed.json()["version"] == 2
    assert (
        account_client.patch(
            "/api/v1/me",
            headers=bearer(farmer),
            json={
                "display_name": "Stale",
                "expected_version": 1,
            },
        ).status_code
        == 409
    )
    admin = login(account_client, "admin")
    page = account_client.get(
        "/api/v1/admin/users?role=farmer&q=other&page_size=1", headers=bearer(admin)
    ).json()
    assert page["total"] == 1 and len(page["items"]) == 1
    assert "password_hash" not in str(page)
    assert (
        account_client.get("/api/v1/admin/users?page_size=101", headers=bearer(admin)).status_code
        == 422
    )
    assert (
        account_client.get(f"/api/v1/admin/users/{uuid4()}", headers=bearer(admin)).status_code
        == 404
    )


def test_role_status_changes_revoke_sessions_and_audit(account_client, accounts):
    farmer = login(account_client)
    farmer_cookie = account_client.cookies.get(COOKIE_NAME)
    admin = login(account_client, "admin")
    target = accounts[3]["farmer"]
    change = {"role": "advisor", "reason": "Synthetic advisor assignment", "expected_version": 1}
    response = account_client.patch(
        f"/api/v1/admin/users/{target}/role", headers=bearer(admin), json=change
    )
    assert response.status_code == 200 and response.json()["role"] == "advisor"
    assert account_client.get("/api/v1/me", headers=bearer(farmer)).status_code == 401
    assert (
        account_client.post(
            "/api/v1/auth/refresh", headers={"Cookie": f"{COOKIE_NAME}={farmer_cookie}"}
        ).status_code
        == 401
    )
    assert (
        account_client.patch(
            f"/api/v1/admin/users/{target}/role", headers=bearer(admin), json=change
        ).status_code
        == 409
    )
    advisor = login(account_client)
    assert account_client.get("/api/v1/admin/users", headers=bearer(advisor)).status_code == 403
    disable = {"enabled": False, "reason": "Synthetic account disabled", "expected_version": 2}
    assert (
        account_client.patch(
            f"/api/v1/admin/users/{target}/status", headers=bearer(admin), json=disable
        ).status_code
        == 200
    )
    assert account_client.get("/api/v1/me", headers=bearer(advisor)).status_code == 401
    enable = {"enabled": True, "reason": "Synthetic account re-enabled", "expected_version": 3}
    assert (
        account_client.patch(
            f"/api/v1/admin/users/{target}/status", headers=bearer(admin), json=enable
        ).status_code
        == 200
    )
    assert account_client.get("/api/v1/me", headers=bearer(advisor)).status_code == 401
    with Session(accounts[1]) as db:
        assert db.scalar(select(func.count()).select_from(AuditLog)) == 3
        assert all(
            item.revoked_at
            for item in db.scalars(select(RefreshSession).where(RefreshSession.user_id == target))
        )
    with accounts[1].begin() as connection, pytest.raises(ProgrammingError):
        connection.execute(text("UPDATE audit_logs SET reason='tampered'"))
    with accounts[1].begin() as connection, pytest.raises(ProgrammingError):
        connection.execute(text("DELETE FROM audit_logs"))


def test_admin_removal_scrubs_identity_revokes_sessions_and_retains_audit(account_client, accounts):
    farmer = login(account_client)
    farmer_cookie = account_client.cookies.get(COOKIE_NAME)
    admin = login(account_client, "admin")
    target = accounts[3]["farmer"]
    response = account_client.request(
        "DELETE",
        f"/api/v1/admin/users/{target}",
        headers=bearer(admin),
        json={
            "reason": "Synthetic unauthorized registration",
            "expected_version": 1,
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["display_name"] == "Deleted account"
    assert response.json()["deleted_at"] is not None
    assert response.json()["email"].endswith("@deleted.invalid")
    assert account_client.get("/api/v1/me", headers=bearer(farmer)).status_code == 401
    assert (
        account_client.post(
            "/api/v1/auth/refresh", headers={"Cookie": f"{COOKIE_NAME}={farmer_cookie}"}
        ).status_code
        == 401
    )
    regular_matches = account_client.get(
        "/api/v1/admin/users?q=farmer@example.com", headers=bearer(admin)
    ).json()
    assert all(item["id"] != str(target) for item in regular_matches["items"])
    deleted = account_client.get("/api/v1/admin/users?status=deleted", headers=bearer(admin)).json()
    record = next(item for item in deleted["items"] if item["id"] == str(target))
    assert record["email"].endswith("@deleted.invalid")
    assert (
        account_client.post(
            "/api/v1/auth/login",
            json={"email": "farmer@example.com", "password": PASSWORD},
        ).status_code
        == 401
    )
    with Session(accounts[1]) as db:
        item = db.get(User, target)
        assert item.deleted_at is not None and item.disabled_at is not None
        assert item.email == f"deleted+{target}@deleted.invalid"
        audit = db.scalar(select(AuditLog).where(AuditLog.action == "account_deleted"))
        assert audit is not None and audit.target_id == target
        assert audit.reason == "Synthetic unauthorized registration"


def test_admin_cannot_remove_self_or_non_admin_cannot_remove_accounts(account_client, accounts):
    admin = login(account_client, "admin")
    response = account_client.request(
        "DELETE",
        f"/api/v1/admin/users/{accounts[3]['admin']}",
        headers=bearer(admin),
        json={"reason": "Self removal attempt", "expected_version": 1},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "SELF_MANAGEMENT_BLOCKED"
    stale = account_client.request(
        "DELETE",
        f"/api/v1/admin/users/{accounts[3]['farmer']}",
        headers=bearer(admin),
        json={"reason": "Synthetic stale removal", "expected_version": 2},
    )
    assert stale.status_code == 409
    assert stale.json()["code"] == "VERSION_CONFLICT"
    farmer = login(account_client)
    forbidden = account_client.request(
        "DELETE",
        f"/api/v1/admin/users/{accounts[3]['other-farmer']}",
        headers=bearer(farmer),
        json={"reason": "Synthetic unauthorized attempt", "expected_version": 1},
    )
    assert forbidden.status_code == 403
    with Session(accounts[1]) as db:
        assert db.get(User, accounts[3]["farmer"]).deleted_at is None
        assert db.get(User, accounts[3]["other-farmer"]).deleted_at is None


def test_concurrent_admin_removals_preserve_one_active_administrator(account_client, accounts):
    first = login(account_client, "admin")
    second = login(account_client, "second-admin")
    barrier = Barrier(2)

    def remove(item):
        result, target = item
        with TestClient(create_app(accounts[0]), headers=HEADERS) as client:
            barrier.wait(timeout=10)
            return client.request(
                "DELETE",
                f"/api/v1/admin/users/{target}",
                headers=bearer(result),
                json={"expected_version": 1, "reason": "Concurrent synthetic removal"},
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(
            pool.map(remove, [(first, accounts[3]["second-admin"]), (second, accounts[3]["admin"])])
        )
    assert sorted(outcomes) == [200, 401]
    with Session(accounts[1]) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(User)
                .where(
                    User.role == "administrator",
                    User.disabled_at.is_(None),
                    User.deleted_at.is_(None),
                )
            )
            == 1
        )


def test_admin_removal_rolls_back_if_audit_insert_fails(account_client, accounts, monkeypatch):
    admin = login(account_client, "admin")
    original = service.write_audit

    def invalid_audit(db, actor, target, action, previous, current, reason, request_id):
        original(db, actor, target, action, previous, current, "x" * 301, request_id)

    monkeypatch.setattr(service, "write_audit", invalid_audit)
    response = account_client.request(
        "DELETE",
        f"/api/v1/admin/users/{accounts[3]['farmer']}",
        headers=bearer(admin),
        json={"reason": "Audit failure should cancel removal", "expected_version": 1},
    )
    assert response.status_code == 503
    with Session(accounts[1]) as db:
        person = db.get(User, accounts[3]["farmer"])
        assert person.deleted_at is None and person.email == "farmer@example.com"
        assert db.scalar(select(func.count()).select_from(AuditLog)) == 0


def test_password_change_enforces_policy_and_revokes_other_sessions(account_client, accounts):
    current_session = login(account_client)
    other_session = login(account_client)
    invalid = account_client.post(
        "/api/v1/me/password",
        headers=bearer(current_session),
        json={"current_password": PASSWORD, "new_password": "password123"},
    )
    assert invalid.status_code == 422 and "password123" not in invalid.text
    wrong = account_client.post(
        "/api/v1/me/password",
        headers=bearer(current_session),
        json={"current_password": "wrong synthetic password", "new_password": "New!letter123"},
    )
    assert wrong.status_code == 400
    changed = account_client.post(
        "/api/v1/me/password",
        headers=bearer(current_session),
        json={"current_password": PASSWORD, "new_password": "New!letter123"},
    )
    assert changed.status_code == 200 and changed.json()["version"] == 2
    assert account_client.get("/api/v1/me", headers=bearer(current_session)).status_code == 200
    assert account_client.get("/api/v1/me", headers=bearer(other_session)).status_code == 401
    assert (
        account_client.post(
            "/api/v1/auth/login",
            json={"email": "farmer@example.com", "password": PASSWORD},
        ).status_code
        == 401
    )
    assert (
        account_client.post(
            "/api/v1/auth/login",
            json={"email": "farmer@example.com", "password": "New!letter123"},
        ).status_code
        == 200
    )
    with Session(accounts[1]) as db:
        audit = db.scalar(select(AuditLog).where(AuditLog.action == "password_changed"))
        assert audit is not None and audit.actor_id == audit.target_id == accounts[3]["farmer"]


def test_password_change_requires_browser_origin_and_valid_current_password(
    account_client,
):
    farmer = login(account_client)
    denied_origin = account_client.post(
        "/api/v1/me/password",
        headers={**bearer(farmer), "Origin": "https://attacker.example"},
        json={"current_password": PASSWORD, "new_password": "New!letter123"},
    )
    assert denied_origin.status_code == 403
    assert (
        account_client.post(
            "/api/v1/me/password",
            headers=bearer(farmer),
            json={"current_password": "wrong password", "new_password": "New!letter123"},
        ).status_code
        == 400
    )


def test_administrator_audit_view_is_filtered_access_controlled_and_itself_audited(
    account_client, accounts
):
    admin = login(account_client, "admin")
    target = accounts[3]["farmer"]
    changed = account_client.patch(
        f"/api/v1/admin/users/{target}/role",
        headers=bearer(admin),
        json={
            "role": "advisor",
            "reason": "Synthetic advisor assignment",
            "expected_version": 1,
        },
    )
    assert changed.status_code == 200
    other = login(account_client, "other-farmer")
    assert account_client.get("/api/v1/admin/audit-logs", headers=bearer(other)).status_code == 403
    today = now().date().isoformat()
    response = account_client.get(
        "/api/v1/admin/audit-logs",
        headers=bearer(admin),
        params={
            "action": "role",
            "q": "farmer@example.com",
            "from_date": today,
            "to_date": today,
            "page_size": 1,
        },
    )
    assert response.status_code == 200, response.text
    page = response.json()
    assert page["total"] == 1 and len(page["items"]) == 1
    event = page["items"][0]
    assert event["action"] == "role"
    assert event["actor_name"] == "Admin" and event["target_name"] == "Farmer"
    assert event["reason"] == "Synthetic advisor assignment"
    assert event["previous_value"] == "farmer" and event["new_value"] == "advisor"
    assert "farmer@example.com" not in response.text
    assert "password_hash" not in response.text
    viewed = account_client.get(
        "/api/v1/admin/audit-logs?action=audit_viewed", headers=bearer(admin)
    )
    assert viewed.status_code == 200 and viewed.json()["total"] == 1
    invalid_range = account_client.get(
        "/api/v1/admin/audit-logs",
        headers=bearer(admin),
        params={"from_date": "2026-11-19", "to_date": "2026-11-18"},
    )
    assert invalid_range.status_code == 422


def test_in_app_notifications_are_private_and_read_state_is_owner_scoped(account_client, accounts):
    admin = login(account_client, "admin")
    target = accounts[3]["farmer"]
    changed = account_client.patch(
        f"/api/v1/admin/users/{target}/role",
        headers=bearer(admin),
        json={
            "role": "advisor",
            "reason": "Synthetic role notification",
            "expected_version": 1,
        },
    )
    assert changed.status_code == 200
    recipient = login(account_client, "farmer")
    page = account_client.get("/api/v1/notifications", headers=bearer(recipient)).json()
    assert page["total"] == page["unread_count"] == 1
    item = page["items"][0]
    assert item["event_type"] == "role_changed"
    assert "advisor" in item["body"] and item["read_at"] is None
    assert (
        account_client.get(
            "/api/v1/notifications?unread_only=true", headers=bearer(recipient)
        ).json()["total"]
        == 1
    )
    other = login(account_client, "other-farmer")
    forbidden = account_client.patch(
        f"/api/v1/notifications/{item['id']}",
        headers=bearer(other),
        json={"read": True},
    )
    assert forbidden.status_code == 404
    assert (
        account_client.patch(
            f"/api/v1/notifications/{item['id']}",
            headers=bearer(recipient),
            json={"read": True},
        ).json()["read_at"]
        is not None
    )
    assert (
        account_client.get(
            "/api/v1/notifications?unread_only=true", headers=bearer(recipient)
        ).json()["unread_count"]
        == 0
    )
    assert (
        account_client.patch(
            f"/api/v1/notifications/{item['id']}",
            headers=bearer(recipient),
            json={"read": False},
        ).json()["read_at"]
        is None
    )


def test_admin_write_rolls_back_on_audit_failure(account_client, accounts, monkeypatch):
    farmer = login(account_client)
    admin = login(account_client, "admin")
    original = service.write_audit

    def invalid_audit(db, actor, target, action, previous, current, reason, request_id):
        original(db, actor, target, action, previous, current, "x" * 301, request_id)

    monkeypatch.setattr(service, "write_audit", invalid_audit)
    response = account_client.patch(
        f"/api/v1/admin/users/{accounts[3]['farmer']}/role",
        headers=bearer(admin),
        json={
            "role": "advisor",
            "reason": "Audit must fail",
            "expected_version": 1,
        },
    )
    assert response.status_code == 503
    assert "password_hash" not in response.text and "INSERT" not in response.text
    assert account_client.get("/api/v1/me", headers=bearer(farmer)).status_code == 200
    with Session(accounts[1]) as db:
        person = db.get(User, accounts[3]["farmer"])
        assert person.role == "farmer" and person.version == 1
        assert db.scalar(select(func.count()).select_from(AuditLog)) == 0


@pytest.mark.parametrize(
    "origin,header",
    [(None, "web"), ("null", "web"), ("https://evil.example", "web"), (HEADERS["Origin"], "wrong")],
)
def test_browser_writes_require_origin_and_header(account_client, origin, header):
    headers = {"X-WagaMaga-Client": header}
    if origin is not None:
        headers["Origin"] = origin
    account_client.headers.pop("Origin", None)
    response = account_client.post(
        "/api/v1/auth/login",
        headers=headers,
        json={"email": "farmer@example.com", "password": PASSWORD},
    )
    assert response.status_code == 403


def test_shared_rate_limits_and_retry_after(accounts):
    settings = accounts[0].model_copy(update={"auth_login_failures": 2})
    with (
        TestClient(create_app(settings), headers=HEADERS) as one,
        TestClient(create_app(settings), headers=HEADERS) as two,
    ):
        data = {"email": "unknown@example.com", "password": "wrong"}
        assert one.post("/api/v1/auth/login", json=data).status_code == 401
        assert two.post("/api/v1/auth/login", json=data).status_code == 401
        response = one.post("/api/v1/auth/login", json=data)
        assert response.status_code == 429 and int(response.headers["retry-after"]) > 0


def test_concurrent_refresh_reuse_revokes_winning_session(account_client, accounts):
    result = login(account_client)
    raw = account_client.cookies.get(COOKIE_NAME)
    barrier = Barrier(2)

    def rotate(_):
        with TestClient(create_app(accounts[0]), headers=HEADERS) as client:
            barrier.wait(timeout=10)
            return client.post(
                "/api/v1/auth/refresh", headers={"Cookie": f"{COOKIE_NAME}={raw}"}
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(rotate, range(2)))
    assert sorted(outcomes) == [200, 401]
    assert account_client.get("/api/v1/me", headers=bearer(result)).status_code == 401


def test_concurrent_admin_changes_preserve_an_active_admin(account_client, accounts):
    first = login(account_client, "admin")
    second = login(account_client, "second-admin")
    self_change = account_client.patch(
        f"/api/v1/admin/users/{accounts[3]['admin']}/status",
        headers=bearer(first),
        json={
            "enabled": False,
            "expected_version": 1,
            "reason": "Self disable attempt",
        },
    )
    assert self_change.status_code == 409
    barrier = Barrier(2)

    def disable(item):
        result, target = item
        with TestClient(create_app(accounts[0]), headers=HEADERS) as client:
            barrier.wait(timeout=10)
            return client.patch(
                f"/api/v1/admin/users/{target}/status",
                headers=bearer(result),
                json={
                    "enabled": False,
                    "reason": "Concurrent disable attempt",
                    "expected_version": 1,
                },
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(
            pool.map(
                disable, [(first, accounts[3]["second-admin"]), (second, accounts[3]["admin"])]
            )
        )
    assert sorted(outcomes) == [200, 401]
    with Session(accounts[1]) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(User)
                .where(User.role == "administrator", User.disabled_at.is_(None))
            )
            == 1
        )


def test_concurrent_registration_and_first_admin_bootstrap(accounts):
    barrier = Barrier(2)
    data = Register(email="duplicate@example.com", display_name="Duplicate", password=PASSWORD)

    def signup(_):
        with Session(accounts[1]) as db, db.begin():
            barrier.wait(timeout=10)
            service.register(db, data)

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(signup, range(2)))
    with Session(accounts[1]) as db:
        assert (
            db.scalar(select(func.count()).select_from(User).where(User.email == data.email)) == 1
        )
    with accounts[2].begin() as connection:
        connection.execute(
            text(
                "TRUNCATE knowledge_evaluation_runs, knowledge_evaluation_decisions, "
                "knowledge_source_pdfs, knowledge_demo_decisions, "
                "knowledge_demo_versions, "
                "support_events, support_messages, support_tickets, "
                "weather_task_alerts, weather_alert_rules, "
                "task_plan_decisions, task_plans, farm_task_events, farm_tasks, "
                "farm_forecasts, farm_deletions, farm_audit_events, "
                "observation_revisions, cultivation_revisions, "
                "farm_revisions, farm_observations, cultivations, farms, "
                "notifications, audit_logs, refresh_tokens, refresh_sessions, "
                "auth_rate_limits, users"
            )
        )
    barrier = Barrier(2)

    def bootstrap(index):
        try:
            with Session(accounts[1]) as db, db.begin():
                barrier.wait(timeout=10)
                service.bootstrap_admin(
                    db,
                    Register(
                        email=f"bootstrap{index}@example.com",
                        display_name="Initial admin",
                        password=PASSWORD,
                    ),
                )
            return "created"
        except IdentityError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(bootstrap, range(2))) == ["BOOTSTRAP_CLOSED", "created"]
    with Session(accounts[1]) as db:
        assert (
            db.scalar(select(func.count()).select_from(User).where(User.role == "administrator"))
            == 1
        )
        assert db.scalar(select(func.count()).select_from(AuditLog)) == 1


def test_production_cookie_is_secure_and_session_expiry_is_enforced(accounts):
    settings = accounts[0].model_copy(update={"app_env": "production"})
    with TestClient(create_app(settings), headers=HEADERS, base_url="https://testserver") as client:
        response = client.post(
            "/api/v1/auth/login", json={"email": "farmer@example.com", "password": PASSWORD}
        )
        assert "Secure" in response.headers["set-cookie"]
        assert client.get("/docs").status_code == 404
        with Session(accounts[1]) as db, db.begin():
            for session in db.scalars(select(RefreshSession)):
                session.expires_at = now() - timedelta(seconds=1)
        assert client.get("/api/v1/me", headers=bearer(response.json())).status_code == 401
        assert client.post("/api/v1/auth/refresh").status_code == 401


def test_rate_limit_expiry_and_auth_endpoint_caps(accounts, monkeypatch):
    clock = now()
    monkeypatch.setattr(service, "now", lambda: clock)
    limits = service.Limiter(accounts[1], accounts[0])
    limits.check("expiry-test", "synthetic", 1, 60)
    with pytest.raises(IdentityError) as failure:
        limits.check("expiry-test", "synthetic", 1, 60)
    assert failure.value.status == 429
    clock += timedelta(seconds=61)
    limits.check("expiry-test", "synthetic", 1, 60)
    with Session(accounts[1]) as db:
        assert db.scalar(select(func.count()).select_from(RateLimit)) == 1
    settings = accounts[0].model_copy(
        update={
            "auth_registration_attempts": 1,
            "auth_refresh_attempts": 1,
        }
    )
    with TestClient(create_app(settings), headers=HEADERS) as client:
        data = {"email": "limited@example.com", "display_name": "Synthetic", "password": PASSWORD}
        assert client.post("/api/v1/auth/register", json=data).status_code == 200
        assert client.post("/api/v1/auth/register", json=data).status_code == 429
        login(client)
        assert client.post("/api/v1/auth/refresh").status_code == 200
        assert client.post("/api/v1/auth/refresh").status_code == 429


def test_migration_fresh_rebuild_and_metadata_privileges(identity_engines):
    from pathlib import Path

    from alembic import command
    from alembic.config import Config

    _, app_engine, owner = identity_engines
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    with owner.begin() as connection:
        config.attributes["connection"] = connection
        command.downgrade(config, "0001_foundation")
        assert connection.scalar(text("SELECT to_regclass('public.users')")) is None
        command.downgrade(config, "base")
        command.upgrade(config, "head")
    with app_engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == SCHEMA_REVISION
        assert connection.scalar(text("SELECT count(*) FROM users")) == 0
        assert connection.scalar(
            text("SELECT has_table_privilege(current_user, 'audit_logs', 'INSERT')")
        )
        assert not connection.scalar(
            text("SELECT has_table_privilege(current_user, 'audit_logs', 'DELETE')")
        )


def test_commit_failure_never_returns_success_or_partial_account_change(account_client, accounts):
    farmer = login(account_client)
    admin = login(account_client, "admin")
    with accounts[2].begin() as connection:
        connection.execute(
            text("""
            CREATE FUNCTION public.um1_test_reject_audit() RETURNS trigger
            LANGUAGE plpgsql AS $$ BEGIN
                RAISE EXCEPTION 'Synthetic deferred audit failure';
            END; $$
        """)
        )
        connection.execute(
            text("""
            CREATE CONSTRAINT TRIGGER um1_test_deferred_audit
            AFTER INSERT ON public.audit_logs DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION public.um1_test_reject_audit()
        """)
        )
    try:
        response = account_client.patch(
            f"/api/v1/admin/users/{accounts[3]['farmer']}/role",
            headers=bearer(admin),
            json={"role": "advisor", "expected_version": 1, "reason": "Commit must fail"},
        )
        assert response.status_code == 503
        assert "Synthetic deferred" not in response.text
    finally:
        with accounts[2].begin() as connection:
            connection.execute(text("DROP TRIGGER um1_test_deferred_audit ON public.audit_logs"))
            connection.execute(text("DROP FUNCTION public.um1_test_reject_audit()"))
    assert account_client.get("/api/v1/me", headers=bearer(farmer)).status_code == 200
    with Session(accounts[1]) as db:
        assert db.get(User, accounts[3]["farmer"]).role == "farmer"
        assert db.scalar(select(func.count()).select_from(AuditLog)) == 0

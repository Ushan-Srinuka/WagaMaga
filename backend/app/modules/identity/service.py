"""Identity rules and transaction boundaries, shared by HTTP and the local CLI."""

import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import Engine, delete, func, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.modules.identity.models import AuditLog, RateLimit, RefreshSession, RefreshToken, User
from app.modules.identity.schemas import AdminChange, PasswordChange, Profile, Register, UserOut
from app.modules.identity.security import (
    DUMMY_HASH,
    IdentityError,
    access_token,
    bucket_key,
    now,
    passwords,
    token_hash,
)
from app.modules.notifications.service import create_notification

ADMIN_LOCK = 713491
LOGIN_ERROR = "Email or password is incorrect, or the account is unavailable."


def denied() -> IdentityError:
    return IdentityError(401, "AUTHENTICATION_REQUIRED", "Please sign in again.", clear_cookie=True)


class Limiter:
    """Independent transactions keep failed-attempt counters after request rollback."""

    def __init__(self, engine: Engine, settings: Settings):
        self.engine = engine
        self.settings = settings

    def bucket(self, scope: str, value: str, seconds: int) -> tuple[str, datetime, int]:
        stamp = int(now().timestamp())
        boundary = (stamp // seconds + 1) * seconds
        identifier = bucket_key(self.settings, f"{scope}:{value}:{stamp // seconds}")
        return identifier, datetime.fromtimestamp(boundary, UTC), boundary - stamp

    def check(self, scope: str, value: str, limit: int, seconds: int, *, hit: bool = True) -> None:
        identifier, expiry, wait = self.bucket(scope, value, seconds)
        with Session(self.engine) as db, db.begin():
            db.execute(delete(RateLimit).where(RateLimit.expires_at < now()))
            if hit:
                statement = insert(RateLimit).values(key=identifier, count=1, expires_at=expiry)
                count = db.execute(
                    statement.on_conflict_do_update(
                        index_elements=[RateLimit.key],
                        set_={"count": RateLimit.count + 1},
                    ).returning(RateLimit.count)
                ).scalar_one()
            else:
                count = db.scalar(select(RateLimit.count).where(RateLimit.key == identifier)) or 0
        if count > limit if hit else count >= limit:
            raise IdentityError(
                429, "RATE_LIMITED", "Too many attempts. Please try again later.", retry_after=wait
            )


def active_actor(db: Session, ids: tuple[UUID, UUID], *, lock: bool = False) -> User:
    user_id, session_id = ids
    query = select(User).where(User.id == user_id).execution_options(populate_existing=True)
    if lock:
        query = query.with_for_update()
    user = db.scalar(query)
    session_query = (
        select(RefreshSession)
        .where(
            RefreshSession.id == session_id,
            RefreshSession.user_id == user_id,
        )
        .execution_options(populate_existing=True)
    )
    if lock:
        session_query = session_query.with_for_update()
    session = db.scalar(session_query)
    if (
        user is None
        or user.disabled_at is not None
        or user.deleted_at is not None
        or session is None
        or session.revoked_at is not None
        or session.expires_at <= now()
    ):
        raise denied()
    return user


def require_admin(user: User) -> None:
    if user.role != "administrator":
        raise IdentityError(403, "ACCESS_DENIED", "Administrator access is required.")


def register(db: Session, data: Register) -> None:
    # Hash for both outcomes; database uniqueness also handles concurrent signups.
    encoded = passwords.hash(data.password.get_secret_value())
    db.execute(
        insert(User)
        .values(
            id=uuid4(),
            email=data.email,
            display_name=data.display_name,
            password_hash=encoded,
            role="farmer",
            version=1,
        )
        .on_conflict_do_nothing(index_elements=[User.email])
    )


def create_refresh(db: Session, session: RefreshSession) -> str:
    raw = secrets.token_urlsafe(48)
    db.add(RefreshToken(session_id=session.id, token_hash=token_hash(raw)))
    db.flush()
    return raw


def token_result(settings: Settings, user: User, session: RefreshSession) -> dict:
    return {
        "access_token": access_token(settings, user.id, session.id),
        "token_type": "bearer",
        "expires_in": settings.auth_access_minutes * 60,
        "user": UserOut.model_validate(user),
    }


def login(db: Session, settings: Settings, limiter: Limiter, email: str, password: str, ip: str):
    limiter.check("login-ip", ip, settings.auth_login_ip_attempts, 900)
    limiter.check("login-account", email, settings.auth_login_failures, 900, hit=False)
    user = db.scalar(select(User).where(User.email == email).with_for_update())
    valid = passwords.verify(password, user.password_hash if user else DUMMY_HASH)
    if user is None or not valid or user.disabled_at is not None:
        limiter.check("login-account", email, settings.auth_login_failures, 900)
        raise IdentityError(401, "INVALID_CREDENTIALS", LOGIN_ERROR)
    session = RefreshSession(
        user_id=user.id, expires_at=now() + timedelta(days=settings.auth_session_days)
    )
    db.add(session)
    db.flush()
    raw = create_refresh(db, session)
    return token_result(settings, user, session), raw, session.expires_at


def refresh(db: Session, settings: Settings, limiter: Limiter, raw: str | None, ip: str):
    limiter.check("refresh-ip", ip, settings.auth_refresh_attempts, 60)
    if not raw or len(raw) > 200:
        raise denied()
    token = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash(raw)))
    if token is None:
        raise denied()
    family = db.get(RefreshSession, token.session_id)
    if family is None:
        raise denied()
    limiter.check("refresh-session", str(family.id), settings.auth_refresh_attempts, 60)
    # Every session mutation locks user -> session, matching role/status/logout operations.
    user = active_actor(db, (family.user_id, family.id), lock=True)
    db.refresh(token)
    if token.consumed_at is not None:
        family.revoked_at = now()
        db.commit()  # Replay revocation must survive the error response.
        raise denied()
    token.consumed_at = now()
    successor = create_refresh(db, family)
    return token_result(settings, user, family), successor, family.expires_at


def logout(db: Session, raw: str | None) -> None:
    if not raw or len(raw) > 200:
        return
    token = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash(raw)))
    if token is None:
        return
    family = db.get(RefreshSession, token.session_id)
    if family is None:
        return
    db.execute(select(User).where(User.id == family.user_id).with_for_update())
    db.refresh(family, with_for_update=True)
    family.revoked_at = family.revoked_at or now()


def update_profile(db: Session, ids: tuple[UUID, UUID], data: Profile) -> User:
    user = active_actor(db, ids, lock=True)
    check_version(user, data.expected_version)
    user.display_name = data.display_name
    user.version += 1
    user.updated_at = now()
    db.flush()
    return user


def change_password(
    db: Session,
    ids: tuple[UUID, UUID],
    data: PasswordChange,
    request_id: str,
    limiter: Limiter,
    settings: Settings,
    ip: str,
) -> User:
    user = active_actor(db, ids, lock=True)
    limiter.check("login-ip", ip, settings.auth_login_ip_attempts, 900)
    limiter.check("login-account", user.email, settings.auth_login_failures, 900, hit=False)
    current = data.current_password.get_secret_value()
    if not passwords.verify(current, user.password_hash):
        limiter.check("login-account", user.email, settings.auth_login_failures, 900)
        raise IdentityError(400, "CURRENT_PASSWORD_INCORRECT", "Current password is incorrect.")
    new_password = data.new_password.get_secret_value()
    if passwords.verify(new_password, user.password_hash):
        raise IdentityError(409, "PASSWORD_UNCHANGED", "Choose a different password.")
    user.password_hash = passwords.hash(new_password)
    user.version += 1
    user.updated_at = now()
    # Keep the current session; revoke every other device/session on password change.
    db.execute(
        update(RefreshSession)
        .where(
            RefreshSession.user_id == user.id,
            RefreshSession.id != ids[1],
            RefreshSession.revoked_at.is_(None),
        )
        .values(revoked_at=now())
    )
    write_audit(
        db,
        user.id,
        user.id,
        "password_changed",
        None,
        "changed",
        "Self-service password change",
        request_id,
    )
    create_notification(
        db,
        user.id,
        "password_changed",
        "Password changed",
        "Your password was changed. Other sessions have been signed out.",
    )
    db.flush()
    return user


def delete_account(
    db: Session,
    ids: tuple[UUID, UUID],
    target_id: UUID,
    data: AdminChange,
    request_id: str,
) -> User:
    require_admin(active_actor(db, ids))
    db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": ADMIN_LOCK})
    actor = active_actor(db, ids, lock=True)
    require_admin(actor)
    if actor.id == target_id:
        raise IdentityError(
            409, "SELF_MANAGEMENT_BLOCKED", "Use another administrator for this action."
        )
    target = db.scalar(select(User).where(User.id == target_id).with_for_update())
    if target is None:
        raise IdentityError(404, "ACCOUNT_NOT_FOUND", "Account not found.")
    check_version(target, data.expected_version)
    if target.deleted_at is not None:
        raise IdentityError(
            409, "ACCOUNT_ALREADY_DELETED", "This account has already been removed."
        )
    if target.role == "administrator" and target.disabled_at is None:
        active_admins = db.scalar(
            select(func.count())
            .select_from(User)
            .where(
                User.role == "administrator", User.disabled_at.is_(None), User.deleted_at.is_(None)
            )
        )
        if active_admins <= 1:
            raise IdentityError(
                409, "LAST_ADMINISTRATOR", "Keep at least one active administrator."
            )
    stamp = now()
    previous_role = target.role
    target.email = f"deleted+{target.id}@deleted.invalid"
    target.display_name = "Deleted account"
    target.password_hash = passwords.hash(secrets.token_urlsafe(48))
    target.disabled_at = stamp
    target.deleted_at = stamp
    target.version += 1
    target.updated_at = stamp
    db.execute(
        update(RefreshSession)
        .where(RefreshSession.user_id == target.id, RefreshSession.revoked_at.is_(None))
        .values(revoked_at=stamp)
    )
    write_audit(
        db,
        actor.id,
        target.id,
        "account_deleted",
        previous_role,
        "deleted",
        data.reason,
        request_id,
    )
    db.flush()
    return target


def check_version(user: User, expected: int) -> None:
    if user.version != expected:
        raise IdentityError(
            409, "VERSION_CONFLICT", "This account changed. Reload it before saving."
        )


def change_account(
    db: Session,
    ids: tuple[UUID, UUID],
    target_id: UUID,
    data: AdminChange,
    kind: str,
    value: str | bool,
    request_id: str,
) -> User:
    require_admin(active_actor(db, ids))  # Reject before revealing the target.
    db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": ADMIN_LOCK})
    # Admin changes share a global lifecycle lock; other operations lock only their own user.
    actor = active_actor(db, ids, lock=True)
    require_admin(actor)
    if actor.id == target_id:
        raise IdentityError(
            409, "SELF_MANAGEMENT_BLOCKED", "Use another administrator for this action."
        )
    target = db.scalar(select(User).where(User.id == target_id).with_for_update())
    if target is None:
        raise IdentityError(404, "ACCOUNT_NOT_FOUND", "Account not found.")
    check_version(target, data.expected_version)
    if target.deleted_at is not None:
        raise IdentityError(
            409, "ACCOUNT_ALREADY_DELETED", "This account has already been removed."
        )
    losing_admin = (
        target.role == "administrator"
        and target.disabled_at is None
        and target.deleted_at is None
        and (kind == "role" and value != "administrator" or kind == "status" and not value)
    )
    if (
        losing_admin
        and db.scalar(
            select(func.count())
            .select_from(User)
            .where(
                User.role == "administrator",
                User.disabled_at.is_(None),
                User.deleted_at.is_(None),
            )
        )
        <= 1
    ):
        raise IdentityError(409, "LAST_ADMINISTRATOR", "Keep at least one active administrator.")
    previous = (
        target.role if kind == "role" else ("enabled" if target.disabled_at is None else "disabled")
    )
    if kind == "role":
        target.role = str(value)
        current = target.role
    else:
        target.disabled_at = None if value else now()
        current = "enabled" if value else "disabled"
    target.version += 1
    target.updated_at = now()
    if kind == "role" or not value:
        db.execute(
            update(RefreshSession)
            .where(
                RefreshSession.user_id == target.id,
                RefreshSession.revoked_at.is_(None),
            )
            .values(revoked_at=now())
        )
    write_audit(db, actor.id, target.id, kind, previous, current, data.reason, request_id)
    if kind == "role" and current != previous and target.disabled_at is None:
        create_notification(
            db,
            target.id,
            "role_changed",
            "Account role updated",
            f"Your WagaMaga account role is now {current}.",
        )
    elif kind == "status" and value and previous == "disabled":
        create_notification(
            db,
            target.id,
            "account_reenabled",
            "Account access restored",
            "Your account was re-enabled. Sign in to continue.",
        )
    db.flush()
    return target


def write_audit(
    db: Session,
    actor: UUID,
    target: UUID,
    action: str,
    previous: str | None,
    current: str,
    reason: str,
    request_id: str,
) -> None:
    db.add(
        AuditLog(
            actor_id=actor,
            target_id=target,
            action=action,
            previous_value=previous,
            new_value=current,
            reason=reason,
            request_id=request_id,
        )
    )


def bootstrap_admin(db: Session, data: Register) -> User:
    db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": ADMIN_LOCK})
    if db.scalar(select(func.count()).select_from(User).where(User.role == "administrator")):
        raise IdentityError(
            409, "BOOTSTRAP_CLOSED", "Administrator bootstrap has already been completed."
        )
    if db.scalar(select(User.id).where(User.email == data.email)):
        raise IdentityError(
            409, "ACCOUNT_EXISTS", "Use a new account for the initial administrator."
        )
    user = User(
        email=data.email,
        display_name=data.display_name,
        password_hash=passwords.hash(data.password.get_secret_value()),
        role="administrator",
    )
    db.add(user)
    db.flush()
    write_audit(
        db,
        user.id,
        user.id,
        "bootstrap",
        None,
        "administrator",
        "Controlled initial administrator setup",
        str(uuid4()),
    )
    return user

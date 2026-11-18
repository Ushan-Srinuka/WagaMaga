"""Password hashing and strictly verified, short-lived access tokens."""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from pwdlib import PasswordHash

from app.core.config import Settings

passwords = PasswordHash.recommended()
DUMMY_HASH = passwords.hash(secrets.token_urlsafe(32))
COOKIE_NAME = "wagamaga_refresh"
COOKIE_PATH = "/api/v1/auth"


class IdentityError(Exception):
    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        *,
        clear_cookie: bool = False,
        retry_after: int | None = None,
    ):
        self.status = status
        self.code = code
        self.message = message
        self.clear_cookie = clear_cookie
        self.retry_after = retry_after


def now() -> datetime:
    return datetime.now(UTC)


def key(settings: Settings) -> str:
    if settings.auth_signing_key is None:
        raise IdentityError(503, "IDENTITY_NOT_CONFIGURED", "Account access is not configured.")
    return settings.auth_signing_key.get_secret_value()


def token_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def bucket_key(settings: Settings, value: str) -> str:
    return hmac.new(
        key(settings).encode(), b"rate-limit:" + value.encode(), hashlib.sha256
    ).hexdigest()


def access_token(settings: Settings, user_id: UUID, session_id: UUID) -> str:
    issued = now()
    return jwt.encode(
        {
            "sub": str(user_id),
            "sid": str(session_id),
            "iss": settings.auth_issuer,
            "aud": settings.auth_audience,
            "iat": issued,
            "exp": issued + timedelta(minutes=settings.auth_access_minutes),
        },
        key(settings),
        algorithm="HS256",
    )


def claims(settings: Settings, token: str) -> tuple[UUID, UUID]:
    try:
        data = jwt.decode(
            token,
            key(settings),
            algorithms=["HS256"],
            issuer=settings.auth_issuer,
            audience=settings.auth_audience,
            options={"require": ["sub", "sid", "iss", "aud", "iat", "exp"]},
        )
        if not isinstance(data["sub"], str) or not isinstance(data["sid"], str):
            raise ValueError("Invalid identifier claim")
        return UUID(data["sub"]), UUID(data["sid"])
    except jwt.PyJWTError, ValueError, TypeError, KeyError:
        raise IdentityError(401, "AUTHENTICATION_REQUIRED", "Please sign in again.") from None

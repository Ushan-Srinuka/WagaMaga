"""Request-owned transactions and server-derived actors."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.modules.identity.security import IdentityError, claims, key
from app.modules.identity.service import Limiter, active_actor, denied, require_admin

bearer = HTTPBearer(auto_error=False)


def database(request: Request):
    engine = request.app.state.database.engine
    if engine is None:
        raise IdentityError(
            503, "DATABASE_UNAVAILABLE", "Account access is temporarily unavailable."
        )
    key(request.app.state.settings)
    with Session(engine, expire_on_commit=False) as db, db.begin():
        yield db


DB = Annotated[Session, Depends(database, scope="function")]


def principal(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> tuple[UUID, UUID]:
    if credentials is None:
        raise denied()
    return claims(request.app.state.settings, credentials.credentials)


Principal = Annotated[tuple[UUID, UUID], Depends(principal)]


def administrator(db: DB, ids: Principal):
    user = active_actor(db, ids)
    require_admin(user)
    return user


def browser_write(
    request: Request,
    x_wagamaga_client: Annotated[str | None, Header()] = None,
):
    settings = request.app.state.settings
    if (
        request.headers.get("origin") not in settings.auth_allowed_origins
        or x_wagamaga_client != "web"
    ):
        raise IdentityError(403, "ORIGIN_DENIED", "This request origin is not permitted.")
    if request.headers.get("content-length", "0") != "0" and (
        request.headers.get("content-type", "").split(";")[0] != "application/json"
    ):
        raise IdentityError(415, "JSON_REQUIRED", "Send a JSON request.")


def limiter(request: Request) -> Limiter:
    engine = request.app.state.database.engine
    if engine is None:
        raise IdentityError(
            503, "DATABASE_UNAVAILABLE", "Account access is temporarily unavailable."
        )
    return Limiter(engine, request.app.state.settings)

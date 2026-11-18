"""Thin account HTTP handlers; all permissions are checked on the server."""

from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import aliased

from app.modules.identity import service
from app.modules.identity.dependencies import DB, Principal, administrator, browser_write, limiter
from app.modules.identity.models import AuditLog, User
from app.modules.identity.schemas import (
    Acknowledgement,
    AdminChange,
    AuditAction,
    AuditPage,
    Login,
    PasswordChange,
    Profile,
    Register,
    Role,
    RoleChange,
    StatusChange,
    TokenOut,
    UserOut,
    UserPage,
)
from app.modules.identity.security import COOKIE_NAME, COOKIE_PATH, IdentityError

router = APIRouter(prefix="/api/v1", tags=["Accounts"])
auth = APIRouter(prefix="/auth", dependencies=[Depends(browser_write)])
admin = APIRouter(prefix="/admin/users", dependencies=[Depends(administrator)])
audit_admin = APIRouter(
    prefix="/admin/audit-logs", tags=["Audit"], dependencies=[Depends(administrator)]
)
Limit = Annotated[service.Limiter, Depends(limiter)]


def set_refresh(request: Request, response: Response, raw: str, expiry: datetime):
    response.set_cookie(
        COOKIE_NAME,
        raw,
        httponly=True,
        secure=request.app.state.settings.app_env == "production",
        samesite="lax",
        path=COOKIE_PATH,
        expires=expiry.astimezone(UTC),
    )


def client_ip(request: Request) -> str:
    # Uvicorn is run with --no-proxy-headers; untrusted forwarding headers are not parsed here.
    return request.client.host if request.client else "unknown"


@auth.post("/register", response_model=Acknowledgement)
def registration(data: Register, request: Request, db: DB, limits: Limit):
    settings = request.app.state.settings
    limits.check("registration", client_ip(request), settings.auth_registration_attempts, 3600)
    service.register(db, data)
    return {"message": "Registration request processed. You can now try signing in."}


@auth.post("/login", response_model=TokenOut)
def login(data: Login, request: Request, response: Response, db: DB, limits: Limit):
    result, raw, expiry = service.login(
        db,
        request.app.state.settings,
        limits,
        data.email,
        data.password.get_secret_value(),
        client_ip(request),
    )
    set_refresh(request, response, raw, expiry)
    return result


@auth.post("/refresh", response_model=TokenOut)
def refresh(request: Request, response: Response, db: DB, limits: Limit):
    result, raw, expiry = service.refresh(
        db, request.app.state.settings, limits, request.cookies.get(COOKIE_NAME), client_ip(request)
    )
    set_refresh(request, response, raw, expiry)
    return result


@auth.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: DB):
    service.logout(db, request.cookies.get(COOKIE_NAME))
    response.delete_cookie(COOKIE_NAME, path=COOKIE_PATH)


@router.get("/me", response_model=UserOut)
def me(db: DB, ids: Principal):
    return service.active_actor(db, ids)


@router.patch("/me", response_model=UserOut)
def update_me(data: Profile, db: DB, ids: Principal):
    return service.update_profile(db, ids, data)


@router.post("/me/password", response_model=UserOut, dependencies=[Depends(browser_write)])
def change_my_password(
    data: PasswordChange, request: Request, db: DB, ids: Principal, limits: Limit
):
    return service.change_password(
        db,
        ids,
        data,
        request.state.request_id,
        limits,
        request.app.state.settings,
        client_ip(request),
    )


@admin.get("", response_model=UserPage)
def users(
    db: DB,
    q: Annotated[str, Query(max_length=100)] = "",
    role: Role | None = None,
    status: Literal["enabled", "disabled", "deleted"] | None = None,
    page: Annotated[int, Query(ge=1, le=10000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    filters = []
    if q.strip():
        filters.append(
            or_(
                User.email.icontains(q.strip(), autoescape=True),
                User.display_name.icontains(q.strip(), autoescape=True),
            )
        )
    if role:
        filters.append(User.role == role)
    if status == "deleted":
        filters.append(User.deleted_at.is_not(None))
    elif status == "enabled":
        filters.extend([User.disabled_at.is_(None), User.deleted_at.is_(None)])
    elif status == "disabled":
        filters.extend([User.disabled_at.is_not(None), User.deleted_at.is_(None)])
    else:
        filters.append(User.deleted_at.is_(None))
    total = db.scalar(select(func.count()).select_from(User).where(*filters))
    records = db.scalars(
        select(User)
        .where(*filters)
        .order_by(User.created_at.desc(), User.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {"items": records, "total": total, "page": page, "page_size": page_size}


@admin.get("/{user_id}", response_model=UserOut)
def user_detail(user_id: UUID, db: DB):
    user = db.get(User, user_id)
    if user is None:
        from app.modules.identity.security import IdentityError

        raise IdentityError(404, "ACCOUNT_NOT_FOUND", "Account not found.")
    return user


@admin.patch("/{user_id}/role", response_model=UserOut)
def change_role(user_id: UUID, data: RoleChange, request: Request, db: DB, ids: Principal):
    return service.change_account(
        db, ids, user_id, data, "role", data.role, request.state.request_id
    )


@admin.patch("/{user_id}/status", response_model=UserOut)
def change_status(user_id: UUID, data: StatusChange, request: Request, db: DB, ids: Principal):
    return service.change_account(
        db, ids, user_id, data, "status", data.enabled, request.state.request_id
    )


@admin.delete("/{user_id}", response_model=UserOut, dependencies=[Depends(browser_write)])
def delete_user(user_id: UUID, data: AdminChange, request: Request, db: DB, ids: Principal):
    return service.delete_account(db, ids, user_id, data, request.state.request_id)


@audit_admin.get("", response_model=AuditPage)
def audit_events(
    request: Request,
    db: DB,
    ids: Principal,
    q: Annotated[str, Query(max_length=100)] = "",
    action: AuditAction | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    page: Annotated[int, Query(ge=1, le=10000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
):
    actor = service.active_actor(db, ids)
    actor_user = aliased(User)
    target_user = aliased(User)
    filters = []
    if action:
        filters.append(AuditLog.action == action)
    if q.strip():
        term = q.strip()
        filters.append(
            or_(
                actor_user.display_name.icontains(term, autoescape=True),
                actor_user.email.icontains(term, autoescape=True),
                target_user.display_name.icontains(term, autoescape=True),
                target_user.email.icontains(term, autoescape=True),
            )
        )
    if from_date and to_date and from_date > to_date:
        raise IdentityError(422, "INVALID_DATE_RANGE", "End date must be on or after start date.")
    if from_date:
        filters.append(AuditLog.created_at >= datetime.combine(from_date, time.min, UTC))
    if to_date:
        filters.append(
            AuditLog.created_at < datetime.combine(to_date + timedelta(days=1), time.min, UTC)
        )
    joins = (
        select(AuditLog, actor_user.display_name, target_user.display_name)
        .outerjoin(actor_user, actor_user.id == AuditLog.actor_id)
        .outerjoin(target_user, target_user.id == AuditLog.target_id)
    )
    count_query = (
        select(func.count())
        .select_from(AuditLog)
        .outerjoin(actor_user, actor_user.id == AuditLog.actor_id)
        .outerjoin(target_user, target_user.id == AuditLog.target_id)
        .where(*filters)
    )
    total = db.scalar(count_query) or 0
    records = db.execute(
        joins.where(*filters)
        .order_by(AuditLog.created_at.desc(), AuditLog.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    items = [
        {
            "id": event.id,
            "actor_id": event.actor_id,
            "actor_name": actor_name,
            "target_id": event.target_id,
            "target_name": target_name,
            "action": event.action,
            "previous_value": event.previous_value,
            "new_value": event.new_value,
            "reason": event.reason,
            "request_id": event.request_id,
            "created_at": event.created_at,
        }
        for event, actor_name, target_name in records
    ]
    # Reading this administrator-only feed is itself recorded without query values or private data.
    service.write_audit(
        db,
        actor.id,
        actor.id,
        "audit_viewed",
        None,
        "viewed",
        "Administrator viewed audit history",
        request.state.request_id,
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


router.include_router(auth)
router.include_router(admin)
router.include_router(audit_admin)

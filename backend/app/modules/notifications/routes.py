"""Recipient-owned in-app notification API."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.modules.farms.reminders import visible_notification
from app.modules.identity.dependencies import DB, Principal
from app.modules.identity.service import active_actor
from app.modules.notifications import service
from app.modules.notifications.models import Notification
from app.modules.notifications.schemas import NotificationChange, NotificationOut, NotificationPage

router = APIRouter(prefix="/api/v1/notifications", tags=["Notifications"])


@router.get("", response_model=NotificationPage)
def list_notifications(
    db: DB,
    ids: Principal,
    unread_only: bool = False,
    page: Annotated[int, Query(ge=1, le=10000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    actor = active_actor(db, ids)
    filters = [Notification.recipient_id == actor.id, visible_notification()]
    if unread_only:
        filters.append(Notification.read_at.is_(None))
    total = db.scalar(select(func.count()).select_from(Notification).where(*filters)) or 0
    records = db.scalars(
        select(Notification)
        .where(*filters)
        .order_by(Notification.created_at.desc(), Notification.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": records,
        "total": total,
        "unread_count": service.unread_count(db, actor.id),
        "page": page,
        "page_size": page_size,
    }


@router.patch("/{notification_id}", response_model=NotificationOut)
def update_notification(
    notification_id: UUID,
    data: NotificationChange,
    db: DB,
    ids: Principal,
):
    actor = active_actor(db, ids)
    return service.update_read_state(db, actor.id, notification_id, data)

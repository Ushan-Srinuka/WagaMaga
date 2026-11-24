"""Notification creation and recipient-scoped state changes."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.farms.reminders import visible_notification
from app.modules.identity.security import IdentityError, now
from app.modules.notifications.models import Notification
from app.modules.notifications.schemas import NotificationChange


def create_notification(
    db: Session,
    recipient_id: UUID,
    event_type: str,
    title: str,
    body: str,
    *,
    review_plan_id: UUID | None = None,
) -> None:
    """Add a trusted, templated account event to the current transaction."""
    db.add(
        Notification(
            recipient_id=recipient_id,
            event_type=event_type,
            title=title,
            body=body,
            review_plan_id=review_plan_id,
        )
    )


def unread_count(db: Session, recipient_id: UUID) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.recipient_id == recipient_id,
                Notification.read_at.is_(None),
                visible_notification(),
            )
        )
        or 0
    )


def update_read_state(
    db: Session,
    recipient_id: UUID,
    notification_id: UUID,
    data: NotificationChange,
) -> Notification:
    item = db.scalar(
        select(Notification)
        .where(
            Notification.id == notification_id,
            Notification.recipient_id == recipient_id,
            visible_notification(),
        )
        .with_for_update()
    )
    if item is None:
        raise IdentityError(404, "NOTIFICATION_NOT_FOUND", "Notification not found.")
    item.read_at = (item.read_at or now()) if data.read else None
    db.flush()
    return item

"""Persisted in-app notification records."""

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('role_changed','account_reenabled','password_changed',"
            "'support_updated','weather_review','advisor_review','task_due','task_overdue')",
            name="notifications_event_type",
        ),
        Index("ix_notifications_recipient_created", "recipient_id", "created_at", "id"),
        CheckConstraint(
            "(event_type = 'advisor_review') = (review_plan_id IS NOT NULL)",
            name="notifications_review_link",
        ),
        CheckConstraint(
            "(event_type IN ('task_due','task_overdue')) = (reminder_task_id IS NOT NULL) "
            "AND (reminder_task_id IS NULL) = (reminder_due_date IS NULL)",
            name="notifications_task_reminder_link",
        ),
        UniqueConstraint(
            "reminder_task_id",
            "reminder_due_date",
            "event_type",
            name="uq_notifications_task_reminder",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    recipient_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_plan_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("task_plans.id", name="fk_notifications_review_plan", ondelete="RESTRICT")
    )
    reminder_task_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("farm_tasks.id", name="fk_notifications_reminder_task", ondelete="RESTRICT")
    )
    reminder_due_date: Mapped[date | None]

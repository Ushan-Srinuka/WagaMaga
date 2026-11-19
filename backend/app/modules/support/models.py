"""Farmer-submitted support conversations; no private farm or AI-chat references."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

STATES = "'open','in_progress','resolved'"


class SupportTicket(Base):
    __tablename__ = "support_tickets"
    __table_args__ = (
        CheckConstraint(
            "category IN ('account','farm_records','technical','feedback')",
            name="support_ticket_category",
        ),
        CheckConstraint(f"status IN ({STATES})", name="support_ticket_status"),
        CheckConstraint("subject ~ '[^[:space:]]'", name="support_ticket_subject"),
        CheckConstraint("version > 0", name="support_ticket_version"),
        Index("ix_support_tickets_owner_updated", "farmer_id", "updated_at", "id"),
        Index("ix_support_tickets_status_updated", "status", "updated_at", "id"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    farmer_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    category: Mapped[str] = mapped_column(String(20))
    subject: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(16), default="open")
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SupportMessage(Base):
    __tablename__ = "support_messages"
    __table_args__ = (
        CheckConstraint("author_role IN ('farmer','administrator')", name="support_message_role"),
        CheckConstraint(
            "body ~ '[^[:space:]]' AND char_length(body) <= 4000", name="support_message_body"
        ),
        CheckConstraint("ticket_version > 0", name="support_message_version"),
        UniqueConstraint("ticket_id", "ticket_version", name="uq_support_message_version"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    ticket_id: Mapped[UUID] = mapped_column(ForeignKey("support_tickets.id", ondelete="RESTRICT"))
    author_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    author_role: Mapped[str] = mapped_column(String(16))
    body: Mapped[str] = mapped_column(Text)
    ticket_version: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SupportEvent(Base):
    __tablename__ = "support_events"
    __table_args__ = (
        CheckConstraint(
            "operation IN ('created','replied','status_changed')", name="support_event_operation"
        ),
        CheckConstraint(
            f"previous_status IS NULL OR previous_status IN ({STATES})",
            name="support_event_previous",
        ),
        CheckConstraint(f"status IN ({STATES})", name="support_event_status"),
        CheckConstraint("ticket_version > 0", name="support_event_version"),
        UniqueConstraint("ticket_id", "ticket_version", name="uq_support_event_version"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    ticket_id: Mapped[UUID] = mapped_column(ForeignKey("support_tickets.id", ondelete="RESTRICT"))
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    operation: Mapped[str] = mapped_column(String(20))
    previous_status: Mapped[str | None] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16))
    ticket_version: Mapped[int] = mapped_column(Integer)
    request_id: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

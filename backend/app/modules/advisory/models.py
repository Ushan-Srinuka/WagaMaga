"""Explicit advisor assignment and append-only decisions on immutable task plans."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AdvisorCase(Base):
    __tablename__ = "advisor_cases"
    __table_args__ = (
        UniqueConstraint("plan_id", "advisor_id", name="uq_advisor_case_assignment"),
        Index("ix_advisor_cases_recipient", "advisor_id", "submitted_at", "plan_id"),
    )

    plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("task_plans.id", ondelete="RESTRICT"), primary_key=True
    )
    farmer_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    advisor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    request_id: Mapped[str] = mapped_column(String(36))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoke_request_id: Mapped[str | None] = mapped_column(String(36))


class AdvisorDecision(Base):
    __tablename__ = "advisor_decisions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["plan_id", "advisor_id"],
            ["advisor_cases.plan_id", "advisor_cases.advisor_id"],
            name="fk_advisor_decision_assignment",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["plan_id", "plan_version", "action_hash"],
            ["task_plans.id", "task_plans.version", "task_plans.action_hash"],
            name="fk_advisor_decision_plan",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "outcome IN ('cleared','declined','changes_requested')",
            name="advisor_decisions_outcome",
        ),
        CheckConstraint("reason ~ '[^[:space:]]'", name="advisor_decisions_reason"),
    )

    plan_id: Mapped[UUID] = mapped_column(primary_key=True)
    advisor_id: Mapped[UUID] = mapped_column()
    plan_version: Mapped[int] = mapped_column()
    action_hash: Mapped[str] = mapped_column(String(64))
    outcome: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str] = mapped_column(String(500))
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    request_id: Mapped[str] = mapped_column(String(36))

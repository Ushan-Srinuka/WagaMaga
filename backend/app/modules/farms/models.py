"""Farm persistence models reused by the owner-scoped FR-C services."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

CHILLI_ID = UUID("1e7402ea-35ab-4673-a8de-834c4bb70401")
AREA_CHECK = "area_value > 0 AND area_value < 1000000000000 AND area_value = trunc(area_value, 6)"


class RecordColumns:
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Farm(RecordColumns, Base):
    __tablename__ = "farms"
    __table_args__ = (
        CheckConstraint("version > 0", name="farms_version"),
        CheckConstraint("name ~ '[^[:space:]]'", name="farms_name"),
        CheckConstraint("location ~ '[^[:space:]]'", name="farms_location"),
        CheckConstraint("timezone ~ '[^[:space:]]'", name="farms_timezone"),
        CheckConstraint("(latitude IS NULL) = (longitude IS NULL)", name="farms_coordinate_pair"),
        CheckConstraint("latitude BETWEEN -90 AND 90", name="farms_latitude"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="farms_longitude"),
        CheckConstraint("(area_value IS NULL) = (area_unit IS NULL)", name="farms_area_pair"),
        CheckConstraint(AREA_CHECK, name="farms_area_value"),
        CheckConstraint("area_unit IN ('ha','acre','m2')", name="farms_area_unit"),
        Index("ix_farms_owner_archive_created", "farmer_id", "archived_at", "created_at", "id"),
    )

    farmer_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    name: Mapped[str] = mapped_column(String(120))
    location: Mapped[str] = mapped_column(String(200))
    timezone: Mapped[str] = mapped_column(String(100), default="Asia/Colombo")
    latitude: Mapped[Decimal | None] = mapped_column(Numeric())
    longitude: Mapped[Decimal | None] = mapped_column(Numeric())
    area_value: Mapped[Decimal | None] = mapped_column(Numeric())
    area_unit: Mapped[str | None] = mapped_column(String(4))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CropType(Base):
    __tablename__ = "crop_types"
    __table_args__ = (
        CheckConstraint("code ~ '^[a-z][a-z0-9_]*$'", name="crop_types_code"),
        CheckConstraint("display_name ~ '[^[:space:]]'", name="crop_types_name"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    display_name: Mapped[str] = mapped_column(String(80))
    supported: Mapped[bool] = mapped_column(Boolean, default=False)


class FarmDeletion(Base):
    """Append-only workspace tombstone; retained farm evidence is not erased."""

    __tablename__ = "farm_deletions"
    __table_args__ = (
        CheckConstraint("entity_version > 0", name="farm_deletions_version"),
        CheckConstraint("isfinite(deleted_at)", name="farm_deletions_time"),
    )

    farm_id: Mapped[UUID] = mapped_column(
        ForeignKey("farms.id", ondelete="RESTRICT"), primary_key=True
    )
    deleted_by: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    entity_version: Mapped[int] = mapped_column(Integer)


def visible_farm():
    return ~select(FarmDeletion.farm_id).where(FarmDeletion.farm_id == Farm.id).exists()


class Cultivation(RecordColumns, Base):
    __tablename__ = "cultivations"
    __table_args__ = (
        UniqueConstraint("id", "farm_id", name="uq_cultivations_id_farm"),
        CheckConstraint("version > 0", name="cultivations_version"),
        CheckConstraint(AREA_CHECK, name="cultivations_area_value"),
        CheckConstraint("area_unit IN ('ha','acre','m2')", name="cultivations_area_unit"),
        CheckConstraint("isfinite(planting_date)", name="cultivations_planting_date"),
        CheckConstraint("char_length(soil_notes) <= 2000", name="cultivations_soil_notes"),
        CheckConstraint(
            "(confirmed_stage IS NULL AND confirmed_by IS NULL AND confirmed_at IS NULL) OR "
            "(confirmed_stage IS NOT NULL AND confirmed_by IS NOT NULL "
            "AND confirmed_at IS NOT NULL AND confirmed_stage ~ '[^[:space:]]')",
            name="cultivations_confirmation",
        ),
        CheckConstraint("estimated_stage IS NULL", name="cultivations_no_estimator"),
        Index("ix_cultivations_farm_archive_created", "farm_id", "archived_at", "created_at", "id"),
        Index("ix_cultivations_crop", "crop_type_id"),
    )

    farm_id: Mapped[UUID] = mapped_column(ForeignKey("farms.id", ondelete="RESTRICT"))
    crop_type_id: Mapped[UUID] = mapped_column(ForeignKey("crop_types.id", ondelete="RESTRICT"))
    planting_date: Mapped[date] = mapped_column(Date)
    area_value: Mapped[Decimal] = mapped_column(Numeric())
    area_unit: Mapped[str] = mapped_column(String(4))
    soil_notes: Mapped[str | None] = mapped_column(Text)
    estimated_stage: Mapped[str | None] = mapped_column(String(80))
    confirmed_stage: Mapped[str | None] = mapped_column(String(80))
    confirmed_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FarmObservation(RecordColumns, Base):
    __tablename__ = "farm_observations"
    __table_args__ = (
        UniqueConstraint("id", "cultivation_id", name="uq_observations_id_cultivation"),
        CheckConstraint("version > 0", name="farm_observations_version"),
        CheckConstraint(
            "notes ~ '[^[:space:]]' AND char_length(notes) <= 4000",
            name="farm_observations_notes",
        ),
        CheckConstraint("isfinite(observed_at)", name="farm_observations_observed_at"),
        CheckConstraint(
            "soil_moisture IN ('dry','moist','waterlogged')", name="farm_observations_soil_moisture"
        ),
        Index("ix_observations_cultivation_observed", "cultivation_id", "observed_at", "id"),
    )

    cultivation_id: Mapped[UUID] = mapped_column(ForeignKey("cultivations.id", ondelete="RESTRICT"))
    soil_moisture: Mapped[str | None] = mapped_column(String(12))
    recorded_by: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str] = mapped_column(Text)


class FarmTask(RecordColumns, Base):
    __tablename__ = "farm_tasks"
    __table_args__ = (
        CheckConstraint("version > 0", name="farm_tasks_version"),
        CheckConstraint("title ~ '[^[:space:]]'", name="farm_tasks_title"),
        CheckConstraint("isfinite(due_date)", name="farm_tasks_due_date"),
        CheckConstraint(
            "status IN ('pending', 'completed', 'cancelled')", name="farm_tasks_status"
        ),
        Index("ix_farm_tasks_due", "cultivation_id", "due_date", "id"),
    )

    cultivation_id: Mapped[UUID] = mapped_column(ForeignKey("cultivations.id", ondelete="RESTRICT"))
    title: Mapped[str] = mapped_column(String(120))
    due_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(9), default="pending")


class FarmTaskEvent(Base):
    __tablename__ = "farm_task_events"
    __table_args__ = (
        CheckConstraint(
            "(version = 1 AND action = 'created') OR "
            "(version > 1 AND action IN ('edited', 'completed', 'cancelled'))",
            name="farm_task_events_action",
        ),
        CheckConstraint("title ~ '[^[:space:]]'", name="farm_task_events_title"),
        CheckConstraint("isfinite(due_date)", name="farm_task_events_due_date"),
    )

    task_id: Mapped[UUID] = mapped_column(
        ForeignKey("farm_tasks.id", ondelete="RESTRICT"), primary_key=True
    )
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    due_date: Mapped[date] = mapped_column(Date)
    action: Mapped[str] = mapped_column(String(9))
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    request_id: Mapped[str] = mapped_column(String(36))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class TaskPlan(Base):
    __tablename__ = "task_plans"
    __table_args__ = (
        UniqueConstraint("id", "version", "action_hash", name="uq_task_plan_binding"),
        CheckConstraint("version = 1", name="task_plans_version"),
        CheckConstraint(
            "(action_type = 'create_task' AND target_task_id IS NULL "
            "AND target_task_version IS NULL "
            "AND previous_due_date IS NULL AND weather_evidence IS NULL) OR "
            "(action_type = 'reschedule_task' AND target_task_id IS NOT NULL "
            "AND target_task_version IS NOT NULL AND target_task_version > 0 "
            "AND previous_due_date IS NOT NULL AND isfinite(previous_due_date) "
            "AND previous_due_date <> due_date AND weather_evidence IS NOT NULL "
            "AND jsonb_typeof(weather_evidence) = 'object')",
            name="task_plans_action",
        ),
        CheckConstraint("farm_version > 0 AND cultivation_version > 0", name="task_plans_context"),
        UniqueConstraint("revises_plan_id", name="uq_task_plan_revision_parent"),
        CheckConstraint("isfinite(due_date) AND expires_at > created_at", name="task_plans_dates"),
        Index("ix_task_plans_cultivation_created", "cultivation_id", "created_at", "id"),
        Index("ix_task_plans_target_created", "target_task_id", "created_at", "id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    cultivation_id: Mapped[UUID] = mapped_column(ForeignKey("cultivations.id", ondelete="RESTRICT"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    action_type: Mapped[str] = mapped_column(String(16), default="create_task")
    action_hash: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(120))
    due_date: Mapped[date] = mapped_column(Date)
    evidence_code: Mapped[str] = mapped_column(String(40))
    evidence_text: Mapped[str] = mapped_column(Text)
    farm_version: Mapped[int] = mapped_column(Integer)
    cultivation_version: Mapped[int] = mapped_column(Integer)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    request_id: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    target_task_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("farm_tasks.id", ondelete="RESTRICT")
    )
    target_task_version: Mapped[int | None] = mapped_column(Integer)
    previous_due_date: Mapped[date | None] = mapped_column(Date)
    weather_evidence: Mapped[dict | None] = mapped_column(JSONB(none_as_null=True))
    revises_plan_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("task_plans.id", name="fk_task_plan_revision_parent", ondelete="RESTRICT")
    )


class TaskPlanDecision(Base):
    __tablename__ = "task_plan_decisions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["plan_id", "plan_version", "action_hash"],
            ["task_plans.id", "task_plans.version", "task_plans.action_hash"],
            name="fk_task_plan_decision_binding",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "(outcome = 'accepted' AND task_id IS NOT NULL AND task_version IS NOT NULL) OR "
            "(outcome = 'rejected' AND task_id IS NULL AND task_version IS NULL)",
            name="task_plan_decisions_effect",
        ),
        UniqueConstraint("task_id", "task_version", name="uq_task_plan_decision_effect"),
        ForeignKeyConstraint(
            ["task_id", "task_version"],
            ["farm_task_events.task_id", "farm_task_events.version"],
            name="fk_task_plan_decision_effect",
            ondelete="RESTRICT",
        ),
    )

    plan_id: Mapped[UUID] = mapped_column(primary_key=True)
    plan_version: Mapped[int] = mapped_column(Integer)
    action_hash: Mapped[str] = mapped_column(String(64))
    outcome: Mapped[str] = mapped_column(String(8))
    task_id: Mapped[UUID | None] = mapped_column(ForeignKey("farm_tasks.id", ondelete="RESTRICT"))
    task_version: Mapped[int | None] = mapped_column(Integer)
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    request_id: Mapped[str] = mapped_column(String(36))
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    plan: Mapped[TaskPlan] = relationship()


class RevisionColumns:
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    version: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict] = mapped_column(JSONB)
    changed_by: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


def snapshot_check(parent: str, record: type[Base], *, optional: str | None = None) -> str:
    # Explicit top-level keys prevent untrusted extra fields from entering history.
    keys = ",".join(f"'{column.name}'" for column in record.__table__.columns)
    required = (
        ",".join(
            f"'{column.name}'" for column in record.__table__.columns if column.name != optional
        )
        if optional
        else keys
    )
    return (
        "jsonb_typeof(snapshot) = 'object' "
        f"AND snapshot ?& ARRAY[{required}] "
        f"AND snapshot - ARRAY[{keys}] = '{{}}'::jsonb "
        f"AND (snapshot->>'id' = {parent}::text) IS TRUE "
        "AND (snapshot->>'version' = version::text) IS TRUE"
    )


class FarmRevision(RevisionColumns, Base):
    __tablename__ = "farm_revisions"
    __table_args__ = (
        UniqueConstraint("farm_id", "version", name="uq_farm_revisions_version"),
        CheckConstraint("version > 0", name="farm_revisions_version"),
        CheckConstraint(snapshot_check("farm_id", Farm), name="farm_revisions_snapshot"),
    )

    farm_id: Mapped[UUID] = mapped_column(ForeignKey("farms.id", ondelete="RESTRICT"))


class CultivationRevision(RevisionColumns, Base):
    __tablename__ = "cultivation_revisions"
    __table_args__ = (
        UniqueConstraint("cultivation_id", "version", name="uq_cultivation_revisions_version"),
        CheckConstraint("version > 0", name="cultivation_revisions_version"),
        CheckConstraint(
            snapshot_check("cultivation_id", Cultivation), name="cultivation_revisions_snapshot"
        ),
    )

    cultivation_id: Mapped[UUID] = mapped_column(ForeignKey("cultivations.id", ondelete="RESTRICT"))


class ObservationRevision(RevisionColumns, Base):
    __tablename__ = "observation_revisions"
    __table_args__ = (
        UniqueConstraint("observation_id", "version", name="uq_observation_revisions_version"),
        CheckConstraint("version > 0", name="observation_revisions_version"),
        CheckConstraint(
            snapshot_check("observation_id", FarmObservation, optional="soil_moisture")
            + " AND (NOT (snapshot ? 'soil_moisture') OR (snapshot->>'soil_moisture' "
            "IN ('dry','moist','waterlogged')) IS TRUE)",
            name="observation_revisions_snapshot",
        ),
    )

    observation_id: Mapped[UUID] = mapped_column(
        ForeignKey("farm_observations.id", ondelete="RESTRICT")
    )


class FarmAuditEvent(Base):
    __tablename__ = "farm_audit_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["cultivation_id", "farm_id"],
            ["cultivations.id", "cultivations.farm_id"],
            ondelete="RESTRICT",
            name="fk_farm_audit_cultivation_parent",
        ),
        ForeignKeyConstraint(
            ["observation_id", "cultivation_id"],
            ["farm_observations.id", "farm_observations.cultivation_id"],
            ondelete="RESTRICT",
            name="fk_farm_audit_observation_parent",
        ),
        CheckConstraint("entity_version > 0", name="farm_audit_version"),
        CheckConstraint("outcome = 'succeeded'", name="farm_audit_outcome"),
        CheckConstraint(
            "(operation IN ('farm_created','farm_updated','farm_archived',"
            "'farm_restored','farm_deleted') "
            "AND cultivation_id IS NULL AND observation_id IS NULL) OR "
            "(operation IN ('cultivation_created','cultivation_updated',"
            "'cultivation_archived','stage_confirmed') "
            "AND cultivation_id IS NOT NULL AND observation_id IS NULL) OR "
            "(operation IN ('observation_created','observation_updated') "
            "AND cultivation_id IS NOT NULL AND observation_id IS NOT NULL)",
            name="farm_audit_operation_parent",
        ),
        Index("ix_farm_audit_farm_created", "farm_id", "created_at", "id"),
        Index(
            "uq_farm_audit_farm_version",
            "farm_id",
            "entity_version",
            unique=True,
            postgresql_where=text("cultivation_id IS NULL"),
        ),
        Index(
            "uq_farm_audit_cultivation_version",
            "cultivation_id",
            "entity_version",
            unique=True,
            postgresql_where=text("cultivation_id IS NOT NULL AND observation_id IS NULL"),
        ),
        Index(
            "uq_farm_audit_observation_version",
            "observation_id",
            "entity_version",
            unique=True,
            postgresql_where=text("observation_id IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    farm_id: Mapped[UUID] = mapped_column(ForeignKey("farms.id", ondelete="RESTRICT"))
    cultivation_id: Mapped[UUID | None] = mapped_column()
    observation_id: Mapped[UUID | None] = mapped_column()
    operation: Mapped[str] = mapped_column(String(40))
    entity_version: Mapped[int] = mapped_column(Integer)
    outcome: Mapped[str] = mapped_column(String(16), default="succeeded")
    request_id: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

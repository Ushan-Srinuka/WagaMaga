"""Bounded farm DTOs. Ownership and provenance are never writable client fields."""

import re
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    model_validator,
)


class DiaryEntry(BaseModel):
    id: UUID
    kind: Literal["observation", "completed", "cancelled", "create_task", "reschedule_task"]
    occurred_at: datetime
    description: str
    soil_moisture: str | None
    previous_due_date: date | None
    due_date: date | None


def trimmed(value: str) -> str:
    value = value.strip()
    if not value or "\x00" in value:
        raise ValueError("Enter nonblank text without null characters")
    return value


def soil_text(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    return trimmed(value)


def query_text(value: str) -> str:
    if "\x00" in value:
        raise ValueError("Search cannot contain null characters")
    return value


def local_date(value):
    if type(value) is date or isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return value
    raise ValueError("Use an ISO date")


def instant(value):
    if isinstance(value, (str, datetime)):
        return value
    raise ValueError("Use an ISO timestamp with an offset")


Name = Annotated[str, AfterValidator(trimmed), Field(max_length=120)]
Location = Annotated[str, AfterValidator(trimmed), Field(max_length=200)]
Timezone = Annotated[str, AfterValidator(trimmed), Field(max_length=100)]
Soil = Annotated[Annotated[str, Field(max_length=2000)] | None, AfterValidator(soil_text)]
Notes = Annotated[str, AfterValidator(trimmed), Field(max_length=4000)]
Stage = Annotated[str, AfterValidator(trimmed), Field(max_length=80)]
Area = Annotated[
    Decimal,
    Field(strict=False, gt=0, lt=Decimal("1000000000000"), decimal_places=6, allow_inf_nan=False),
]
Latitude = Annotated[Decimal, Field(strict=False, ge=-90, le=90, allow_inf_nan=False)]
Longitude = Annotated[Decimal, Field(strict=False, ge=-180, le=180, allow_inf_nan=False)]
Unit = Literal["ha", "acre", "m2"]
Identifier = Annotated[UUID, Field(strict=False)]
LocalDate = Annotated[date, Field(strict=False), BeforeValidator(local_date)]
ObservedAt = Annotated[
    AwareDatetime,
    Field(strict=False),
    BeforeValidator(instant),
    AfterValidator(lambda value: value.astimezone(UTC)),
]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class VersionCommand(Input):
    expected_version: int = Field(ge=1)


class FarmDelete(VersionCommand):
    confirmation_name: Name


class FarmDeleted(BaseModel):
    id: UUID
    deleted: Literal[True] = True
    message: str = "Farm removed from your workspace. Historical records are retained."


class FarmCreate(Input):
    name: Name
    location: Location
    timezone: Timezone = "Asia/Colombo"
    latitude: Latitude | None = None
    longitude: Longitude | None = None
    area_value: Area | None = None
    area_unit: Unit | None = None

    @model_validator(mode="after")
    def pairs(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Supply both coordinates or neither")
        if (self.area_value is None) != (self.area_unit is None):
            raise ValueError("Supply area and unit together")
        return self


class Patch(VersionCommand):
    @model_validator(mode="after")
    def required_values(self):
        nullable = {
            "latitude",
            "longitude",
            "area_value",
            "area_unit",
            "soil_notes",
            "soil_moisture",
        }
        # Cultivation areas are required, unlike optional farm area.
        if isinstance(self, CultivationPatch):
            nullable -= {"area_value", "area_unit"}
        for field in self.model_fields_set - nullable:
            if getattr(self, field) is None:
                raise ValueError("This field cannot be null")
        return self


class FarmPatch(Patch):
    name: Name | None = None
    location: Location | None = None
    timezone: Timezone | None = None
    latitude: Latitude | None = None
    longitude: Longitude | None = None
    area_value: Area | None = None
    area_unit: Unit | None = None


class CultivationCreate(Input):
    crop_type_id: Identifier
    planting_date: LocalDate
    area_value: Area
    area_unit: Unit
    soil_notes: Soil = None


class CultivationPatch(Patch):
    crop_type_id: Identifier | None = None
    planting_date: LocalDate | None = None
    area_value: Area | None = None
    area_unit: Unit | None = None
    soil_notes: Soil = None


class StageConfirmation(VersionCommand):
    stage: Stage


SoilMoisture = Literal["dry", "moist", "waterlogged"]


class ObservationCreate(Input):
    observed_at: ObservedAt
    notes: Notes
    soil_moisture: SoilMoisture | None = None


class ObservationPatch(Patch):
    observed_at: ObservedAt | None = None
    notes: Notes | None = None
    soil_moisture: SoilMoisture | None = None


class Paging(BaseModel):
    model_config = ConfigDict(extra="forbid")
    page: int = Field(default=1, ge=1, le=10000)
    page_size: int = Field(default=20, ge=1, le=100)


class FarmQuery(Paging):
    status: Literal["active", "archived", "all"] = "active"
    q: Annotated[str, AfterValidator(query_text)] = Field(default="", max_length=100)


class CultivationQuery(Paging):
    status: Literal["active", "archived", "all"] = "active"
    crop_type_id: UUID | None = None


class ObservationQuery(Paging):
    from_date: LocalDate | None = None
    to_date: LocalDate | None = None

    @model_validator(mode="after")
    def ordered(self):
        if self.from_date and self.to_date and self.from_date > self.to_date:
            raise ValueError("Dates must be ordered")
        return self


TaskStatus = Literal["pending", "completed", "cancelled"]
TaskOutcome = Literal["completed", "cancelled"]


class TaskQuery(Paging):
    status: TaskStatus | Literal["all"] = "pending"
    task_id: UUID | None = None


class TaskCreate(Input):
    title: Name
    due_date: LocalDate


class TaskEdit(TaskCreate, VersionCommand):
    pass


class TaskTransition(VersionCommand):
    status: TaskOutcome


class RecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    version: int
    created_at: datetime
    updated_at: datetime


class FarmSnapshot(RecordOut):
    farmer_id: UUID
    name: str
    location: str
    timezone: str
    latitude: Decimal | None
    longitude: Decimal | None
    area_value: Decimal | None
    area_unit: Unit | None
    archived_at: datetime | None


class FarmOut(FarmSnapshot):
    effective_archived: bool = False


class CultivationSnapshot(RecordOut):
    farm_id: UUID
    crop_type_id: UUID
    planting_date: date
    area_value: Decimal
    area_unit: Unit
    soil_notes: str | None
    estimated_stage: str | None
    confirmed_stage: str | None
    confirmed_by: UUID | None
    confirmed_at: datetime | None
    archived_at: datetime | None


class CultivationOut(CultivationSnapshot):
    effective_archived: bool = False
    planned: bool = False


class ObservationSnapshot(RecordOut):
    cultivation_id: UUID
    recorded_by: UUID
    observed_at: datetime
    notes: str
    soil_moisture: SoilMoisture | None = None


class ObservationOut(ObservationSnapshot):
    effective_archived: bool = False


class TaskOut(RecordOut):
    cultivation_id: UUID
    title: str
    due_date: date
    status: TaskStatus


class TaskEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: UUID
    version: int
    title: str
    due_date: date
    action: Literal["created", "edited", "completed", "cancelled"]
    occurred_at: datetime


PlanOutcome = Literal["accepted", "rejected"]


class DateReviewOut(BaseModel):
    id: UUID
    version: int
    action_hash: str
    task_id: UUID
    title: str
    current_due_date: date
    proposed_due_date: date
    evidence_text: str
    forecast_fetched_at: datetime | None
    expires_at: datetime


class PlanDecision(VersionCommand):
    action_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    outcome: PlanOutcome


class PlanDecisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    plan_id: UUID
    plan_version: int
    action_hash: str
    outcome: PlanOutcome
    task_id: UUID | None
    task_version: int | None
    decided_at: datetime


class PlanOut(BaseModel):
    id: UUID
    version: int
    action_type: Literal["create_task"]
    action_hash: str
    title: str
    due_date: date
    evidence_text: str
    expires_at: datetime
    state: Literal["pending", "accepted", "rejected", "expired", "stale"]
    decision: PlanDecisionOut | None


class LatestPlan(BaseModel):
    plan: PlanOut | None


class PlanHistoryOut(PlanDecisionOut):
    title: str
    due_date: date
    evidence_text: str
    action_type: Literal["create_task", "reschedule_task"]
    previous_due_date: date | None
    advisor_outcome: Literal["cleared", "declined", "changes_requested"] | None = None
    advisor_reason: str | None = None


class CropOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    display_name: str
    supported: bool


class HistoryItem[T](BaseModel):
    id: UUID
    version: int
    snapshot: T
    changed_by: UUID
    changed_at: datetime


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    page_size: int


class TaskPage(Page[TaskOut]):
    farm_today: date

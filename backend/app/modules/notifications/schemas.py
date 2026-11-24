"""Public DTOs for recipient-owned notification operations."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_type: Literal[
        "role_changed",
        "account_reenabled",
        "password_changed",
        "support_updated",
        "weather_review",
        "advisor_review",
        "task_due",
        "task_overdue",
    ]
    title: str
    body: str
    created_at: datetime
    read_at: datetime | None
    review_plan_id: UUID | None = None


class NotificationChange(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    read: bool


class NotificationPage(BaseModel):
    items: list[NotificationOut]
    total: int
    unread_count: int
    page: int
    page_size: int

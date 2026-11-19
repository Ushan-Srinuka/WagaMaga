"""Strict support inputs and bounded conversation projections."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, Field


def trimmed(value: str) -> str:
    value = value.strip()
    if not value or "\x00" in value:
        raise ValueError("Enter nonblank text without null characters")
    return value


State = Literal["open", "in_progress", "resolved"]
Category = Literal["account", "farm_records", "technical", "feedback"]
Subject = Annotated[str, AfterValidator(trimmed), Field(max_length=120)]
Body = Annotated[str, AfterValidator(trimmed), Field(max_length=4000)]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Create(Input):
    category: Category
    subject: Subject
    body: Body


class Reply(Input):
    expected_version: int = Field(ge=1)
    body: Body


class ChangeStatus(Input):
    expected_version: int = Field(ge=1)
    status: State


class Paging(BaseModel):
    model_config = ConfigDict(extra="forbid")
    page: int = Field(default=1, ge=1, le=10000)
    page_size: int = Field(default=20, ge=1, le=100)


class Query(Paging):
    status: Literal["open", "in_progress", "resolved", "all"] = "all"
    category: Category | None = None


class TicketOut(BaseModel):
    id: UUID
    farmer_id: UUID
    category: Category
    subject: str
    status: State
    version: int
    created_at: datetime
    updated_at: datetime
    requester_name: str
    requester_available: bool


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    author_role: Literal["farmer", "administrator"]
    body: str
    ticket_version: int
    created_at: datetime


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    page_size: int


class Contact(BaseModel):
    email: str | None

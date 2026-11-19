"""Explicit count-only reporting contracts."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class Accounts(BaseModel):
    total: int = Field(ge=0)
    enabled: int = Field(ge=0)
    disabled: int = Field(ge=0)
    farmers: int = Field(ge=0)
    advisors: int = Field(ge=0)
    administrators: int = Field(ge=0)
    new_farmers_30_days: int = Field(ge=0)
    removed: int = Field(ge=0)


class Records(BaseModel):
    total: int = Field(ge=0)
    active: int = Field(ge=0)
    archived: int = Field(ge=0)


class Support(BaseModel):
    total: int = Field(ge=0)
    open: int = Field(ge=0)
    in_progress: int = Field(ge=0)
    resolved: int = Field(ge=0)


class Overview(BaseModel):
    generated_at: datetime
    accounts: Accounts
    farms: Records
    cultivations: Records
    support: Support


class FarmerSummary(BaseModel):
    user_id: UUID
    generated_at: datetime
    farms: Records
    cultivations: Records

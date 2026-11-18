"""Explicit DTOs prevent role/status mass assignment and secret responses."""

from datetime import datetime
from typing import Literal
from unicodedata import category
from uuid import UUID

from email_validator import EmailNotValidError, validate_email
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

Role = Literal["farmer", "advisor", "administrator"]


def normalize_email(value: str) -> str:
    try:
        return validate_email(value.strip(), check_deliverability=False).normalized.casefold()
    except EmailNotValidError:
        raise ValueError("Enter a valid email address") from None


def normalize_name(value: str) -> str:
    value = value.strip()
    if len(value) < 2 or any(ord(char) < 32 for char in value):
        raise ValueError("Enter a display name of 2-80 characters")
    return value


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Login(Input):
    email: str = Field(max_length=254)
    password: SecretStr = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def email_value(cls, value: str) -> str:
        return normalize_email(value)


class Register(Login):
    display_name: str = Field(min_length=2, max_length=80)
    password: SecretStr = Field(
        min_length=8,
        max_length=128,
        description="8-128 characters with at least one letter, one number and one symbol.",
    )

    @field_validator("password")
    @classmethod
    def password_value(cls, value: SecretStr) -> SecretStr:
        return validate_new_password(value)

    @field_validator("display_name")
    @classmethod
    def name_value(cls, value: str) -> str:
        return normalize_name(value)


class Profile(Input):
    display_name: str = Field(min_length=2, max_length=80)
    expected_version: int = Field(ge=1)

    @field_validator("display_name")
    @classmethod
    def name_value(cls, value: str) -> str:
        return normalize_name(value)


class AdminChange(Input):
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=300)

    @field_validator("reason")
    @classmethod
    def reason_value(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("A reason is required")
        return value


class RoleChange(AdminChange):
    role: Role


class StatusChange(AdminChange):
    enabled: bool


def validate_new_password(value: SecretStr) -> SecretStr:
    password = value.get_secret_value()
    if not (
        any(char.isalpha() for char in password)
        and any(char.isdecimal() for char in password)
        and any(category(char)[0] in {"P", "S"} for char in password)
    ):
        raise ValueError("Use at least one letter, one number and one symbol")
    return value


class PasswordChange(Input):
    current_password: SecretStr = Field(min_length=1, max_length=128)
    new_password: SecretStr = Field(
        min_length=8,
        max_length=128,
        description="8-128 characters with at least one letter, one number and one symbol.",
    )

    @field_validator("new_password")
    @classmethod
    def new_password_value(cls, value: SecretStr) -> SecretStr:
        return validate_new_password(value)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    display_name: str
    role: Role
    disabled_at: datetime | None
    deleted_at: datetime | None
    version: int
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: UserOut


class UserPage(BaseModel):
    items: list[UserOut]
    total: int
    page: int
    page_size: int


AuditAction = Literal[
    "bootstrap",
    "role",
    "status",
    "account_deleted",
    "password_changed",
    "audit_viewed",
]


class AuditEventOut(BaseModel):
    id: UUID
    actor_id: UUID
    actor_name: str | None
    target_id: UUID
    target_name: str | None
    action: str
    previous_value: str | None
    new_value: str
    reason: str
    request_id: str
    created_at: datetime


class AuditPage(BaseModel):
    items: list[AuditEventOut]
    total: int
    page: int
    page_size: int


class Acknowledgement(BaseModel):
    message: str

"""Shared metadata for future domain models; no business tables in M0."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass

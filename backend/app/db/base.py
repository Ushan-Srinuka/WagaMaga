"""Shared declarative metadata; modules register only their implemented models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass

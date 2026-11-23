"""Latest successful forecast per farm."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FarmForecast(Base):
    __tablename__ = "farm_forecasts"
    __table_args__ = (
        CheckConstraint("latitude BETWEEN -90 AND 90", name="farm_forecasts_latitude"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="farm_forecasts_longitude"),
        CheckConstraint("provider = 'open-meteo'", name="farm_forecasts_provider"),
        CheckConstraint("isfinite(fetched_at)", name="farm_forecasts_fetched_at"),
        CheckConstraint(
            "CASE WHEN jsonb_typeof(days) = 'array' "
            "THEN jsonb_array_length(days) = 3 ELSE false END",
            name="farm_forecasts_days",
        ),
    )

    farm_id: Mapped[UUID] = mapped_column(
        ForeignKey("farms.id", ondelete="RESTRICT"), primary_key=True
    )
    latitude: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    longitude: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    timezone: Mapped[str] = mapped_column(String(100))
    provider: Mapped[str] = mapped_column(String(20))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    days: Mapped[list[dict]] = mapped_column(JSONB)


class WeatherAlertRule(Base):
    __tablename__ = "weather_alert_rules"
    __table_args__ = (
        CheckConstraint("threshold_mm BETWEEN 1 AND 1000", name="weather_alert_rules_threshold"),
        CheckConstraint("version > 0", name="weather_alert_rules_version"),
    )

    cultivation_id: Mapped[UUID] = mapped_column(
        ForeignKey("cultivations.id", ondelete="RESTRICT"), primary_key=True
    )
    threshold_mm: Mapped[int | None] = mapped_column(Integer)
    version: Mapped[int] = mapped_column(Integer)
    changed_by: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class WeatherTaskAlert(Base):
    __tablename__ = "weather_task_alerts"
    __table_args__ = (
        CheckConstraint("isfinite(due_date)", name="weather_task_alerts_due_date"),
        CheckConstraint("rule_version > 0", name="weather_task_alerts_rule_version"),
        CheckConstraint(
            "precipitation_mm BETWEEN 0 AND 3000", name="weather_task_alerts_precipitation"
        ),
    )

    task_id: Mapped[UUID] = mapped_column(
        ForeignKey("farm_tasks.id", ondelete="RESTRICT"), primary_key=True
    )
    due_date: Mapped[date] = mapped_column(Date, primary_key=True)
    rule_version: Mapped[int] = mapped_column(Integer)
    forecast_fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    precipitation_mm: Mapped[float] = mapped_column(Float)


class WeatherRefreshSchedule(Base):
    __tablename__ = "weather_refresh_schedules"
    __table_args__ = (
        CheckConstraint("version > 0", name="weather_refresh_schedules_version"),
        CheckConstraint(
            "(lease_token IS NULL) = (lease_until IS NULL)",
            name="weather_refresh_schedules_lease",
        ),
        Index(
            "ix_weather_refresh_schedules_due",
            "next_refresh_at",
            "farm_id",
            postgresql_where=text("enabled"),
        ),
    )

    farm_id: Mapped[UUID] = mapped_column(
        ForeignKey("farms.id", ondelete="RESTRICT"), primary_key=True
    )
    enabled: Mapped[bool]
    version: Mapped[int]
    next_refresh_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    lease_token: Mapped[UUID | None]
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WeatherReviewNotice(Base):
    __tablename__ = "weather_review_notices"

    cultivation_id: Mapped[UUID] = mapped_column(
        ForeignKey("cultivations.id", ondelete="RESTRICT"), primary_key=True
    )
    due_date: Mapped[date] = mapped_column(Date, primary_key=True)

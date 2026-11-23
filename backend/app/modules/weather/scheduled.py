"""Opt-in farm forecast jobs and durable recipient-only weather notices."""

from contextlib import suppress
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import Date, cast, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.integrations import open_meteo
from app.modules.farms import schemas
from app.modules.farms import service as farms
from app.modules.farms.models import Cultivation, Farm, FarmTask
from app.modules.identity.models import User
from app.modules.identity.security import IdentityError
from app.modules.notifications.service import create_notification
from app.modules.weather import alerts, live
from app.modules.weather.models import (
    WeatherAlertRule,
    WeatherRefreshSchedule,
    WeatherReviewNotice,
    WeatherTaskAlert,
)

INTERVAL = timedelta(minutes=90)
RETRY = timedelta(minutes=15)
LEASE = timedelta(minutes=2)


class ScheduleEdit(schemas.Input):
    enabled: bool
    expected_version: int = Field(ge=0)


class ScheduleOut(BaseModel):
    enabled: bool
    version: int
    can_enable: bool
    can_disable: bool


def view(schedule, farm, settings):
    enabled = schedule is not None and schedule.enabled
    return ScheduleOut(
        enabled=enabled,
        version=schedule.version if schedule else 0,
        can_enable=farm.archived_at is None
        and live.area_for(farm) is not None
        and live.provider_enabled(settings),
        can_disable=enabled,
    )


def get(db, ids, farm_id, settings):
    actor = farms.farmer(db, ids)
    farm = farms.farm_for(db, actor.id, farm_id)
    return view(db.get(WeatherRefreshSchedule, farm.id), farm, settings)


def save(db, ids, farm_id, settings, data):
    actor = farms.farmer(db, ids, write=True)
    farm = farms.farm_for(db, actor.id, farm_id, lock=True)
    schedule = db.get(WeatherRefreshSchedule, farm.id, with_for_update=True)
    current = view(schedule, farm, settings)
    if current.version != data.expected_version:
        raise IdentityError(
            409, "WEATHER_SCHEDULE_CONFLICT", "Automatic alerts changed. Reload them."
        )
    if data.enabled == current.enabled:
        return current
    if data.enabled and not current.can_enable:
        raise IdentityError(
            409, "WEATHER_SCHEDULE_UNAVAILABLE", "Automatic alerts are unavailable for this farm."
        )
    if schedule is None:
        schedule = WeatherRefreshSchedule(farm_id=farm.id, version=0)
        db.add(schedule)
    schedule.enabled = data.enabled
    schedule.version += 1
    schedule.next_refresh_at = live.now()
    schedule.lease_token = None
    schedule.lease_until = None
    db.flush()
    return view(schedule, farm, settings)


def has_pending_task(stamp):
    today = cast(func.timezone(Farm.timezone, stamp), Date)
    return (
        select(FarmTask.id)
        .join(Cultivation, Cultivation.id == FarmTask.cultivation_id)
        .join(WeatherAlertRule, WeatherAlertRule.cultivation_id == Cultivation.id)
        .where(
            Cultivation.farm_id == Farm.id,
            Cultivation.archived_at.is_(None),
            WeatherAlertRule.threshold_mm.is_not(None),
            FarmTask.status == "pending",
            FarmTask.due_date.between(today, today + (open_meteo.DAYS - 1)),
        )
        .exists()
    )


def active_user():
    return (User.role == "farmer", User.disabled_at.is_(None), User.deleted_at.is_(None))


@dataclass(frozen=True)
class Claim:
    farm_id: UUID
    owner_id: UUID
    token: UUID
    area: live.Area
    first_day: date
    started_at: datetime
    reuse_cache: bool


def claim_next(db, stamp):
    row = db.execute(
        select(WeatherRefreshSchedule, Farm)
        .join(Farm, Farm.id == WeatherRefreshSchedule.farm_id)
        .join(User, User.id == Farm.farmer_id)
        .where(
            WeatherRefreshSchedule.enabled,
            WeatherRefreshSchedule.next_refresh_at <= stamp,
            or_(
                WeatherRefreshSchedule.lease_until.is_(None),
                WeatherRefreshSchedule.lease_until <= stamp,
            ),
            Farm.archived_at.is_(None),
            Farm.latitude.is_not(None),
            farms.visible_farm(),
            *active_user(),
            has_pending_task(stamp),
        )
        .order_by(WeatherRefreshSchedule.next_refresh_at, Farm.id)
        .limit(1)
        .with_for_update(of=WeatherRefreshSchedule, skip_locked=True)
    ).first()
    if row is None:
        return None
    schedule, farm = row
    schedule.lease_token = token = uuid4()
    schedule.lease_until = stamp + LEASE
    forecast, fresh = live.examine(db, farm, stamp)
    return Claim(
        farm.id,
        farm.farmer_id,
        token,
        live.area_for(farm),
        farms.local_today(db, farm, at=stamp),
        stamp,
        fresh and stamp - forecast.fetched_at < live.REUSE_FOR,
    )


def notify(db, farm, forecast):
    qualifying = (
        select(Cultivation.id, FarmTask.due_date)
        .join(FarmTask, FarmTask.cultivation_id == Cultivation.id)
        .join(
            WeatherTaskAlert,
            (WeatherTaskAlert.task_id == FarmTask.id)
            & (WeatherTaskAlert.due_date == FarmTask.due_date),
        )
        .join(WeatherAlertRule, WeatherAlertRule.cultivation_id == Cultivation.id)
        .where(
            Cultivation.farm_id == farm.id,
            Cultivation.archived_at.is_(None),
            FarmTask.status == "pending",
            WeatherTaskAlert.forecast_fetched_at == forecast.fetched_at,
            WeatherTaskAlert.rule_version == WeatherAlertRule.version,
            WeatherAlertRule.threshold_mm <= WeatherTaskAlert.precipitation_mm,
        )
        .distinct()
    )
    candidates = insert(WeatherReviewNotice).from_select(["cultivation_id", "due_date"], qualifying)
    added = db.scalars(
        candidates.on_conflict_do_nothing().returning(WeatherReviewNotice.due_date)
    ).all()
    for due_date in added:
        create_notification(
            db,
            farm.farmer_id,
            "weather_review",
            "Rain forecast for a farm task",
            f"A forecast met your rainfall threshold for {due_date}. "
            "Open My Farms to review the task date.",
        )


def finish(db, job, days, stamp):
    owner = db.scalar(
        select(User.id).where(User.id == job.owner_id, *active_user()).with_for_update()
    )
    try:
        farm = farms.farm_for(db, owner, job.farm_id, lock=True) if owner else None
    except IdentityError as error:
        if error.status != 404:
            raise
        farm = None
    schedule = db.get(WeatherRefreshSchedule, job.farm_id, with_for_update=True)
    if (
        schedule is None
        or not schedule.enabled
        or schedule.lease_token != job.token
        or schedule.lease_until <= stamp
    ):
        return
    schedule.lease_token = None
    schedule.lease_until = None
    schedule.next_refresh_at = stamp + RETRY
    if (
        farm is None
        or farm.archived_at is not None
        or live.area_for(farm) != job.area
        or farms.local_today(db, farm, at=stamp) != job.first_day
        or not db.scalar(select(has_pending_task(stamp)).where(Farm.id == farm.id))
    ):
        return
    forecast, fresh = live.examine(db, farm, stamp)
    if days is not None and not (fresh and forecast.fetched_at >= job.started_at):
        live.store_forecast(db, farm, job.area, stamp, days)
        forecast, fresh = live.examine(db, farm, stamp)
    if not fresh or (days is None and not job.reuse_cache and forecast.fetched_at < job.started_at):
        return
    alerts.sync(db, farm)
    notify(db, farm, forecast)
    schedule.next_refresh_at = min(stamp + INTERVAL, forecast.fresh_until)


def process_one(engine, settings):
    if not live.provider_enabled(settings):
        return False
    with Session(engine) as db, db.begin():
        job = claim_next(db, live.now())
    if job is None:
        return False
    days = None
    if not job.reuse_cache:
        with suppress(open_meteo.Unavailable):
            days = open_meteo.forecast(
                settings,
                job.area.latitude,
                job.area.longitude,
                job.area.timezone,
                job.first_day,
            )
    with Session(engine) as db, db.begin():
        finish(db, job, days, live.now())
    return True

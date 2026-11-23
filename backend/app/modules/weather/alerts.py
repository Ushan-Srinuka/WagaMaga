"""Owner-configured precipitation review alerts derived from a fresh forecast."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, and_, literal, or_, select
from sqlalchemy.dialects.postgresql import insert

from app.modules.farms import schemas as dto
from app.modules.farms import service as farms
from app.modules.farms.models import Cultivation, FarmTask
from app.modules.identity.security import IdentityError
from app.modules.weather import live
from app.modules.weather.models import WeatherAlertRule, WeatherTaskAlert


class RuleEdit(dto.Input):
    threshold_mm: int | None = Field(ge=1, le=1000)
    expected_version: int = Field(ge=0)


class RuleOut(BaseModel):
    threshold_mm: int | None
    version: int


class AlertOut(BaseModel):
    task_id: UUID
    title: str
    due_date: date
    task_version: int
    rule_version: int
    threshold_mm: int
    precipitation_mm: float
    forecast_fetched_at: datetime


class AlertPage(dto.Page[AlertOut]):
    rule: RuleOut
    can_edit: bool
    forecast_fresh: bool


def rule_view(rule):
    return (
        RuleOut(threshold_mm=rule.threshold_mm, version=rule.version)
        if rule
        else RuleOut(threshold_mm=None, version=0)
    )


def sync(db, farm, *, cultivation_id=None, task_id=None):
    if farm.archived_at is not None:
        return
    if cultivation_id is not None:
        rule = db.get(WeatherAlertRule, cultivation_id)
        if rule is None or rule.threshold_mm is None:
            return
    forecast, fresh = live.examine(db, farm, live.now())
    if not fresh:
        return
    for day in forecast.days:
        pending = (
            select(
                FarmTask.id,
                FarmTask.due_date,
                WeatherAlertRule.version,
                literal(forecast.fetched_at, type_=DateTime(timezone=True)),
                literal(day.precipitation_mm),
            )
            .join(Cultivation, Cultivation.id == FarmTask.cultivation_id)
            .join(WeatherAlertRule, WeatherAlertRule.cultivation_id == Cultivation.id)
            .where(
                Cultivation.farm_id == farm.id,
                Cultivation.archived_at.is_(None),
                WeatherAlertRule.threshold_mm <= day.precipitation_mm,
                FarmTask.status == "pending",
                FarmTask.due_date == day.date,
            )
        )
        if cultivation_id is not None:
            pending = pending.where(Cultivation.id == cultivation_id)
        if task_id is not None:
            pending = pending.where(FarmTask.id == task_id)
        claim = insert(WeatherTaskAlert).from_select(
            ["task_id", "due_date", "rule_version", "forecast_fetched_at", "precipitation_mm"],
            pending,
        )
        db.execute(
            claim.on_conflict_do_update(
                index_elements=[WeatherTaskAlert.task_id, WeatherTaskAlert.due_date],
                set_={
                    "rule_version": claim.excluded.rule_version,
                    "forecast_fetched_at": claim.excluded.forecast_fetched_at,
                    "precipitation_mm": claim.excluded.precipitation_mm,
                },
                where=or_(
                    WeatherTaskAlert.rule_version != claim.excluded.rule_version,
                    WeatherTaskAlert.forecast_fetched_at != claim.excluded.forecast_fetched_at,
                ),
            )
        )


def refresh_forecast(db, ids, farm_id, cultivation_id, settings, on_provider_call):
    live.refresh(db, ids, farm_id, cultivation_id, settings, on_provider_call)
    actor = farms.farmer(db, ids, write=True)
    farm, cultivation = farms.cultivation_for(
        db, actor.id, cultivation_id, farm_id=farm_id, lock=True
    )
    farms.active(farm, cultivation)
    sync(db, farm)
    return live.present(db, settings, farm, cultivation, live.now())


def save_rule(db, ids, farm_id, cultivation_id, data):
    actor = farms.farmer(db, ids, write=True)
    farm, cultivation = farms.cultivation_for(
        db, actor.id, cultivation_id, farm_id=farm_id, lock=True
    )
    farms.active(farm, cultivation)
    rule = db.get(WeatherAlertRule, cultivation.id, populate_existing=True)
    if rule_view(rule).version != data.expected_version:
        raise IdentityError(
            409, "WEATHER_RULE_CONFLICT", "The weather alert setting changed. Reload it."
        )
    if rule is None:
        rule = WeatherAlertRule(
            cultivation_id=cultivation.id,
            threshold_mm=data.threshold_mm,
            version=1,
            changed_by=actor.id,
            changed_at=live.now(),
        )
        db.add(rule)
    elif rule.threshold_mm != data.threshold_mm:
        rule.threshold_mm = data.threshold_mm
        rule.version += 1
        rule.changed_by = actor.id
        rule.changed_at = live.now()
    db.flush()
    sync(db, farm, cultivation_id=cultivation.id)
    return rule_view(rule)


def qualifying_days(rule, forecast):
    if rule is None or rule.threshold_mm is None or forecast is None:
        return {}
    return {
        day.date: day.precipitation_mm
        for day in forecast.days
        if day.precipitation_mm >= rule.threshold_mm
    }


def list_alerts(db, ids, farm_id, cultivation_id, query):
    actor = farms.farmer(db, ids)
    farm, cultivation = farms.cultivation_for(db, actor.id, cultivation_id, farm_id=farm_id)
    rule = db.get(WeatherAlertRule, cultivation.id)
    can_edit = farm.archived_at is None and cultivation.archived_at is None
    forecast, fresh = live.examine(db, farm, live.now())
    shared = {"rule": rule_view(rule), "can_edit": can_edit, "forecast_fresh": fresh}
    days = qualifying_days(rule, forecast) if can_edit and fresh else {}
    if not days:
        return AlertPage(items=[], total=0, page=query.page, page_size=query.page_size, **shared)
    statement = (
        select(FarmTask)
        .join(
            WeatherTaskAlert,
            and_(
                WeatherTaskAlert.task_id == FarmTask.id,
                WeatherTaskAlert.due_date == FarmTask.due_date,
            ),
        )
        .where(
            FarmTask.cultivation_id == cultivation.id,
            FarmTask.status == "pending",
            FarmTask.due_date.in_(list(days)),
            WeatherTaskAlert.rule_version == rule.version,
            WeatherTaskAlert.forecast_fetched_at == forecast.fetched_at,
        )
        .order_by(FarmTask.due_date, FarmTask.id)
    )

    def project(task):
        return AlertOut(
            task_id=task.id,
            title=task.title,
            due_date=task.due_date,
            task_version=task.version,
            rule_version=rule.version,
            threshold_mm=rule.threshold_mm,
            precipitation_mm=days[task.due_date],
            forecast_fetched_at=forecast.fetched_at,
        )

    return AlertPage(**farms.paged(db, statement, query, project), **shared)

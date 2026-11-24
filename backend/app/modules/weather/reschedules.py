"""Review and execute one immutable task date change against fresh weather evidence."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.modules.farms import date_reviews, plans, service, tasks
from app.modules.farms import schemas as dto
from app.modules.farms.models import TaskPlan, TaskPlanDecision
from app.modules.weather import alerts, live
from app.modules.weather.models import WeatherAlertRule, WeatherTaskAlert

ACTION = date_reviews.ACTION
EVIDENCE_CODE = "manual_weather_threshold_v1"


class RescheduleInput(dto.VersionCommand):
    proposed_due_date: dto.LocalDate
    expected_rule_version: int = Field(ge=1)
    expected_forecast_fetched_at: dto.ObservedAt


class Evidence(BaseModel):
    provider: Literal["open-meteo"]
    forecast_date: date
    fetched_at: datetime
    fresh_until: datetime
    precipitation_mm: float
    threshold_mm: int
    rule_version: int
    latitude: Decimal
    longitude: Decimal
    timezone: str


class RescheduleOut(dto.DateReviewOut):
    forecast_fetched_at: datetime


def current_evidence(db, farm, task, stamp):
    rule = db.get(WeatherAlertRule, task.cultivation_id, populate_existing=True)
    forecast, fresh = live.examine(db, farm, stamp)
    days = alerts.qualifying_days(rule, forecast) if fresh else {}
    if task.status != "pending" or task.due_date not in days:
        raise plans.conflict("This task no longer has a current weather alert. Reload the alerts.")
    alert = db.get(WeatherTaskAlert, (task.id, task.due_date), populate_existing=True)
    if (
        alert is None
        or alert.rule_version != rule.version
        or alert.forecast_fetched_at != forecast.fetched_at
        or alert.precipitation_mm != days[task.due_date]
    ):
        raise plans.conflict("The weather alert changed. Reload it before reviewing a date.")
    area = live.area_for(farm)
    return Evidence(
        provider=forecast.provider,
        forecast_date=task.due_date,
        fetched_at=forecast.fetched_at,
        fresh_until=forecast.fresh_until,
        precipitation_mm=days[task.due_date],
        threshold_mm=rule.threshold_mm,
        rule_version=rule.version,
        latitude=area.latitude,
        longitude=area.longitude,
        timezone=area.timezone,
    )


def hash_action(farm, cultivation, task, proposed_date, evidence):
    return plans.fingerprint(
        {
            "type": ACTION,
            "policy": EVIDENCE_CODE,
            "task_id": str(task.id),
            "task_version": task.version,
            "title": task.title,
            "current_due_date": str(task.due_date),
            "proposed_due_date": str(proposed_date),
            "farm_version": farm.version,
            "cultivation_version": cultivation.version,
            "weather": evidence.model_dump(mode="json"),
        }
    )


def view(plan, evidence):
    return RescheduleOut(
        id=plan.id,
        version=plan.version,
        action_hash=plan.action_hash,
        task_id=plan.target_task_id,
        title=plan.title,
        current_due_date=plan.previous_due_date,
        proposed_due_date=plan.due_date,
        evidence_text=plan.evidence_text,
        forecast_fetched_at=evidence.fetched_at,
        expires_at=plan.expires_at,
    )


def prepare(db, ids, farm_id, cultivation_id, task_id, data, request_id):
    actor, farm, cultivation = tasks.writable_context(db, ids, farm_id, cultivation_id)
    service.active(farm, cultivation)
    task = tasks.task_for_update(db, cultivation.id, task_id)
    service.check_version(task, data.expected_version)
    stamp = live.now()
    evidence = current_evidence(db, farm, task, stamp)
    if (
        evidence.rule_version != data.expected_rule_version
        or evidence.fetched_at != data.expected_forecast_fetched_at
    ):
        raise plans.conflict("The weather alert changed. Reload it before reviewing a date.")
    date_reviews.valid_date(db, farm, task.due_date, data.proposed_due_date, stamp)
    digest = hash_action(farm, cultivation, task, data.proposed_due_date, evidence)
    latest = date_reviews.latest_for_task(db, cultivation.id, task.id)
    if latest is not None:
        if latest.action_hash == digest and db.get(TaskPlanDecision, latest.id) is None:
            return view(latest, evidence)
        stamp = max(stamp, latest.created_at + timedelta(microseconds=1))
        if stamp >= evidence.fresh_until:
            raise plans.conflict("The weather forecast expired. Refresh before starting a review.")
    plan = TaskPlan(
        cultivation_id=cultivation.id,
        action_type=ACTION,
        action_hash=digest,
        title=task.title,
        due_date=data.proposed_due_date,
        previous_due_date=task.due_date,
        target_task_id=task.id,
        target_task_version=task.version,
        evidence_code=EVIDENCE_CODE,
        evidence_text=(
            f"Open-Meteo forecast {evidence.precipitation_mm:g} mm on {task.due_date}. "
            f"Your alert threshold was {evidence.threshold_mm} mm."
        ),
        weather_evidence=evidence.model_dump(mode="json"),
        farm_version=farm.version,
        cultivation_version=cultivation.version,
        created_by=actor.id,
        request_id=request_id,
        created_at=stamp,
        expires_at=evidence.fresh_until,
    )
    db.add(plan)
    db.flush()
    return view(plan, evidence)


def decide(db, ids, farm_id, cultivation_id, plan_id, key, data, request_id):
    actor, farm, cultivation = tasks.writable_context(db, ids, farm_id, cultivation_id)
    plan = date_reviews.plan_for_decision(db, cultivation.id, plan_id, EVIDENCE_CODE)
    saved = plans.replay_decision(db, plan, key, data)
    if saved is not None:
        return saved
    stamp = live.now()
    task = date_reviews.current_task(db, farm, cultivation, plan, stamp)
    evidence = current_evidence(db, farm, task, stamp)
    if (
        evidence.model_dump(mode="json") != plan.weather_evidence
        or hash_action(farm, cultivation, task, plan.due_date, evidence) != plan.action_hash
    ):
        raise plans.conflict("The weather or alert setting changed. Start a new review.")
    return date_reviews.finish(db, actor.id, farm, plan, task, data.outcome, stamp, request_id)

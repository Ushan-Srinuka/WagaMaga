"""Review and execute one immutable task date change against fresh weather evidence."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import select

from app.modules.farms import plans, service, tasks
from app.modules.farms import schemas as dto
from app.modules.farms.models import TaskPlan, TaskPlanDecision
from app.modules.weather import alerts, live
from app.modules.weather.models import WeatherAlertRule, WeatherTaskAlert

ACTION = "reschedule_task"
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


class RescheduleOut(BaseModel):
    id: UUID
    version: int
    action_hash: str
    task_id: UUID
    title: str
    current_due_date: date
    proposed_due_date: date
    evidence_text: str
    forecast_fetched_at: datetime
    expires_at: datetime


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


def valid_date(db, farm, current_date, proposed_date, stamp):
    today = service.local_today(db, farm, at=stamp)
    if current_date == proposed_date or not today <= proposed_date <= today + timedelta(days=7):
        raise plans.conflict("Choose a different date within the next seven days.")


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


def latest_for_task(db, cultivation_id, task_id):
    return db.scalar(
        select(TaskPlan)
        .where(
            TaskPlan.cultivation_id == cultivation_id,
            TaskPlan.target_task_id == task_id,
            TaskPlan.action_type == ACTION,
        )
        .order_by(TaskPlan.created_at.desc(), TaskPlan.id.desc())
        .limit(1)
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
    valid_date(db, farm, task.due_date, data.proposed_due_date, stamp)
    digest = hash_action(farm, cultivation, task, data.proposed_due_date, evidence)
    latest = latest_for_task(db, cultivation.id, task.id)
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
    plan = db.scalar(
        select(TaskPlan).where(
            TaskPlan.id == plan_id,
            TaskPlan.cultivation_id == cultivation.id,
            TaskPlan.action_type == ACTION,
        )
    )
    if plan is None:
        raise service.missing()
    saved = plans.replay_decision(db, plan, key, data)
    if saved is not None:
        return saved
    service.active(farm, cultivation)
    stamp = live.now()
    if (
        stamp >= plan.expires_at
        or plan.farm_version != farm.version
        or plan.cultivation_version != cultivation.version
        or plan.evidence_code != EVIDENCE_CODE
    ):
        raise plans.conflict("This review expired or the farm changed. Start a new review.")
    if latest_for_task(db, cultivation.id, plan.target_task_id).id != plan.id:
        raise plans.conflict("A newer date was reviewed for this task. Use the latest review.")
    task = tasks.task_for_update(db, cultivation.id, plan.target_task_id)
    if task.version != plan.target_task_version or task.due_date != plan.previous_due_date:
        raise plans.conflict("This task changed. Start a new review.")
    evidence = current_evidence(db, farm, task, stamp)
    if (
        evidence.model_dump(mode="json") != plan.weather_evidence
        or hash_action(farm, cultivation, task, plan.due_date, evidence) != plan.action_hash
    ):
        raise plans.conflict("The weather or alert setting changed. Start a new review.")
    valid_date(db, farm, task.due_date, plan.due_date, stamp)
    effect = None
    if data.outcome == "accepted":
        service.assign(task, {"due_date": plan.due_date})
        tasks.record_event(db, task, actor.id, "edited", request_id)
        alerts.sync(db, farm, cultivation_id=cultivation.id, task_id=task.id)
        effect = task
    return plans.record_decision(db, plan, actor.id, data.outcome, effect, stamp, request_id)

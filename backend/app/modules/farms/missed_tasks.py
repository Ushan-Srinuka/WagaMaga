"""Prepare a farmer-selected date for an overdue task, with optional forecast context."""

from datetime import date, datetime, timedelta
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, Field

from app.modules.farms import date_reviews, plans, service, tasks
from app.modules.farms import schemas as dto
from app.modules.farms.models import TaskPlan, TaskPlanDecision
from app.modules.weather import live

POLICY = "owner_missed_task_v1"
REVIEW_FOR = timedelta(minutes=30)


class MissedTaskInput(dto.VersionCommand):
    proposed_due_date: dto.LocalDate
    reason: Annotated[str, AfterValidator(dto.trimmed), Field(max_length=240)] | None = None


class ForecastEvidence(BaseModel):
    provider: Literal["open-meteo"]
    due_date: date
    precipitation_mm: float
    fetched_at: datetime
    fresh_until: datetime
    timezone: str


def ensure_overdue(db, farm, task, stamp):
    today = service.local_today(db, farm, at=stamp)
    if task.status != "pending" or task.due_date >= today:
        raise plans.conflict("Only overdue pending tasks can start a missed-task review.")


def forecast_evidence(db, farm, due_date, stamp):
    forecast, fresh = live.examine(db, farm, stamp)
    if fresh:
        for day in forecast.days:
            if day.date == due_date:
                return ForecastEvidence(
                    provider=forecast.provider,
                    due_date=due_date,
                    precipitation_mm=day.precipitation_mm,
                    fetched_at=forecast.fetched_at,
                    fresh_until=forecast.fresh_until,
                    timezone=farm.timezone,
                )
    return None


def snapshot(forecast):
    return {"forecast": forecast.model_dump(mode="json") if forecast else None}


def fingerprint(farm, cultivation, task, proposed_date, evidence, text):
    return plans.fingerprint(
        {
            "type": date_reviews.ACTION,
            "policy": POLICY,
            "task_id": str(task.id),
            "task_version": task.version,
            "title": task.title,
            "previous_due_date": str(task.due_date),
            "proposed_due_date": str(proposed_date),
            "farm_version": farm.version,
            "cultivation_version": cultivation.version,
            "weather": evidence,
            "evidence_text": text,
        }
    )


def description(forecast, reason):
    parts = ["Missed-task review."]
    if reason:
        parts.append(f"Reason recorded by you: {reason}")
    parts.append(
        f"Open-Meteo forecasts {forecast.precipitation_mm:g} mm of rain on {forecast.due_date}."
        if forecast
        else "No current forecast is available for the proposed date."
    )
    return " ".join(parts)


def view(plan, forecast):
    return dto.DateReviewOut(
        id=plan.id,
        version=plan.version,
        action_hash=plan.action_hash,
        task_id=plan.target_task_id,
        title=plan.title,
        current_due_date=plan.previous_due_date,
        proposed_due_date=plan.due_date,
        evidence_text=plan.evidence_text,
        forecast_fetched_at=forecast.fetched_at if forecast else None,
        expires_at=plan.expires_at,
    )


def prepare(db, ids, farm_id, cultivation_id, task_id, data, request_id):
    actor, farm, cultivation = tasks.writable_context(db, ids, farm_id, cultivation_id)
    service.active(farm, cultivation)
    task = tasks.task_for_update(db, cultivation.id, task_id)
    service.check_version(task, data.expected_version)
    stamp = live.now()
    ensure_overdue(db, farm, task, stamp)
    date_reviews.valid_date(db, farm, task.due_date, data.proposed_due_date, stamp)
    forecast = forecast_evidence(db, farm, data.proposed_due_date, stamp)
    evidence = snapshot(forecast)
    text = description(forecast, data.reason)
    digest = fingerprint(farm, cultivation, task, data.proposed_due_date, evidence, text)
    latest = date_reviews.latest_for_task(db, cultivation.id, task.id)
    if latest is not None:
        if (
            latest.action_hash == digest
            and stamp < latest.expires_at
            and db.get(TaskPlanDecision, latest.id) is None
        ):
            return view(latest, forecast)
        stamp = max(stamp, latest.created_at + timedelta(microseconds=1))
    expiry = stamp + REVIEW_FOR
    if forecast:
        expiry = min(expiry, forecast.fresh_until)
        if expiry <= stamp:
            raise plans.conflict("The forecast expired. Start a new review.")
    plan = TaskPlan(
        cultivation_id=cultivation.id,
        action_type=date_reviews.ACTION,
        action_hash=digest,
        title=task.title,
        due_date=data.proposed_due_date,
        previous_due_date=task.due_date,
        target_task_id=task.id,
        target_task_version=task.version,
        evidence_code=POLICY,
        evidence_text=text,
        weather_evidence=evidence,
        farm_version=farm.version,
        cultivation_version=cultivation.version,
        created_by=actor.id,
        request_id=request_id,
        created_at=stamp,
        expires_at=expiry,
    )
    db.add(plan)
    db.flush()
    return view(plan, forecast)


def decide(db, ids, farm_id, cultivation_id, plan_id, key, data, request_id):
    actor, farm, cultivation = tasks.writable_context(db, ids, farm_id, cultivation_id)
    plan = date_reviews.plan_for_decision(db, cultivation.id, plan_id, POLICY)
    saved = plans.replay_decision(db, plan, key, data)
    if saved is not None:
        return saved
    stamp = live.now()
    task = date_reviews.current_task(db, farm, cultivation, plan, stamp)
    ensure_overdue(db, farm, task, stamp)
    evidence = snapshot(forecast_evidence(db, farm, plan.due_date, stamp))
    if (
        evidence != plan.weather_evidence
        or fingerprint(farm, cultivation, task, plan.due_date, evidence, plan.evidence_text)
        != plan.action_hash
    ):
        raise plans.conflict("The forecast or review changed. Compare the dates again.")
    return date_reviews.finish(db, actor.id, farm, plan, task, data.outcome, stamp, request_id)

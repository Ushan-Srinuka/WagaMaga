"""Farm-local weekly tasks and evidence-bound date suggestions."""

from datetime import date, datetime, timedelta
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import and_, or_, select

from app.modules.advisory.models import AdvisorCase, AdvisorDecision
from app.modules.farms import date_reviews, plans, service, tasks
from app.modules.farms import schemas as dto
from app.modules.farms.models import FarmTask, TaskPlan, TaskPlanDecision
from app.modules.identity.models import User
from app.modules.identity.security import IdentityError
from app.modules.weather import alerts, live
from app.modules.weather.models import WeatherAlertRule

POLICY = "weekly_forecast_date_v1"
WEEK = timedelta(days=6)
BATCH_SIZE = 20


class WeekTask(dto.TaskOut):
    precipitation_mm: float | None = None
    rain_alert: bool = False


class Week(dto.Page[WeekTask]):
    starts_on: date
    ends_on: date


class Evidence(BaseModel):
    provider: Literal["open-meteo"]
    fetched_at: datetime
    fresh_until: datetime
    due_rain_mm: float
    proposed_rain_mm: float
    threshold_mm: int
    rule_version: int
    confirmed_stage: str | None


class WeeklyPlan(dto.DateReviewOut):
    evidence: Evidence
    requires_advisor: bool
    advisor_assigned: bool
    revises_plan_id: UUID | None
    prior_proposed_date: date | None
    can_revise: bool
    state: Literal[
        "ready",
        "advisor_required",
        "awaiting_advisor",
        "cleared",
        "declined",
        "changes_requested",
        "revoked",
        "stale",
        "accepted",
        "rejected",
    ]
    advisor_reason: str | None = None


class LatestWeeklyPlan(BaseModel):
    plan: WeeklyPlan | None = None


class WeeklySelection(dto.VersionCommand):
    plan_id: UUID = Field(strict=False)
    action_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


class WeeklyBatch(dto.Input):
    changes: list[WeeklySelection] = Field(min_length=1, max_length=BATCH_SIZE)


class WeeklyBatchReceipt(BaseModel):
    decisions: list[dto.PlanDecisionOut]


def week(db, ids, farm_id, cultivation_id, query):
    actor = service.farmer(db, ids)
    farm, cultivation = service.cultivation_for(db, actor.id, cultivation_id, farm_id=farm_id)
    return week_for(db, farm, cultivation, query)


def week_for(db, farm, cultivation, query, *, scope="all"):
    stamp = live.now()
    start = service.local_today(db, farm, at=stamp)
    end = start + WEEK
    forecast, fresh = live.examine(db, farm, stamp)
    days = {day.date: day.precipitation_mm for day in forecast.days} if fresh else {}
    rule = db.get(WeatherAlertRule, cultivation.id)
    qualifying = alerts.qualifying_days(rule, forecast) if fresh else {}
    editable = farm.archived_at is None and cultivation.archived_at is None
    in_week = FarmTask.due_date.between(start, end)
    overdue = and_(FarmTask.due_date < start, FarmTask.status == "pending")
    upcoming = and_(in_week, FarmTask.status == "pending")
    window = {"all": or_(in_week, overdue), "upcoming": upcoming, "overdue": overdue}[scope]
    statement = (
        select(FarmTask)
        .where(FarmTask.cultivation_id == cultivation.id, window)
        .order_by(FarmTask.due_date, FarmTask.id)
    )

    def project(task):
        return WeekTask(
            **dto.TaskOut.model_validate(task).model_dump(),
            precipitation_mm=days.get(task.due_date),
            rain_alert=editable and task.status == "pending" and task.due_date in qualifying,
        )

    return Week(**service.paged(db, statement, query, project), starts_on=start, ends_on=end)


def candidate(db, farm, cultivation, task, stamp, *, proposed_date=None):
    today = service.local_today(db, farm, at=stamp)
    rule = db.get(WeatherAlertRule, cultivation.id, populate_existing=True)
    forecast, fresh = live.examine(db, farm, stamp)
    qualifying = alerts.qualifying_days(rule, forecast) if fresh else {}
    if task.status != "pending" or task.due_date < today or task.due_date not in qualifying:
        raise plans.conflict(
            "This task needs a current rainfall alert before a date can be suggested."
        )
    later = next(
        (
            day
            for day in forecast.days
            if task.due_date < day.date <= today + WEEK
            and day.precipitation_mm < rule.threshold_mm
            and (proposed_date is None or day.date == proposed_date)
        ),
        None,
    )
    if later is None:
        if proposed_date is not None:
            raise plans.conflict(
                "Choose a later date this week with a forecast below your rainfall threshold."
            )
        raise plans.conflict(
            "The current forecast has no later day below your threshold this week."
        )
    return later.date, Evidence(
        provider=forecast.provider,
        fetched_at=forecast.fetched_at,
        fresh_until=forecast.fresh_until,
        due_rain_mm=qualifying[task.due_date],
        proposed_rain_mm=later.precipitation_mm,
        threshold_mm=rule.threshold_mm,
        rule_version=rule.version,
        confirmed_stage=cultivation.confirmed_stage,
    )


def digest(farm, cultivation, task, proposed, evidence, *, parent=None):
    action = {
        "policy": POLICY,
        "type": date_reviews.ACTION,
        "task_id": str(task.id),
        "version": task.version,
        "title": task.title,
        "current_due_date": str(task.due_date),
        "proposed_due_date": str(proposed),
        "farm_version": farm.version,
        "cultivation_version": cultivation.version,
        "evidence": evidence.model_dump(mode="json"),
    }
    if parent is not None:
        action["revises_plan_id"] = str(parent)
    return plans.fingerprint(action)


def verify_evidence(db, farm, cultivation, task, plan, stamp):
    proposed, evidence = candidate(
        db,
        farm,
        cultivation,
        task,
        stamp,
        proposed_date=plan.due_date if plan.revises_plan_id else None,
    )
    if (
        proposed != plan.due_date
        or evidence.model_dump(mode="json") != plan.weather_evidence
        or digest(farm, cultivation, task, proposed, evidence, parent=plan.revises_plan_id)
        != plan.action_hash
    ):
        raise plans.conflict("The forecast, crop stage or task changed. Request a new suggestion.")


def evidence_current(db, farm, cultivation, task, plan, stamp):
    try:
        verify_evidence(db, farm, cultivation, task, plan, stamp)
    except IdentityError as error:
        if error.status == 409:
            return False
        raise
    return True


def latest_plan(db, cultivation_id, task_id):
    return db.scalar(
        select(TaskPlan)
        .where(
            TaskPlan.cultivation_id == cultivation_id,
            TaskPlan.target_task_id == task_id,
            TaskPlan.evidence_code == POLICY,
        )
        .order_by(TaskPlan.created_at.desc(), TaskPlan.id.desc())
        .limit(1)
    )


def needs_advisor(db, plan, evidence):
    # A fresh plan for the same task revision cannot discard an existing referral requirement.
    return evidence.confirmed_stage is None or db.scalar(
        select(
            select(AdvisorCase.plan_id)
            .join(TaskPlan, TaskPlan.id == AdvisorCase.plan_id)
            .where(
                TaskPlan.target_task_id == plan.target_task_id,
                TaskPlan.target_task_version == plan.target_task_version,
                TaskPlan.evidence_code == POLICY,
            )
            .exists()
        )
    )


def view(db, farm, cultivation, task, plan, stamp):
    evidence = Evidence.model_validate(plan.weather_evidence)
    decision = db.get(TaskPlanDecision, plan.id)
    case = db.get(AdvisorCase, plan.id)
    review = db.get(AdvisorDecision, plan.id) if case else None
    parent = db.get(TaskPlan, plan.revises_plan_id) if plan.revises_plan_id else None
    required = needs_advisor(db, plan, evidence)
    current = date_reviews.latest_for_task(db, cultivation.id, task.id).id == plan.id
    can_revise = bool(
        current
        and not decision
        and case
        and not case.revoked_at
        and review
        and review.outcome == "changes_requested"
        and task.status == "pending"
        and task.version == plan.target_task_version
        and not farm.archived_at
        and not cultivation.archived_at
    )
    if decision:
        state = decision.outcome
    elif (
        farm.archived_at
        or cultivation.archived_at
        or stamp >= plan.expires_at
        or farm.version != plan.farm_version
        or cultivation.version != plan.cultivation_version
        or task.version != plan.target_task_version
        or task.status != "pending"
        or not current
        or not evidence_current(db, farm, cultivation, task, plan, stamp)
    ):
        state = "stale"
    elif case:
        state = "revoked" if case.revoked_at else review.outcome if review else "awaiting_advisor"
    else:
        state = "advisor_required" if required else "ready"
    return WeeklyPlan(
        id=plan.id,
        version=plan.version,
        action_hash=plan.action_hash,
        task_id=task.id,
        title=plan.title,
        current_due_date=plan.previous_due_date,
        proposed_due_date=plan.due_date,
        evidence_text=plan.evidence_text,
        forecast_fetched_at=evidence.fetched_at,
        expires_at=plan.expires_at,
        evidence=evidence,
        requires_advisor=required,
        advisor_assigned=case is not None and case.revoked_at is None,
        revises_plan_id=plan.revises_plan_id,
        prior_proposed_date=parent.due_date if parent else None,
        can_revise=can_revise,
        state=state,
        advisor_reason=review.reason if review else None,
    )


def read_task(db, cultivation_id, task_id):
    task = db.scalar(
        select(FarmTask).where(FarmTask.id == task_id, FarmTask.cultivation_id == cultivation_id)
    )
    if task is None:
        raise service.missing()
    return task


def latest(db, ids, farm_id, cultivation_id, task_id):
    actor = service.farmer(db, ids)
    farm, cultivation = service.cultivation_for(db, actor.id, cultivation_id, farm_id=farm_id)
    task = read_task(db, cultivation.id, task_id)
    plan = latest_plan(db, cultivation.id, task.id)
    return LatestWeeklyPlan(
        plan=view(db, farm, cultivation, task, plan, live.now()) if plan else None
    )


def prepare(db, ids, farm_id, cultivation_id, task_id, data, request_id):
    actor, farm, cultivation = tasks.writable_context(db, ids, farm_id, cultivation_id)
    service.active(farm, cultivation)
    task = tasks.task_for_update(db, cultivation.id, task_id)
    service.check_version(task, data.expected_version)
    return prepare_task(db, actor, farm, cultivation, task, live.now(), request_id)


def prepare_task(db, actor, farm, cultivation, task, stamp, request_id):
    proposed, evidence = candidate(db, farm, cultivation, task, stamp)
    action_hash = digest(farm, cultivation, task, proposed, evidence)
    latest = date_reviews.latest_for_task(db, cultivation.id, task.id)
    if latest is not None:
        if latest.action_hash == action_hash:
            existing = view(db, farm, cultivation, task, latest, stamp)
            if (
                existing.state in {"ready", "advisor_required", "awaiting_advisor", "cleared"}
                or existing.can_revise
            ):
                return existing
        if latest.evidence_code == POLICY:
            existing = view(db, farm, cultivation, task, latest, stamp)
            if existing.can_revise or existing.state in {"awaiting_advisor", "cleared"}:
                return existing
        stamp = max(stamp, latest.created_at + timedelta(microseconds=1))
    plan = persist(db, actor.id, farm, cultivation, task, proposed, evidence, stamp, request_id)
    return view(db, farm, cultivation, task, plan, stamp)


def persist(
    db, actor_id, farm, cultivation, task, proposed, evidence, stamp, request_id, *, parent=None
):
    if stamp >= evidence.fresh_until:
        raise plans.conflict("The forecast expired. Request a new suggestion after refreshing it.")
    plan = TaskPlan(
        cultivation_id=cultivation.id,
        action_type=date_reviews.ACTION,
        action_hash=digest(farm, cultivation, task, proposed, evidence, parent=parent),
        title=task.title,
        due_date=proposed,
        previous_due_date=task.due_date,
        target_task_id=task.id,
        target_task_version=task.version,
        evidence_code=POLICY,
        evidence_text=(
            f"Weekly forecast suggests reviewing the date. Open-Meteo predicts "
            f"{evidence.due_rain_mm:g} mm on {task.due_date} and "
            f"{evidence.proposed_rain_mm:g} mm on {proposed}. "
            f"Your threshold is {evidence.threshold_mm} mm."
        ),
        weather_evidence=evidence.model_dump(mode="json"),
        farm_version=farm.version,
        cultivation_version=cultivation.version,
        created_by=actor_id,
        request_id=request_id,
        created_at=stamp,
        expires_at=evidence.fresh_until,
        revises_plan_id=parent,
    )
    db.add(plan)
    db.flush()
    return plan


def active_advisors():
    return (User.role == "advisor", User.disabled_at.is_(None), User.deleted_at.is_(None))


def decide(db, ids, farm_id, cultivation_id, plan_id, key, data, request_id):
    actor, farm, cultivation = tasks.writable_context(db, ids, farm_id, cultivation_id)
    plan = date_reviews.plan_for_decision(db, cultivation.id, plan_id, POLICY)
    saved = plans.replay_decision(db, plan, key, data)
    if saved is not None:
        return saved
    stamp = live.now()
    task = date_reviews.current_task(db, farm, cultivation, plan, stamp)
    verify_evidence(db, farm, cultivation, task, plan, stamp)
    case = db.get(AdvisorCase, plan.id, with_for_update=True)
    if data.outcome == "accepted" and needs_advisor(
        db, plan, Evidence.model_validate(plan.weather_evidence)
    ):
        review = db.get(AdvisorDecision, plan.id) if case and not case.revoked_at else None
        active = (
            db.scalar(select(User.id).where(User.id == case.advisor_id, *active_advisors()))
            if review
            else None
        )
        if not active or review.outcome != "cleared":
            raise plans.conflict("This suggestion needs clearance from its assigned advisor.")
    return date_reviews.finish(db, actor.id, farm, plan, task, data.outcome, stamp, request_id)

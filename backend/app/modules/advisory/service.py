"""Revocable, assignment-scoped review of explicitly submitted weekly suggestions."""

from datetime import date, datetime, timedelta
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AfterValidator, BaseModel, EmailStr, Field
from sqlalchemy import select

from app.modules.advisory.models import AdvisorCase, AdvisorDecision
from app.modules.farms import date_reviews, plans, tasks, weekly
from app.modules.farms import schemas as dto
from app.modules.farms import service as farms
from app.modules.farms.models import Cultivation, Farm, FarmTask, TaskPlan, TaskPlanDecision
from app.modules.identity.models import User
from app.modules.identity.security import IdentityError
from app.modules.identity.service import active_actor
from app.modules.notifications.service import create_notification
from app.modules.weather import live

Outcome = Literal["cleared", "declined", "changes_requested"]


class Binding(dto.VersionCommand):
    action_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


class Assignment(Binding):
    advisor_email: EmailStr = Field(max_length=254)


class Revision(Binding):
    proposed_due_date: dto.LocalDate


class DecisionInput(Binding):
    outcome: Outcome
    reason: Annotated[str, AfterValidator(dto.trimmed), Field(max_length=500)]


class DecisionOut(BaseModel):
    plan_id: UUID
    outcome: Outcome
    reason: str
    decided_at: datetime


class CaseOut(dto.DateReviewOut):
    evidence: weekly.Evidence
    review: DecisionOut | None
    can_review: bool
    prior_proposed_date: date | None


class FarmerReview(BaseModel):
    role: Literal["farmer"] = "farmer"
    farm_id: UUID
    cultivation_id: UUID
    timezone: str
    task: weekly.WeekTask
    plan: weekly.WeeklyPlan


class AssignedReview(BaseModel):
    role: Literal["advisor"] = "advisor"
    case: CaseOut


def check_binding(plan, data):
    if data.expected_version != plan.version or data.action_hash != plan.action_hash:
        raise plans.conflict("This action is for a different suggestion. Reload the review.")


def submit_case(db, plan, farmer_id, advisor_id, stamp, request_id, *, revised=False):
    db.add(
        AdvisorCase(
            plan_id=plan.id,
            farmer_id=farmer_id,
            advisor_id=advisor_id,
            submitted_at=stamp,
            request_id=request_id,
        )
    )
    create_notification(
        db,
        advisor_id,
        "advisor_review",
        "Revised plan assigned" if revised else "Plan review assigned",
        "A weekly date suggestion is ready for your review.",
        review_plan_id=plan.id,
    )
    db.flush()


def assign(db, ids, farm_id, cultivation_id, plan_id, data, request_id):
    actor, farm, cultivation = tasks.writable_context(db, ids, farm_id, cultivation_id)
    plan = date_reviews.plan_for_decision(db, cultivation.id, plan_id, weekly.POLICY)
    check_binding(plan, data)
    if db.get(TaskPlanDecision, plan.id):
        raise plans.conflict("This suggestion already has a farmer decision.")
    stamp = live.now()
    task = date_reviews.current_task(db, farm, cultivation, plan, stamp)
    weekly.verify_evidence(db, farm, cultivation, task, plan, stamp)
    advisor = db.scalar(
        select(User.id).where(
            User.email == data.advisor_email.casefold(), *weekly.active_advisors()
        )
    )
    if advisor is None:
        raise IdentityError(404, "ADVISOR_NOT_FOUND", "No active advisor matched that email.")
    case = db.get(AdvisorCase, plan.id, with_for_update=True)
    if case is not None:
        if case.revoked_at or case.advisor_id != advisor:
            raise plans.conflict("Request a fresh suggestion before assigning another review.")
    else:
        submit_case(db, plan, actor.id, advisor, stamp, request_id)
    return weekly.view(db, farm, cultivation, task, plan, stamp)


def revise(db, ids, farm_id, cultivation_id, plan_id, data, request_id):
    actor, farm, cultivation = tasks.writable_context(db, ids, farm_id, cultivation_id)
    farms.active(farm, cultivation)
    previous = date_reviews.plan_for_decision(db, cultivation.id, plan_id, weekly.POLICY)
    check_binding(previous, data)
    task = tasks.task_for_update(db, cultivation.id, previous.target_task_id)
    retry = db.scalar(select(TaskPlan).where(TaskPlan.revises_plan_id == previous.id))
    stamp = live.now()
    if retry is not None:
        if retry.due_date != data.proposed_due_date:
            raise plans.conflict(
                "This suggestion already has a revised date. Open its latest review."
            )
        return weekly.view(db, farm, cultivation, task, retry, stamp)
    if not weekly.view(db, farm, cultivation, task, previous, stamp).can_revise:
        raise plans.conflict(
            "This suggestion can no longer be revised from the advisor's feedback."
        )
    if data.proposed_due_date == previous.due_date:
        raise plans.conflict("Choose a date different from the previous suggestion.")
    case = db.get(AdvisorCase, previous.id, with_for_update=True)
    advisor = db.scalar(
        select(User.id).where(User.id == case.advisor_id, *weekly.active_advisors())
    )
    if advisor is None:
        raise plans.conflict(
            "The assigned advisor is unavailable. Revoke sharing before requesting another review."
        )
    proposed, evidence = weekly.candidate(
        db, farm, cultivation, task, stamp, proposed_date=data.proposed_due_date
    )
    stamp = max(stamp, previous.created_at + timedelta(microseconds=1))
    revision = weekly.persist(
        db,
        actor.id,
        farm,
        cultivation,
        task,
        proposed,
        evidence,
        stamp,
        request_id,
        parent=previous.id,
    )
    submit_case(db, revision, actor.id, advisor, stamp, request_id, revised=True)
    return weekly.view(db, farm, cultivation, task, revision, stamp)


def revoke(db, ids, farm_id, cultivation_id, plan_id, data, request_id):
    _, farm, cultivation = tasks.writable_context(db, ids, farm_id, cultivation_id)
    plan = date_reviews.plan_for_decision(db, cultivation.id, plan_id, weekly.POLICY)
    check_binding(plan, data)
    case = db.get(AdvisorCase, plan.id, with_for_update=True)
    if case is None:
        raise farms.missing()
    stamp = live.now()
    if case.revoked_at is None:
        case.revoked_at = stamp
        case.revoke_request_id = request_id
    task = weekly.read_task(db, cultivation.id, plan.target_task_id)
    return weekly.view(db, farm, cultivation, task, plan, stamp)


def advisor_actor(db, ids, *, lock=False):
    actor = active_actor(db, ids, lock=lock)
    if actor.role != "advisor":
        raise IdentityError(403, "ACCESS_DENIED", "Advisor access is required.")
    return actor


def assigned_plans(advisor_id, stamp):
    return (
        select(TaskPlan)
        .join(AdvisorCase, AdvisorCase.plan_id == TaskPlan.id)
        .join(Cultivation, Cultivation.id == TaskPlan.cultivation_id)
        .join(Farm, Farm.id == Cultivation.farm_id)
        .join(User, User.id == Farm.farmer_id)
        .join(FarmTask, FarmTask.id == TaskPlan.target_task_id)
        .where(
            AdvisorCase.advisor_id == advisor_id,
            AdvisorCase.revoked_at.is_(None),
            AdvisorCase.farmer_id == Farm.farmer_id,
            TaskPlan.evidence_code == weekly.POLICY,
            TaskPlan.expires_at > stamp,
            TaskPlan.cultivation_version == Cultivation.version,
            TaskPlan.farm_version == Farm.version,
            TaskPlan.target_task_version == FarmTask.version,
            Farm.archived_at.is_(None),
            Cultivation.archived_at.is_(None),
            farms.visible_farm(),
            User.role == "farmer",
            User.disabled_at.is_(None),
            User.deleted_at.is_(None),
            FarmTask.status == "pending",
            date_reviews.current_plan_filter(),
            ~select(TaskPlanDecision.plan_id)
            .where(TaskPlanDecision.plan_id == TaskPlan.id)
            .exists(),
        )
    )


def decision_view(decision):
    return DecisionOut(
        plan_id=decision.plan_id,
        outcome=decision.outcome,
        reason=decision.reason,
        decided_at=decision.decided_at,
    )


def case_view(db, plan):
    evidence = weekly.Evidence.model_validate(plan.weather_evidence)
    review = db.get(AdvisorDecision, plan.id)
    cultivation = db.get(Cultivation, plan.cultivation_id)
    farm = db.get(Farm, cultivation.farm_id)
    task = weekly.read_task(db, cultivation.id, plan.target_task_id)
    parent = db.get(TaskPlan, plan.revises_plan_id) if plan.revises_plan_id else None
    return CaseOut(
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
        evidence=evidence,
        review=decision_view(review) if review else None,
        prior_proposed_date=parent.due_date if parent else None,
        can_review=review is None
        and weekly.evidence_current(db, farm, cultivation, task, plan, live.now()),
    )


def inbox(db, ids, query):
    actor = advisor_actor(db, ids)
    statement = assigned_plans(actor.id, live.now()).order_by(
        TaskPlan.created_at.desc(), TaskPlan.id.desc()
    )
    return farms.paged(db, statement, query, lambda plan: case_view(db, plan))


def open_review(db, ids, plan_id):
    actor = active_actor(db, ids)
    stamp = live.now()
    if actor.role == "advisor":
        plan = db.scalar(assigned_plans(actor.id, stamp).where(TaskPlan.id == plan_id))
        if plan is None:
            raise farms.missing()
        return AssignedReview(case=case_view(db, plan))
    if actor.role != "farmer":
        raise farms.missing()
    plan = db.scalar(
        select(TaskPlan).where(TaskPlan.id == plan_id, TaskPlan.evidence_code == weekly.POLICY)
    )
    if plan is None:
        raise farms.missing()
    farm, cultivation = farms.cultivation_for(db, actor.id, plan.cultivation_id)
    task = weekly.read_task(db, cultivation.id, plan.target_task_id)
    return FarmerReview(
        farm_id=farm.id,
        cultivation_id=cultivation.id,
        timezone=farm.timezone,
        task=weekly.WeekTask.model_validate(task),
        plan=weekly.view(db, farm, cultivation, task, plan, stamp),
    )


def decide(db, ids, plan_id, data, request_id):
    actor = advisor_actor(db, ids, lock=True)
    stamp = live.now()
    plan = db.scalar(
        assigned_plans(actor.id, stamp)
        .where(TaskPlan.id == plan_id)
        .with_for_update(of=AdvisorCase)
    )
    if plan is None:
        raise farms.missing()
    check_binding(plan, data)
    previous = db.get(AdvisorDecision, plan.id)
    if previous:
        if previous.outcome == data.outcome and previous.reason == data.reason:
            return decision_view(previous)
        raise plans.conflict("This advisor decision is already recorded.")
    cultivation = db.get(Cultivation, plan.cultivation_id)
    farm = db.get(Farm, cultivation.farm_id)
    task = weekly.read_task(db, cultivation.id, plan.target_task_id)
    weekly.verify_evidence(db, farm, cultivation, task, plan, stamp)
    decision = AdvisorDecision(
        plan_id=plan.id,
        advisor_id=actor.id,
        plan_version=plan.version,
        action_hash=plan.action_hash,
        outcome=data.outcome,
        reason=data.reason,
        decided_at=stamp,
        request_id=request_id,
    )
    db.add(decision)
    case = db.get(AdvisorCase, plan.id)
    create_notification(
        db,
        case.farmer_id,
        "advisor_review",
        {
            "cleared": "Plan cleared by advisor",
            "declined": "Plan declined by advisor",
            "changes_requested": "Advisor requested changes",
        }[data.outcome],
        "Open your weekly suggestion to read the advisor's decision.",
        review_plan_id=plan.id,
    )
    db.flush()
    return decision_view(decision)

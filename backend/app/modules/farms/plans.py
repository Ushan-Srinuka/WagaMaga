"""Create and execute the fixed portfolio task suggestion."""

import hashlib
import json
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import contains_eager

from app.modules.farms import schemas as dto
from app.modules.farms import service, tasks
from app.modules.farms.models import FarmTask, TaskPlan, TaskPlanDecision
from app.modules.identity.security import IdentityError, now

TITLE = "Check plot labels"
EVIDENCE_CODE = "portfolio_plot_labels_v1"
EVIDENCE = "Sample recordkeeping checklist: check that the plot labels match the farm notebook."
ACTION = "create_task"


def hash_action(action_type, title, due_date):
    return fingerprint({"type": action_type, "title": title, "due_date": due_date.isoformat()})


def fingerprint(action):
    return hashlib.sha256(json.dumps(action, sort_keys=True).encode()).hexdigest()


def conflict(message):
    return IdentityError(409, "PLAN_CONFLICT", message)


def pending_state(plan, farm, cultivation, stamp):
    if plan.expires_at <= stamp:
        return "expired"
    if (
        plan.farm_version != farm.version
        or plan.cultivation_version != cultivation.version
        or plan.evidence_code != EVIDENCE_CODE
        or plan.evidence_text != EVIDENCE
    ):
        return "stale"
    return "pending"


def view(plan, decision, farm, cultivation, stamp):
    return dto.PlanOut(
        id=plan.id,
        version=plan.version,
        action_type=plan.action_type,
        action_hash=plan.action_hash,
        title=plan.title,
        due_date=plan.due_date,
        evidence_text=plan.evidence_text,
        expires_at=plan.expires_at,
        state=decision.outcome if decision else pending_state(plan, farm, cultivation, stamp),
        decision=dto.PlanDecisionOut.model_validate(decision) if decision else None,
    )


def newest_plan(db, cultivation_id):
    return db.scalar(
        select(TaskPlan)
        .where(TaskPlan.cultivation_id == cultivation_id, TaskPlan.action_type == ACTION)
        .order_by(TaskPlan.created_at.desc(), TaskPlan.id.desc())
        .limit(1)
    )


def latest(db, ids, farm_id, cultivation_id):
    actor = service.farmer(db, ids)
    farm, cultivation = service.cultivation_for(db, actor.id, cultivation_id, farm_id=farm_id)
    plan = newest_plan(db, cultivation.id)
    if plan is None:
        return dto.LatestPlan(plan=None)
    decision = db.get(TaskPlanDecision, plan.id)
    return dto.LatestPlan(plan=view(plan, decision, farm, cultivation, now()))


def create(db, ids, farm_id, cultivation_id, request_id):
    actor, farm, cultivation = tasks.writable_context(db, ids, farm_id, cultivation_id)
    service.active(farm, cultivation)
    stamp = now()
    plan = newest_plan(db, cultivation.id)
    if (
        plan is not None
        and db.get(TaskPlanDecision, plan.id) is None
        and pending_state(plan, farm, cultivation, stamp) == "pending"
    ):
        return view(plan, None, farm, cultivation, stamp)
    due_date = service.local_today(db, farm) + timedelta(days=1)
    plan = TaskPlan(
        cultivation_id=cultivation.id,
        action_type=ACTION,
        action_hash=hash_action(ACTION, TITLE, due_date),
        title=TITLE,
        due_date=due_date,
        evidence_code=EVIDENCE_CODE,
        evidence_text=EVIDENCE,
        farm_version=farm.version,
        cultivation_version=cultivation.version,
        created_by=actor.id,
        request_id=request_id,
        created_at=stamp,
        expires_at=stamp + timedelta(days=1),
    )
    db.add(plan)
    db.flush()
    return view(plan, None, farm, cultivation, stamp)


def decide(db, ids, farm_id, cultivation_id, plan_id, key, data, request_id):
    # The same parent locks serialize review with task writes, new suggestions and archives.
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
    saved = replay_decision(db, plan, key, data)
    if saved is not None:
        return saved

    service.active(farm, cultivation)
    stamp = now()
    if pending_state(plan, farm, cultivation, stamp) != "pending":
        raise conflict("This plan expired or its records changed. Review a new example.")

    task = (
        execute_action(db, actor.id, farm, plan, request_id) if data.outcome == "accepted" else None
    )
    return record_decision(db, plan, actor.id, data.outcome, task, stamp, request_id)


def replay_decision(db, plan, key, data):
    if (
        key != plan.id
        or data.expected_version != plan.version
        or data.action_hash != plan.action_hash
    ):
        raise conflict("The decision does not match the saved plan. Reload and review it.")
    saved = db.get(TaskPlanDecision, plan.id)
    if saved is not None:
        if saved.outcome != data.outcome:
            raise conflict("This plan already has a different decision.")
        return dto.PlanDecisionOut.model_validate(saved)
    return None


def record_decision(db, plan, actor_id, outcome, task, stamp, request_id):
    decision = TaskPlanDecision(
        plan_id=plan.id,
        plan_version=plan.version,
        action_hash=plan.action_hash,
        outcome=outcome,
        task_id=task.id if task is not None else None,
        task_version=task.version if task is not None else None,
        actor_id=actor_id,
        request_id=request_id,
        decided_at=stamp,
    )
    db.add(decision)
    db.flush()
    return dto.PlanDecisionOut.model_validate(decision)


def execute_action(db, actor_id, farm, plan, request_id):
    today = service.local_today(db, farm)
    if (
        plan.action_type != ACTION
        or plan.title != TITLE
        or plan.action_hash != hash_action(plan.action_type, plan.title, plan.due_date)
        or not today <= plan.due_date <= today + timedelta(days=7)
    ):
        raise conflict("This plan no longer matches the demo action. Review a new example.")
    duplicate = db.scalar(
        select(FarmTask.id)
        .where(
            FarmTask.cultivation_id == plan.cultivation_id,
            func.lower(FarmTask.title) == plan.title.lower(),
            FarmTask.due_date == plan.due_date,
            FarmTask.status == "pending",
        )
        .limit(1)
    )
    if duplicate is not None:
        raise conflict("A matching task is already pending.")
    data = dto.TaskCreate(title=plan.title, due_date=plan.due_date)
    return tasks.add_task(db, farm, plan.cultivation_id, actor_id, data, request_id)


def history(db, ids, farm_id, cultivation_id, query):
    actor = service.farmer(db, ids)
    service.cultivation_for(db, actor.id, cultivation_id, farm_id=farm_id)
    statement = (
        select(TaskPlanDecision)
        .join(TaskPlanDecision.plan)
        .options(contains_eager(TaskPlanDecision.plan))
        .where(TaskPlan.cultivation_id == cultivation_id)
        .order_by(TaskPlanDecision.decided_at.desc(), TaskPlanDecision.plan_id)
    )

    def project(decision):
        return dto.PlanHistoryOut(
            **dto.PlanDecisionOut.model_validate(decision).model_dump(),
            title=decision.plan.title,
            due_date=decision.plan.due_date,
            evidence_text=decision.plan.evidence_text,
            action_type=decision.plan.action_type,
            previous_due_date=decision.plan.previous_due_date,
        )

    return service.paged(db, statement, query, project)

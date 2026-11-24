"""Common scope checks and atomic effects for owner-reviewed task dates."""

from datetime import timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import aliased

from app.modules.farms import plans, service, tasks
from app.modules.farms.models import TaskPlan
from app.modules.weather import alerts

ACTION = "reschedule_task"


def current_plan_filter():
    newer = aliased(TaskPlan)
    return (
        ~select(newer.id)
        .where(
            newer.target_task_id == TaskPlan.target_task_id,
            newer.action_type == ACTION,
            or_(
                newer.created_at > TaskPlan.created_at,
                (newer.created_at == TaskPlan.created_at) & (newer.id > TaskPlan.id),
            ),
        )
        .exists()
    )


def valid_date(db, farm, current_date, proposed_date, stamp):
    today = service.local_today(db, farm, at=stamp)
    if current_date == proposed_date or not today <= proposed_date <= today + timedelta(days=7):
        raise plans.conflict("Choose a different date within the next seven days.")


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


def plan_for_decision(db, cultivation_id, plan_id, policy):
    plan = db.scalar(
        select(TaskPlan).where(
            TaskPlan.id == plan_id,
            TaskPlan.cultivation_id == cultivation_id,
            TaskPlan.action_type == ACTION,
            TaskPlan.evidence_code == policy,
        )
    )
    if plan is None:
        raise service.missing()
    return plan


def current_task(db, farm, cultivation, plan, stamp):
    service.active(farm, cultivation)
    if (
        stamp >= plan.expires_at
        or plan.farm_version != farm.version
        or plan.cultivation_version != cultivation.version
    ):
        raise plans.conflict("This review expired or the farm changed. Start a new review.")
    if latest_for_task(db, cultivation.id, plan.target_task_id).id != plan.id:
        raise plans.conflict("A newer date was reviewed for this task. Use the latest review.")
    task = tasks.task_for_update(db, cultivation.id, plan.target_task_id)
    if (
        task.status != "pending"
        or task.version != plan.target_task_version
        or task.due_date != plan.previous_due_date
    ):
        raise plans.conflict("This task changed. Start a new review.")
    valid_date(db, farm, task.due_date, plan.due_date, stamp)
    return task


def finish(db, actor_id, farm, plan, task, outcome, stamp, request_id):
    effect = None
    if outcome == "accepted":
        service.assign(task, {"due_date": plan.due_date})
        tasks.record_event(db, task, actor_id, "edited", request_id)
        alerts.sync(db, farm, cultivation_id=task.cultivation_id, task_id=task.id)
        effect = task
    return plans.record_decision(db, plan, actor_id, outcome, effect, stamp, request_id)

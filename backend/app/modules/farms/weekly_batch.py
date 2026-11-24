"""Review several independent date changes and apply a selected set atomically."""

from pydantic import BaseModel
from sqlalchemy import select

from app.modules.farms import date_reviews, plans, service, tasks, weekly
from app.modules.farms import schemas as dto
from app.modules.farms.models import FarmTask, TaskPlan, TaskPlanDecision
from app.modules.identity.security import IdentityError
from app.modules.weather import alerts, live
from app.modules.weather.models import WeatherAlertRule


class Preparation(BaseModel):
    prepared: int


def list_plans(db, ids, farm_id, cultivation_id, query, *, history=False):
    actor = service.farmer(db, ids)
    farm, cultivation = service.cultivation_for(db, actor.id, cultivation_id, farm_id=farm_id)
    stamp = live.now()
    statement = select(TaskPlan).where(
        TaskPlan.cultivation_id == cultivation.id, TaskPlan.evidence_code == weekly.POLICY
    )
    if history:
        statement = statement.order_by(TaskPlan.created_at.desc(), TaskPlan.id.desc())
    else:
        today = service.local_today(db, farm, at=stamp)
        statement = (
            statement.join(FarmTask, FarmTask.id == TaskPlan.target_task_id)
            .where(
                FarmTask.status == "pending",
                TaskPlan.previous_due_date.between(today, today + weekly.WEEK),
                date_reviews.current_plan_filter(),
                ~select(TaskPlanDecision.plan_id)
                .where(TaskPlanDecision.plan_id == TaskPlan.id)
                .exists(),
            )
            .order_by(TaskPlan.previous_due_date, TaskPlan.id)
        )

    def project(plan):
        task = weekly.read_task(db, cultivation.id, plan.target_task_id)
        return weekly.view(db, farm, cultivation, task, plan, stamp)

    return service.paged(db, statement, query, project)


def prepare(db, ids, farm_id, cultivation_id, request_id):
    actor, farm, cultivation = tasks.writable_context(db, ids, farm_id, cultivation_id)
    service.active(farm, cultivation)
    stamp = live.now()
    forecast, fresh = live.examine(db, farm, stamp)
    rule = db.get(WeatherAlertRule, cultivation.id)
    dates = alerts.qualifying_days(rule, forecast) if fresh else {}
    if not dates:
        return Preparation(prepared=0)
    candidates = db.scalars(
        select(FarmTask)
        .where(
            FarmTask.cultivation_id == cultivation.id,
            FarmTask.status == "pending",
            FarmTask.due_date.in_(list(dates)),
        )
        .order_by(FarmTask.due_date, FarmTask.id)
        .limit(weekly.BATCH_SIZE)
    ).all()
    prepared = 0
    for task in candidates:
        latest = date_reviews.latest_for_task(db, cultivation.id, task.id)
        if (
            latest
            and latest.evidence_code != weekly.POLICY
            and latest.expires_at > stamp
            and not db.get(TaskPlanDecision, latest.id)
        ):
            continue
        try:
            weekly.prepare_task(db, actor, farm, cultivation, task, stamp, request_id)
        except IdentityError as error:
            if error.status != 409:
                raise
        else:
            prepared += 1
    return Preparation(prepared=prepared)


def accept(db, ids, farm_id, cultivation_id, data, request_id):
    _, farm, cultivation = tasks.writable_context(db, ids, farm_id, cultivation_id)
    service.active(farm, cultivation)
    selected = [
        date_reviews.plan_for_decision(db, cultivation.id, item.plan_id, weekly.POLICY)
        for item in data.changes
    ]
    if len({plan.target_task_id for plan in selected}) != len(selected):
        raise plans.conflict("Choose only one suggestion for each task.")
    decisions = []
    for item in data.changes:
        decision = dto.PlanDecision(
            expected_version=item.expected_version, action_hash=item.action_hash, outcome="accepted"
        )
        decisions.append(
            weekly.decide(
                db, ids, farm_id, cultivation_id, item.plan_id, item.plan_id, decision, request_id
            )
        )
    return weekly.WeeklyBatchReceipt(decisions=decisions)

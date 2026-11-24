"""A read-only timeline projected from the owner's existing cultivation records."""

from sqlalchemy import Date, cast, func, literal, select, union_all

from app.modules.farms import service
from app.modules.farms.models import (
    FarmObservation,
    FarmTask,
    FarmTaskEvent,
    TaskPlan,
    TaskPlanDecision,
)
from app.modules.farms.schemas import DiaryEntry


def list_entries(db, ids, farm_id, cultivation_id, query):
    actor = service.farmer(db, ids)
    service.cultivation_for(db, actor.id, cultivation_id, farm_id=farm_id)
    observation = FarmObservation
    event = FarmTaskEvent
    decision = TaskPlanDecision
    entries = union_all(
        select(
            observation.id.label("id"),
            literal("observation").label("kind"),
            observation.observed_at.label("occurred_at"),
            observation.notes.label("description"),
            observation.soil_moisture.label("soil_moisture"),
            cast(None, Date).label("previous_due_date"),
            cast(None, Date).label("due_date"),
        ).where(observation.cultivation_id == cultivation_id),
        select(
            event.task_id,
            event.action,
            event.occurred_at,
            event.title,
            literal(None),
            cast(None, Date),
            event.due_date,
        )
        .join(FarmTask)
        .where(
            FarmTask.cultivation_id == cultivation_id,
            event.action.in_(("completed", "cancelled")),
        ),
        select(
            TaskPlan.id,
            TaskPlan.action_type,
            decision.decided_at,
            TaskPlan.title,
            literal(None),
            TaskPlan.previous_due_date,
            TaskPlan.due_date,
        )
        .join(decision, decision.plan_id == TaskPlan.id)
        .where(
            TaskPlan.cultivation_id == cultivation_id,
            decision.outcome == "accepted",
        ),
    ).subquery()
    total = db.scalar(select(func.count()).select_from(entries))
    results = db.execute(
        select(entries)
        .order_by(entries.c.occurred_at.desc(), entries.c.kind, entries.c.id)
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    ).mappings()
    return {
        "items": [DiaryEntry.model_validate(row) for row in results],
        "total": total,
        "page": query.page,
        "page_size": query.page_size,
    }

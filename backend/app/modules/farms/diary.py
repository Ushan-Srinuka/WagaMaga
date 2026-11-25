"""A read-only timeline projected from the owner's existing cultivation records."""

from sqlalchemy import Date, case, cast, func, literal, select, union_all
from sqlalchemy.orm import aliased

from app.modules.farms import missed_tasks, service, weekly
from app.modules.farms.models import (
    FarmObservation,
    FarmTask,
    FarmTaskEvent,
    TaskPlan,
    TaskPlanDecision,
)
from app.modules.farms.schemas import DiaryEntry
from app.modules.weather import reschedules


def list_entries(db, ids, farm_id, cultivation_id, query):
    actor = service.farmer(db, ids)
    service.cultivation_for(db, actor.id, cultivation_id, farm_id=farm_id)
    observation = FarmObservation
    event = FarmTaskEvent
    decision = TaskPlanDecision
    previous = aliased(FarmTaskEvent)
    weather = TaskPlan.evidence_code == reschedules.EVIDENCE_CODE
    kept = decision.outcome == "rejected"
    plan_kind = case(
        (weather & kept, "weather_kept"),
        (weather, "weather_rescheduled"),
        ((TaskPlan.evidence_code == missed_tasks.POLICY) & kept, "missed_task_kept"),
        (kept, "plan_declined"),
        else_=TaskPlan.action_type,
    )
    entries = union_all(
        select(
            observation.id.label("id"),
            literal("observation").label("kind"),
            observation.observed_at.label("occurred_at"),
            observation.notes.label("description"),
            observation.soil_moisture.label("soil_moisture"),
            cast(None, Date).label("previous_due_date"),
            cast(None, Date).label("due_date"),
            literal(None).label("revision"),
            literal(None).label("evidence"),
            literal(False).label("weekly_review"),
        ).where(observation.cultivation_id == cultivation_id),
        select(
            event.task_id,
            event.action,
            event.occurred_at,
            event.title,
            literal(None),
            case((event.action == "edited", previous.due_date), else_=cast(None, Date)),
            event.due_date,
            event.version,
            literal(None),
            literal(False),
        )
        .select_from(event)
        .join(FarmTask, FarmTask.id == event.task_id)
        .outerjoin(
            previous,
            (previous.task_id == event.task_id) & (previous.version == event.version - 1),
        )
        .where(
            FarmTask.cultivation_id == cultivation_id,
            ~select(decision.plan_id)
            .where(
                decision.task_id == event.task_id,
                decision.task_version == event.version,
                decision.outcome == "accepted",
            )
            .exists(),
        ),
        select(
            TaskPlan.id,
            plan_kind,
            decision.decided_at,
            TaskPlan.title,
            literal(None),
            TaskPlan.previous_due_date,
            TaskPlan.due_date,
            TaskPlan.version,
            TaskPlan.evidence_text,
            TaskPlan.evidence_code == weekly.POLICY,
        )
        .join(decision, decision.plan_id == TaskPlan.id)
        .where(
            TaskPlan.cultivation_id == cultivation_id,
        ),
    ).subquery()
    total = db.scalar(select(func.count()).select_from(entries))
    results = db.execute(
        select(entries)
        .order_by(
            entries.c.occurred_at.desc(), entries.c.kind, entries.c.id, entries.c.revision.desc()
        )
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    ).mappings()
    return {
        "items": [DiaryEntry.model_validate(row) for row in results],
        "total": total,
        "page": query.page,
        "page_size": query.page_size,
    }

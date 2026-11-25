"""Questions grounded in the selected cultivation's planner and saved evidence."""

import re
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field

from app.modules.farms import schemas as dto
from app.modules.farms import service, weekly
from app.modules.farms.models import CHILLI_ID
from app.modules.weather import live


class Question(dto.Input):
    question: Annotated[str, AfterValidator(dto.trimmed), Field(max_length=240)]
    task_id: dto.Identifier | None = None


class Answer(BaseModel):
    message: str
    tasks: weekly.Week | None = None
    plan: weekly.WeeklyPlan | None = None


def ask(db, ids, farm_id, cultivation_id, data):
    actor = service.farmer(db, ids)
    farm, cultivation = service.cultivation_for(db, actor.id, cultivation_id, farm_id=farm_id)
    if cultivation.crop_type_id != CHILLI_ID:
        raise service.missing()

    words = set(re.findall(r"[a-z]+", data.question.lower()))
    if words & {"why", "explain", "reason"} and words & {
        "date",
        "suggest",
        "suggested",
        "suggestion",
        "moved",
        "reschedule",
    }:
        if data.task_id is None:
            return Answer(
                message="Which task’s suggested date should I explain? Choose a task below, "
                "or use the seven-day planner to find it.",
                tasks=weekly.week_for(db, farm, cultivation, dto.Paging(), scope="all"),
            )
        task = weekly.read_task(db, cultivation.id, data.task_id)
        plan = weekly.latest_plan(db, cultivation.id, task.id)
        if plan is None:
            return Answer(message="There is no saved weekly date suggestion for this task.")
        return Answer(
            message=plan.evidence_text,
            plan=weekly.view(db, farm, cultivation, task, plan, live.now()),
        )

    if words & {"overdue", "miss", "missed", "late", "past"}:
        scope, present, empty = "overdue", "Pending overdue tasks", "No pending overdue tasks."
    elif words & {"week", "upcoming", "next", "due", "schedule"}:
        scope = "upcoming"
        present = "Pending tasks in the next seven farm-local days"
        empty = "No pending tasks in the next seven farm-local days."
    else:
        return Answer(
            message="Ask what’s due this week, what’s overdue, or why a date was suggested."
        )

    week = weekly.week_for(db, farm, cultivation, dto.Paging(), scope=scope)
    return Answer(message=f"{present} ({week.total})." if week.total else empty, tasks=week)

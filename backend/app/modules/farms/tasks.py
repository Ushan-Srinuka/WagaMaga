"""Manual tasks and their append-only history under an owned cultivation."""

from sqlalchemy import select

from app.modules.farms import schemas as dto
from app.modules.farms import service
from app.modules.farms.models import FarmTask, FarmTaskEvent
from app.modules.identity.security import IdentityError
from app.modules.weather import alerts


def list_tasks(db, ids, farm_id, cultivation_id, query):
    actor = service.farmer(db, ids)
    service.cultivation_for(db, actor.id, cultivation_id, farm_id=farm_id)
    statement = select(FarmTask).where(FarmTask.cultivation_id == cultivation_id)
    if query.status != "all":
        statement = statement.where(FarmTask.status == query.status)
    return service.paged(
        db, statement.order_by(FarmTask.due_date, FarmTask.id), query, dto.TaskOut.model_validate
    )


def task_history(db, ids, farm_id, cultivation_id, query):
    actor = service.farmer(db, ids)
    service.cultivation_for(db, actor.id, cultivation_id, farm_id=farm_id)
    statement = (
        select(FarmTaskEvent)
        .join(FarmTask)
        .where(FarmTask.cultivation_id == cultivation_id)
        .order_by(
            FarmTaskEvent.occurred_at.desc(), FarmTaskEvent.task_id, FarmTaskEvent.version.desc()
        )
    )
    return service.paged(db, statement, query, dto.TaskEventOut.model_validate)


def writable_context(db, ids, farm_id, cultivation_id):
    actor = service.farmer(db, ids, write=True)
    farm, cultivation = service.cultivation_for(
        db, actor.id, cultivation_id, farm_id=farm_id, lock=True
    )
    return actor, farm, cultivation


def record_event(db, task, actor_id, action, request_id):
    db.flush()
    db.add(
        FarmTaskEvent(
            task_id=task.id,
            version=task.version,
            title=task.title,
            due_date=task.due_date,
            action=action,
            actor_id=actor_id,
            request_id=request_id,
            occurred_at=task.updated_at,
        )
    )
    db.flush()


def create_task(db, ids, farm_id, cultivation_id, data, request_id):
    actor, farm, cultivation = writable_context(db, ids, farm_id, cultivation_id)
    service.active(farm, cultivation)
    return dto.TaskOut.model_validate(
        add_task(db, farm, cultivation.id, actor.id, data, request_id)
    )


def add_task(db, farm, cultivation_id, actor_id, data, request_id):
    task = FarmTask(cultivation_id=cultivation_id, **data.model_dump())
    db.add(task)
    record_event(db, task, actor_id, "created", request_id)
    alerts.sync(db, farm, cultivation_id=cultivation_id, task_id=task.id)
    return task


def task_for_update(db, cultivation_id, task_id):
    task = db.scalar(
        select(FarmTask)
        .where(FarmTask.id == task_id, FarmTask.cultivation_id == cultivation_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if task is None:
        raise service.missing()
    return task


def change_task(db, ids, farm_id, cultivation_id, task_id, data, request_id):
    actor, farm, cultivation = writable_context(db, ids, farm_id, cultivation_id)
    task = task_for_update(db, cultivation.id, task_id)
    service.active(farm, cultivation)
    service.check_version(task, data.expected_version)
    if task.status != "pending":
        raise IdentityError(409, "TASK_CLOSED", "Completed and cancelled tasks cannot be changed.")
    if service.assign(task, data.model_dump(exclude={"expected_version"})):
        action = data.status if isinstance(data, dto.TaskTransition) else "edited"
        record_event(db, task, actor.id, action, request_id)
        if task.status == "pending":
            alerts.sync(db, farm, cultivation_id=cultivation.id, task_id=task.id)
    return dto.TaskOut.model_validate(task)

"""Persistent farm-local task reminders maintained by the worker."""

from sqlalchemy import Date, case, cast, func, literal, or_, select
from sqlalchemy.dialects.postgresql import insert

from app.modules.farms.models import Cultivation, Farm, FarmTask, visible_farm
from app.modules.identity.models import User
from app.modules.notifications.models import Notification


def eligible_tasks():
    today = cast(func.timezone(Farm.timezone, func.now()), Date)
    kind = case((FarmTask.due_date < today, "task_overdue"), else_="task_due")
    return (
        select(FarmTask.id, FarmTask.due_date, Farm.farmer_id, kind.label("event_type"))
        .join(Cultivation, Cultivation.id == FarmTask.cultivation_id)
        .join(Farm, Farm.id == Cultivation.farm_id)
        .join(User, User.id == Farm.farmer_id)
        .where(
            FarmTask.status == "pending",
            FarmTask.due_date <= today + 1,
            Cultivation.archived_at.is_(None),
            Farm.archived_at.is_(None),
            visible_farm(),
            User.role == "farmer",
            User.disabled_at.is_(None),
            User.deleted_at.is_(None),
        )
    )


def visible_notification():
    tasks = eligible_tasks().subquery()
    return or_(
        Notification.reminder_task_id.is_(None),
        select(tasks.c.id)
        .where(
            tasks.c.id == Notification.reminder_task_id,
            tasks.c.due_date == Notification.reminder_due_date,
            tasks.c.farmer_id == Notification.recipient_id,
            tasks.c.event_type == Notification.event_type,
        )
        .exists(),
    )


def process_batch(engine):
    tasks = eligible_tasks().subquery()
    already_sent = (
        select(Notification.id)
        .where(
            Notification.reminder_task_id == tasks.c.id,
            Notification.reminder_due_date == tasks.c.due_date,
            Notification.event_type == tasks.c.event_type,
        )
        .exists()
    )
    candidates = (
        select(
            func.gen_random_uuid(),
            tasks.c.farmer_id,
            tasks.c.event_type,
            case(
                (tasks.c.event_type == "task_overdue", "Farm task overdue"),
                else_="Farm task due soon",
            ),
            literal("Open the seven-day planner to review your farm tasks."),
            tasks.c.id,
            tasks.c.due_date,
        )
        .where(~already_sent)
        .order_by(tasks.c.due_date, tasks.c.id)
        .limit(100)
    )
    statement = (
        insert(Notification)
        .from_select(
            [
                "id",
                "recipient_id",
                "event_type",
                "title",
                "body",
                "reminder_task_id",
                "reminder_due_date",
            ],
            candidates,
        )
        .on_conflict_do_nothing(constraint="uq_notifications_task_reminder")
    )
    with engine.begin() as connection:
        connection.execute(statement)

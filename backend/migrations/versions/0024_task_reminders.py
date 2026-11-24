"""Bind each task reminder to its scheduled date and reminder type."""

import sqlalchemy as sa
from alembic import op

revision = "0024_task_reminders"
down_revision = "0023_plan_revision_notices"
branch_labels = None
depends_on = None

OLD_EVENTS = (
    "'role_changed','account_reenabled','password_changed',"
    "'support_updated','weather_review','advisor_review'"
)


def upgrade():
    op.add_column("notifications", sa.Column("reminder_task_id", sa.Uuid()))
    op.add_column("notifications", sa.Column("reminder_due_date", sa.Date()))
    op.create_foreign_key(
        "fk_notifications_reminder_task",
        "notifications",
        "farm_tasks",
        ["reminder_task_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_notifications_task_reminder",
        "notifications",
        ["reminder_task_id", "reminder_due_date", "event_type"],
    )
    op.create_check_constraint(
        "notifications_task_reminder_link",
        "notifications",
        "(event_type IN ('task_due','task_overdue')) = (reminder_task_id IS NOT NULL) "
        "AND (reminder_task_id IS NULL) = (reminder_due_date IS NULL)",
    )
    op.drop_constraint("notifications_event_type", "notifications", type_="check")
    op.create_check_constraint(
        "notifications_event_type",
        "notifications",
        f"event_type IN ({OLD_EVENTS},'task_due','task_overdue')",
    )


def downgrade():
    if op.get_bind().scalar(
        sa.text("SELECT EXISTS (SELECT 1 FROM notifications WHERE reminder_task_id IS NOT NULL)")
    ):
        raise RuntimeError("Cannot remove saved task reminder evidence.")
    op.drop_constraint("notifications_event_type", "notifications", type_="check")
    op.create_check_constraint(
        "notifications_event_type", "notifications", f"event_type IN ({OLD_EVENTS})"
    )
    op.drop_constraint("notifications_task_reminder_link", "notifications", type_="check")
    op.drop_constraint("uq_notifications_task_reminder", "notifications", type_="unique")
    op.drop_constraint("fk_notifications_reminder_task", "notifications", type_="foreignkey")
    op.drop_column("notifications", "reminder_due_date")
    op.drop_column("notifications", "reminder_task_id")

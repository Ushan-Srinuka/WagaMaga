"""Link each immutable revision to its parent and persist review notification links."""

import sqlalchemy as sa
from alembic import op

revision = "0023_plan_revision_notices"
down_revision = "0022_advisor_plan_cases"
branch_labels = None
depends_on = None

OLD_EVENTS = (
    "'role_changed','account_reenabled','password_changed','support_updated','weather_review'"
)


def upgrade():
    op.add_column("task_plans", sa.Column("revises_plan_id", sa.Uuid()))
    op.create_foreign_key(
        "fk_task_plan_revision_parent",
        "task_plans",
        "task_plans",
        ["revises_plan_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint("uq_task_plan_revision_parent", "task_plans", ["revises_plan_id"])
    op.add_column("notifications", sa.Column("review_plan_id", sa.Uuid()))
    op.create_foreign_key(
        "fk_notifications_review_plan",
        "notifications",
        "task_plans",
        ["review_plan_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint("notifications_event_type", "notifications", type_="check")
    op.create_check_constraint(
        "notifications_event_type",
        "notifications",
        f"event_type IN ({OLD_EVENTS},'advisor_review')",
    )
    op.create_check_constraint(
        "notifications_review_link",
        "notifications",
        "(event_type = 'advisor_review') = (review_plan_id IS NOT NULL)",
    )


def downgrade():
    if op.get_bind().scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM task_plans WHERE revises_plan_id IS NOT NULL) OR "
            "EXISTS (SELECT 1 FROM notifications WHERE review_plan_id IS NOT NULL)"
        )
    ):
        raise RuntimeError("Cannot remove saved plan revision or review notice evidence.")
    op.drop_constraint("notifications_review_link", "notifications", type_="check")
    op.drop_constraint("notifications_event_type", "notifications", type_="check")
    op.create_check_constraint(
        "notifications_event_type", "notifications", f"event_type IN ({OLD_EVENTS})"
    )
    op.drop_constraint("fk_notifications_review_plan", "notifications", type_="foreignkey")
    op.drop_column("notifications", "review_plan_id")
    op.drop_constraint("uq_task_plan_revision_parent", "task_plans", type_="unique")
    op.drop_constraint("fk_task_plan_revision_parent", "task_plans", type_="foreignkey")
    op.drop_column("task_plans", "revises_plan_id")

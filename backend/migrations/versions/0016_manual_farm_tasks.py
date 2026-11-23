"""Add private manual cultivation tasks and append-only task history."""

import sqlalchemy as sa
from alembic import op

from app.core.config import Settings

revision = "0016_manual_farm_tasks"
down_revision = "0015_knowledge_translations"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "farm_tasks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "cultivation_id",
            sa.Uuid(),
            sa.ForeignKey("cultivations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(9), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("version > 0", name="farm_tasks_version"),
        sa.CheckConstraint("title ~ '[^[:space:]]'", name="farm_tasks_title"),
        sa.CheckConstraint("isfinite(due_date)", name="farm_tasks_due_date"),
        sa.CheckConstraint(
            "status IN ('pending', 'completed', 'cancelled')", name="farm_tasks_status"
        ),
    )
    op.create_index("ix_farm_tasks_due", "farm_tasks", ["cultivation_id", "due_date", "id"])
    op.create_table(
        "farm_task_events",
        sa.Column(
            "task_id",
            sa.Uuid(),
            sa.ForeignKey("farm_tasks.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("version", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("action", sa.String(9), nullable=False),
        sa.Column(
            "actor_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("request_id", sa.String(36), nullable=False),
        sa.Column(
            "occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "(version = 1 AND action = 'created') OR "
            "(version > 1 AND action IN ('edited', 'completed', 'cancelled'))",
            name="farm_task_events_action",
        ),
        sa.CheckConstraint("title ~ '[^[:space:]]'", name="farm_task_events_title"),
        sa.CheckConstraint("isfinite(due_date)", name="farm_task_events_due_date"),
    )
    op.execute(
        """
        CREATE FUNCTION guard_farm_task_update() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF OLD.status <> 'pending' OR NEW.version <> OLD.version + 1
               OR NEW.id <> OLD.id OR NEW.cultivation_id <> OLD.cultivation_id
               OR NEW.created_at <> OLD.created_at THEN
                RAISE EXCEPTION 'Invalid farm task update' USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER guard_farm_task_update BEFORE UPDATE ON farm_tasks
        FOR EACH ROW EXECUTE FUNCTION guard_farm_task_update()
        """
    )
    role = op.get_bind().dialect.identifier_preparer.quote(Settings().app_db_user)
    op.execute(f"GRANT SELECT, INSERT ON public.farm_tasks, public.farm_task_events TO {role}")
    op.execute(
        "GRANT UPDATE (title, due_date, status, version, updated_at) "
        f"ON public.farm_tasks TO {role}"
    )


def downgrade():
    if op.get_bind().scalar(sa.text("SELECT EXISTS (SELECT 1 FROM farm_tasks)")):
        raise RuntimeError("Cannot downgrade while farm task history exists")
    op.drop_table("farm_task_events")
    op.drop_table("farm_tasks")
    op.execute("DROP FUNCTION guard_farm_task_update()")

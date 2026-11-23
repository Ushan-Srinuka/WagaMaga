"""Persist immutable example task plans and their decisions and effects."""

import sqlalchemy as sa
from alembic import op

from app.core.config import Settings

revision = "0017_suggested_task_plans"
down_revision = "0016_manual_farm_tasks"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "task_plans",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "cultivation_id",
            sa.Uuid(),
            sa.ForeignKey("cultivations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("action_type", sa.String(16), nullable=False),
        sa.Column("action_hash", sa.String(64), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("evidence_code", sa.String(40), nullable=False),
        sa.Column("evidence_text", sa.Text(), nullable=False),
        sa.Column("farm_version", sa.Integer(), nullable=False),
        sa.Column("cultivation_version", sa.Integer(), nullable=False),
        sa.Column(
            "created_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("request_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("id", "version", "action_hash", name="uq_task_plan_binding"),
        sa.CheckConstraint("version = 1", name="task_plans_version"),
        sa.CheckConstraint("action_type = 'create_task'", name="task_plans_action"),
        sa.CheckConstraint(
            "farm_version > 0 AND cultivation_version > 0", name="task_plans_context"
        ),
        sa.CheckConstraint(
            "isfinite(due_date) AND expires_at > created_at", name="task_plans_dates"
        ),
    )
    op.create_index(
        "ix_task_plans_cultivation_created", "task_plans", ["cultivation_id", "created_at", "id"]
    )
    op.create_table(
        "task_plan_decisions",
        sa.Column("plan_id", sa.Uuid(), primary_key=True),
        sa.Column("plan_version", sa.Integer(), nullable=False),
        sa.Column("action_hash", sa.String(64), nullable=False),
        sa.Column("outcome", sa.String(8), nullable=False),
        sa.Column(
            "task_id", sa.Uuid(), sa.ForeignKey("farm_tasks.id", ondelete="RESTRICT"), unique=True
        ),
        sa.Column(
            "actor_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("request_id", sa.String(36), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["plan_id", "plan_version", "action_hash"],
            ["task_plans.id", "task_plans.version", "task_plans.action_hash"],
            name="fk_task_plan_decision_binding",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "(outcome = 'accepted' AND task_id IS NOT NULL) OR "
            "(outcome = 'rejected' AND task_id IS NULL)",
            name="task_plan_decisions_effect",
        ),
    )
    role = op.get_bind().dialect.identifier_preparer.quote(Settings().app_db_user)
    op.execute(f"GRANT SELECT, INSERT ON public.task_plans, public.task_plan_decisions TO {role}")


def downgrade():
    if op.get_bind().scalar(sa.text("SELECT EXISTS (SELECT 1 FROM task_plans)")):
        raise RuntimeError("Cannot downgrade while task plan history exists")
    op.drop_table("task_plan_decisions")
    op.drop_table("task_plans")

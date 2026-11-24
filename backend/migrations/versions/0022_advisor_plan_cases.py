"""Persist advisor assignment and exact-plan decisions for weekly suggestions."""

import sqlalchemy as sa
from alembic import op

from app.core.config import Settings

revision = "0022_advisor_plan_cases"
down_revision = "0021_guidance_observations"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "advisor_cases",
        sa.Column(
            "plan_id",
            sa.Uuid(),
            sa.ForeignKey("task_plans.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column(
            "farmer_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column(
            "advisor_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_id", sa.String(36), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("revoke_request_id", sa.String(36)),
        sa.UniqueConstraint("plan_id", "advisor_id", name="uq_advisor_case_assignment"),
    )
    op.create_index(
        "ix_advisor_cases_recipient", "advisor_cases", ["advisor_id", "submitted_at", "plan_id"]
    )
    op.create_table(
        "advisor_decisions",
        sa.Column("plan_id", sa.Uuid(), primary_key=True),
        sa.Column("advisor_id", sa.Uuid(), nullable=False),
        sa.Column("plan_version", sa.Integer(), nullable=False),
        sa.Column("action_hash", sa.String(64), nullable=False),
        sa.Column("outcome", sa.String(20), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_id", sa.String(36), nullable=False),
        sa.ForeignKeyConstraint(
            ["plan_id", "advisor_id"],
            ["advisor_cases.plan_id", "advisor_cases.advisor_id"],
            name="fk_advisor_decision_assignment",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["plan_id", "plan_version", "action_hash"],
            ["task_plans.id", "task_plans.version", "task_plans.action_hash"],
            name="fk_advisor_decision_plan",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "outcome IN ('cleared','declined','changes_requested')",
            name="advisor_decisions_outcome",
        ),
        sa.CheckConstraint("reason ~ '[^[:space:]]'", name="advisor_decisions_reason"),
    )
    role = op.get_bind().dialect.identifier_preparer.quote(Settings().app_db_user)
    op.execute(f"GRANT SELECT, INSERT ON advisor_cases, advisor_decisions TO {role}")
    op.execute(f"GRANT UPDATE (revoked_at, revoke_request_id) ON advisor_cases TO {role}")


def downgrade():
    if op.get_bind().scalar(sa.text("SELECT EXISTS (SELECT 1 FROM advisor_cases)")):
        raise RuntimeError("Cannot remove recorded advisor cases or decisions.")
    op.drop_table("advisor_decisions")
    op.drop_table("advisor_cases")

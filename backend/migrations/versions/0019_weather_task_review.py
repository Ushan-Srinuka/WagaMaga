"""Persist threshold alerts and bind weather date changes to task history."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

from app.core.config import Settings

revision = "0019_weather_task_review"
down_revision = "0018_live_farm_weather"
branch_labels = None
depends_on = None

PLANS = "task_plans"
DECISIONS = "task_plan_decisions"
ACTION_CHECK = (
    "(action_type = 'create_task' AND target_task_id IS NULL AND target_task_version IS NULL "
    "AND previous_due_date IS NULL AND weather_evidence IS NULL) OR "
    "(action_type = 'reschedule_task' AND target_task_id IS NOT NULL "
    "AND target_task_version IS NOT NULL AND target_task_version > 0 "
    "AND previous_due_date IS NOT NULL AND isfinite(previous_due_date) "
    "AND previous_due_date <> due_date AND weather_evidence IS NOT NULL "
    "AND jsonb_typeof(weather_evidence) = 'object')"
)
DECISION_CHECK = (
    "(outcome = 'accepted' AND task_id IS NOT NULL AND task_version IS NOT NULL) OR "
    "(outcome = 'rejected' AND task_id IS NULL AND task_version IS NULL)"
)


def upgrade():
    op.create_table(
        "weather_alert_rules",
        sa.Column(
            "cultivation_id",
            sa.Uuid(),
            sa.ForeignKey("cultivations.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("threshold_mm", sa.Integer(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "changed_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("threshold_mm BETWEEN 1 AND 1000", name="weather_alert_rules_threshold"),
        sa.CheckConstraint("version > 0", name="weather_alert_rules_version"),
    )
    op.create_table(
        "weather_task_alerts",
        sa.Column(
            "task_id",
            sa.Uuid(),
            sa.ForeignKey("farm_tasks.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("due_date", sa.Date(), primary_key=True),
        sa.Column("rule_version", sa.Integer(), nullable=False),
        sa.Column("forecast_fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("precipitation_mm", sa.Float(), nullable=False),
        sa.CheckConstraint("isfinite(due_date)", name="weather_task_alerts_due_date"),
        sa.CheckConstraint("rule_version > 0", name="weather_task_alerts_rule_version"),
        sa.CheckConstraint(
            "precipitation_mm BETWEEN 0 AND 3000", name="weather_task_alerts_precipitation"
        ),
    )
    op.add_column(PLANS, sa.Column("target_task_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "task_plans_target_task_id_fkey",
        PLANS,
        "farm_tasks",
        ["target_task_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.add_column(PLANS, sa.Column("target_task_version", sa.Integer(), nullable=True))
    op.add_column(PLANS, sa.Column("previous_due_date", sa.Date(), nullable=True))
    op.add_column(PLANS, sa.Column("weather_evidence", JSONB(none_as_null=True), nullable=True))
    op.create_index("ix_task_plans_target_created", PLANS, ["target_task_id", "created_at", "id"])
    op.drop_constraint("task_plans_action", PLANS, type_="check")
    op.create_check_constraint("task_plans_action", PLANS, ACTION_CHECK)

    op.add_column(DECISIONS, sa.Column("task_version", sa.Integer(), nullable=True))
    op.execute("UPDATE task_plan_decisions SET task_version = 1 WHERE task_id IS NOT NULL")
    op.drop_constraint("task_plan_decisions_effect", DECISIONS, type_="check")
    op.create_check_constraint("task_plan_decisions_effect", DECISIONS, DECISION_CHECK)
    op.drop_constraint("task_plan_decisions_task_id_key", DECISIONS, type_="unique")
    op.create_unique_constraint(
        "uq_task_plan_decision_effect", DECISIONS, ["task_id", "task_version"]
    )
    op.create_foreign_key(
        "fk_task_plan_decision_effect",
        DECISIONS,
        "farm_task_events",
        ["task_id", "task_version"],
        ["task_id", "version"],
        ondelete="RESTRICT",
    )

    role = op.get_bind().dialect.identifier_preparer.quote(Settings().app_db_user)
    op.execute(
        f"GRANT SELECT, INSERT ON public.weather_alert_rules, public.weather_task_alerts TO {role}"
    )
    op.execute(
        f"GRANT UPDATE (threshold_mm, version, changed_by, changed_at) "
        f"ON public.weather_alert_rules TO {role}"
    )
    op.execute(
        "GRANT UPDATE (rule_version, forecast_fetched_at, precipitation_mm) "
        f"ON public.weather_task_alerts TO {role}"
    )


def downgrade():
    if op.get_bind().scalar(
        sa.text("SELECT EXISTS (SELECT 1 FROM task_plans WHERE action_type='reschedule_task')")
    ):
        raise RuntimeError("Cannot downgrade while weather reschedule history exists")
    op.drop_constraint("fk_task_plan_decision_effect", DECISIONS, type_="foreignkey")
    op.drop_constraint("uq_task_plan_decision_effect", DECISIONS, type_="unique")
    op.create_unique_constraint("task_plan_decisions_task_id_key", DECISIONS, ["task_id"])
    op.drop_constraint("task_plan_decisions_effect", DECISIONS, type_="check")
    op.create_check_constraint(
        "task_plan_decisions_effect",
        DECISIONS,
        "(outcome = 'accepted' AND task_id IS NOT NULL) OR "
        "(outcome = 'rejected' AND task_id IS NULL)",
    )
    op.drop_column(DECISIONS, "task_version")
    op.drop_constraint("task_plans_action", PLANS, type_="check")
    op.create_check_constraint("task_plans_action", PLANS, "action_type = 'create_task'")
    op.drop_column(PLANS, "weather_evidence")
    op.drop_column(PLANS, "previous_due_date")
    op.drop_column(PLANS, "target_task_version")
    op.drop_index("ix_task_plans_target_created", table_name=PLANS)
    op.drop_constraint("task_plans_target_task_id_fkey", PLANS, type_="foreignkey")
    op.drop_column(PLANS, "target_task_id")
    op.drop_table("weather_task_alerts")
    op.drop_table("weather_alert_rules")

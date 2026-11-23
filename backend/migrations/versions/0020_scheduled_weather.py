"""Remember farm opt-ins, forecast leases and unique weather review notices."""

import sqlalchemy as sa
from alembic import op

from app.core.config import Settings

revision = "0020_scheduled_weather"
down_revision = "0019_weather_task_review"
branch_labels = None
depends_on = None

OLD_EVENTS = "'role_changed','account_reenabled','password_changed','support_updated'"


def upgrade():
    op.create_table(
        "weather_refresh_schedules",
        sa.Column(
            "farm_id", sa.Uuid(), sa.ForeignKey("farms.id", ondelete="RESTRICT"), primary_key=True
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("next_refresh_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_token", sa.Uuid()),
        sa.Column("lease_until", sa.DateTime(timezone=True)),
        sa.CheckConstraint("version > 0", name="weather_refresh_schedules_version"),
        sa.CheckConstraint(
            "(lease_token IS NULL) = (lease_until IS NULL)", name="weather_refresh_schedules_lease"
        ),
    )
    op.create_index(
        "ix_weather_refresh_schedules_due",
        "weather_refresh_schedules",
        ["next_refresh_at", "farm_id"],
        postgresql_where=sa.text("enabled"),
    )
    op.create_table(
        "weather_review_notices",
        sa.Column(
            "cultivation_id",
            sa.Uuid(),
            sa.ForeignKey("cultivations.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("due_date", sa.Date(), primary_key=True),
    )
    op.drop_constraint("notifications_event_type", "notifications", type_="check")
    op.create_check_constraint(
        "notifications_event_type",
        "notifications",
        f"event_type IN ({OLD_EVENTS},'weather_review')",
    )
    role = op.get_bind().dialect.identifier_preparer.quote(Settings().app_db_user)
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON weather_refresh_schedules TO {role}")
    op.execute(f"GRANT SELECT, INSERT ON weather_review_notices TO {role}")


def downgrade():
    saved = op.get_bind().scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM weather_refresh_schedules) "
            "OR EXISTS (SELECT 1 FROM weather_review_notices) "
            "OR EXISTS (SELECT 1 FROM notifications WHERE event_type='weather_review')"
        )
    )
    if saved:
        raise RuntimeError("Cannot remove saved weather schedules or notices.")
    op.drop_constraint("notifications_event_type", "notifications", type_="check")
    op.create_check_constraint(
        "notifications_event_type", "notifications", f"event_type IN ({OLD_EVENTS})"
    )
    op.drop_table("weather_review_notices")
    op.drop_table("weather_refresh_schedules")

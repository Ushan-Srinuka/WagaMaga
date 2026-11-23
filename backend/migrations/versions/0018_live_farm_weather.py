"""Store the latest successful live forecast for an owned farm."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

from app.core.config import Settings

revision = "0018_live_farm_weather"
down_revision = "0017_suggested_task_plans"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "farm_forecasts",
        sa.Column(
            "farm_id", sa.Uuid(), sa.ForeignKey("farms.id", ondelete="RESTRICT"), primary_key=True
        ),
        sa.Column("latitude", sa.Numeric(5, 2), nullable=False),
        sa.Column("longitude", sa.Numeric(5, 2), nullable=False),
        sa.Column("timezone", sa.String(100), nullable=False),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("days", JSONB(), nullable=False),
        sa.CheckConstraint("latitude BETWEEN -90 AND 90", name="farm_forecasts_latitude"),
        sa.CheckConstraint("longitude BETWEEN -180 AND 180", name="farm_forecasts_longitude"),
        sa.CheckConstraint("provider = 'open-meteo'", name="farm_forecasts_provider"),
        sa.CheckConstraint("isfinite(fetched_at)", name="farm_forecasts_fetched_at"),
        sa.CheckConstraint(
            "CASE WHEN jsonb_typeof(days) = 'array' "
            "THEN jsonb_array_length(days) = 3 ELSE false END",
            name="farm_forecasts_days",
        ),
    )
    role = op.get_bind().dialect.identifier_preparer.quote(Settings().app_db_user)
    op.execute(f"GRANT SELECT, INSERT ON public.farm_forecasts TO {role}")
    op.execute(
        "GRANT UPDATE (latitude, longitude, timezone, provider, fetched_at, days) "
        f"ON public.farm_forecasts TO {role}"
    )


def downgrade():
    op.drop_table("farm_forecasts")

"""Add optional farmer-reported soil moisture to field observations."""

import sqlalchemy as sa
from alembic import op

revision = "0021_guidance_observations"
down_revision = "0020_scheduled_weather"
branch_labels = None
depends_on = None

SNAPSHOT = "observation_revisions_snapshot"
KEYS = (
    "'cultivation_id','recorded_by','observed_at','notes','id','version','created_at','updated_at'"
)
REQUIRED = f"jsonb_typeof(snapshot) = 'object' AND snapshot ?& ARRAY[{KEYS}]"
IDENTITY = (
    "(snapshot->>'id' = observation_id::text) IS TRUE "
    "AND (snapshot->>'version' = version::text) IS TRUE"
)


def upgrade():
    op.add_column("farm_observations", sa.Column("soil_moisture", sa.String(12)))
    op.create_check_constraint(
        "farm_observations_soil_moisture",
        "farm_observations",
        "soil_moisture IN ('dry','moist','waterlogged')",
    )
    op.drop_constraint(SNAPSHOT, "observation_revisions", type_="check")
    op.create_check_constraint(
        SNAPSHOT,
        "observation_revisions",
        f"{REQUIRED} AND snapshot - ARRAY[{KEYS},'soil_moisture'] = '{{}}'::jsonb AND {IDENTITY} "
        "AND (NOT (snapshot ? 'soil_moisture') OR (snapshot->>'soil_moisture' "
        "IN ('dry','moist','waterlogged')) IS TRUE)",
    )


def downgrade():
    saved = op.get_bind().scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM farm_observations WHERE soil_moisture IS NOT NULL) "
            "OR EXISTS (SELECT 1 FROM observation_revisions "
            "WHERE snapshot->>'soil_moisture' IS NOT NULL)"
        )
    )
    if saved:
        raise RuntimeError("Cannot remove recorded soil moisture observation data.")
    op.drop_constraint(SNAPSHOT, "observation_revisions", type_="check")
    op.create_check_constraint(
        SNAPSHOT,
        "observation_revisions",
        f"{REQUIRED} AND snapshot - ARRAY[{KEYS}] = '{{}}'::jsonb AND {IDENTITY}",
    )
    op.drop_column("farm_observations", "soil_moisture")

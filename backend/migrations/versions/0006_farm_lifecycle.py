"""Owner restore and append-only farm workspace deletion evidence."""

import sqlalchemy as sa
from alembic import op

from app.core.config import Settings

revision = "0006_farm_lifecycle"
down_revision = "0005_farm_records"
branch_labels = None
depends_on = None


def audit_check(farm_operations):
    return (
        f"(operation IN ({farm_operations}) AND cultivation_id IS NULL "
        "AND observation_id IS NULL) OR "
        "(operation IN ('cultivation_created','cultivation_updated',"
        "'cultivation_archived','stage_confirmed') "
        "AND cultivation_id IS NOT NULL AND observation_id IS NULL) OR "
        "(operation IN ('observation_created','observation_updated') "
        "AND cultivation_id IS NOT NULL AND observation_id IS NOT NULL)"
    )


def upgrade() -> None:
    op.create_table(
        "farm_deletions",
        sa.Column(
            "farm_id", sa.Uuid(), sa.ForeignKey("farms.id", ondelete="RESTRICT"), primary_key=True
        ),
        sa.Column(
            "deleted_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column(
            "deleted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("entity_version", sa.Integer(), nullable=False),
        sa.CheckConstraint("entity_version > 0", name="farm_deletions_version"),
        sa.CheckConstraint("isfinite(deleted_at)", name="farm_deletions_time"),
    )
    op.drop_constraint("farm_audit_operation_parent", "farm_audit_events", type_="check")
    op.create_check_constraint(
        "farm_audit_operation_parent",
        "farm_audit_events",
        audit_check("'farm_created','farm_updated','farm_archived','farm_restored','farm_deleted'"),
    )
    role = op.get_bind().dialect.identifier_preparer.quote(Settings().app_db_user)
    op.execute(f"GRANT SELECT, INSERT ON TABLE public.farm_deletions TO {role}")


def downgrade() -> None:
    # An ordinary schema downgrade must not resurrect removed records or erase evidence.
    if op.get_bind().scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM farm_deletions) OR EXISTS "
            "(SELECT 1 FROM farm_audit_events WHERE operation IN ('farm_restored','farm_deleted'))"
        )
    ):
        raise RuntimeError("Cannot downgrade while farm lifecycle evidence exists")
    op.drop_table("farm_deletions")
    op.drop_constraint("farm_audit_operation_parent", "farm_audit_events", type_="check")
    op.create_check_constraint(
        "farm_audit_operation_parent",
        "farm_audit_events",
        audit_check("'farm_created','farm_updated','farm_archived'"),
    )

"""Store synthetic guide versions and their review decisions."""

import sqlalchemy as sa
from alembic import op

from app.core.config import Settings

revision = "0008_knowledge_demo"
down_revision = "0007_support"
branch_labels = None
depends_on = None

STATES = "status IN ('draft','reviewed','published','withdrawn')"


def stamp():
    return sa.Column(
        "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )


def upgrade():
    op.create_table(
        "knowledge_demo_versions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        stamp(),
        sa.CheckConstraint(STATES, name="knowledge_demo_status"),
        sa.CheckConstraint("revision BETWEEN 1 AND 4", name="knowledge_demo_revision"),
    )
    op.create_table(
        "knowledge_demo_decisions",
        sa.Column(
            "version_id",
            sa.Uuid(),
            sa.ForeignKey("knowledge_demo_versions.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("revision", sa.Integer(), primary_key=True),
        sa.Column(
            "actor_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("request_id", sa.String(36), nullable=False),
        stamp(),
        sa.CheckConstraint(STATES, name="knowledge_demo_decision_status"),
    )
    role = op.get_bind().dialect.identifier_preparer.quote(Settings().app_db_user)
    op.execute(
        f"GRANT SELECT, INSERT ON TABLE public.knowledge_demo_versions, "
        f"public.knowledge_demo_decisions TO {role}"
    )
    op.execute(f"GRANT UPDATE (status, revision) ON TABLE public.knowledge_demo_versions TO {role}")


def downgrade():
    if op.get_bind().scalar(sa.text("SELECT EXISTS (SELECT 1 FROM knowledge_demo_versions)")):
        raise RuntimeError("Cannot downgrade while knowledge demo review history exists")
    op.drop_table("knowledge_demo_decisions")
    op.drop_table("knowledge_demo_versions")

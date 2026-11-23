"""Store reviewed quotations and append-only evaluation checks."""

import sqlalchemy as sa
from alembic import op

from app.core.config import Settings

revision = "0012_chilli_pilot"
down_revision = "0011_knowledge_eval"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "knowledge_evaluation_decisions",
        sa.Column("approved_excerpt", sa.String(500), nullable=False, server_default=""),
    )
    op.create_table(
        "knowledge_evaluation_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("case_id", sa.String(5), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("detail", sa.String(80), nullable=False),
        sa.Column("model", sa.String(77), nullable=False),
        sa.Column(
            "actor_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_knowledge_run_case_fingerprint", "knowledge_evaluation_runs", ["case_id", "fingerprint"]
    )
    role = op.get_bind().dialect.identifier_preparer.quote(Settings().app_db_user)
    op.execute(f"GRANT SELECT, INSERT ON TABLE public.knowledge_evaluation_runs TO {role}")


def downgrade():
    if op.get_bind().scalar(
        sa.text("""
        SELECT EXISTS (SELECT 1 FROM knowledge_evaluation_runs)
            OR EXISTS (SELECT 1 FROM knowledge_evaluation_decisions WHERE approved_excerpt <> '')
    """)
    ):
        raise RuntimeError("Cannot downgrade while pilot evaluation evidence exists")
    op.drop_table("knowledge_evaluation_runs")
    op.drop_column("knowledge_evaluation_decisions", "approved_excerpt")

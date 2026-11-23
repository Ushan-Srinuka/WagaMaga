"""Retain administrator evidence review decisions for the evaluation suite."""

import sqlalchemy as sa
from alembic import op

from app.core.config import Settings

revision = "0011_knowledge_eval"
down_revision = "0010_discard_pdf"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "knowledge_evaluation_decisions",
        sa.Column("case_id", sa.String(5), primary_key=True),
        sa.Column("revision", sa.Integer(), primary_key=True),
        sa.Column(
            "version_id",
            sa.Uuid(),
            sa.ForeignKey("knowledge_source_pdfs.version_id", ondelete="RESTRICT"),
        ),
        sa.Column("page_number", sa.Integer()),
        sa.Column("outcome", sa.String(12), nullable=False),
        sa.Column("note", sa.String(500), nullable=False),
        sa.Column(
            "actor_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("request_id", sa.String(36), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("revision > 0", name="knowledge_eval_revision"),
        sa.CheckConstraint(
            "(outcome = 'missing' AND version_id IS NULL AND page_number IS NULL) OR "
            "(outcome IN ('suitable','out_of_scope') AND version_id IS NOT NULL "
            "AND page_number IS NOT NULL AND page_number BETWEEN 1 AND 20)",
            name="knowledge_eval_evidence",
        ),
    )
    role = op.get_bind().dialect.identifier_preparer.quote(Settings().app_db_user)
    op.execute(f"GRANT SELECT, INSERT ON TABLE public.knowledge_evaluation_decisions TO {role}")


def downgrade():
    statement = sa.text("SELECT EXISTS (SELECT 1 FROM knowledge_evaluation_decisions)")
    if op.get_bind().scalar(statement):
        raise RuntimeError("Cannot downgrade while evaluation decisions exist")
    op.drop_table("knowledge_evaluation_decisions")

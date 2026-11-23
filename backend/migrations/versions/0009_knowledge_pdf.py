"""Add private PDF originals and durable extraction state."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

from app.core.config import Settings

revision = "0009_knowledge_pdf"
down_revision = "0008_knowledge_demo"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "knowledge_source_pdfs",
        sa.Column(
            "version_id",
            sa.Uuid(),
            sa.ForeignKey("knowledge_demo_versions.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("original", sa.LargeBinary(), nullable=False),
        sa.Column("state", sa.String(8), nullable=False),
        sa.Column("pages", JSONB(), nullable=True),
        sa.Column("error", sa.String(24), nullable=True),
        sa.CheckConstraint(
            "octet_length(original) BETWEEN 1 AND 2097152", name="knowledge_pdf_size"
        ),
        sa.CheckConstraint(
            "(state = 'queued' AND pages IS NULL AND error IS NULL) OR "
            "(state = 'ready' AND pages IS NOT NULL AND error IS NULL) OR "
            "(state = 'failed' AND pages IS NULL AND error IS NOT NULL)",
            name="knowledge_pdf_state",
        ),
    )
    op.create_index("ix_knowledge_pdf_queue", "knowledge_source_pdfs", ["state", "version_id"])
    role = op.get_bind().dialect.identifier_preparer.quote(Settings().app_db_user)
    op.execute(f"GRANT SELECT, INSERT ON TABLE public.knowledge_source_pdfs TO {role}")
    op.execute(
        f"GRANT UPDATE (state, pages, error) ON TABLE public.knowledge_source_pdfs TO {role}"
    )
    op.execute("""
        CREATE FUNCTION public.knowledge_pdf_finish_once() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF OLD.state <> 'queued' OR NEW.state NOT IN ('ready', 'failed') THEN
                RAISE EXCEPTION 'PDF processing result is immutable' USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END; $$
    """)
    op.execute("REVOKE ALL ON FUNCTION public.knowledge_pdf_finish_once() FROM PUBLIC")
    op.execute("""
        CREATE TRIGGER knowledge_pdf_finish_once BEFORE UPDATE ON public.knowledge_source_pdfs
        FOR EACH ROW EXECUTE FUNCTION public.knowledge_pdf_finish_once()
    """)


def downgrade():
    if op.get_bind().scalar(sa.text("SELECT EXISTS (SELECT 1 FROM knowledge_source_pdfs)")):
        raise RuntimeError("Cannot downgrade while uploaded PDF versions exist")
    op.drop_table("knowledge_source_pdfs")
    op.execute("DROP FUNCTION public.knowledge_pdf_finish_once()")

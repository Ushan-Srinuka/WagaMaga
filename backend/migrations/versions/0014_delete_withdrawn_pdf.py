"""Allow administrators to delete withdrawn PDF files and extracted text."""

import sqlalchemy as sa
from alembic import op

from app.core.config import Settings

revision = "0014_delete_withdrawn_pdf"
down_revision = "0013_knowledge_pdf_limits"
branch_labels = None
depends_on = None


def upgrade():
    role = op.get_bind().dialect.identifier_preparer.quote(Settings().app_db_user)
    for table, constraint in (
        ("knowledge_demo_versions", "knowledge_demo_status"),
        ("knowledge_demo_decisions", "knowledge_demo_decision_status"),
    ):
        op.drop_constraint(constraint, table, type_="check")
        op.create_check_constraint(
            constraint,
            table,
            "status IN ('draft','reviewed','published','withdrawn','discarded','deleted')",
        )
    op.drop_constraint("knowledge_demo_revision", "knowledge_demo_versions", type_="check")
    op.create_check_constraint(
        "knowledge_demo_revision", "knowledge_demo_versions", "revision BETWEEN 1 AND 5"
    )

    op.drop_constraint("knowledge_pdf_size", "knowledge_source_pdfs", type_="check")
    op.alter_column("knowledge_source_pdfs", "original", nullable=True)
    op.create_check_constraint(
        "knowledge_pdf_size",
        "knowledge_source_pdfs",
        "original IS NULL OR octet_length(original) BETWEEN 1 AND 6291456",
    )
    op.drop_constraint("knowledge_pdf_state", "knowledge_source_pdfs", type_="check")
    op.create_check_constraint(
        "knowledge_pdf_state",
        "knowledge_source_pdfs",
        "(state = 'queued' AND original IS NOT NULL AND pages IS NULL AND error IS NULL) OR "
        "(state = 'ready' AND original IS NOT NULL AND pages IS NOT NULL AND error IS NULL) OR "
        "(state = 'failed' AND original IS NOT NULL AND pages IS NULL AND error IS NOT NULL) OR "
        "(state = 'deleted' AND original IS NULL AND pages IS NULL AND error IS NULL)",
    )
    op.execute(
        f"GRANT UPDATE (original, state, pages, error) "
        f"ON TABLE public.knowledge_source_pdfs TO {role}"
    )
    op.execute("DROP TRIGGER knowledge_pdf_finish_once ON public.knowledge_source_pdfs")
    op.execute("DROP FUNCTION public.knowledge_pdf_finish_once()")
    op.execute("""
        CREATE FUNCTION public.knowledge_pdf_finish_once() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF OLD.state = 'queued' AND NEW.state IN ('ready', 'failed')
                AND NEW.original IS NOT DISTINCT FROM OLD.original THEN
                RETURN NEW;
            END IF;
            IF OLD.state IN ('ready', 'failed') AND NEW.state = 'deleted'
                AND NEW.original IS NULL AND NEW.pages IS NULL AND NEW.error IS NULL
                AND EXISTS (
                    SELECT 1 FROM public.knowledge_demo_versions
                    WHERE id = NEW.version_id AND status = 'deleted'
                ) THEN
                RETURN NEW;
            END IF;
            RAISE EXCEPTION 'PDF processing result is immutable' USING ERRCODE = '23514';
        END; $$
    """)
    op.execute("REVOKE ALL ON FUNCTION public.knowledge_pdf_finish_once() FROM PUBLIC")
    op.execute("""
        CREATE TRIGGER knowledge_pdf_finish_once BEFORE UPDATE ON public.knowledge_source_pdfs
        FOR EACH ROW EXECUTE FUNCTION public.knowledge_pdf_finish_once()
    """)


def downgrade():
    has_deleted = op.get_bind().scalar(
        sa.text("SELECT EXISTS (SELECT 1 FROM knowledge_demo_versions WHERE status='deleted')")
    )
    if has_deleted:
        raise RuntimeError("Cannot downgrade while withdrawn PDF deletion evidence exists")
    role = op.get_bind().dialect.identifier_preparer.quote(Settings().app_db_user)
    op.execute("DROP TRIGGER knowledge_pdf_finish_once ON public.knowledge_source_pdfs")
    op.execute("DROP FUNCTION public.knowledge_pdf_finish_once()")
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
    op.execute(f"REVOKE UPDATE (original) ON TABLE public.knowledge_source_pdfs FROM {role}")
    op.drop_constraint("knowledge_pdf_state", "knowledge_source_pdfs", type_="check")
    op.create_check_constraint(
        "knowledge_pdf_state",
        "knowledge_source_pdfs",
        "(state = 'queued' AND pages IS NULL AND error IS NULL) OR "
        "(state = 'ready' AND pages IS NOT NULL AND error IS NULL) OR "
        "(state = 'failed' AND pages IS NULL AND error IS NOT NULL)",
    )
    op.drop_constraint("knowledge_pdf_size", "knowledge_source_pdfs", type_="check")
    op.create_check_constraint(
        "knowledge_pdf_size",
        "knowledge_source_pdfs",
        "octet_length(original) BETWEEN 1 AND 6291456",
    )
    op.alter_column("knowledge_source_pdfs", "original", nullable=False)
    op.drop_constraint("knowledge_demo_revision", "knowledge_demo_versions", type_="check")
    op.create_check_constraint(
        "knowledge_demo_revision", "knowledge_demo_versions", "revision BETWEEN 1 AND 4"
    )
    for table, constraint in (
        ("knowledge_demo_versions", "knowledge_demo_status"),
        ("knowledge_demo_decisions", "knowledge_demo_decision_status"),
    ):
        op.drop_constraint(constraint, table, type_="check")
        op.create_check_constraint(
            constraint,
            table,
            "status IN ('draft','reviewed','published','withdrawn','discarded')",
        )

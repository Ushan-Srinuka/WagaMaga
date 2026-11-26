"""Track screened PDF intake and append-only source reviews."""

from importlib import import_module

import sqlalchemy as sa
from alembic import op

from app.core.config import Settings

revision = "0029_screened_knowledge"
down_revision = "0028_chilli_jobs"
branch_labels = None
depends_on = None


def pdf_state_constraint(screened):
    failed_original = (
        "((error <> 'scan_rejected' AND original IS NOT NULL) OR "
        "(error = 'scan_rejected' AND screening_required AND original IS NULL))"
        if screened
        else "original IS NOT NULL"
    )
    op.drop_constraint("knowledge_pdf_state", "knowledge_source_pdfs", type_="check")
    op.create_check_constraint(
        "knowledge_pdf_state",
        "knowledge_source_pdfs",
        "(state = 'queued' AND original IS NOT NULL AND pages IS NULL AND error IS NULL) OR "
        "(state = 'ready' AND original IS NOT NULL AND pages IS NOT NULL AND error IS NULL) OR "
        f"(state = 'failed' AND pages IS NULL AND error IS NOT NULL AND {failed_original}) OR "
        "(state = 'deleted' AND original IS NULL AND pages IS NULL AND error IS NULL)",
    )


def upgrade():
    role = op.get_bind().dialect.identifier_preparer.quote(Settings().app_db_user)
    op.add_column(
        "knowledge_source_pdfs",
        sa.Column("screening_required", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    pdf_state_constraint(True)
    op.create_table(
        "knowledge_source_review_events",
        sa.Column(
            "version_id",
            sa.Uuid(),
            sa.ForeignKey("knowledge_source_pdfs.version_id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("sequence", sa.Integer(), primary_key=True),
        sa.Column(
            "advisor_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column(
            "actor_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("event", sa.String(20), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("request_id", sa.String(36), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("sequence > 0", name="knowledge_source_review_sequence"),
        sa.CheckConstraint(
            "event IN ('assigned','revoked','approved','changes_requested')",
            name="knowledge_source_review_event",
        ),
    )
    op.create_index(
        "ix_knowledge_source_review_advisor",
        "knowledge_source_review_events",
        ["advisor_id", "version_id"],
    )
    op.execute(f"GRANT SELECT, INSERT ON TABLE knowledge_source_review_events TO {role}")
    op.execute("""
        CREATE OR REPLACE FUNCTION public.knowledge_pdf_finish_once()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.screening_required IS DISTINCT FROM OLD.screening_required THEN
                RAISE EXCEPTION 'PDF screening requirement is immutable' USING ERRCODE = '23514';
            END IF;
            IF OLD.state = 'queued' AND NEW.state IN ('ready', 'failed')
                AND ((NEW.error IS DISTINCT FROM 'scan_rejected'
                    AND NEW.original IS NOT DISTINCT FROM OLD.original)
                    OR (OLD.screening_required AND NEW.state = 'failed'
                        AND NEW.error = 'scan_rejected' AND NEW.original IS NULL))
                AND NEW.retry_count = OLD.retry_count THEN
                RETURN NEW;
            END IF;
            IF OLD.state = 'failed' AND NEW.state = 'queued'
                AND OLD.error IN ('timed_out', 'parser_stopped', 'scan_unavailable')
                AND NEW.original IS NOT DISTINCT FROM OLD.original
                AND NEW.retry_count = OLD.retry_count + 1 AND NEW.retry_count <= 3
                AND EXISTS (
                    SELECT 1 FROM public.knowledge_demo_versions
                    WHERE id = NEW.version_id AND status = 'draft'
                ) THEN
                RETURN NEW;
            END IF;
            IF OLD.state IN ('ready', 'failed') AND NEW.state = 'deleted'
                AND NEW.original IS NULL AND NEW.pages IS NULL AND NEW.error IS NULL
                AND NEW.retry_count = OLD.retry_count
                AND EXISTS (
                    SELECT 1 FROM public.knowledge_demo_versions
                    WHERE id = NEW.version_id AND status = 'deleted'
                ) THEN
                RETURN NEW;
            END IF;
            RAISE EXCEPTION 'PDF processing result is immutable' USING ERRCODE = '23514';
        END; $$
    """)


def downgrade():
    if op.get_bind().scalar(
        sa.text("""
        SELECT EXISTS (SELECT 1 FROM knowledge_source_review_events)
            OR EXISTS (SELECT 1 FROM knowledge_source_pdfs WHERE screening_required)
    """)
    ):
        raise RuntimeError("Cannot remove saved source reviews or screened PDFs.")
    import_module("migrations.versions.0028_chilli_jobs").pdf_transition(True)
    op.drop_table("knowledge_source_review_events")
    pdf_state_constraint(False)
    op.drop_column("knowledge_source_pdfs", "screening_required")

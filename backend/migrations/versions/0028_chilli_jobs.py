"""Persist fenced Chilli AI jobs."""

import sqlalchemy as sa
from alembic import op

from app.core.config import Settings

revision = "0028_chilli_jobs"
down_revision = "0027_private_chilli_chats"
branch_labels = None
depends_on = None


def pdf_transition(retry):
    retry_clause = (
        """
            IF OLD.state = 'failed' AND NEW.state = 'queued'
                AND OLD.error IN ('timed_out', 'parser_stopped')
                AND NEW.original IS NOT DISTINCT FROM OLD.original
                AND NEW.retry_count = OLD.retry_count + 1 AND NEW.retry_count <= 3
                AND EXISTS (
                    SELECT 1 FROM public.knowledge_demo_versions
                    WHERE id = NEW.version_id AND status = 'draft'
                ) THEN
                RETURN NEW;
            END IF;
    """
        if retry
        else ""
    )
    unchanged_retries = "AND NEW.retry_count = OLD.retry_count" if retry else ""
    op.execute(f"""
        CREATE OR REPLACE FUNCTION public.knowledge_pdf_finish_once()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF OLD.state = 'queued' AND NEW.state IN ('ready', 'failed')
                AND NEW.original IS NOT DISTINCT FROM OLD.original {unchanged_retries} THEN
                RETURN NEW;
            END IF;
            {retry_clause}
            IF OLD.state IN ('ready', 'failed') AND NEW.state = 'deleted'
                AND NEW.original IS NULL AND NEW.pages IS NULL AND NEW.error IS NULL
                {unchanged_retries}
                AND EXISTS (
                    SELECT 1 FROM public.knowledge_demo_versions
                    WHERE id = NEW.version_id AND status = 'deleted'
                ) THEN
                RETURN NEW;
            END IF;
            RAISE EXCEPTION 'PDF processing result is immutable' USING ERRCODE = '23514';
        END; $$
    """)


def upgrade():
    op.create_table(
        "chilli_jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "chat_id",
            sa.Uuid(),
            sa.ForeignKey("chilli_chats.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("question", sa.String(240), nullable=False),
        sa.Column("use_gemini", sa.Boolean(), nullable=False),
        sa.Column("state", sa.String(12), nullable=False),
        sa.Column("failure_code", sa.String(30)),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("lease_token", sa.Uuid()),
        sa.Column("lease_until", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "state IN ('queued','running','succeeded','failed')", name="chilli_jobs_state"
        ),
        sa.CheckConstraint(
            "attempts BETWEEN 0 AND 3 AND revision BETWEEN 0 AND 19", name="chilli_jobs_attempts"
        ),
        sa.CheckConstraint(
            "(state = 'running' AND lease_token IS NOT NULL AND lease_until IS NOT NULL) OR "
            "(state <> 'running' AND lease_token IS NULL AND lease_until IS NULL)",
            name="chilli_jobs_lease",
        ),
    )
    op.create_index(
        "uq_chilli_job_active_revision",
        "chilli_jobs",
        ["chat_id", "revision"],
        unique=True,
        postgresql_where=sa.text("state IN ('queued','running','succeeded')"),
    )
    op.create_index("ix_chilli_jobs_queue", "chilli_jobs", ["state", "lease_until", "created_at"])
    role = op.get_bind().dialect.identifier_preparer.quote(Settings().app_db_user)
    op.add_column(
        "knowledge_source_pdfs",
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.execute(f"GRANT UPDATE (retry_count) ON TABLE knowledge_source_pdfs TO {role}")
    pdf_transition(True)
    op.execute(f"GRANT SELECT, INSERT ON TABLE chilli_jobs TO {role}")
    op.execute(
        "GRANT UPDATE (session_id, state, failure_code, attempts, lease_token, lease_until) "
        f"ON TABLE chilli_jobs TO {role}"
    )


def downgrade():
    if op.get_bind().scalar(sa.text("SELECT EXISTS (SELECT 1 FROM chilli_jobs)")):
        raise RuntimeError("Cannot remove saved Chilli AI jobs.")
    if op.get_bind().scalar(
        sa.text("SELECT EXISTS (SELECT 1 FROM knowledge_source_pdfs WHERE retry_count > 0)")
    ):
        raise RuntimeError("Cannot remove saved PDF retry counts.")
    pdf_transition(False)
    op.drop_column("knowledge_source_pdfs", "retry_count")
    op.drop_table("chilli_jobs")

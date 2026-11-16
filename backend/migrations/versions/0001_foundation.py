"""Enable pgvector and allow the application to read migration readiness."""

from alembic import op

from app.core.config import Settings

revision = "0001_foundation"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    role = op.get_bind().dialect.identifier_preparer.quote(Settings().app_db_user)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(f"GRANT SELECT ON TABLE public.alembic_version TO {role}")


def downgrade() -> None:
    role = op.get_bind().dialect.identifier_preparer.quote(Settings().app_db_user)
    op.execute(f"REVOKE SELECT ON TABLE public.alembic_version FROM {role}")
    op.execute("DROP EXTENSION vector")

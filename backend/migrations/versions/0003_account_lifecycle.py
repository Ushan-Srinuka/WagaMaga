"""Support privacy-preserving account removal."""

import sqlalchemy as sa
from alembic import op

revision = "0003_account_lifecycle"
down_revision = "0002_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("deleted_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("users", "deleted_at")

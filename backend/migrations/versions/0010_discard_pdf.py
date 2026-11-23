"""Allow audited removal of unpublished knowledge PDFs."""

import sqlalchemy as sa
from alembic import op

revision = "0010_discard_pdf"
down_revision = "0009_knowledge_pdf"
branch_labels = None
depends_on = None

TABLES = (
    ("knowledge_demo_versions", "knowledge_demo_status"),
    ("knowledge_demo_decisions", "knowledge_demo_decision_status"),
)


def change_constraints(states):
    for table, constraint in TABLES:
        op.drop_constraint(constraint, table, type_="check")
        op.create_check_constraint(constraint, table, f"status IN ({states})")


def upgrade():
    change_constraints("'draft','reviewed','published','withdrawn','discarded'")


def downgrade():
    if op.get_bind().scalar(
        sa.text("SELECT EXISTS (SELECT 1 FROM knowledge_demo_decisions WHERE status='discarded')")
    ):
        raise RuntimeError("Cannot downgrade while PDF removal evidence exists")
    change_constraints("'draft','reviewed','published','withdrawn'")

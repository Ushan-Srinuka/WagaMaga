"""Allow evidence reviews for the full PDF and retain reviewed translations."""

import sqlalchemy as sa
from alembic import op

revision = "0015_knowledge_translations"
down_revision = "0014_delete_withdrawn_pdf"
branch_labels = None
depends_on = None

TABLE = "knowledge_evaluation_decisions"


def set_page_limit(limit):
    op.drop_constraint("knowledge_eval_evidence", TABLE, type_="check")
    op.create_check_constraint(
        "knowledge_eval_evidence",
        TABLE,
        "(outcome = 'missing' AND version_id IS NULL AND page_number IS NULL) OR "
        "(outcome IN ('suitable','out_of_scope') AND version_id IS NOT NULL "
        f"AND page_number IS NOT NULL AND page_number BETWEEN 1 AND {limit})",
    )


def upgrade():
    set_page_limit(100)
    op.add_column(
        TABLE, sa.Column("english_translation", sa.String(500), server_default="", nullable=False)
    )
    op.create_check_constraint(
        "knowledge_eval_translation",
        TABLE,
        "english_translation = '' OR (outcome = 'suitable' AND approved_excerpt <> '')",
    )


def downgrade():
    if op.get_bind().scalar(
        sa.text("""
        SELECT EXISTS (SELECT 1 FROM knowledge_evaluation_decisions
          WHERE page_number > 20 OR english_translation <> '')
    """)
    ):
        raise RuntimeError("Cannot downgrade while extended PDF reviews exist")
    op.drop_constraint("knowledge_eval_translation", TABLE, type_="check")
    op.drop_column(TABLE, "english_translation")
    set_page_limit(20)

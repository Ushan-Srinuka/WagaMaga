"""Allow bounded full-length agriculture PDFs."""

import sqlalchemy as sa
from alembic import op

revision = "0013_knowledge_pdf_limits"
down_revision = "0012_chilli_pilot"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("knowledge_pdf_size", "knowledge_source_pdfs", type_="check")
    op.create_check_constraint(
        "knowledge_pdf_size",
        "knowledge_source_pdfs",
        "octet_length(original) BETWEEN 1 AND 6291456",
    )


def downgrade():
    has_large_pdf = op.get_bind().scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM knowledge_source_pdfs "
            "WHERE octet_length(original) > 2097152)"
        )
    )
    if has_large_pdf:
        raise RuntimeError("Cannot downgrade while PDFs exceed the prior 2 MiB limit")
    op.drop_constraint("knowledge_pdf_size", "knowledge_source_pdfs", type_="check")
    op.create_check_constraint(
        "knowledge_pdf_size",
        "knowledge_source_pdfs",
        "octet_length(original) BETWEEN 1 AND 2097152",
    )

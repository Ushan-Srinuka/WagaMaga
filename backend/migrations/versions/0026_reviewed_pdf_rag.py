"""Store reviewed PDF metadata, immutable passages and versioned vectors."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

from app.core.config import Settings

revision = "0026_reviewed_pdf_rag"
down_revision = "0025_knowledge_replacements"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("knowledge_demo_versions", sa.Column("rag_metadata", JSONB()))
    op.execute("""
        CREATE TABLE knowledge_passages (
            id uuid PRIMARY KEY,
            version_id uuid NOT NULL REFERENCES knowledge_demo_versions(id) ON DELETE RESTRICT,
            page_number integer NOT NULL CHECK (page_number BETWEEN 1 AND 100),
            ordinal integer NOT NULL CHECK (ordinal > 0),
            body text NOT NULL CHECK (char_length(body) BETWEEN 1 AND 900),
            embedding vector(768),
            embedding_model text,
            index_version text,
            CHECK ((embedding IS NULL AND embedding_model IS NULL AND index_version IS NULL)
                OR (embedding IS NOT NULL AND embedding_model IS NOT NULL
                    AND index_version IS NOT NULL)),
            UNIQUE (version_id, page_number, ordinal)
        )
    """)
    op.execute("""
        CREATE INDEX ix_knowledge_passages_fts ON knowledge_passages
        USING gin (to_tsvector('simple', body))
    """)
    role = op.get_bind().dialect.identifier_preparer.quote(Settings().app_db_user)
    op.execute(f"GRANT SELECT, INSERT, DELETE ON TABLE knowledge_passages TO {role}")
    op.execute(
        f"GRANT UPDATE (embedding, embedding_model, index_version) ON knowledge_passages TO {role}"
    )


def downgrade():
    saved = op.get_bind().scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM knowledge_demo_versions WHERE rag_metadata IS NOT NULL)"
        )
    )
    if saved:
        raise RuntimeError("Cannot remove saved reviewed PDF metadata.")
    op.drop_table("knowledge_passages")
    op.drop_column("knowledge_demo_versions", "rag_metadata")

"""Persist owner-only conversations independently of farm decision evidence."""

import sqlalchemy as sa
from alembic import op

from app.core.config import Settings

revision = "0027_private_chilli_chats"
down_revision = "0026_reviewed_pdf_rag"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "chilli_chats",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "owner_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column(
            "cultivation_id",
            sa.Uuid(),
            sa.ForeignKey("cultivations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_chilli_chats_owner_cultivation", "chilli_chats", ["owner_id", "cultivation_id"]
    )
    op.create_table(
        "chilli_chat_turns",
        sa.Column(
            "chat_id",
            sa.Uuid(),
            sa.ForeignKey("chilli_chats.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("ordinal", sa.Integer(), primary_key=True),
        sa.Column("question", sa.String(240), nullable=False),
        sa.Column("outcome", sa.String(20), nullable=False),
        sa.Column("quote", sa.String(500)),
        sa.Column("passage_id", sa.Uuid()),
        sa.CheckConstraint("ordinal BETWEEN 1 AND 20", name="chilli_chat_turn_ordinal"),
        sa.CheckConstraint(
            "(outcome = 'answered' AND quote IS NOT NULL AND passage_id IS NOT NULL) OR "
            "(outcome IN ('no_evidence','clarify','unavailable') "
            "AND quote IS NULL AND passage_id IS NULL)",
            name="chilli_chat_turn_evidence",
        ),
    )
    role = op.get_bind().dialect.identifier_preparer.quote(Settings().app_db_user)
    op.execute(f"GRANT SELECT, INSERT, DELETE ON TABLE chilli_chats TO {role}")
    op.execute(f"GRANT UPDATE (revision) ON TABLE chilli_chats TO {role}")
    op.execute(f"GRANT SELECT, INSERT ON TABLE chilli_chat_turns TO {role}")


def downgrade():
    if op.get_bind().scalar(sa.text("SELECT EXISTS (SELECT 1 FROM chilli_chats)")):
        raise RuntimeError("Cannot remove saved chilli conversations.")
    op.drop_table("chilli_chat_turns")
    op.drop_table("chilli_chats")

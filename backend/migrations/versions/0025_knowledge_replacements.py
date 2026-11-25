"""Link immutable uploaded PDF replacements to their previous published version."""

import sqlalchemy as sa
from alembic import op

revision = "0025_knowledge_replacements"
down_revision = "0024_task_reminders"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("knowledge_demo_versions", sa.Column("replaces_version_id", sa.Uuid()))
    op.create_foreign_key(
        "fk_knowledge_replacement",
        "knowledge_demo_versions",
        "knowledge_demo_versions",
        ["replaces_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "uq_knowledge_active_replacement",
        "knowledge_demo_versions",
        ["replaces_version_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('draft','reviewed','published')"),
    )


def downgrade():
    if op.get_bind().scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM knowledge_demo_versions "
            "WHERE replaces_version_id IS NOT NULL)"
        )
    ):
        raise RuntimeError("Cannot remove saved knowledge replacement history.")
    op.drop_index("uq_knowledge_active_replacement", table_name="knowledge_demo_versions")
    op.drop_constraint("fk_knowledge_replacement", "knowledge_demo_versions", type_="foreignkey")
    op.drop_column("knowledge_demo_versions", "replaces_version_id")

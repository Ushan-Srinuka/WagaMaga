"""Farmer support requests, append-only messages/events and safe in-app notices."""

import sqlalchemy as sa
from alembic import op

from app.core.config import Settings

revision = "0007_support"
down_revision = "0006_farm_lifecycle"
branch_labels = None
depends_on = None


def stamp(name):
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "support_tickets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "farmer_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("subject", sa.String(120), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        stamp("created_at"),
        stamp("updated_at"),
        sa.CheckConstraint(
            "category IN ('account','farm_records','technical','feedback')",
            name="support_ticket_category",
        ),
        sa.CheckConstraint(
            "status IN ('open','in_progress','resolved')", name="support_ticket_status"
        ),
        sa.CheckConstraint("subject ~ '[^[:space:]]'", name="support_ticket_subject"),
        sa.CheckConstraint("version > 0", name="support_ticket_version"),
    )
    op.create_index(
        "ix_support_tickets_owner_updated", "support_tickets", ["farmer_id", "updated_at", "id"]
    )
    op.create_index(
        "ix_support_tickets_status_updated", "support_tickets", ["status", "updated_at", "id"]
    )
    op.create_table(
        "support_messages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "ticket_id",
            sa.Uuid(),
            sa.ForeignKey("support_tickets.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "author_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("author_role", sa.String(16), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("ticket_version", sa.Integer(), nullable=False),
        stamp("created_at"),
        sa.CheckConstraint(
            "author_role IN ('farmer','administrator')", name="support_message_role"
        ),
        sa.CheckConstraint(
            "body ~ '[^[:space:]]' AND char_length(body) <= 4000", name="support_message_body"
        ),
        sa.CheckConstraint("ticket_version > 0", name="support_message_version"),
        sa.UniqueConstraint("ticket_id", "ticket_version", name="uq_support_message_version"),
    )
    op.create_table(
        "support_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "ticket_id",
            sa.Uuid(),
            sa.ForeignKey("support_tickets.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "actor_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("operation", sa.String(20), nullable=False),
        sa.Column("previous_status", sa.String(16)),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("ticket_version", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.String(36), nullable=False),
        stamp("created_at"),
        sa.CheckConstraint(
            "operation IN ('created','replied','status_changed')", name="support_event_operation"
        ),
        sa.CheckConstraint(
            "previous_status IS NULL OR previous_status IN ('open','in_progress','resolved')",
            name="support_event_previous",
        ),
        sa.CheckConstraint(
            "status IN ('open','in_progress','resolved')", name="support_event_status"
        ),
        sa.CheckConstraint("ticket_version > 0", name="support_event_version"),
        sa.UniqueConstraint("ticket_id", "ticket_version", name="uq_support_event_version"),
    )
    op.execute("""
        CREATE FUNCTION public.support_ticket_identity_guard() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF (NEW.id, NEW.farmer_id, NEW.category, NEW.subject, NEW.created_at)
                IS DISTINCT FROM (OLD.id, OLD.farmer_id, OLD.category, OLD.subject, OLD.created_at)
            THEN RAISE EXCEPTION 'Support request identity is immutable' USING ERRCODE='23514';
            END IF;
            RETURN NEW;
        END; $$
    """)
    op.execute("REVOKE ALL ON FUNCTION public.support_ticket_identity_guard() FROM PUBLIC")
    op.execute(
        "CREATE TRIGGER support_ticket_identity_guard BEFORE UPDATE ON support_tickets "
        "FOR EACH ROW EXECUTE FUNCTION public.support_ticket_identity_guard()"
    )
    role = op.get_bind().dialect.identifier_preparer.quote(Settings().app_db_user)
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON TABLE public.support_tickets TO {role}")
    op.execute(
        f"GRANT SELECT, INSERT ON TABLE public.support_messages, public.support_events TO {role}"
    )
    op.drop_constraint("notifications_event_type", "notifications", type_="check")
    op.create_check_constraint(
        "notifications_event_type",
        "notifications",
        "event_type IN ('role_changed','account_reenabled','password_changed','support_updated')",
    )


def downgrade() -> None:
    if op.get_bind().scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM support_tickets) OR EXISTS "
            "(SELECT 1 FROM notifications WHERE event_type='support_updated')"
        )
    ):
        raise RuntimeError("Cannot downgrade while support evidence exists")
    op.drop_table("support_events")
    op.drop_table("support_messages")
    op.drop_table("support_tickets")
    op.execute("DROP FUNCTION public.support_ticket_identity_guard()")
    op.drop_constraint("notifications_event_type", "notifications", type_="check")
    op.create_check_constraint(
        "notifications_event_type",
        "notifications",
        "event_type IN ('role_changed','account_reenabled','password_changed')",
    )

"""Owner/admin support access and atomic messages, status, audit and notices."""

from sqlalchemy import func, select

from app.modules.identity.models import User
from app.modules.identity.security import IdentityError, now
from app.modules.identity.service import active_actor, require_admin
from app.modules.notifications.service import create_notification
from app.modules.support import schemas as dto
from app.modules.support.models import SupportEvent, SupportMessage, SupportTicket


def actor_for(db, ids, *, admin=False, write=False):
    actor = active_actor(db, ids, lock=write)
    if admin:
        require_admin(actor)
    elif actor.role != "farmer":
        raise IdentityError(403, "ACCESS_DENIED", "Farmer access is required for support requests.")
    return actor


def ticket_for(db, actor, ticket_id, *, admin=False, write=False):
    statement = select(SupportTicket).where(SupportTicket.id == ticket_id)
    if not admin:
        statement = statement.where(SupportTicket.farmer_id == actor.id)
    # Admin writes lock requester before ticket, matching owner->ticket write order.
    if write and admin:
        owner_id = db.scalar(statement.with_only_columns(SupportTicket.farmer_id))
        if owner_id is None:
            raise missing()
        db.scalar(select(User).where(User.id == owner_id).with_for_update())
    if write:
        statement = statement.with_for_update()
    ticket = db.scalar(statement.execution_options(populate_existing=True))
    if ticket is None:
        raise missing()
    return ticket


def missing():
    return IdentityError(404, "SUPPORT_NOT_FOUND", "Support request not found.")


def available(user):
    return user.role == "farmer" and user.disabled_at is None and user.deleted_at is None


def view(ticket, user):
    return dto.TicketOut(
        **{column.name: getattr(ticket, column.name) for column in SupportTicket.__table__.columns},
        requester_name=user.display_name,
        requester_available=available(user),
    )


def paged(db, statement, query, project):
    total = db.scalar(select(func.count()).select_from(statement.order_by(None).subquery())) or 0
    records = db.execute(
        statement.offset((query.page - 1) * query.page_size).limit(query.page_size)
    )
    return {
        "items": [project(row) for row in records],
        "total": total,
        "page": query.page,
        "page_size": query.page_size,
    }


def list_tickets(db, ids, query, *, admin=False):
    actor = actor_for(db, ids, admin=admin)
    statement = select(SupportTicket, User).join(User, User.id == SupportTicket.farmer_id)
    if not admin:
        statement = statement.where(SupportTicket.farmer_id == actor.id)
    if query.status != "all":
        statement = statement.where(SupportTicket.status == query.status)
    if query.category:
        statement = statement.where(SupportTicket.category == query.category)
    return paged(
        db,
        statement.order_by(SupportTicket.updated_at.desc(), SupportTicket.id),
        query,
        lambda row: view(*row),
    )


def get_ticket(db, ids, ticket_id, *, admin=False):
    actor = actor_for(db, ids, admin=admin)
    ticket = ticket_for(db, actor, ticket_id, admin=admin)
    return view(ticket, db.get(User, ticket.farmer_id))


def event(db, ticket, actor, operation, previous, request_id):
    db.add(
        SupportEvent(
            ticket_id=ticket.id,
            actor_id=actor.id,
            operation=operation,
            previous_status=previous,
            status=ticket.status,
            ticket_version=ticket.version,
            request_id=request_id,
        )
    )
    db.flush()


def check_version(ticket, version):
    if ticket.version != version:
        raise IdentityError(
            409, "SUPPORT_VERSION_CONFLICT", "This request changed. Reload and review it."
        )


def create_ticket(db, ids, data, request_id):
    actor = actor_for(db, ids, write=True)
    stamp = now()
    ticket = SupportTicket(
        farmer_id=actor.id,
        category=data.category,
        subject=data.subject,
        status="open",
        version=1,
        created_at=stamp,
        updated_at=stamp,
    )
    db.add(ticket)
    db.flush()
    db.add(
        SupportMessage(
            ticket_id=ticket.id,
            author_id=actor.id,
            author_role=actor.role,
            body=data.body,
            ticket_version=1,
            created_at=stamp,
        )
    )
    event(db, ticket, actor, "created", None, request_id)
    return view(ticket, actor)


def list_messages(db, ids, ticket_id, query, *, admin=False):
    actor = actor_for(db, ids, admin=admin)
    ticket = ticket_for(db, actor, ticket_id, admin=admin)
    statement = (
        select(SupportMessage)
        .where(SupportMessage.ticket_id == ticket.id)
        .order_by(SupportMessage.ticket_version.desc())
    )
    return paged(db, statement, query, lambda row: dto.MessageOut.model_validate(row[0]))


def reply(db, ids, ticket_id, data, request_id, *, admin=False):
    actor = actor_for(db, ids, admin=admin, write=True)
    ticket = ticket_for(db, actor, ticket_id, admin=admin, write=True)
    check_version(ticket, data.expected_version)
    if ticket.status == "resolved":
        raise IdentityError(409, "SUPPORT_RESOLVED", "Reopen this request before replying.")
    owner = db.get(User, ticket.farmer_id, populate_existing=True)
    if not available(owner):
        raise IdentityError(
            409, "REQUESTER_UNAVAILABLE", "The requester account cannot receive replies."
        )
    ticket.version += 1
    ticket.updated_at = now()
    db.add(
        SupportMessage(
            ticket_id=ticket.id,
            author_id=actor.id,
            author_role=actor.role,
            body=data.body,
            ticket_version=ticket.version,
            created_at=now(),
        )
    )
    event(db, ticket, actor, "replied", ticket.status, request_id)
    if admin:
        create_notification(
            db,
            owner.id,
            "support_updated",
            "Support replied to your request",
            "Open My support requests to read the reply.",
        )
    db.flush()
    return view(ticket, owner)


def change_status(db, ids, ticket_id, data, request_id, *, admin=False):
    actor = actor_for(db, ids, admin=admin, write=True)
    ticket = ticket_for(db, actor, ticket_id, admin=admin, write=True)
    check_version(ticket, data.expected_version)
    if not admin and data.status == "in_progress":
        raise IdentityError(403, "ACCESS_DENIED", "Only support can mark a request in progress.")
    if not admin and data.status == "open" and ticket.status == "in_progress":
        raise IdentityError(
            409, "SUPPORT_STATUS_CONFLICT", "You can resolve this request or wait for support."
        )
    owner = db.get(User, ticket.farmer_id, populate_existing=True)
    if ticket.status != data.status:
        previous = ticket.status
        ticket.status = data.status
        ticket.version += 1
        ticket.updated_at = now()
        event(db, ticket, actor, "status_changed", previous, request_id)
        if admin and available(owner):
            create_notification(
                db,
                owner.id,
                "support_updated",
                "Support request status updated",
                "Open My support requests to review its status.",
            )
        db.flush()
    return view(ticket, owner)

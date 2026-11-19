"""HTTP support adapters. All object/role rules remain in domain services."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from app.modules.identity.dependencies import DB, Principal, browser_write, limiter
from app.modules.identity.service import Limiter
from app.modules.support import schemas as dto
from app.modules.support import service

router = APIRouter(prefix="/api/v1", tags=["Help and Support"])
TicketQuery = Annotated[dto.Query, Query()]
Paging = Annotated[dto.Paging, Query()]
Limits = Annotated[Limiter, Depends(limiter)]


def farmer_access(db: DB, ids: Principal):
    service.actor_for(db, ids)


def admin_access(db: DB, ids: Principal):
    service.actor_for(db, ids, admin=True)


farmer = APIRouter(prefix="/support/tickets", dependencies=[Depends(farmer_access)])
admin = APIRouter(prefix="/admin/support/tickets", dependencies=[Depends(admin_access)])
write = [Depends(browser_write)]


@router.get("/help/contact", response_model=dto.Contact)
def contact(request: Request):
    return dto.Contact(email=request.app.state.settings.support_contact_email)


@farmer.get("", response_model=dto.Page[dto.TicketOut])
def farmer_tickets(db: DB, ids: Principal, query: TicketQuery):
    return service.list_tickets(db, ids, query)


@farmer.post("", response_model=dto.TicketOut, status_code=201, dependencies=write)
def create_ticket(data: dto.Create, request: Request, db: DB, ids: Principal, limits: Limits):
    limits.check("support_create", str(ids[0]), 5, 3600)
    return service.create_ticket(db, ids, data, request.state.request_id)


@farmer.get("/{ticket_id}", response_model=dto.TicketOut)
def farmer_ticket(ticket_id: UUID, db: DB, ids: Principal):
    return service.get_ticket(db, ids, ticket_id)


@farmer.get("/{ticket_id}/messages", response_model=dto.Page[dto.MessageOut])
def farmer_messages(ticket_id: UUID, db: DB, ids: Principal, query: Paging):
    return service.list_messages(db, ids, ticket_id, query)


@farmer.post("/{ticket_id}/messages", response_model=dto.TicketOut, dependencies=write)
def farmer_reply(
    ticket_id: UUID, data: dto.Reply, request: Request, db: DB, ids: Principal, limits: Limits
):
    limits.check("support_reply", str(ids[0]), 30, 3600)
    return service.reply(db, ids, ticket_id, data, request.state.request_id)


@farmer.post("/{ticket_id}/status", response_model=dto.TicketOut, dependencies=write)
def farmer_status(
    ticket_id: UUID,
    data: dto.ChangeStatus,
    request: Request,
    db: DB,
    ids: Principal,
    limits: Limits,
):
    limits.check("support_status", str(ids[0]), 60, 3600)
    return service.change_status(db, ids, ticket_id, data, request.state.request_id)


@admin.get("", response_model=dto.Page[dto.TicketOut])
def admin_tickets(db: DB, ids: Principal, query: TicketQuery):
    return service.list_tickets(db, ids, query, admin=True)


@admin.get("/{ticket_id}", response_model=dto.TicketOut)
def admin_ticket(ticket_id: UUID, db: DB, ids: Principal):
    return service.get_ticket(db, ids, ticket_id, admin=True)


@admin.get("/{ticket_id}/messages", response_model=dto.Page[dto.MessageOut])
def admin_messages(ticket_id: UUID, db: DB, ids: Principal, query: Paging):
    return service.list_messages(db, ids, ticket_id, query, admin=True)


@admin.post("/{ticket_id}/messages", response_model=dto.TicketOut, dependencies=write)
def admin_reply(
    ticket_id: UUID, data: dto.Reply, request: Request, db: DB, ids: Principal, limits: Limits
):
    limits.check("support_reply", str(ids[0]), 30, 3600)
    return service.reply(db, ids, ticket_id, data, request.state.request_id, admin=True)


@admin.post("/{ticket_id}/status", response_model=dto.TicketOut, dependencies=write)
def admin_status(
    ticket_id: UUID,
    data: dto.ChangeStatus,
    request: Request,
    db: DB,
    ids: Principal,
    limits: Limits,
):
    limits.check("support_status", str(ids[0]), 60, 3600)
    return service.change_status(db, ids, ticket_id, data, request.state.request_id, admin=True)


router.include_router(farmer)
router.include_router(admin)

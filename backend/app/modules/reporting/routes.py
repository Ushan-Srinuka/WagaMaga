"""Administrator reporting adapters, independent of farmer record-read permissions."""

from uuid import UUID

from fastapi import APIRouter, Depends, Request

from app.modules.identity.dependencies import DB, Principal, administrator
from app.modules.reporting import schemas as dto
from app.modules.reporting import service

router = APIRouter(
    prefix="/api/v1/admin", tags=["Administration Reporting"], dependencies=[Depends(administrator)]
)


@router.get("/overview", response_model=dto.Overview)
def overview(request: Request, db: DB, ids: Principal):
    return service.overview(db, ids, request.state.request_id)


@router.get("/users/{user_id}/farm-summary", response_model=dto.FarmerSummary)
def farmer_summary(user_id: UUID, request: Request, db: DB, ids: Principal):
    return service.farmer_summary(db, ids, user_id, request.state.request_id)

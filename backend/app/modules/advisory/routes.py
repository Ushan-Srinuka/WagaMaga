"""HTTP endpoints for advisor-assigned weekly plan cases."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from app.modules.advisory import service
from app.modules.farms import schemas as dto
from app.modules.identity.dependencies import DB, Principal, browser_write

router = APIRouter(prefix="/api/v1/advisor/cases", tags=["Advisor cases"])
review_router = APIRouter(prefix="/api/v1/plan-reviews", tags=["Plan review links"])


@review_router.get("/{plan_id}", response_model=service.FarmerReview | service.AssignedReview)
def open_review(plan_id: UUID, db: DB, ids: Principal):
    return service.open_review(db, ids, plan_id)


@router.get("", response_model=dto.Page[service.CaseOut])
def cases(db: DB, ids: Principal, query: Annotated[dto.Paging, Query()]):
    return service.inbox(db, ids, query)


@router.post(
    "/{plan_id}/decision", response_model=service.DecisionOut, dependencies=[Depends(browser_write)]
)
def decide(plan_id: UUID, data: service.DecisionInput, request: Request, db: DB, ids: Principal):
    return service.decide(db, ids, plan_id, data, request.state.request_id)

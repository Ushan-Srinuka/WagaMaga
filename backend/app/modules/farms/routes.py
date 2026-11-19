"""Farm HTTP adapter. Services own all record access and business transitions."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from app.modules.farms import schemas as dto
from app.modules.farms import service
from app.modules.identity.dependencies import DB, Principal, browser_write


def farmer_access(db: DB, ids: Principal):
    service.farmer(db, ids)


router = APIRouter(
    prefix="/api/v1",
    tags=["Farm Records"],
    dependencies=[Depends(farmer_access)],
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Farmer or browser-origin access denied"},
        404: {"description": "Record not found"},
        409: {"description": "Stale version or archived record"},
        422: {"description": "Invalid fields or unsupported crop"},
        503: {"description": "Storage temporarily unavailable"},
    },
)
write = [Depends(browser_write)]
Paging = Annotated[dto.Paging, Query()]
FarmQuery = Annotated[dto.FarmQuery, Query()]
CultivationQuery = Annotated[dto.CultivationQuery, Query()]
ObservationQuery = Annotated[dto.ObservationQuery, Query()]
FarmHistory = dto.Page[dto.HistoryItem[dto.FarmSnapshot]]
CultivationHistory = dto.Page[dto.HistoryItem[dto.CultivationSnapshot]]
ObservationHistory = dto.Page[dto.HistoryItem[dto.ObservationSnapshot]]


@router.get("/crop-types", response_model=dto.Page[dto.CropOut])
def crops(db: DB, ids: Principal, query: Paging):
    return service.list_crops(db, ids, query)


@router.get("/farms", response_model=dto.Page[dto.FarmOut])
def farms(db: DB, ids: Principal, query: FarmQuery):
    return service.list_farms(db, ids, query)


@router.post("/farms", response_model=dto.FarmOut, status_code=201, dependencies=write)
def create_farm(data: dto.FarmCreate, request: Request, db: DB, ids: Principal):
    return service.create_farm(db, ids, data, request.state.request_id)


@router.get("/farms/{farm_id}", response_model=dto.FarmOut)
def farm(farm_id: UUID, db: DB, ids: Principal):
    return service.get_farm(db, ids, farm_id)


@router.patch("/farms/{farm_id}", response_model=dto.FarmOut, dependencies=write)
def update_farm(farm_id: UUID, data: dto.FarmPatch, request: Request, db: DB, ids: Principal):
    return service.update_farm(db, ids, farm_id, data, request.state.request_id)


@router.post("/farms/{farm_id}/archive", response_model=dto.FarmOut, dependencies=write)
def archive_farm(farm_id: UUID, data: dto.VersionCommand, request: Request, db: DB, ids: Principal):
    return service.archive_farm(db, ids, farm_id, data, request.state.request_id)


@router.get("/farms/{farm_id}/history", response_model=FarmHistory)
def farm_history(farm_id: UUID, db: DB, ids: Principal, query: Paging):
    return service.history(db, ids, "farm", query, farm_id=farm_id)


@router.post("/farms/{farm_id}/restore", response_model=dto.FarmOut, dependencies=write)
def restore_farm(farm_id: UUID, data: dto.VersionCommand, request: Request, db: DB, ids: Principal):
    return service.restore_farm(db, ids, farm_id, data, request.state.request_id)


@router.post("/farms/{farm_id}/delete", response_model=dto.FarmDeleted, dependencies=write)
def delete_farm(farm_id: UUID, data: dto.FarmDelete, request: Request, db: DB, ids: Principal):
    return service.delete_farm(db, ids, farm_id, data, request.state.request_id)


@router.get("/farms/{farm_id}/cultivations", response_model=dto.Page[dto.CultivationOut])
def cultivations(farm_id: UUID, db: DB, ids: Principal, query: CultivationQuery):
    return service.list_cultivations(db, ids, farm_id, query)


@router.post(
    "/farms/{farm_id}/cultivations",
    response_model=dto.CultivationOut,
    status_code=201,
    dependencies=write,
)
def create_cultivation(
    farm_id: UUID,
    data: dto.CultivationCreate,
    request: Request,
    db: DB,
    ids: Principal,
):
    return service.create_cultivation(db, ids, farm_id, data, request.state.request_id)


@router.get("/farms/{farm_id}/cultivations/{cultivation_id}", response_model=dto.CultivationOut)
def cultivation(farm_id: UUID, cultivation_id: UUID, db: DB, ids: Principal):
    return service.get_cultivation(db, ids, farm_id, cultivation_id)


@router.patch(
    "/farms/{farm_id}/cultivations/{cultivation_id}",
    response_model=dto.CultivationOut,
    dependencies=write,
)
def update_cultivation(
    farm_id: UUID,
    cultivation_id: UUID,
    data: dto.CultivationPatch,
    request: Request,
    db: DB,
    ids: Principal,
):
    return service.update_cultivation(
        db, ids, farm_id, cultivation_id, data, request.state.request_id
    )


@router.post(
    "/farms/{farm_id}/cultivations/{cultivation_id}/archive",
    response_model=dto.CultivationOut,
    dependencies=write,
)
def archive_cultivation(
    farm_id: UUID,
    cultivation_id: UUID,
    data: dto.VersionCommand,
    request: Request,
    db: DB,
    ids: Principal,
):
    return service.archive_cultivation(
        db, ids, farm_id, cultivation_id, data, request.state.request_id
    )


@router.post(
    "/farms/{farm_id}/cultivations/{cultivation_id}/stage-confirmation",
    response_model=dto.CultivationOut,
    dependencies=write,
)
def stage_confirmation(
    farm_id: UUID,
    cultivation_id: UUID,
    data: dto.StageConfirmation,
    request: Request,
    db: DB,
    ids: Principal,
):
    return service.confirm_stage(db, ids, farm_id, cultivation_id, data, request.state.request_id)


@router.get(
    "/farms/{farm_id}/cultivations/{cultivation_id}/history",
    response_model=CultivationHistory,
)
def cultivation_history(farm_id: UUID, cultivation_id: UUID, db: DB, ids: Principal, query: Paging):
    return service.history(
        db, ids, "cultivation", query, farm_id=farm_id, cultivation_id=cultivation_id
    )


@router.get(
    "/cultivations/{cultivation_id}/observations", response_model=dto.Page[dto.ObservationOut]
)
def observations(cultivation_id: UUID, db: DB, ids: Principal, query: ObservationQuery):
    return service.list_observations(db, ids, cultivation_id, query)


@router.post(
    "/cultivations/{cultivation_id}/observations",
    response_model=dto.ObservationOut,
    status_code=201,
    dependencies=write,
)
def create_observation(
    cultivation_id: UUID,
    data: dto.ObservationCreate,
    request: Request,
    db: DB,
    ids: Principal,
):
    return service.create_observation(db, ids, cultivation_id, data, request.state.request_id)


@router.get(
    "/cultivations/{cultivation_id}/observations/{observation_id}",
    response_model=dto.ObservationOut,
)
def observation(cultivation_id: UUID, observation_id: UUID, db: DB, ids: Principal):
    return service.get_observation(db, ids, cultivation_id, observation_id)


@router.patch(
    "/cultivations/{cultivation_id}/observations/{observation_id}",
    response_model=dto.ObservationOut,
    dependencies=write,
)
def update_observation(
    cultivation_id: UUID,
    observation_id: UUID,
    data: dto.ObservationPatch,
    request: Request,
    db: DB,
    ids: Principal,
):
    return service.update_observation(
        db, ids, cultivation_id, observation_id, data, request.state.request_id
    )


@router.get(
    "/cultivations/{cultivation_id}/observations/{observation_id}/history",
    response_model=ObservationHistory,
)
def observation_history(
    cultivation_id: UUID,
    observation_id: UUID,
    db: DB,
    ids: Principal,
    query: Paging,
):
    return service.history(
        db, ids, "observation", query, cultivation_id=cultivation_id, observation_id=observation_id
    )

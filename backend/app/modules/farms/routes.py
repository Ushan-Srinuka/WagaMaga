"""Farm HTTP adapter. Services own all record access and business transitions."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request

from app.modules.farms import plans, service, tasks
from app.modules.farms import schemas as dto
from app.modules.identity.dependencies import DB, Principal, browser_write, limiter
from app.modules.identity.service import Limiter
from app.modules.knowledge import cultivation_guidance
from app.modules.weather import alerts, reschedules, scheduled
from app.modules.weather import demo as weather_demo
from app.modules.weather import live as live_weather


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
TaskQuery = Annotated[dto.TaskQuery, Query()]
TASKS = "/farms/{farm_id}/cultivations/{cultivation_id}/tasks"
PLANS = "/farms/{farm_id}/cultivations/{cultivation_id}/task-plans"
WEATHER = "/farms/{farm_id}/cultivations/{cultivation_id}/weather"
ALERTS = WEATHER + "/alerts"
WEATHER_SCHEDULE = "/farms/{farm_id}/weather-schedule"
GUIDANCE = "/farms/{farm_id}/cultivations/{cultivation_id}/chilli-guidance"
PlanKey = Annotated[UUID, Header(alias="Idempotency-Key")]


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


@router.get(WEATHER_SCHEDULE, response_model=scheduled.ScheduleOut)
def weather_schedule(farm_id: UUID, request: Request, db: DB, ids: Principal):
    return scheduled.get(db, ids, farm_id, request.app.state.settings)


@router.post(GUIDANCE, response_model=cultivation_guidance.GuidanceAnswer, dependencies=write)
def ask_cultivation_guidance(
    farm_id: UUID,
    cultivation_id: UUID,
    data: cultivation_guidance.GuidanceQuestion,
    db: DB,
    ids: Principal,
):
    return cultivation_guidance.ask(db, ids, farm_id, cultivation_id, data)


@router.patch(WEATHER_SCHEDULE, response_model=scheduled.ScheduleOut, dependencies=write)
def save_weather_schedule(
    farm_id: UUID,
    data: scheduled.ScheduleEdit,
    request: Request,
    db: DB,
    ids: Principal,
):
    return scheduled.save(db, ids, farm_id, request.app.state.settings, data)


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


@router.get(TASKS, response_model=dto.Page[dto.TaskOut])
def list_tasks(farm_id: UUID, cultivation_id: UUID, db: DB, ids: Principal, query: TaskQuery):
    return tasks.list_tasks(db, ids, farm_id, cultivation_id, query)


@router.post(TASKS, response_model=dto.TaskOut, status_code=201, dependencies=write)
def create_task(
    farm_id: UUID,
    cultivation_id: UUID,
    data: dto.TaskCreate,
    request: Request,
    db: DB,
    ids: Principal,
):
    return tasks.create_task(db, ids, farm_id, cultivation_id, data, request.state.request_id)


@router.patch(TASKS + "/{task_id}", response_model=dto.TaskOut, dependencies=write)
def edit_task(
    farm_id: UUID,
    cultivation_id: UUID,
    task_id: UUID,
    data: dto.TaskEdit,
    request: Request,
    db: DB,
    ids: Principal,
):
    return tasks.change_task(
        db, ids, farm_id, cultivation_id, task_id, data, request.state.request_id
    )


@router.post(TASKS + "/{task_id}/status", response_model=dto.TaskOut, dependencies=write)
def change_task_status(
    farm_id: UUID,
    cultivation_id: UUID,
    task_id: UUID,
    data: dto.TaskTransition,
    request: Request,
    db: DB,
    ids: Principal,
):
    return tasks.change_task(
        db, ids, farm_id, cultivation_id, task_id, data, request.state.request_id
    )


@router.get(TASKS + "/history", response_model=dto.Page[dto.TaskEventOut])
def task_history(farm_id: UUID, cultivation_id: UUID, db: DB, ids: Principal, query: Paging):
    return tasks.task_history(db, ids, farm_id, cultivation_id, query)


@router.get(PLANS, response_model=dto.LatestPlan)
def latest_plan(farm_id: UUID, cultivation_id: UUID, db: DB, ids: Principal):
    return plans.latest(db, ids, farm_id, cultivation_id)


@router.post(PLANS, response_model=dto.PlanOut, dependencies=write)
def create_plan(
    farm_id: UUID, cultivation_id: UUID, _body: dto.Input, request: Request, db: DB, ids: Principal
):
    return plans.create(db, ids, farm_id, cultivation_id, request.state.request_id)


@router.post(PLANS + "/{plan_id}/decision", response_model=dto.PlanDecisionOut, dependencies=write)
def decide_plan(
    farm_id: UUID,
    cultivation_id: UUID,
    plan_id: UUID,
    key: PlanKey,
    data: dto.PlanDecision,
    request: Request,
    db: DB,
    ids: Principal,
):
    return plans.decide(
        db, ids, farm_id, cultivation_id, plan_id, key, data, request.state.request_id
    )


@router.get(PLANS + "/history", response_model=dto.Page[dto.PlanHistoryOut])
def plan_history(farm_id: UUID, cultivation_id: UUID, db: DB, ids: Principal, query: Paging):
    return plans.history(db, ids, farm_id, cultivation_id, query)


@router.get(
    "/farms/{farm_id}/cultivations/{cultivation_id}/demo-weather",
    response_model=weather_demo.DemoForecast,
)
def demo_weather(farm_id: UUID, cultivation_id: UUID, db: DB, ids: Principal):
    return weather_demo.for_cultivation(db, ids, farm_id, cultivation_id)


@router.get(WEATHER, response_model=live_weather.WeatherView)
def weather(farm_id: UUID, cultivation_id: UUID, request: Request, db: DB, ids: Principal):
    return live_weather.for_cultivation(
        db, ids, farm_id, cultivation_id, request.app.state.settings
    )


@router.post(WEATHER + "/refresh", response_model=live_weather.WeatherView, dependencies=write)
def refresh_weather(
    farm_id: UUID,
    cultivation_id: UUID,
    _body: dto.Input,
    request: Request,
    db: DB,
    ids: Principal,
    limits: Annotated[Limiter, Depends(limiter)],
):
    def quota(owned_farm_id):
        limits.check("weather_farmer", str(ids[0]), 12, 3600)
        limits.check("weather_farm", str(owned_farm_id), 2, 300)

    return alerts.refresh_forecast(
        db, ids, farm_id, cultivation_id, request.app.state.settings, quota
    )


@router.get(ALERTS, response_model=alerts.AlertPage)
def weather_alerts(farm_id: UUID, cultivation_id: UUID, db: DB, ids: Principal, query: Paging):
    return alerts.list_alerts(db, ids, farm_id, cultivation_id, query)


@router.patch(ALERTS + "/rule", response_model=alerts.RuleOut, dependencies=write)
def weather_alert_rule(
    farm_id: UUID, cultivation_id: UUID, data: alerts.RuleEdit, db: DB, ids: Principal
):
    return alerts.save_rule(db, ids, farm_id, cultivation_id, data)


@router.post(
    ALERTS + "/tasks/{task_id}/reschedule",
    response_model=reschedules.RescheduleOut,
    dependencies=write,
)
def prepare_reschedule(
    farm_id: UUID,
    cultivation_id: UUID,
    task_id: UUID,
    data: reschedules.RescheduleInput,
    request: Request,
    db: DB,
    ids: Principal,
):
    return reschedules.prepare(
        db, ids, farm_id, cultivation_id, task_id, data, request.state.request_id
    )


@router.post(
    ALERTS + "/reschedules/{plan_id}/decision",
    response_model=dto.PlanDecisionOut,
    dependencies=write,
)
def decide_reschedule(
    farm_id: UUID,
    cultivation_id: UUID,
    plan_id: UUID,
    key: PlanKey,
    data: dto.PlanDecision,
    request: Request,
    db: DB,
    ids: Principal,
):
    return reschedules.decide(
        db, ids, farm_id, cultivation_id, plan_id, key, data, request.state.request_id
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

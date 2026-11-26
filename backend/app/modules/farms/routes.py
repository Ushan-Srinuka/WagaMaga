"""Farm HTTP adapter. Services own all record access and business transitions."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request

from app.modules.advisory import service as advisory
from app.modules.farms import (
    diary,
    missed_tasks,
    planner_chat,
    plans,
    service,
    tasks,
    weekly,
    weekly_batch,
)
from app.modules.farms import schemas as dto
from app.modules.identity.dependencies import DB, Principal, browser_write, limiter
from app.modules.identity.service import Limiter
from app.modules.knowledge import chat_jobs, chilli_chat, cultivation_guidance, rag
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
WEEK = "/farms/{farm_id}/cultivations/{cultivation_id}/week"
SUGGESTION = TASKS + "/{task_id}/weekly-suggestion"
WEEKLY_PLAN = PLANS + "/weekly/{plan_id}"
BATCH = PLANS + "/weekly-batch"
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


@router.get(
    "/farms/{farm_id}/cultivations/{cultivation_id}/diary",
    response_model=dto.Page[dto.DiaryEntry],
)
def cultivation_diary(farm_id: UUID, cultivation_id: UUID, db: DB, ids: Principal, query: Paging):
    return diary.list_entries(db, ids, farm_id, cultivation_id, query)


@router.get(TASKS, response_model=dto.TaskPage)
def list_tasks(farm_id: UUID, cultivation_id: UUID, db: DB, ids: Principal, query: TaskQuery):
    return tasks.list_tasks(db, ids, farm_id, cultivation_id, query)


@router.get(WEEK, response_model=weekly.Week)
def planner_week(farm_id: UUID, cultivation_id: UUID, db: DB, ids: Principal, query: Paging):
    return weekly.week(db, ids, farm_id, cultivation_id, query)


REVIEWED_SOURCES = "/farms/{farm_id}/cultivations/{cultivation_id}/reviewed-sources"
CHILLI_CHATS = "/farms/{farm_id}/cultivations/{cultivation_id}/chilli-chats"


@router.get(CHILLI_CHATS, response_model=dto.Page[chilli_chat.ChatSummary])
def chilli_chats(farm_id: UUID, cultivation_id: UUID, db: DB, ids: Principal, query: Paging):
    return chilli_chat.list_chats(db, ids, farm_id, cultivation_id, query)


@router.post(
    CHILLI_CHATS, response_model=chilli_chat.ChatSummary, status_code=201, dependencies=write
)
def start_chilli_chat(farm_id: UUID, cultivation_id: UUID, db: DB, ids: Principal):
    return chilli_chat.create(db, ids, farm_id, cultivation_id)


@router.get(CHILLI_CHATS + "/{chat_id}", response_model=chilli_chat.History)
def chilli_chat_history(
    farm_id: UUID, cultivation_id: UUID, chat_id: UUID, request: Request, db: DB, ids: Principal
):
    return chilli_chat.history(
        db, ids, farm_id, cultivation_id, chat_id, request.app.state.settings
    )


@router.delete(CHILLI_CHATS + "/{chat_id}", status_code=204, dependencies=write)
def delete_chilli_chat(farm_id: UUID, cultivation_id: UUID, chat_id: UUID, db: DB, ids: Principal):
    chilli_chat.delete(db, ids, farm_id, cultivation_id, chat_id)


CHAT_JOBS = CHILLI_CHATS + "/{chat_id}/jobs"


@router.post(CHAT_JOBS, response_model=chat_jobs.Status, status_code=202, dependencies=write)
def submit_chilli_job(
    farm_id: UUID,
    cultivation_id: UUID,
    chat_id: UUID,
    data: chilli_chat.Ask,
    db: DB,
    ids: Principal,
):
    return chat_jobs.submit(db, ids, farm_id, cultivation_id, chat_id, data)


@router.get(CHAT_JOBS, response_model=chat_jobs.Latest)
def latest_chilli_job(farm_id: UUID, cultivation_id: UUID, chat_id: UUID, db: DB, ids: Principal):
    return chat_jobs.Latest(job=chat_jobs.status(db, ids, farm_id, cultivation_id, chat_id))


@router.get(CHAT_JOBS + "/{job_id}", response_model=chat_jobs.Status)
def read_chilli_job(
    farm_id: UUID,
    cultivation_id: UUID,
    chat_id: UUID,
    job_id: UUID,
    db: DB,
    ids: Principal,
):
    return chat_jobs.status(db, ids, farm_id, cultivation_id, chat_id, job_id)


@router.post(CHAT_JOBS + "/{job_id}/retry", response_model=chat_jobs.Status, dependencies=write)
def retry_chilli_job(
    farm_id: UUID,
    cultivation_id: UUID,
    chat_id: UUID,
    job_id: UUID,
    db: DB,
    ids: Principal,
):
    return chat_jobs.retry(db, ids, farm_id, cultivation_id, chat_id, job_id)


@router.post(CHILLI_CHATS + "/{chat_id}/ask", response_model=chilli_chat.Turn, dependencies=write)
def ask_chilli_chat(
    farm_id: UUID,
    cultivation_id: UUID,
    chat_id: UUID,
    data: chilli_chat.Ask,
    db: DB,
    ids: Principal,
    request: Request,
    limits: Annotated[Limiter, Depends(limiter)],
):
    return chilli_chat.ask(
        db,
        ids,
        farm_id,
        cultivation_id,
        chat_id,
        data,
        request.app.state.settings,
        lambda: limits.check("chilli_pdf_chat", str(ids[0]), 16, 60),
    )


@router.post(REVIEWED_SOURCES + "/search", response_model=rag.Results, dependencies=write)
def search_reviewed_sources(
    farm_id: UUID,
    cultivation_id: UUID,
    data: rag.Search,
    db: DB,
    ids: Principal,
    request: Request,
    limits: Annotated[Limiter, Depends(limiter)],
):
    return rag.search(
        db,
        ids,
        farm_id,
        cultivation_id,
        data,
        request.app.state.settings,
        lambda: limits.check("rag_semantic", str(ids[0]), 12, 60),
    )


@router.get(REVIEWED_SOURCES + "/{passage_id}", response_model=rag.Passage)
def reviewed_source_passage(
    farm_id: UUID,
    cultivation_id: UUID,
    passage_id: UUID,
    request: Request,
    db: DB,
    ids: Principal,
):
    return rag.source_passage(
        db,
        ids,
        farm_id,
        cultivation_id,
        passage_id,
        screened_only=request.app.state.settings.app_env == "production",
    )


@router.post(WEEK + "/ask", response_model=planner_chat.Answer, dependencies=write)
def ask_planner(
    farm_id: UUID, cultivation_id: UUID, data: planner_chat.Question, db: DB, ids: Principal
):
    return planner_chat.ask(db, ids, farm_id, cultivation_id, data)


@router.get(SUGGESTION, response_model=weekly.LatestWeeklyPlan)
def weekly_suggestion(farm_id: UUID, cultivation_id: UUID, task_id: UUID, db: DB, ids: Principal):
    return weekly.latest(db, ids, farm_id, cultivation_id, task_id)


@router.post(SUGGESTION, response_model=weekly.WeeklyPlan, dependencies=write)
def prepare_weekly_suggestion(
    farm_id: UUID,
    cultivation_id: UUID,
    task_id: UUID,
    data: dto.VersionCommand,
    request: Request,
    db: DB,
    ids: Principal,
):
    return weekly.prepare(db, ids, farm_id, cultivation_id, task_id, data, request.state.request_id)


@router.post(WEEKLY_PLAN + "/decision", response_model=dto.PlanDecisionOut, dependencies=write)
def decide_weekly_suggestion(
    farm_id: UUID,
    cultivation_id: UUID,
    plan_id: UUID,
    key: PlanKey,
    data: dto.PlanDecision,
    request: Request,
    db: DB,
    ids: Principal,
):
    return weekly.decide(
        db, ids, farm_id, cultivation_id, plan_id, key, data, request.state.request_id
    )


@router.post(WEEKLY_PLAN + "/advisor", response_model=weekly.WeeklyPlan, dependencies=write)
def assign_weekly_suggestion(
    farm_id: UUID,
    cultivation_id: UUID,
    plan_id: UUID,
    data: advisory.Assignment,
    request: Request,
    db: DB,
    ids: Principal,
    limits: Annotated[Limiter, Depends(limiter)],
):
    limits.check("advisor_assign", str(ids[0]), 12, 3600)
    return advisory.assign(
        db, ids, farm_id, cultivation_id, plan_id, data, request.state.request_id
    )


@router.post(WEEKLY_PLAN + "/advisor/revoke", response_model=weekly.WeeklyPlan, dependencies=write)
def revoke_weekly_suggestion(
    farm_id: UUID,
    cultivation_id: UUID,
    plan_id: UUID,
    data: advisory.Binding,
    request: Request,
    db: DB,
    ids: Principal,
):
    return advisory.revoke(
        db, ids, farm_id, cultivation_id, plan_id, data, request.state.request_id
    )


@router.post(WEEKLY_PLAN + "/revise", response_model=weekly.WeeklyPlan, dependencies=write)
def revise_weekly_suggestion(
    farm_id: UUID,
    cultivation_id: UUID,
    plan_id: UUID,
    data: advisory.Revision,
    request: Request,
    db: DB,
    ids: Principal,
):
    return advisory.revise(
        db, ids, farm_id, cultivation_id, plan_id, data, request.state.request_id
    )


@router.get(BATCH, response_model=dto.Page[weekly.WeeklyPlan | dto.PlanOut])
def weekly_batch_plans(farm_id: UUID, cultivation_id: UUID, db: DB, ids: Principal, query: Paging):
    return weekly_batch.list_plans(db, ids, farm_id, cultivation_id, query)


@router.get(BATCH + "/history", response_model=dto.Page[weekly.WeeklyPlan])
def weekly_batch_history(
    farm_id: UUID, cultivation_id: UUID, db: DB, ids: Principal, query: Paging
):
    return weekly_batch.list_plans(db, ids, farm_id, cultivation_id, query, history=True)


@router.post(BATCH + "/prepare", response_model=weekly_batch.Preparation, dependencies=write)
def prepare_weekly_batch(
    farm_id: UUID, cultivation_id: UUID, _data: dto.Input, request: Request, db: DB, ids: Principal
):
    return weekly_batch.prepare(db, ids, farm_id, cultivation_id, request.state.request_id)


@router.post(BATCH + "/accept", response_model=weekly.WeeklyBatchReceipt, dependencies=write)
def accept_weekly_batch(
    farm_id: UUID,
    cultivation_id: UUID,
    data: weekly.WeeklyBatch,
    request: Request,
    db: DB,
    ids: Principal,
):
    return weekly_batch.accept(db, ids, farm_id, cultivation_id, data, request.state.request_id)


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


@router.post(
    TASKS + "/{task_id}/missed-review", response_model=dto.DateReviewOut, dependencies=write
)
def review_missed_task(
    farm_id: UUID,
    cultivation_id: UUID,
    task_id: UUID,
    data: missed_tasks.MissedTaskInput,
    request: Request,
    db: DB,
    ids: Principal,
):
    return missed_tasks.prepare(
        db, ids, farm_id, cultivation_id, task_id, data, request.state.request_id
    )


@router.post(
    PLANS + "/missed-reviews/{plan_id}/decision",
    response_model=dto.PlanDecisionOut,
    dependencies=write,
)
def decide_missed_task(
    farm_id: UUID,
    cultivation_id: UUID,
    plan_id: UUID,
    key: PlanKey,
    data: dto.PlanDecision,
    request: Request,
    db: DB,
    ids: Principal,
):
    return missed_tasks.decide(
        db, ids, farm_id, cultivation_id, plan_id, key, data, request.state.request_id
    )


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

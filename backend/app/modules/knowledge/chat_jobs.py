"""Durable Chilli AI requests with a fenced, atomic turn and completion write."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.modules.farms import service as farms
from app.modules.farms.models import Cultivation
from app.modules.identity.security import IdentityError, now
from app.modules.identity.service import Limiter
from app.modules.knowledge import chilli_chat
from app.modules.knowledge.models import ChilliChat, ChilliJob

LEASE = timedelta(seconds=90)
MAX_ATTEMPTS = 3


class Status(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    revision: int
    state: Literal["queued", "running", "succeeded", "failed"]
    failure_code: str | None


class Latest(BaseModel):
    job: Status | None


class LostLease(Exception):
    pass


def job_for(db, chat_id, job_id, *, lock=False):
    query = select(ChilliJob).where(ChilliJob.chat_id == chat_id, ChilliJob.id == job_id)
    if lock:
        query = query.with_for_update()
    return db.scalar(query.execution_options(populate_existing=True))


def active_for(db, chat_id, revision):
    return db.scalar(
        select(ChilliJob).where(
            ChilliJob.chat_id == chat_id,
            ChilliJob.revision == revision,
            ChilliJob.state != "failed",
        )
    )


def submit(db, ids, farm_id, cultivation_id, chat_id, data):
    actor, farm, cultivation = chilli_chat.context(db, ids, farm_id, cultivation_id, write=True)
    farms.active(farm, cultivation)
    chat = chilli_chat.chat_for(db, actor, cultivation, chat_id, lock=True)
    existing = active_for(db, chat.id, data.expected_revision)
    if existing is not None and (existing.question, existing.use_gemini) == (
        data.question,
        data.use_gemini,
    ):
        return Status.model_validate(existing)
    chilli_chat.check_revision(chat, data.expected_revision)
    if existing is not None:
        raise IdentityError(409, "AI_JOB_PENDING", "Wait for the current question to finish.")
    job = ChilliJob(
        chat_id=chat.id,
        session_id=ids[1],
        revision=chat.revision,
        question=data.question,
        use_gemini=data.use_gemini,
    )
    db.add(job)
    db.flush()
    return Status.model_validate(job)


def status(db, ids, farm_id, cultivation_id, chat_id, job_id=None):
    actor, _, cultivation = chilli_chat.context(db, ids, farm_id, cultivation_id)
    chat = chilli_chat.chat_for(db, actor, cultivation, chat_id)
    if job_id is None:
        job = db.scalar(
            select(ChilliJob)
            .where(ChilliJob.chat_id == chat.id)
            .order_by(ChilliJob.created_at.desc(), ChilliJob.id.desc())
            .limit(1)
        )
        return Status.model_validate(job) if job else None
    job = job_for(db, chat.id, job_id)
    if job is None:
        raise farms.missing()
    return Status.model_validate(job)


def retry(db, ids, farm_id, cultivation_id, chat_id, job_id):
    actor, farm, cultivation = chilli_chat.context(db, ids, farm_id, cultivation_id, write=True)
    farms.active(farm, cultivation)
    chat = chilli_chat.chat_for(db, actor, cultivation, chat_id, lock=True)
    job = job_for(db, chat.id, job_id, lock=True)
    if job is None:
        raise farms.missing()
    chilli_chat.check_revision(chat, job.revision)
    if job.state != "failed" or active_for(db, chat.id, job.revision) is not None:
        raise IdentityError(409, "AI_JOB_CHANGED", "Reload the conversation before retrying.")
    job.session_id = ids[1]
    job.attempts = 0
    finish(job, "queued")
    return Status.model_validate(job)


@dataclass(frozen=True)
class Claim:
    id: UUID
    chat_id: UUID
    farm_id: UUID
    cultivation_id: UUID
    ids: tuple[UUID, UUID]
    token: UUID
    request: chilli_chat.Ask


def finish(job, state, failure=None):
    job.state = state
    job.failure_code = failure
    job.lease_token = None
    job.lease_until = None


def claim_next(db, stamp: datetime):
    row = db.execute(
        select(ChilliJob, ChilliChat.owner_id, ChilliChat.cultivation_id, Cultivation.farm_id)
        .join(ChilliChat, ChilliChat.id == ChilliJob.chat_id)
        .join(Cultivation, Cultivation.id == ChilliChat.cultivation_id)
        .where(
            or_(
                ChilliJob.state == "queued",
                (ChilliJob.state == "running") & (ChilliJob.lease_until <= stamp),
            )
        )
        .order_by(ChilliJob.created_at, ChilliJob.id)
        .limit(1)
        .with_for_update(of=ChilliJob, skip_locked=True)
    ).first()
    if row is None:
        return None
    job, owner, cultivation, farm = row
    if job.attempts >= MAX_ATTEMPTS:
        finish(job, "failed", "LEASE_EXPIRED")
        return None
    job.state = "running"
    job.lease_token = token = uuid4()
    job.lease_until = stamp + LEASE
    job.attempts += 1
    return Claim(
        job.id,
        job.chat_id,
        farm,
        cultivation,
        (owner, job.session_id),
        token,
        chilli_chat.Ask(
            question=job.question,
            expected_revision=job.revision,
            use_gemini=job.use_gemini,
        ),
    )


def verify_lease(db, claim, *, lock=False):
    job = job_for(db, claim.chat_id, claim.id, lock=lock)
    if (
        job is None
        or job.state != "running"
        or job.lease_token != claim.token
        or job.lease_until <= now()
    ):
        raise LostLease
    return job


def process_claim(engine, settings, claim):
    limiter = Limiter(engine, settings)
    try:
        with Session(engine) as db, db.begin():
            verify_lease(db, claim)
            chilli_chat.ask(
                db,
                claim.ids,
                claim.farm_id,
                claim.cultivation_id,
                claim.chat_id,
                claim.request,
                settings,
                lambda: limiter.check("chilli_pdf_chat", str(claim.ids[0]), 16, 60),
                retry_unavailable=True,
            )
            finish(verify_lease(db, claim, lock=True), "succeeded")
    except LostLease:
        return
    except IdentityError as error:
        with Session(engine) as db, db.begin():
            try:
                finish(verify_lease(db, claim, lock=True), "failed", error.code)
            except LostLease:
                return


def process_one(engine, settings):
    with Session(engine) as db, db.begin():
        claim = claim_next(db, now())
    if claim:
        process_claim(engine, settings, claim)
    return claim is not None

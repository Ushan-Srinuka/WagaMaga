"""Answer bounded chilli questions with public sources and trusted farm context."""

from datetime import datetime, timedelta
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import select

from app.modules.farms import schemas
from app.modules.farms import service as farms
from app.modules.farms.models import CHILLI_ID, CropType, FarmObservation
from app.modules.identity.security import now
from app.modules.knowledge.research import ENTRIES, VERSION, ExtensionCitation

Topic = Literal["nursery-setup", "irrigation-checks", "soil-test"]
RECENT = timedelta(hours=24)
NURSERY_STAGES = {"nursery", "nursery preparation", "seedling", "seedlings", "seedling stage"}
DISTRICT_NAMES = {"anuradhapura", "anuradhapura district"}


class GuidanceQuestion(schemas.Input):
    topic: Topic


class MoistureReading(BaseModel):
    value: schemas.SoilMoisture
    observed_at: datetime


class GuidanceAnswer(BaseModel):
    answer: str | None = None
    citation: ExtensionCitation | None = None
    passage_id: Topic | None = None
    corpus_version: str = VERSION
    confirmed_stage: str | None = None
    soil_moisture: MoistureReading | None = None
    missing: list[str]
    timezone: str


def reported_district(location):
    parts = [part.strip().casefold() for part in location.split(",")]
    if parts[-1] == "sri lanka":
        parts.pop()
    return bool(parts) and parts[-1] in DISTRICT_NAMES


def recent_moisture(db, cultivation_id, stamp):
    observation = db.scalar(
        select(FarmObservation)
        .where(
            FarmObservation.cultivation_id == cultivation_id,
            FarmObservation.soil_moisture.is_not(None),
            FarmObservation.observed_at.between(stamp - RECENT, stamp),
        )
        .order_by(FarmObservation.observed_at.desc(), FarmObservation.id)
        .limit(1)
    )
    if observation is not None:
        return MoistureReading(value=observation.soil_moisture, observed_at=observation.observed_at)
    return None


def ask(db, ids, farm_id, cultivation_id, data):
    actor = farms.farmer(db, ids)
    farm, cultivation = farms.cultivation_for(db, actor.id, cultivation_id, farm_id=farm_id)
    farms.active(farm, cultivation)
    shared = {"confirmed_stage": cultivation.confirmed_stage, "timezone": farm.timezone}
    if cultivation.crop_type_id != CHILLI_ID or not db.get(CropType, CHILLI_ID).supported:
        return GuidanceAnswer(missing=["Cultivation guidance currently covers chilli."], **shared)
    if not reported_district(farm.location):
        return GuidanceAnswer(
            missing=["This feature needs a farm record identifying Anuradhapura as its district."],
            **shared,
        )

    entry = ENTRIES[data.topic]
    answer = entry.summary
    missing = []
    reading = None
    stage = cultivation.confirmed_stage
    if data.topic == "nursery-setup":
        if stage and stage.strip().casefold() in NURSERY_STAGES:
            answer = "Use these checks for the nursery stage you recorded. " + answer
        missing.append(
            "Check how much sunlight reaches the nursery spot and what grew there before."
        )
    elif data.topic == "irrigation-checks":
        reading = recent_moisture(db, cultivation.id, now())
        if reading is None:
            missing.append(
                "Record a recent soil moisture observation to see it alongside the guidance."
            )
        else:
            answer = "Check whether soil moisture has changed since your last reading. " + answer
        if not stage:
            missing.append("Confirm the current crop stage in the cultivation record.")
        missing.append(
            "Check the soil texture and current field moisture before choosing when to irrigate."
        )
    else:
        missing.append(
            "Get a soil test for this plot before deciding on phosphorus or potassium amounts."
        )
    return GuidanceAnswer(
        answer=answer,
        citation=entry.citation,
        passage_id=data.topic,
        soil_moisture=reading,
        missing=missing,
        **shared,
    )

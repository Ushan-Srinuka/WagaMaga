"""Read-only sample rain scenario for an owned cultivation."""

from datetime import date, timedelta
from typing import Literal

from pydantic import BaseModel

from app.modules.farms import service as farms


class DemoForecast(BaseModel):
    source: Literal["fixture"] = "fixture"
    fixture_version: Literal["sample-rain-v1"] = "sample-rain-v1"
    location: str
    timezone: str
    forecast_date: date
    condition: Literal["rain"] = "rain"
    rainfall_mm: Literal[18] = 18
    review_due_on: date | None


def for_cultivation(db, ids, farm_id, cultivation_id):
    actor = farms.farmer(db, ids)
    farm, cultivation = farms.cultivation_for(db, actor.id, cultivation_id, farm_id=farm_id)
    sample_date = farms.local_today(db, farm) + timedelta(days=1)
    archived = farm.archived_at is not None or cultivation.archived_at is not None
    return DemoForecast(
        location=farm.location,
        timezone=farm.timezone,
        forecast_date=sample_date,
        review_due_on=None if archived else sample_date,
    )

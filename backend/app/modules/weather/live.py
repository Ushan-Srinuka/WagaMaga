"""Owner-only forecast retrieval and shared weather freshness policy."""

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import text

from app.integrations import open_meteo
from app.modules.farms import service as farms
from app.modules.identity.security import IdentityError, now
from app.modules.weather.models import FarmForecast

REUSE_FOR = timedelta(minutes=30)
FRESH_FOR = timedelta(hours=2)
PRECISION = Decimal("0.01")


@dataclass(frozen=True)
class Area:
    latitude: Decimal
    longitude: Decimal
    timezone: str


class Forecast(BaseModel):
    provider: Literal["open-meteo"]
    fetched_at: datetime
    fresh_until: datetime
    days: list[open_meteo.Day]


class WeatherView(BaseModel):
    status: Literal["needs_coordinates", "unfetched", "fresh", "stale", "provider_disabled"]
    location: str
    timezone: str
    checked_at: datetime
    can_refresh: bool = False
    forecast: Forecast | None = None


def provider_enabled(settings):
    return (
        settings.app_env != "production"
        or settings.open_meteo_noncommercial
        or settings.open_meteo_api_key is not None
    )


def area_for(farm):
    if farm.latitude is None or farm.longitude is None:
        return None
    return Area(
        farm.latitude.quantize(PRECISION, rounding=ROUND_HALF_UP),
        farm.longitude.quantize(PRECISION, rounding=ROUND_HALF_UP),
        farm.timezone,
    )


def matching_cache(db, farm, area):
    snapshot = db.get(FarmForecast, farm.id, populate_existing=True)
    if snapshot and Area(snapshot.latitude, snapshot.longitude, snapshot.timezone) == area:
        return snapshot
    return None


def examine(db, farm, stamp):
    area = area_for(farm)
    if area is None:
        return None, False
    snapshot = matching_cache(db, farm, area)
    if snapshot is None:
        return None, False
    days = [open_meteo.Day.model_validate(day) for day in snapshot.days]
    today = farms.local_today(db, farm, at=stamp)
    tomorrow = datetime.combine(days[0].date + timedelta(days=1), time.min)
    end_of_first_day = db.scalar(
        text("SELECT timezone(:zone, CAST(:local_midnight AS timestamp))"),
        {"zone": area.timezone, "local_midnight": tomorrow},
    )
    fresh_until = min(snapshot.fetched_at + FRESH_FOR, end_of_first_day)
    forecast = Forecast(
        provider=snapshot.provider,
        fetched_at=snapshot.fetched_at,
        fresh_until=fresh_until,
        days=[day for day in days if day.date >= today],
    )
    return forecast, days[0].date == today and snapshot.fetched_at <= stamp < fresh_until


def present(db, settings, farm, cultivation, stamp):
    shared = {"location": farm.location, "timezone": farm.timezone, "checked_at": stamp}
    if area_for(farm) is None:
        return WeatherView(status="needs_coordinates", **shared)
    enabled = provider_enabled(settings)
    can_refresh = enabled and farm.archived_at is None and cultivation.archived_at is None
    forecast, fresh = examine(db, farm, stamp)
    if forecast is None:
        return WeatherView(
            status="unfetched" if enabled else "provider_disabled",
            can_refresh=can_refresh,
            **shared,
        )
    return WeatherView(
        status="fresh" if fresh else "stale",
        can_refresh=can_refresh,
        forecast=forecast,
        **shared,
    )


def for_cultivation(db, ids, farm_id, cultivation_id, settings):
    actor = farms.farmer(db, ids)
    farm, cultivation = farms.cultivation_for(db, actor.id, cultivation_id, farm_id=farm_id)
    return present(db, settings, farm, cultivation, now())


def refresh(db, ids, farm_id, cultivation_id, settings, on_provider_call):
    actor = farms.farmer(db, ids)
    farm, cultivation = farms.cultivation_for(db, actor.id, cultivation_id, farm_id=farm_id)
    farms.active(farm, cultivation)
    area = area_for(farm)
    if area is None:
        raise IdentityError(409, "WEATHER_LOCATION_REQUIRED", "Add coordinates to the farm first.")
    if not provider_enabled(settings):
        raise IdentityError(503, "WEATHER_NOT_CONFIGURED", "Live weather is unavailable.")

    stamp = now()
    current = present(db, settings, farm, cultivation, stamp)
    if current.status == "fresh" and stamp - current.forecast.fetched_at < REUSE_FOR:
        return current
    first_day = farms.local_today(db, farm, at=stamp)
    on_provider_call(farm.id)
    try:
        days = open_meteo.forecast(
            settings, area.latitude, area.longitude, area.timezone, first_day
        )
    except open_meteo.Unavailable:
        raise IdentityError(
            503, "WEATHER_UNAVAILABLE", "Could not fetch the weather forecast."
        ) from None

    # Hold no write locks across the network request. Recheck scope under the normal record locks.
    actor = farms.farmer(db, ids, write=True)
    farm, cultivation = farms.cultivation_for(
        db, actor.id, cultivation_id, farm_id=farm_id, lock=True
    )
    farms.active(farm, cultivation)
    fetched_at = now()
    if area_for(farm) != area or farms.local_today(db, farm, at=fetched_at) != first_day:
        raise IdentityError(
            409, "WEATHER_CONTEXT_CHANGED", "The forecast area or date changed. Refresh again."
        )

    cached, fresh = examine(db, farm, fetched_at)
    if not fresh or cached.fetched_at < stamp:
        store_forecast(db, farm, area, fetched_at, days)
    return present(db, settings, farm, cultivation, fetched_at)


def store_forecast(db, farm, area, fetched_at, days):
    snapshot = db.get(FarmForecast, farm.id, populate_existing=True)
    if snapshot is None:
        snapshot = FarmForecast(farm_id=farm.id)
        db.add(snapshot)
    snapshot.latitude = area.latitude
    snapshot.longitude = area.longitude
    snapshot.timezone = area.timezone
    snapshot.provider = "open-meteo"
    snapshot.fetched_at = fetched_at
    snapshot.days = [day.model_dump(mode="json") for day in days]
    db.flush()

"""Bounded Open-Meteo daily forecast adapter."""

import http.client
import json
from datetime import date, timedelta
from decimal import Decimal
from typing import Annotated, Literal
from urllib.parse import urlencode

from pydantic import BaseModel, ConfigDict, Field

DAYS = 3
MAX_BYTES = 16384
FIELDS = "temperature_2m_min,temperature_2m_max,precipitation_sum"
Temperature = Annotated[float, Field(strict=True, ge=-100, le=100, allow_inf_nan=False)]
Precipitation = Annotated[float, Field(strict=True, ge=0, le=3000, allow_inf_nan=False)]


class Unavailable(Exception):
    pass


class Day(BaseModel):
    date: date
    minimum_c: Temperature
    maximum_c: Temperature
    precipitation_mm: Precipitation


class DailyUnits(BaseModel):
    time: Literal["iso8601"]
    temperature_2m_min: Literal["°C"]
    temperature_2m_max: Literal["°C"]
    precipitation_sum: Literal["mm"]


class DailyValues(BaseModel):
    model_config = ConfigDict(strict=True)

    time: list[str] = Field(min_length=DAYS, max_length=DAYS)
    temperature_2m_min: list[Temperature] = Field(min_length=DAYS, max_length=DAYS)
    temperature_2m_max: list[Temperature] = Field(min_length=DAYS, max_length=DAYS)
    precipitation_sum: list[Precipitation] = Field(min_length=DAYS, max_length=DAYS)


class Response(BaseModel):
    timezone: str
    daily_units: DailyUnits
    daily: DailyValues


def forecast(settings, latitude: Decimal, longitude: Decimal, timezone: str, first_day: date):
    dates = [first_day + timedelta(days=offset) for offset in range(DAYS)]
    params = {
        "latitude": str(latitude),
        "longitude": str(longitude),
        "timezone": timezone,
        "start_date": str(dates[0]),
        "end_date": str(dates[-1]),
        "daily": FIELDS,
        "temperature_unit": "celsius",
        "precipitation_unit": "mm",
    }
    host = "api.open-meteo.com"
    if settings.open_meteo_api_key is not None:
        host = "customer-api.open-meteo.com"
        params["apikey"] = settings.open_meteo_api_key.get_secret_value()
    connection = http.client.HTTPSConnection(host, timeout=5)
    try:
        connection.request("GET", "/v1/forecast?" + urlencode(params))
        response = connection.getresponse()
        if response.status != 200:
            raise Unavailable
        payload = response.read(MAX_BYTES + 1)
        if len(payload) > MAX_BYTES:
            raise Unavailable
        data = Response.model_validate(json.loads(payload))
        daily = data.daily
        if data.timezone != timezone or daily.time != [str(day) for day in dates]:
            raise Unavailable
        days = []
        for day, minimum, maximum, precipitation in zip(
            dates,
            daily.temperature_2m_min,
            daily.temperature_2m_max,
            daily.precipitation_sum,
            strict=True,
        ):
            if minimum > maximum:
                raise Unavailable
            days.append(
                Day(date=day, minimum_c=minimum, maximum_c=maximum, precipitation_mm=precipitation)
            )
        return days
    except OSError, ValueError, http.client.HTTPException:
        raise Unavailable from None
    finally:
        connection.close()

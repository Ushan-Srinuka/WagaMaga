"""Check the bounded wire contract against a deterministic provider double."""

import json
from datetime import date
from decimal import Decimal
from urllib.parse import parse_qs, urlsplit

import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.integrations import open_meteo

FIRST = date(2026, 11, 23)


def source():
    return {
        "timezone": "Asia/Colombo",
        "daily_units": {
            "time": "iso8601",
            "temperature_2m_min": "°C",
            "temperature_2m_max": "°C",
            "precipitation_sum": "mm",
        },
        "daily": {
            "time": ["2026-11-23", "2026-11-24", "2026-11-25"],
            "temperature_2m_min": [23.1, 24, 24],
            "temperature_2m_max": [31, 30, 30],
            "precipitation_sum": [1, 9.5, 0],
        },
    }


def stub(monkeypatch, payload, *, status=200):
    seen = {}

    class Provider:
        def __init__(self, host, timeout):
            seen["host"] = host
            seen["timeout"] = timeout
            self.status = status

        def request(self, method, path):
            seen["method"] = method
            seen["params"] = parse_qs(urlsplit(path).query)

        def getresponse(self):
            return self

        def read(self, length):
            return payload[:length]

        def close(self):
            seen["closed"] = True

    monkeypatch.setattr(open_meteo.http.client, "HTTPSConnection", Provider)
    return seen


@pytest.mark.parametrize("paid", [False, True])
def test_forecast_uses_dates_coordinates_and_correct_endpoint(monkeypatch, paid):
    seen = stub(monkeypatch, json.dumps(source()).encode())
    settings = Settings(_env_file=None, open_meteo_api_key=SecretStr("test-key") if paid else None)
    days = open_meteo.forecast(settings, Decimal("8.31"), Decimal("80.40"), "Asia/Colombo", FIRST)
    assert [day.precipitation_mm for day in days] == [1.0, 9.5, 0.0]
    assert seen["host"] == ("customer-api.open-meteo.com" if paid else "api.open-meteo.com")
    assert seen["method"] == "GET" and seen["closed"]
    assert seen["params"] == {
        "latitude": ["8.31"],
        "longitude": ["80.40"],
        "timezone": ["Asia/Colombo"],
        "start_date": ["2026-11-23"],
        "end_date": ["2026-11-25"],
        "daily": [open_meteo.FIELDS],
        "temperature_unit": ["celsius"],
        "precipitation_unit": ["mm"],
        **({"apikey": ["test-key"]} if paid else {}),
    }


@pytest.mark.parametrize(
    ("section", "key", "wrong"),
    [
        ("daily", "time", ["2026-11-22", "2026-11-23", "2026-11-24"]),
        ("daily", "precipitation_sum", [-1, 3, 4]),
        ("daily", "precipitation_sum", [None, 3, 4]),
        ("daily", "temperature_2m_min", [90, 23, 21]),
        ("daily_units", "precipitation_sum", "inch"),
    ],
)
def test_rejects_malformed_or_misaligned_provider_data(monkeypatch, section, key, wrong):
    bad = source()
    bad[section][key] = wrong
    seen = stub(monkeypatch, json.dumps(bad).encode())
    with pytest.raises(open_meteo.Unavailable):
        open_meteo.forecast(
            Settings(_env_file=None), Decimal("8.31"), Decimal("80.40"), "Asia/Colombo", FIRST
        )
    assert seen["closed"]


@pytest.mark.parametrize(("status", "payload"), [(503, b"{}"), (200, b"x" * 16385)])
def test_reports_unavailable_on_provider_or_size_failure(monkeypatch, status, payload):
    seen = stub(monkeypatch, payload, status=status)
    with pytest.raises(open_meteo.Unavailable):
        open_meteo.forecast(
            Settings(_env_file=None), Decimal("8.31"), Decimal("80.40"), "Asia/Colombo", FIRST
        )
    assert seen["closed"]

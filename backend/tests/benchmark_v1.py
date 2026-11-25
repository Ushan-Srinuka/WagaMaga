"""Opt-in local V1 CRUD timing on the dedicated PostgreSQL test database."""

from concurrent.futures import ThreadPoolExecutor
from math import ceil
from statistics import median
from threading import Barrier
from time import perf_counter

import pytest
from sqlalchemy import text

PREFIX = "/api/v1"
USERS = 10
ITERATIONS = 10


@pytest.mark.integration
def test_v1_crud_latency(account_client, accounts):
    password = "Synthetic benchmark password 1!"
    identities = []
    for index in range(USERS):
        email = f"v1-benchmark-{index}@example.com"
        credentials = {"email": email, "password": password}
        response = account_client.post(
            f"{PREFIX}/auth/register",
            json={**credentials, "display_name": f"Synthetic farmer {index}"},
        )
        assert response.status_code == 200
        response = account_client.post(f"{PREFIX}/auth/login", json=credentials)
        assert response.status_code == 200
        identities.append({"Authorization": f"Bearer {response.json()['access_token']}"})

    start = Barrier(USERS)

    def farm_workflow(entry):
        index, headers = entry
        timings = []

        def measure(method, path, expected, **kwargs):
            began = perf_counter()
            response = account_client.request(method, PREFIX + path, headers=headers, **kwargs)
            timings.append((method, (perf_counter() - began) * 1000))
            assert response.status_code == expected
            return response.json()

        start.wait(timeout=10)
        for iteration in range(ITERATIONS):
            farm = measure(
                "POST",
                "/farms",
                201,
                json={"name": f"Synthetic {index}-{iteration}", "location": "Synthetic location"},
            )
            path = f"/farms/{farm['id']}"
            saved = measure("GET", path, 200)
            updated = measure(
                "PATCH", path, 200, json={"expected_version": saved["version"], "name": "Updated"}
            )
            assert updated["name"] == "Updated"
        return timings

    with ThreadPoolExecutor(max_workers=USERS) as pool:
        samples = [
            timing for group in pool.map(farm_workflow, enumerate(identities)) for timing in group
        ]

    def report(label, values):
        ordered = sorted(values)
        p95 = ordered[ceil(len(ordered) * 0.95) - 1]
        print(f"{label}: n={len(ordered)} p50={median(ordered):.1f} ms p95={p95:.1f} ms")

    report("All CRUD", [elapsed for _, elapsed in samples])
    for method in ("POST", "GET", "PATCH"):
        report(method, [elapsed for verb, elapsed in samples if verb == method])
    with accounts[1].connect() as connection:
        print("Passages:", connection.scalar(text("SELECT count(*) FROM knowledge_passages")))

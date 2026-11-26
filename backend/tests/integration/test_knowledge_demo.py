"""Verify the demo lifecycle and evidence storage on PostgreSQL."""

import subprocess
import sys
from hashlib import sha256
from io import BytesIO
from time import monotonic, sleep
from uuid import uuid4

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from app.modules.knowledge import processing
from app.modules.knowledge.pdf_text import MAX_BYTES
from app.modules.knowledge.processing import process_one

pytestmark = pytest.mark.integration
PATH = "/api/v1/admin/knowledge/sources"


def login(client, who):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": f"{who}@example.com", "password": "a synthetic growing season password 1!"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_demo_requires_review_and_records_each_decision(account_client, accounts):
    headers = login(account_client, "admin")
    assert (
        account_client.post(
            PATH, headers=headers, json={"template": "chilli-demo", "content": "untrusted"}
        ).status_code
        == 422
    )
    response = account_client.post(PATH, headers=headers, json={"template": "chilli-demo"})
    assert response.status_code == 201
    draft = response.json()
    version = f"{PATH}/{draft['id']}"

    def change(action, revision):
        return account_client.post(
            f"{version}/{action}", headers=headers, json={"expected_revision": revision}
        )

    assert draft["status"] == "draft"
    assert change("publish", 1).status_code == 409
    assert change("review", 1).json()["status"] == "reviewed"
    assert change("publish", 1).status_code == 409
    assert change("publish", 2).json()["status"] == "published"
    assert change("discard", 3).status_code == 409
    assert change("withdraw", 3).json()["status"] == "withdrawn"
    assert change("publish", 4).status_code == 409
    listed = account_client.get(PATH, headers=headers).json()["items"]
    assert listed == [dict(draft, status="withdrawn", revision=4)]
    with accounts[1].connect() as connection:
        assert connection.execute(
            text("SELECT status FROM knowledge_demo_decisions ORDER BY revision")
        ).scalars().all() == ["draft", "reviewed", "published", "withdrawn"]

    for sql in (
        "UPDATE knowledge_demo_versions SET content = 'replacement'",
        "DELETE FROM knowledge_demo_decisions",
    ):
        with pytest.raises(ProgrammingError), accounts[1].begin() as connection:
            connection.execute(text(sql))


@pytest.mark.parametrize(("who", "status"), [(None, 401), ("farmer", 403), ("advisor", 403)])
def test_demo_rejects_non_administrators(account_client, who, status):
    headers = login(account_client, who) if who else {}
    assert account_client.get(PATH, headers=headers).status_code == status
    assert (
        account_client.post(PATH, headers=headers, json={"template": "chilli-demo"}).status_code
        == status
    )
    assert (
        account_client.post(
            f"{PATH}/{uuid4()}/publish", headers=headers, json={"expected_revision": 2}
        ).status_code
        == status
    )


def sample_pdf(labels=("Synthetic nursery notes", "Synthetic field notes"), *, blank=False):
    writer = PdfWriter()
    for label in labels:
        page = writer.add_blank_page(width=300, height=300)
        if blank:
            continue
        page[NameObject("/Resources")] = DictionaryObject(
            {
                NameObject("/Font"): DictionaryObject(
                    {
                        NameObject("/F1"): DictionaryObject(
                            {
                                NameObject("/Type"): NameObject("/Font"),
                                NameObject("/Subtype"): NameObject("/Type1"),
                                NameObject("/BaseFont"): NameObject("/Helvetica"),
                            }
                        )
                    }
                )
            }
        )
        contents = DecodedStreamObject()
        contents.set_data(f"BT /F1 12 Tf 25 250 Td ({label}) Tj ET".encode())
        page.replace_contents(contents)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_production_pdf_requires_screening_and_a_version_bound_advisor_decision(
    account_client, accounts, farm_records, monkeypatch
):
    import json

    client = account_client
    settings = client.app.state.settings
    advisor_path = "/api/v1/advisor/knowledge"
    admin = login(client, "admin")
    farmer = login(client, "farmer")
    advisor = login(client, "advisor")
    with accounts[2].begin() as db:
        db.execute(text("UPDATE users SET role='advisor' WHERE email='second-admin@example.com'"))
    other_advisor = login(client, "second-admin")
    content = sample_pdf()
    metadata = json.dumps(
        {
            "publisher": "Synthetic release test",
            "source_url": "https://example.com/review.pdf",
            "reuse_basis": "Synthetic test fixture",
            "language": "en",
            "crop": "chilli",
            "region": "Anuradhapura",
            "published_on": None,
            "valid_until": None,
            "access": "farmers",
        }
    )

    def upload(*, include_metadata=True):
        return client.post(
            PATH + "/pdf",
            content=content,
            headers=admin | {"Content-Type": "application/pdf"},
            params={"title": "Synthetic release PDF"}
            | ({"metadata": metadata} if include_metadata else {}),
        )

    legacy = upload().json()
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "clamav_port", None)
    scores = client.get("/api/v1/admin/knowledge/evaluation/scores/summary", headers=admin)
    assert scores.status_code == 200
    assert scores.json()["independent_review_pending"] is True
    assert not client.get(PATH, headers=admin).json()["upload_available"]
    assert upload().status_code == 503
    assert not process_one(accounts[1], settings)
    monkeypatch.setattr(settings, "clamav_port", 3310)
    assert upload(include_metadata=False).status_code == 422

    monkeypatch.setattr(processing.clamav, "scan", lambda _original, _port: "scan_rejected")
    rejected = upload().json()
    assert process_one(accounts[1], settings)
    rejected_path = f"{PATH}/{rejected['id']}"
    assert client.get(rejected_path + "/pages", headers=admin).status_code == 409
    assert client.post(rejected_path + "/retry-pdf", headers=admin, json={}).status_code == 409
    with accounts[1].connect() as db:
        stored = db.execute(
            text("SELECT original, error FROM knowledge_source_pdfs WHERE version_id=:id"),
            {"id": rejected["id"]},
        ).one()
        assert stored == (None, "scan_rejected")

    screened = upload().json()
    assert screened["screening_required"] is True
    version = f"{PATH}/{screened['id']}"
    assignment = version + "/advisor-review"
    assigned = f"{advisor_path}/{screened['id']}"

    def change(action, revision):
        return client.post(
            f"{version}/{action}", headers=admin, json={"expected_revision": revision}
        )

    def assign(email, sequence):
        return client.patch(
            assignment, headers=admin, json={"expected_sequence": sequence, "advisor_email": email}
        )

    def decide(headers, sequence, outcome="approved"):
        return client.post(
            assigned + "/decision",
            headers=headers,
            json={
                "expected_sequence": sequence,
                "outcome": outcome,
                "reason": "Checked synthetic scope.",
            },
        )

    monkeypatch.setattr(processing.clamav, "scan", lambda _original, _port: "scan_unavailable")
    assert process_one(accounts[1], settings)
    assert client.get(assignment, headers=admin).status_code == 404
    assert change("review", 1).status_code == 409
    assert client.post(version + "/retry-pdf", headers=admin, json={}).status_code == 200

    def clean(original, port):
        assert original == content and port == 3310
        return None

    monkeypatch.setattr(processing.clamav, "scan", clean)
    assert process_one(accounts[1], settings)
    assert not process_one(accounts[1], settings)
    assert client.get(f"{PATH}/{legacy['id']}/pages", headers=admin).status_code == 409
    assert change("review", 1).status_code == 409
    assert client.get(assignment, headers=admin).json() == {"review": None}
    assert client.get(advisor_path, headers=farmer).status_code == 403
    assert client.get(advisor_path, headers=admin).status_code == 403
    assert client.get(assigned + "/pages/1", headers=advisor).status_code == 404
    assert assign("farmer@example.com", 0).status_code == 422
    assert assign("advisor@example.com", 0).json()["event"] == "assigned"
    listing = client.get(advisor_path, headers=advisor)
    assert listing.status_code == 200, listing.json()
    assert listing.json()["items"][0]["id"] == screened["id"]
    assert client.get(assigned + "/pages/1", headers=advisor).json() == {
        "number": 1,
        "text": "Synthetic nursery notes",
        "total": 2,
    }
    assert client.get(assigned + "/pages/3", headers=advisor).status_code == 404
    assert client.get(assigned + "/pages/1", headers=other_advisor).status_code == 404
    assert client.get(assigned, headers=other_advisor).status_code == 404
    assert assign(None, 1).json()["event"] == "revoked"
    assert client.get(assigned, headers=advisor).status_code == 404
    assert client.get(advisor_path, headers=advisor).json()["items"] == []
    assert decide(advisor, 1).status_code == 404
    assert assign("second-admin@example.com", 2).json()["sequence"] == 3
    assert decide(other_advisor, 1).status_code == 409
    assert decide(other_advisor, 3).json()["event"] == "approved"
    assert client.get(advisor_path + "?view=pending", headers=other_advisor).json()["items"] == []
    [reviewed] = client.get(advisor_path + "?view=reviewed", headers=other_advisor).json()["items"]
    assert reviewed["id"] == screened["id"] and reviewed["assigned_at"]
    assert client.get(assigned, headers=other_advisor).json() == reviewed
    assert decide(other_advisor, 3).status_code == 409
    assert assign("advisor@example.com", 4).status_code == 409
    assert change("review", 1).json()["status"] == "reviewed"
    assert change("publish", 2).json()["status"] == "published"
    assert client.get(assigned + "/pages/1", headers=other_advisor).status_code == 404
    farm = farm_records["farmer"]
    owned = f"/api/v1/farms/{farm['farm']}"
    location = client.patch(
        owned,
        headers=farmer,
        json={"expected_version": 1, "location": "Synthetic village, Anuradhapura"},
    )
    assert location.status_code == 200
    search = client.post(
        f"{owned}/cultivations/{farm['cultivation']}/reviewed-sources/search",
        headers=farmer,
        json={"question": "nursery"},
    )
    assert search.status_code == 200
    [passage] = search.json()["items"]
    assert passage["version_id"] == screened["id"]
    assert passage["source_url"] == "https://example.com/review.pdf"
    assert passage["reuse_basis"] == "Synthetic test fixture"
    with pytest.raises(ProgrammingError), accounts[1].begin() as db:
        db.execute(text("DELETE FROM knowledge_source_review_events"))


def test_pdf_upload_requires_processing_then_review(account_client, accounts):
    admin = login(account_client, "admin")
    farmer = login(account_client, "farmer")
    raw = sample_pdf()

    def upload(data, headers=admin):
        return account_client.post(
            PATH + "/pdf", headers={**headers, "Content-Type": "application/pdf"}, content=data
        )

    assert upload(raw, farmer).status_code == 403
    assert upload(raw, admin | {"Origin": "https://other.example.com"}).status_code == 403
    assert upload(b"text").status_code == 422
    assert upload(b"%PDF-" + bytes(MAX_BYTES)).status_code == 413
    uploaded = upload(raw)
    assert uploaded.status_code == 201
    version = uploaded.json()
    assert version["checksum"] == sha256(raw).hexdigest()
    assert version["processing"] == "queued"
    url = f"{PATH}/{version['id']}"

    def change(action, revision):
        return account_client.post(
            f"{url}/{action}", headers=admin, json={"expected_revision": revision}
        )

    def search(query="NURSERY notes", headers=admin):
        response = account_client.get(PATH + "/search", headers=headers, params={"q": query})
        assert response.status_code == 200
        return response.json()

    assert account_client.get(PATH + "/search", params={"q": "nursery"}).status_code == 401
    assert (
        account_client.get(PATH + "/search", params={"q": "nursery"}, headers=farmer).status_code
        == 403
    )
    assert search() == []

    assert change("review", 1).status_code == 409
    assert account_client.get(url + "/pages", headers=admin).status_code == 409
    assert process_one(accounts[1]) is True
    assert process_one(accounts[1]) is False
    assert search() == []
    assert account_client.get(url + "/pages", headers=farmer).status_code == 403
    assert account_client.get(url + "/pages", headers=admin).json() == [
        {"number": 1, "text": "Synthetic nursery notes"},
        {"number": 2, "text": "Synthetic field notes"},
    ]
    assert change("publish", 1).status_code == 409
    assert change("review", 1).json()["status"] == "reviewed"
    assert search() == []
    assert change("publish", 2).json()["status"] == "published"
    (result,) = search()
    assert result["version_id"] == version["id"]
    assert result["title"] == version["title"]
    assert result["checksum"] == version["checksum"]
    assert result["number"] == 1
    assert "nursery" in result["excerpt"]
    assert [item["number"] for item in search("field")] == [2]
    assert search("weather") == []
    assert search("!!!") == []
    assert change("withdraw", 3).json()["status"] == "withdrawn"
    assert search() == []


def test_publishing_pdf_replacement_switches_searchable_versions_atomically(
    account_client, accounts
):
    admin = login(account_client, "admin")
    farmer = login(account_client, "farmer")
    pdf_headers = admin | {"Content-Type": "application/pdf"}

    def upload(labels, params, headers=pdf_headers):
        return account_client.post(
            PATH + "/pdf", headers=headers, params=params, content=sample_pdf(labels)
        )

    def change(source, action, revision):
        return account_client.post(
            f"{PATH}/{source['id']}/{action}",
            headers=admin,
            json={"expected_revision": revision},
        )

    def search():
        result = account_client.get(PATH + "/search", headers=admin, params={"q": "nursery"})
        assert result.status_code == 200
        return [item["version_id"] for item in result.json()]

    original = upload(("Old nursery notes",), {"title": "Chilli reference"}).json()
    assert process_one(accounts[1])
    assert change(original, "review", 1).status_code == 200
    assert change(original, "publish", 2).status_code == 200
    params = {"replaces": original["id"]}
    farmer_pdf = farmer | {"Content-Type": "application/pdf"}
    assert upload(("New nursery notes",), params, farmer_pdf).status_code == 403
    assert upload(("Old nursery notes",), params).status_code == 409
    draft = upload(("New nursery notes",), params)
    assert draft.status_code == 201
    replacement = draft.json()
    assert replacement["title"] == "Chilli reference"
    assert replacement["replaces_version_id"] == original["id"]
    assert upload(("Third nursery notes",), params).status_code == 409
    assert change(replacement, "review", 1).status_code == 409
    assert search() == [original["id"]]
    assert process_one(accounts[1])
    assert change(replacement, "review", 1).status_code == 200
    assert search() == [original["id"]]
    assert change(replacement, "publish", 2).status_code == 200
    assert search() == [replacement["id"]]
    sources = account_client.get(PATH, headers=admin).json()["items"]
    assert {source["id"]: source["status"] for source in sources} == {
        original["id"]: "withdrawn",
        replacement["id"]: "published",
    }
    assert account_client.get(f"{PATH}/{original['id']}/pages", headers=admin).json() == [
        {"number": 1, "text": "Old nursery notes"},
    ]


def test_transient_pdf_failure_can_be_retried_by_administrator(
    account_client, accounts, monkeypatch
):
    admin = login(account_client, "admin")
    farmer = login(account_client, "farmer")
    uploaded = account_client.post(
        PATH + "/pdf",
        headers=admin | {"Content-Type": "application/pdf"},
        content=sample_pdf(),
    )
    assert uploaded.status_code == 201
    version = uploaded.json()
    retry = PATH + "/" + version["id"] + "/retry-pdf"
    with monkeypatch.context() as patch:
        patch.setattr(processing, "extract_pdf", lambda _: {"error": "timed_out"})
        assert process_one(accounts[1])
    [failed] = account_client.get(PATH, headers=admin).json()["items"]
    assert failed["processing"] == "failed" and failed["retryable"]
    assert account_client.post(retry, headers=farmer, json={}).status_code == 403
    queued = account_client.post(retry, headers=admin, json={})
    assert queued.status_code == 200 and queued.json()["processing"] == "queued"
    assert queued.json()["checksum"] == version["checksum"]
    assert account_client.post(retry, headers=admin, json={}).status_code == 409
    assert process_one(accounts[1])
    assert not process_one(accounts[1])
    [ready] = account_client.get(PATH, headers=admin).json()["items"]
    assert ready["processing"] == "ready" and not ready["retryable"]


def test_pdf_queue_recovers_after_worker_process_dies(account_client, accounts, tmp_path):
    admin = login(account_client, "admin")
    queued = account_client.post(
        PATH + "/pdf",
        headers=admin | {"Content-Type": "application/pdf"},
        content=sample_pdf(),
    )
    assert queued.status_code == 201
    version_id = queued.json()["id"]
    marker = tmp_path / "extraction-started"
    worker_code = """
import os
import sys
from pathlib import Path
from threading import Event
from sqlalchemy.engine import make_url
from app.core.config import Settings
from app.modules.knowledge import processing

url = Settings().test_database_url.get_secret_value()
assert (make_url(url).database or "").endswith("_test")
os.environ.update(
    DATABASE_URL=url, APP_ENV="test",
    OPEN_METEO_API_KEY="", OPEN_METEO_NONCOMMERCIAL="false",
)
if len(sys.argv) > 1:
    marker = Path(sys.argv[1])
    def pause_after_claim(_original):
        marker.touch()
        Event().wait()
    processing.extract_pdf = pause_after_claim

from app.worker.__main__ import main
del sys.argv[1:]
raise SystemExit(main())
"""

    def wait_for(worker, done):
        until = monotonic() + 15
        while monotonic() < until:
            assert worker.poll() is None
            if done():
                return
            sleep(0.1)
        pytest.fail("PDF worker did not reach the expected state.")

    with subprocess.Popen([sys.executable, "-c", worker_code, str(marker)]) as interrupted:
        try:
            wait_for(interrupted, marker.is_file)
            assert not process_one(accounts[1])  # The live worker owns the row lock.
        finally:
            interrupted.kill()
            interrupted.wait(timeout=10)

    page_path = f"{PATH}/{version_id}/pages"
    assert account_client.get(page_path, headers=admin).status_code == 409

    with subprocess.Popen([sys.executable, "-c", worker_code]) as restarted:
        try:
            wait_for(
                restarted, lambda: account_client.get(page_path, headers=admin).status_code == 200
            )
        finally:
            restarted.terminate()
            restarted.wait(timeout=10)
    assert account_client.get(page_path, headers=admin).json() == [
        {"number": 1, "text": "Synthetic nursery notes"},
        {"number": 2, "text": "Synthetic field notes"},
    ]
    assert not process_one(accounts[1])


@pytest.mark.parametrize("process", [False, True])
def test_remove_unpublished_pdf(account_client, accounts, process):
    admin = login(account_client, "admin")
    farmer = login(account_client, "farmer")
    response = account_client.post(
        PATH + "/pdf",
        headers={**admin, "Content-Type": "application/pdf"},
        content=sample_pdf(),
    )
    assert response.status_code == 201
    version = response.json()
    url = f"{PATH}/{version['id']}"
    if process:
        assert process_one(accounts[1])
    assert (
        account_client.post(
            url + "/discard", headers=farmer, json={"expected_revision": 1}
        ).status_code
        == 403
    )
    assert (
        account_client.post(
            url + "/discard", headers=admin, json={"expected_revision": 2}
        ).status_code
        == 409
    )
    removed = account_client.post(url + "/discard", headers=admin, json={"expected_revision": 1})
    assert removed.json()["status"] == "discarded"
    assert account_client.get(PATH, headers=admin).json()["items"] == []
    assert account_client.get(url + "/pages", headers=admin).status_code == 404
    for action in ("discard", "review"):
        assert (
            account_client.post(
                f"{url}/{action}", headers=admin, json={"expected_revision": 2}
            ).status_code
            == 404
        )
    assert not process_one(accounts[1])
    with accounts[1].connect() as connection:
        assert connection.execute(
            text("SELECT status FROM knowledge_demo_decisions ORDER BY revision")
        ).scalars().all() == ["draft", "discarded"]


@pytest.mark.parametrize("issue", ["invalid_pdf", "no_text"])
def test_pdf_processing_failure_stays_unpublishable(account_client, accounts, issue):
    admin = login(account_client, "admin")
    data = sample_pdf(blank=True) if issue == "no_text" else b"%PDF-1.7\ninvalid"
    uploaded = account_client.post(
        PATH + "/pdf", headers={**admin, "Content-Type": "application/pdf"}, content=data
    )
    assert uploaded.status_code == 201
    assert process_one(accounts[1]) is True
    item = account_client.get(PATH, headers=admin).json()["items"][0]
    assert item["processing"] == "failed"
    assert item["processing_error"] == issue
    for action in ("review", "publish"):
        response = account_client.post(
            f"{PATH}/{item['id']}/{action}", headers=admin, json={"expected_revision": 1}
        )
        assert response.status_code == 409

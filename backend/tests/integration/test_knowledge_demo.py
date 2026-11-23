"""Verify the demo lifecycle and evidence storage on PostgreSQL."""

from hashlib import sha256
from io import BytesIO
from uuid import uuid4

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

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


def sample_pdf(*, blank=False):
    writer = PdfWriter()
    for label in ("Synthetic nursery notes", "Synthetic field notes"):
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

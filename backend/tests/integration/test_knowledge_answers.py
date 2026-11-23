"""Verify retrieval, provider boundaries and citation validation on PostgreSQL."""

from pydantic import SecretStr

from app.integrations import gemini
from app.modules.knowledge import preview_fixture
from app.modules.knowledge.processing import process_one

PATH = "/api/v1/admin/knowledge/sources"


def login(client, who):
    result = client.post(
        "/api/v1/auth/login",
        json={"email": f"{who}@example.com", "password": "a synthetic growing season password 1!"},
    )
    assert result.status_code == 200
    return {"Authorization": f"Bearer {result.json()['access_token']}"}


def test_gemini_preview_sends_only_fixed_evidence_from_published_fixture(
    account_client, accounts, monkeypatch
):
    client = account_client
    admin = login(client, "admin")
    farmer = login(client, "farmer")
    settings = client.app.state.settings
    monkeypatch.setattr(settings, "gemini_api_key", None)
    calls = []
    response = gemini.Quote(citation_id="C1", quote=preview_fixture.PAGES[0])

    def provider(settings, question, passages):
        calls.append((question, passages))
        return response

    monkeypatch.setattr(gemini, "select_quote", provider)

    def ask(question="nursery", headers=admin):
        return client.post(PATH + "/answer", headers=headers, json={"question": question})

    assert ask(headers={}).status_code == 401
    assert ask(headers=farmer).status_code == 403
    assert ask("Private free-form text").status_code == 422
    assert ask().json() == {"status": "no_evidence"}
    uploaded = client.post(
        PATH + "/pdf",
        headers={**admin, "Content-Type": "application/pdf"},
        content=preview_fixture.PDF.replace(b"DEMO-NURSERY-A", b"PRIVATE-FAKE-A"),
    ).json()
    assert process_one(accounts[1])
    for action, revision in (("review", 1), ("publish", 2)):
        assert (
            client.post(
                f"{PATH}/{uploaded['id']}/{action}",
                headers=admin,
                json={"expected_revision": revision},
            ).status_code
            == 200
        )
    assert client.get(PATH + "/search", headers=admin, params={"q": "nursery"}).json()
    assert ask().json() == {"status": "no_evidence"}
    added = client.post(PATH, headers=admin, json={"template": "gemini-preview-pdf"})
    assert added.status_code == 201
    source = added.json()
    assert source["checksum"] == preview_fixture.CHECKSUM
    assert ask().json() == {"status": "no_evidence"}
    assert process_one(accounts[1])

    def change(action, revision):
        return client.post(
            f"{PATH}/{source['id']}/{action}", headers=admin, json={"expected_revision": revision}
        )

    assert ask().json() == {"status": "no_evidence"}
    assert change("review", 1).status_code == 200
    assert change("publish", 2).status_code == 200
    assert ask().json()["code"] == "GEMINI_NOT_CONFIGURED"
    assert ask("forecast").json() == {"status": "no_evidence"}
    assert calls == []
    monkeypatch.setattr(settings, "gemini_api_key", SecretStr("test-double-key"))
    result = ask()
    assert result.status_code == 200
    assert result.json()["answer"] == preview_fixture.PAGES[0]
    assert result.json()["citation"]["version_id"] == source["id"]
    assert result.json()["citation"]["number"] == 1
    assert calls == [
        (
            preview_fixture.QUESTIONS["nursery"][0],
            [{"citation_id": "C1", "text": preview_fixture.PAGES[0]}],
        )
    ]
    response = gemini.Quote(citation_id="C9", quote=preview_fixture.PAGES[0])
    assert ask().json()["code"] == "INVALID_CITATION"
    response = gemini.Quote(citation_id="C1", quote="Unsupported words")
    assert ask().json()["code"] == "INVALID_CITATION"
    response = gemini.Quote(citation_id="", quote="")
    assert ask().json() == {"status": "no_evidence"}
    assert change("withdraw", 3).status_code == 200
    assert ask().json() == {"status": "no_evidence"}
    assert len(calls) == 4

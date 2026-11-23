"""Verify evaluation eligibility, case labels and retained review history."""

import pytest
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from app.core.config import LocalNurseryReference
from app.integrations import gemini
from app.modules.knowledge import farmer_demo, preview_fixture, processing
from app.modules.knowledge.processing import process_one

pytestmark = pytest.mark.integration
ROOT = "/api/v1/admin/knowledge"


def login(client, who):
    result = client.post(
        "/api/v1/auth/login",
        json={"email": f"{who}@example.com", "password": "a synthetic growing season password 1!"},
    )
    assert result.status_code == 200
    return {"Authorization": f"Bearer {result.json()['access_token']}"}


def test_admin_can_label_only_retrieved_published_pages(account_client, accounts):
    client = account_client
    admin = login(client, "admin")
    farmer = login(client, "farmer")
    endpoint = f"{ROOT}/evaluation/CH-01"
    assert client.get(ROOT + "/evaluation").status_code == 401
    assert client.get(endpoint, headers=farmer).status_code == 403
    assert client.get(f"{ROOT}/evaluation/CH-11", headers=admin).status_code == 404
    cases = client.get(f"{ROOT}/evaluation", headers=admin).json()
    assert [case["id"] for case in cases] == [f"CH-{n:02}" for n in range(1, 11)]

    def read():
        result = client.get(endpoint, headers=admin)
        assert result.status_code == 200
        return result.json()

    def decide(revision, outcome, **fields):
        return client.post(
            endpoint + "/decisions",
            headers=admin,
            json={"expected_revision": revision, "outcome": outcome, **fields},
        )

    assert read()["pages"] == []
    assert decide(0, "suitable").status_code == 422
    assert decide(0, "missing", note="No eligible source yet.").status_code == 201
    assert read()["missing"]["note"] == "No eligible source yet."

    sources = ROOT + "/sources"
    fixture = client.post(sources, headers=admin, json={"template": "gemini-preview-pdf"}).json()
    pdf = preview_fixture.PDF.replace(b"DEMO-NURSERY-A", b"CASE-NURSERY-A")
    result = client.post(
        sources + "/pdf", headers={**admin, "Content-Type": "application/pdf"}, content=pdf
    )
    assert result.status_code == 201
    source = result.json()
    while process_one(accounts[1]):
        pass
    assert read()["pages"] == []
    reference = {"version_id": source["id"], "page_number": 1}
    assert decide(1, "suitable", **reference).status_code == 409
    for item in (fixture, source):
        for action, rev in (("review", 1), ("publish", 2)):
            assert (
                client.post(
                    f"{sources}/{item['id']}/{action}",
                    headers=admin,
                    json={"expected_revision": rev},
                ).status_code
                == 200
            )
    pages = read()["pages"]
    assert [(page["version_id"], page["number"]) for page in pages] == [(source["id"], 1)]
    assert decide(1, "suitable", version_id=source["id"], page_number=2).status_code == 409
    assert decide(1, "out_of_scope", **reference).status_code == 201
    assert read()["pages"][0]["decision"]["outcome"] == "out_of_scope"
    assert decide(1, "suitable", **reference).status_code == 409
    assert decide(2, "suitable", **reference).status_code == 201
    assert read()["missing"] is None
    assert read()["pages"][0]["decision"]["outcome"] == "suitable"
    assert decide(3, "missing").status_code == 409
    assert (
        client.post(
            f"{sources}/{source['id']}/withdraw", headers=admin, json={"expected_revision": 3}
        ).status_code
        == 200
    )
    assert read()["pages"] == []
    assert decide(3, "suitable", **reference).status_code == 409
    with accounts[1].connect() as connection:
        assert connection.execute(
            text("SELECT outcome FROM knowledge_evaluation_decisions ORDER BY revision")
        ).scalars().all() == ["missing", "out_of_scope", "suitable"]
    with pytest.raises(ProgrammingError), accounts[1].begin() as connection:
        connection.execute(text("DELETE FROM knowledge_evaluation_decisions"))


def test_sinhala_draft_matches_stay_in_admin_preview(account_client, accounts, monkeypatch):
    client = account_client
    admin = login(client, "admin")
    farmer = login(client, "farmer")
    sources = ROOT + "/sources"
    endpoint = ROOT + "/evaluation/CH-01"
    matching_text = "තවාන් සඳහා සුදුසු ස්ථානයක්"
    monkeypatch.setattr(
        processing, "extract_pdf", lambda _: {"pages": ["Unrelated page"] * 25 + [matching_text]}
    )

    def upload(tag):
        original = preview_fixture.PDF.replace(b"DEMO-NURSERY-A", tag)
        response = client.post(
            sources + "/pdf", headers={**admin, "Content-Type": "application/pdf"}, content=original
        )
        assert response.status_code == 201
        return response.json()["id"]

    first = upload(b"CASE-NURSERY-A")
    second = upload(b"CASE-NURSERY-B")
    translation = "Choose a suitable site for the nursery."
    draft_fields = {
        "version_id": first,
        "page_number": 26,
        "excerpt": matching_text,
        "english_translation": translation,
    }

    def unexpected_provider(*args):
        pytest.fail("Draft preview attempted a provider call")

    monkeypatch.setattr(gemini, "select_quote", unexpected_provider)

    def answer(headers=admin, **fields):
        return client.post(
            endpoint + "/draft-answer", headers=headers, json={**draft_fields, **fields}
        )

    def preview(version_id, headers=admin, *, case=endpoint):
        return client.get(
            case + "/draft-matches", headers=headers, params={"version_id": version_id}
        )

    assert preview(first, {}).status_code == 401
    assert preview(first, farmer).status_code == 403
    assert preview(first).status_code == 404
    assert answer().status_code == 404
    assert process_one(accounts[1])
    assert process_one(accounts[1])

    for version_id in (first, second):
        result = preview(version_id)
        assert result.status_code == 200
        pages = result.json()["pages"]
        assert [(page["version_id"], page["number"]) for page in pages] == [(version_id, 26)]
        assert "තවාන්" in pages[0]["excerpt"]
    assert preview(first, case=ROOT + "/evaluation/CH-08").json()["pages"] == []
    assert answer({}).status_code == 401
    assert answer(farmer).status_code == 403
    assert answer({**admin, "Origin": "https://example.com"}).status_code == 403
    assert answer(page_number=25).status_code == 409
    assert answer(excerpt="සිංහල").status_code == 422
    assert answer(english_translation=matching_text).status_code == 422
    result = answer()
    assert result.status_code == 200
    assert result.json()["answer"] == translation
    assert result.json()["citation"]["excerpt"] == matching_text
    assert result.json()["citation"]["version_id"] == first
    assert result.json()["citation"]["number"] == 26
    with accounts[1].connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM knowledge_evaluation_decisions")) == 0
        assert connection.scalar(text("SELECT count(*) FROM knowledge_evaluation_runs")) == 0
    assert client.get(endpoint, headers=admin).json()["pages"] == []
    assert client.get(sources + "/search", params={"q": "තවාන්"}, headers=admin).json() == []
    assert (
        client.post(
            f"{sources}/{first}/review",
            headers=admin,
            json={"expected_revision": 1},
        ).status_code
        == 200
    )
    assert preview(first).status_code == 404
    assert answer().status_code == 404


@pytest.mark.parametrize("sinhala", [False, True], ids=["english", "translated-page-26"])
def test_scoring_releases_only_current_reviewed_citations(
    account_client, accounts, monkeypatch, sinhala
):
    client = account_client
    admin = login(client, "admin")
    farmer = login(client, "farmer")
    settings = client.app.state.settings
    monkeypatch.setattr(settings, "gemini_api_key", SecretStr("fake-pilot-key"))
    monkeypatch.setattr(settings, "farmer_advisory_enabled", True)
    monkeypatch.setattr(settings, "gemini_approved_pdf_checksums", set())
    calls = []
    excerpt = preview_fixture.PAGES[0].replace("DEMO-NURSERY-A", "CASE-NURSERY-A")
    page_number = 1
    translation = ""
    if sinhala:
        excerpt = "තවාන් සඳහා සුදුසු ස්ථානයක් තෝරන්න."
        translation = "Choose a suitable site for the nursery."
        page_number = 26
        monkeypatch.setattr(
            processing, "extract_pdf", lambda _: {"pages": ["Unrelated page"] * 25 + [excerpt]}
        )
    expected_answer = translation or excerpt
    returned = gemini.Quote(citation_id="invented", quote=expected_answer)

    def fake_provider(settings, question, passages):
        calls.append((question, passages))
        return returned

    monkeypatch.setattr(gemini, "select_quote", fake_provider)
    farmer_url = "/api/v1/knowledge/chilli"
    evaluation = f"{ROOT}/evaluation"
    scores = evaluation + "/scores"
    assert client.get(farmer_url, headers=farmer).json() == {"released": False, "cases": []}
    assert client.get(farmer_url, headers=admin).status_code == 403
    assert client.post(f"{scores}/CH-01", headers=farmer, json={}).status_code == 403
    assert client.post(f"{scores}/CH-01", headers=admin, json={}).status_code == 409
    pdf = preview_fixture.PDF.replace(b"DEMO-NURSERY-A", b"CASE-NURSERY-A")
    result = client.post(
        ROOT + "/sources/pdf", headers={**admin, "Content-Type": "application/pdf"}, content=pdf
    )
    assert result.status_code == 201
    source = result.json()
    source_url = f"{ROOT}/sources/{source['id']}"
    assert process_one(accounts[1])
    for action, revision in (("review", 1), ("publish", 2)):
        assert (
            client.post(
                f"{source_url}/{action}", headers=admin, json={"expected_revision": revision}
            ).status_code
            == 200
        )

    label = {
        "expected_revision": 0,
        "outcome": "suitable",
        "version_id": source["id"],
        "page_number": page_number,
    }
    label_url = f"{evaluation}/CH-01/decisions"
    assert (
        client.post(
            label_url, headers=admin, json={**label, "approved_excerpt": "Invented words"}
        ).status_code
        == 422
    )
    if sinhala:
        for fields, code in (
            ({"approved_excerpt": excerpt}, 422),
            ({"approved_excerpt": excerpt, "english_translation": excerpt}, 422),
            (
                {
                    "approved_excerpt": excerpt,
                    "english_translation": translation,
                    "page_number": 101,
                },
                422,
            ),
            (
                {
                    "approved_excerpt": excerpt,
                    "english_translation": translation,
                    "page_number": 25,
                },
                409,
            ),
        ):
            assert (
                client.post(label_url, headers=admin, json={**label, **fields}).status_code == code
            )
    assert (
        client.post(
            label_url,
            headers=admin,
            json={**label, "approved_excerpt": excerpt, "english_translation": translation},
        ).status_code
        == 201
    )
    assert client.post(f"{scores}/CH-01", headers=admin, json={}).status_code == 409
    assert calls == []

    monkeypatch.setattr(settings, "gemini_approved_pdf_checksums", {source["checksum"]})
    assert client.post(f"{scores}/CH-01", headers=admin, json={}).json()["passed"] is False
    if sinhala:
        returned = gemini.Quote(citation_id="C1", quote=excerpt)
        assert client.post(f"{scores}/CH-01", headers=admin, json={}).json()["passed"] is False
    returned = gemini.Quote(citation_id="C1", quote=expected_answer)
    assert client.post(f"{scores}/CH-01", headers=admin, json={}).json()["passed"] is True
    assert client.get(farmer_url, headers=farmer).json()["released"] is False
    for number in range(2, 11):
        case_id = f"CH-{number:02}"
        assert (
            client.post(
                f"{evaluation}/{case_id}/decisions",
                headers=admin,
                json={"expected_revision": 0, "outcome": "missing"},
            ).status_code
            == 201
        )
        check = client.post(f"{scores}/{case_id}", headers=admin, json={}).json()
        assert check["passed"] is True and check["model"] == "local"
    assert len(calls) == (3 if sinhala else 2)
    assert client.get(f"{scores}/summary", headers=admin).json()["released"] is True
    assert len(client.get(farmer_url, headers=farmer).json()["cases"]) == 10
    answer = client.post(farmer_url + "/answer", headers=farmer, json={"case_id": "CH-01"}).json()
    assert answer["answer"] == expected_answer
    assert answer["citation"]["excerpt"] == excerpt
    assert answer["citation"]["version_id"] == source["id"]
    assert answer["citation"]["number"] == page_number
    assert client.post(
        farmer_url + "/answer", headers=farmer, json={"case_id": "CH-08"}
    ).json() == {"status": "no_evidence"}
    assert calls[-1][1] == [{"citation_id": "C1", "text": expected_answer}]
    assert len(calls) == (4 if sinhala else 3)
    page_url = f"{farmer_url}/CH-01/sources/{source['id']}/pages"
    assert client.get(f"{page_url}/{page_number}", headers=farmer).json()["text"] == excerpt
    assert client.get(f"{page_url}/{page_number + 1}", headers=farmer).status_code == 404
    assert (
        client.post(
            source_url + "/withdraw", headers=admin, json={"expected_revision": 3}
        ).status_code
        == 200
    )
    assert client.get(f"{page_url}/{page_number}", headers=farmer).status_code == 403
    assert client.get(farmer_url, headers=farmer).json()["released"] is False


def test_local_farmer_demo_matches_fictional_pdf(account_client, monkeypatch):
    client = account_client
    root = "/api/v1/knowledge/chilli"
    demo = root + "/demo"
    farmer = login(client, "farmer")
    admin = login(client, "admin")
    advisor = login(client, "advisor")
    version = str(farmer_demo.VERSION_ID)
    nursery_page = f"{demo}/nursery/sources/{version}/pages/1"

    def answer(case_id, headers=farmer):
        return client.post(demo + "/answer", headers=headers, json={"case_id": case_id})

    def ask(question, headers=farmer):
        return client.post(demo + "/ask", headers=headers, json={"question": question})

    def unexpected_provider(*args):
        pytest.fail("The farmer demo attempted a provider call")

    monkeypatch.setattr(gemini, "select_quote", unexpected_provider)
    assert client.get(root, headers=farmer).json() == {"released": False, "cases": []}
    for headers, status in (({}, 401), (admin, 403), (advisor, 403)):
        assert client.get(demo, headers=headers).status_code == status
        assert answer("nursery", headers).status_code == status
        assert ask("Which label is on the nursery tray?", headers).status_code == status
        assert client.get(nursery_page, headers=headers).status_code == status
    assert answer("nursery", {**farmer, "Origin": "https://example.com"}).status_code == 403
    assert ask("Nursery label?", {**farmer, "Origin": "https://example.com"}).status_code == 403

    response = client.get(demo, headers=farmer)
    assert response.status_code == 200
    assert [case["id"] for case in response.json()["cases"]] == [
        "nursery",
        "irrigation",
        "fertilizer",
        "forecast",
    ]
    pages = processing.extract_pdf(farmer_demo.PDF)["pages"]
    for case_id, number in (("nursery", 1), ("irrigation", 3), ("fertilizer", 4)):
        response = answer(case_id)
        assert response.status_code == 200
        assert response.json()["answer"] == pages[number - 1]
        citation = response.json()["citation"]
        assert citation["number"] == number
        assert citation["checksum"] == farmer_demo.CHECKSUM
        assert citation["version_id"] == version
        assert citation["excerpt"] == pages[number - 1]
        page = client.get(f"{demo}/{case_id}/sources/{version}/pages/{number}", headers=farmer)
        assert page.json() == {"number": number, "text": pages[number - 1]}
    for question, case_id, number in (
        ("  Which LABEL is on the seedling-tray?  ", "nursery", 1),
        ("What information is recorded in the watering log?", "irrigation", 3),
        ("What fields are in the fertiliser log?", "fertilizer", 4),
    ):
        result = ask(question)
        assert result.status_code == 200
        assert result.json()["case_id"] == case_id
        assert result.json()["answer"] == pages[number - 1]
        assert result.json()["citation"]["number"] == number
        assert result.json()["citation"]["version_id"] == version
        assert ask(farmer_demo.CASES[case_id][0]).json() == result.json()
    for unsupported in (
        "Will it rain tomorrow?",
        "How often should I water chilli?",
        "How much fertilizer should I apply?",
        "What is the irrigation log password?",
        "What do the irrigation and fertilizer logs record?",
        "What is the price of a seedling tray?",
    ):
        assert ask(unsupported).json() == {"status": "no_evidence"}
    assert ask("    ").status_code == 422
    assert ask("X" * 241).status_code == 422
    assert answer("forecast").json() == {"status": "no_evidence"}
    assert answer("unknown").status_code == 404
    assert (
        client.get(f"{demo}/forecast/sources/{version}/pages/1", headers=farmer).status_code == 404
    )
    assert (
        client.get(f"{demo}/nursery/sources/{version}/pages/3", headers=farmer).status_code == 404
    )
    assert (
        client.get(
            f"{demo}/nursery/sources/24529335-d644-4fe4-acfd-8beb4dbbcb7d/pages/1", headers=farmer
        ).status_code
        == 404
    )
    assert client.get(root, headers=farmer).json() == {"released": False, "cases": []}

    monkeypatch.setattr(client.app.state.settings, "app_env", "production")
    assert client.get(demo, headers=farmer).status_code == 404
    assert answer("nursery").status_code == 404
    assert ask("What is the nursery tray label?").status_code == 404
    assert client.get(nursery_page, headers=farmer).status_code == 404


def test_local_search_serves_only_current_approved_passages(account_client, accounts, monkeypatch):
    client = account_client
    admin = login(client, "admin")
    farmer = login(client, "farmer")
    root = "/api/v1/knowledge/chilli"
    local = root + "/local"
    sources = f"{ROOT}/sources"
    fixtures = (
        (
            "CH-01",
            "How do I choose a site for a chili nursery in Anuradhapura?",
            26,
            "තවාන් සඳහා සුදුසු ස්ථානයක් සොයන්න.",
            "Find a suitable site for the nursery.",
        ),
        (
            "CH-04",
            "What should I check before watering newly planted chilli?",
            27,
            "ජල සම්පාදනය සඳහා තෙතමන තත්ත්වය පරීක්ෂා කරන්න.",
            "Check soil moisture conditions for irrigation.",
        ),
        (
            "CH-05",
            "Should I test the soil before choosing basal fertiliser?",
            28,
            "මිරිස් වගාවට පෙර පස් සාම්පල පරීක්ෂණාගාරයට යවන්න.",
            "Send a soil sample to the laboratory before chilli cultivation.",
        ),
    )
    pages = ["Unrelated page"] * 25 + [
        f"{row[3]}\nNursery irrigation fertilizer\n{row[1]}\nEnd of sample page."
        for row in fixtures
    ]
    monkeypatch.setattr(processing, "extract_pdf", lambda _: {"pages": pages})

    def unexpected_provider(*args):
        pytest.fail("Local reviewed answers attempted a provider call")

    monkeypatch.setattr(gemini, "select_quote", unexpected_provider)

    def ask(question, headers=farmer):
        return client.post(local + "/ask", headers=headers, json={"question": question})

    def transition(version, action, revision):
        return client.post(
            f"{sources}/{version}/{action}", headers=admin, json={"expected_revision": revision}
        )

    question = fixtures[0][1]
    assert client.get(local, headers=farmer).status_code == 200
    assert ask(question, {}).status_code == 401
    assert ask(question, admin).status_code == 403
    assert ask(question, {**farmer, "Origin": "https://example.com"}).status_code == 403
    assert ask(question).json() == {"status": "no_evidence"}
    original = preview_fixture.PDF.replace(b"DEMO-NURSERY-A", b"CASE-NURSERY-A")
    upload = client.post(
        sources + "/pdf", headers={**admin, "Content-Type": "application/pdf"}, content=original
    )
    assert upload.status_code == 201
    version = upload.json()["id"]
    assert process_one(accounts[1])
    nursery_page = f"{local}/CH-01/sources/{version}/pages/26"
    assert ask(question).json() == {"status": "no_evidence"}
    assert client.get(nursery_page, headers=farmer).status_code == 404
    settings = client.app.state.settings
    _, _, _, quote, translation = fixtures[0]
    reference = LocalNurseryReference(
        version_id=version,
        checksum=upload.json()["checksum"],
        page_number=26,
        title="Synthetic nursery reference",
        excerpt=quote,
        english_translation=translation,
    )
    monkeypatch.setattr(settings, "local_nursery_reference", reference)
    assert ask(question).json() == {"status": "no_evidence"}
    monkeypatch.setattr(settings, "app_env", "development")
    result = ask(question).json()
    assert result["reference_only"] is True
    assert result["answer"] == translation
    assert result["citation"]["excerpt"] == quote
    assert result["citation"]["number"] == 26
    assert client.get(nursery_page, headers=farmer).json() == {"number": 26, "text": quote}
    assert client.get(nursery_page, headers=admin).status_code == 403
    assert (
        client.get(f"{local}/CH-01/sources/{version}/pages/27", headers=farmer).status_code == 404
    )
    monkeypatch.setattr(
        settings, "local_nursery_reference", reference.model_copy(update={"checksum": "0" * 64})
    )
    assert ask(question).json() == {"status": "no_evidence"}
    monkeypatch.setattr(settings, "local_nursery_reference", reference)
    irrigation_reference = LocalNurseryReference(
        version_id=version,
        checksum=upload.json()["checksum"],
        page_number=27,
        title="Synthetic irrigation reference",
        excerpt=fixtures[1][3],
        english_translation="The irrigation conditions are supported by this draft passage.",
    )
    fertilizer_reference = LocalNurseryReference(
        version_id=version,
        checksum=upload.json()["checksum"],
        page_number=28,
        title="Synthetic fertilizer reference",
        excerpt=fixtures[2][3],
        english_translation="The fertilizer conditions are supported by this draft passage.",
    )
    monkeypatch.setattr(
        settings,
        "local_chilli_references",
        {"CH-04": irrigation_reference, "CH-05": fertilizer_reference},
    )
    monkeypatch.setattr(settings, "app_env", "test")
    assert ask(fixtures[1][1]).json()["status"] == "no_evidence"
    assert ask(fixtures[2][1]).json()["status"] == "no_evidence"
    monkeypatch.setattr(settings, "app_env", "development")
    for fixture, expected_page in ((fixtures[1], 27), (fixtures[2], 28)):
        result = ask(fixture[1]).json()
        assert result["reference_only"] is True
        assert result["citation"]["number"] == expected_page
        assert (
            result["answer"]
            == "The "
            + ("irrigation" if expected_page == 27 else "fertilizer")
            + " conditions are supported by this draft passage."
        )
        assert client.get(
            f"{local}/{fixture[0]}/sources/{version}/pages/{expected_page}", headers=farmer
        ).json() == {"number": expected_page, "text": fixture[3]}
    monkeypatch.setattr(settings, "app_env", "test")
    assert transition(version, "review", 1).status_code == 200
    assert transition(version, "publish", 2).status_code == 200
    assert ask(question).json() == {"status": "no_evidence"}

    for case, variant, number, quote, translation in fixtures:
        decision = client.post(
            f"{ROOT}/evaluation/{case}/decisions",
            headers=admin,
            json={
                "expected_revision": 0,
                "outcome": "suitable",
                "version_id": version,
                "page_number": number,
                "approved_excerpt": quote,
                "english_translation": translation,
            },
        )
        assert decision.status_code == 201
        result = ask(variant)
        assert result.status_code == 200
        assert result.json()["answer"] == (translation or quote)
        citation = result.json()["citation"]
        assert result.json()["case_id"] == case
        assert citation["number"] == number
        assert citation["version_id"] == version
        assert citation["excerpt"] == quote
        page = client.get(f"{local}/{case}/sources/{version}/pages/{number}", headers=farmer)
        assert page.json() == {"number": number, "text": pages[number - 1]}

    for unsupported in (
        "How much fertilizer should I apply?",
        "How often should I water?",
        "What should I spray?",
    ):
        assert ask(unsupported).json() == {"status": "no_evidence"}
    assert (
        client.get(f"{local}/CH-01/sources/{version}/pages/27", headers=farmer).status_code == 404
    )
    assert client.get(root, headers=farmer).json() == {"released": False, "cases": []}
    assert (
        client.post(
            f"{ROOT}/evaluation/CH-01/decisions",
            headers=admin,
            json={
                "expected_revision": 1,
                "outcome": "out_of_scope",
                "version_id": version,
                "page_number": 26,
            },
        ).status_code
        == 201
    )
    assert ask(question).json() == {"status": "no_evidence"}
    assert client.get(nursery_page, headers=farmer).status_code == 404
    assert transition(version, "withdraw", 3).status_code == 200
    assert ask(fixtures[1][1]).json() == {"status": "no_evidence"}
    assert (
        client.get(f"{local}/CH-04/sources/{version}/pages/27", headers=farmer).status_code == 404
    )

    monkeypatch.setattr(client.app.state.settings, "app_env", "production")
    assert client.get(local, headers=farmer).status_code == 404
    assert ask(question).status_code == 404
    assert client.get(nursery_page, headers=farmer).status_code == 404

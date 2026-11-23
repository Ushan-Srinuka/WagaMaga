"""Check the Gemini request contract without external calls."""

import json
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from app.integrations import gemini


def test_generate_content_contract(monkeypatch):
    calls = []

    class Connection:
        def __init__(self, host, timeout):
            assert host == "generativelanguage.googleapis.com"
            assert timeout > 0

        def request(self, method, path, body, headers):
            calls.append((method, path, json.loads(body), headers))

        def getresponse(self):
            part = {"text": json.dumps({"citation_id": "C1", "quote": "Fictional note."})}
            data = {"candidates": [{"finishReason": "STOP", "content": {"parts": [part]}}]}
            return SimpleNamespace(status=200, read=lambda limit: json.dumps(data).encode())

        def close(self):
            pass

    monkeypatch.setattr(gemini.http.client, "HTTPSConnection", Connection)
    settings = SimpleNamespace(gemini_model="gemini-test", gemini_api_key=SecretStr("fake-key"))
    quote = gemini.select_quote(
        settings, "Which note?", [{"citation_id": "C1", "text": "Fictional note."}]
    )
    assert quote.citation_id == "C1"
    assert quote.quote == "Fictional note."
    ((method, path, payload, headers),) = calls
    assert (method, path) == ("POST", "/v1beta/models/gemini-test:generateContent")
    assert headers["x-goog-api-key"] == "fake-key"
    assert payload["generationConfig"]["responseMimeType"] == "application/json"
    assert "fake-key" not in json.dumps(payload)
    with pytest.raises(gemini.Unavailable):
        gemini.select_quote(SimpleNamespace(gemini_api_key=None), "Which note?", [])

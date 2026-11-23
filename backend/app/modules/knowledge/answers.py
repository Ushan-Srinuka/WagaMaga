"""Ground the local preview in server-owned fictional PDF text."""

from app.integrations import gemini
from app.modules.identity.security import IdentityError
from app.modules.knowledge import preview_fixture, service


def answer(db, ids, settings, question, on_provider_call):
    prompt, keywords = preview_fixture.QUESTIONS[question]
    matches = service.search_published_pages(db, ids, keywords, checksum=preview_fixture.CHECKSUM)
    citations = {}
    for match in matches:
        number = match["number"]
        if 1 <= number <= len(preview_fixture.PAGES):
            citations[f"C{len(citations) + 1}"] = (
                match,
                preview_fixture.PAGES[number - 1],
            )
    if not citations:
        return {"status": "no_evidence"}
    if settings.gemini_api_key is None:
        raise IdentityError(503, "GEMINI_NOT_CONFIGURED", "Configure Gemini on the server first.")
    on_provider_call()
    try:
        quoted = gemini.select_quote(
            settings,
            prompt,
            [{"citation_id": key, "text": value[1]} for key, value in citations.items()],
        )
    except gemini.Unavailable:
        raise IdentityError(
            503, "GEMINI_UNAVAILABLE", "Gemini could not answer the demo question."
        ) from None
    if not (quoted.citation_id or quoted.quote):
        return {"status": "no_evidence"}
    selected = citations.get(quoted.citation_id)
    if selected is None or quoted.quote != selected[1]:
        raise IdentityError(502, "INVALID_CITATION", "The answer could not be verified.")
    cited, body = selected
    current = service.search_published_pages(db, ids, keywords, checksum=preview_fixture.CHECKSUM)
    if not any(
        match["version_id"] == cited["version_id"] and match["number"] == cited["number"]
        for match in current
    ):
        return {"status": "no_evidence"}
    return {
        "status": "answered",
        "answer": body,
        "citation": {**cited, "excerpt": body},
    }

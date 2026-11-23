"""Serve fixed fictional PDF evidence for a local farmer walkthrough."""

import re
import unicodedata
from hashlib import sha256
from uuid import NAMESPACE_URL, uuid5

from app.modules.identity.security import IdentityError
from app.modules.knowledge import pilot, preview_fixture

TITLE = "Fictional chilli farmer notebook"
PAGES = (
    *preview_fixture.PAGES,
    "The fictional irrigation log records the plot label and watering date.",
    "The fictional fertilizer log records the plot label and a soil test reference.",
)
PDF = preview_fixture.fixture_pdf(PAGES)
CHECKSUM = sha256(PDF).hexdigest()
VERSION_ID = uuid5(NAMESPACE_URL, f"wagamaga:farmer-demo:{CHECKSUM}")
CASES = {
    "nursery": (preview_fixture.QUESTIONS["nursery"][0], 1),
    "irrigation": ("What does the demo irrigation log record?", 3),
    "fertilizer": ("What does the demo fertilizer log record?", 4),
    "forecast": (preview_fixture.QUESTIONS["forecast"][0], None),
}

_QUESTION_WORDS = frozenset(
    [
        "a",
        "about",
        "an",
        "are",
        "at",
        "can",
        "could",
        "demo",
        "demonstration",
        "did",
        "do",
        "does",
        "example",
        "fictional",
        "for",
        "from",
        "in",
        "is",
        "it",
        "me",
        "of",
        "on",
        "s",
        "tell",
        "show",
        "the",
        "this",
        "to",
        "use",
        "used",
        "uses",
        "was",
        "what",
        "which",
        "would",
        "you",
    ]
)
_LOG_WORDS = frozenset(
    [
        "capture",
        "captures",
        "contain",
        "contains",
        "contents",
        "data",
        "detail",
        "details",
        "document",
        "entry",
        "entries",
        "field",
        "fields",
        "include",
        "includes",
        "information",
        "keep",
        "kept",
        "list",
        "log",
        "logbook",
        "logged",
        "notebook",
        "note",
        "record",
        "recorded",
        "records",
        "say",
        "says",
        "show",
        "shows",
        "store",
        "stores",
        "track",
        "tracks",
        "written",
    ]
)
_CASE_WORDS = {
    "nursery": (
        frozenset({"nursery", "seedling", "seedlings"}),
        frozenset(
            {
                "code",
                "id",
                "label",
                "labeled",
                "labelled",
                "labels",
                "name",
                "named",
                "tag",
                "tray",
                "trays",
            }
        ),
    ),
    "irrigation": (frozenset({"irrigation", "water", "watering"}), _LOG_WORDS),
    "fertilizer": (
        frozenset({"fertiliser", "fertilisers", "fertilizer", "fertilizers"}),
        _LOG_WORDS,
    ),
}


def require_access(db, ids, settings):
    if settings.app_env == "production":
        raise IdentityError(404, "DEMO_NOT_FOUND", "The farmer demo is available locally.")
    pilot.require_farmer(db, ids)


def questions(db, ids, settings):
    require_access(db, ids, settings)
    return {
        "cases": [
            {"id": case_id, "question": question} for case_id, (question, _) in CASES.items()
        ],
    }


def answer(db, ids, settings, case_id):
    require_access(db, ids, settings)
    return answer_for_case(case_id)


def ask(db, ids, settings, question):
    require_access(db, ids, settings)
    normalized = unicodedata.normalize("NFKC", question).casefold()
    words = set(re.findall(r"[^\W_]+", normalized))
    # Each sample page covers a specific topic and purpose. Extra content words
    # can change the question, so an overlapping crop or topic term is insufficient.
    for case_id, (topic, purpose) in _CASE_WORDS.items():
        if words & topic and words & purpose and words <= _QUESTION_WORDS | topic | purpose:
            return {"case_id": case_id, **answer_for_case(case_id)}
    return {"status": "no_evidence"}


def answer_for_case(case_id):
    case = CASES.get(case_id)
    if case is None:
        raise IdentityError(404, "DEMO_CASE_NOT_FOUND", "Demo question not found.")
    _, number = case
    if number is None:
        return {"status": "no_evidence"}
    quote = PAGES[number - 1]
    return {
        "status": "answered",
        "answer": quote,
        "citation": {
            "version_id": VERSION_ID,
            "title": TITLE,
            "checksum": CHECKSUM,
            "number": number,
            "excerpt": quote,
        },
    }


def page(db, ids, settings, case_id, version_id, number):
    require_access(db, ids, settings)
    case = CASES.get(case_id)
    if case is None or case[1] != number or version_id != VERSION_ID:
        raise IdentityError(404, "SOURCE_NOT_FOUND", "Demo page not found.")
    return {"number": number, "text": PAGES[number - 1]}

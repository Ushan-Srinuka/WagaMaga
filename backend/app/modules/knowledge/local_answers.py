"""Search approved excerpts for a small set of localhost chilli questions."""

import re
import unicodedata

from sqlalchemy import select

from app.modules.identity.security import IdentityError
from app.modules.knowledge import evaluation, farmer_demo, pilot
from app.modules.knowledge.evaluation_cases import CASES
from app.modules.knowledge.models import SourcePdf, SourceVersion

QUESTION_VARIANTS = {
    "CH-01": (
        "What should I look for in a chilli nursery site?",
        "How do I choose a site for a chilli nursery?",
        "What makes a suitable chilli nursery site?",
        "Where should I set up my chilli nursery?",
    ),
    "CH-04": (
        "What conditions affect irrigation for newly planted chilli?",
        "What should I check before watering newly planted chilli?",
        "What field conditions should I check before irrigating chilli?",
    ),
    "CH-05": (
        "What should I check before choosing fertilizer for chilli?",
        "What should I check before applying basal fertilizer?",
        "Should I test the soil before choosing basal fertilizer?",
    ),
}


def normalized_question(question):
    words = re.findall(r"[^\W_]+", unicodedata.normalize("NFKC", question).casefold())
    spelling = {"chili": "chilli", "fertiliser": "fertilizer"}
    return " ".join(spelling.get(word, word) for word in words).removesuffix(" in anuradhapura")


CASE_BY_QUESTION = {
    normalized_question(question): case_id
    for case_id, variants in QUESTION_VARIANTS.items()
    for question in (CASES[case_id].question, *variants)
}


def require_access(db, ids, settings):
    if settings.app_env == "production":
        raise IdentityError(404, "LOCAL_ANSWERS_NOT_FOUND", "Local answers are unavailable.")
    pilot.require_farmer(db, ids)


def questions(db, ids, settings):
    require_access(db, ids, settings)
    return {"cases": [{"id": key, "question": CASES[key].question} for key in QUESTION_VARIANTS]}


def reviewed_page(db, case_id, *, version_id=None, number=None):
    for page in evaluation.case_evidence(db, case_id)["pages"]:
        if version_id is not None and (page["version_id"], page["number"]) != (version_id, number):
            continue
        decision = page["decision"]
        if (
            page["checksum"] == farmer_demo.CHECKSUM
            or not decision
            or decision.outcome != "suitable"
            or not decision.approved_excerpt
            or (
                evaluation.contains_sinhala(decision.approved_excerpt)
                and not decision.english_translation
            )
        ):
            continue
        body = db.scalar(
            select(SourcePdf.pages[page["number"] - 1].astext)
            .join(SourceVersion)
            .where(
                SourceVersion.id == page["version_id"],
                SourceVersion.status == "published",
                SourcePdf.state == "ready",
            )
        )
        if body and decision.approved_excerpt in " ".join(body.split()):
            return page, body
    return None


def draft_reference(db, settings, case_id):
    reference = (
        settings.local_nursery_reference
        if case_id == "CH-01"
        else settings.local_chilli_references.get(case_id)
    )
    if settings.app_env != "development" or reference is None:
        return None
    body = db.scalar(
        select(SourcePdf.pages[reference.page_number - 1].astext)
        .join(SourceVersion)
        .where(
            SourceVersion.id == reference.version_id,
            SourceVersion.checksum == reference.checksum,
            SourceVersion.status == "draft",
            SourceVersion.rag_metadata.is_(None),
            SourcePdf.state == "ready",
        )
    )
    if not body or not evaluation.contains_sinhala(reference.excerpt):
        return None
    excerpt = " ".join(reference.excerpt.split())
    translation = " ".join(reference.english_translation.split())
    try:
        evaluation.validate_excerpt(body, excerpt, translation)
    except IdentityError:
        return None
    return {
        "status": "answered",
        "case_id": case_id,
        "reference_only": True,
        "answer": translation,
        "citation": {
            "version_id": reference.version_id,
            "checksum": reference.checksum,
            "title": reference.title,
            "number": reference.page_number,
            "excerpt": excerpt,
        },
    }


def ask(db, ids, settings, question):
    require_access(db, ids, settings)
    case_id = CASE_BY_QUESTION.get(normalized_question(question))
    result = reviewed_page(db, case_id) if case_id else None
    if result is None:
        return draft_reference(db, settings, case_id) or {"status": "no_evidence"}
    page, _ = result
    return {
        "status": "answered",
        "case_id": case_id,
        "answer": pilot.answer_text(page),
        "citation": {**page, "excerpt": page["decision"].approved_excerpt},
    }


def cited_page(db, ids, settings, case_id, version_id, number):
    require_access(db, ids, settings)
    if case_id in QUESTION_VARIANTS:
        result = reviewed_page(db, case_id, version_id=version_id, number=number)
        if result is not None:
            return {"number": number, "text": result[1]}
        reference = draft_reference(db, settings, case_id)
        if reference:
            citation = reference["citation"]
            if (citation["version_id"], citation["number"]) == (version_id, number):
                return {"number": number, "text": citation["excerpt"]}
    raise IdentityError(404, "SOURCE_NOT_FOUND", "Reviewed page not found.")

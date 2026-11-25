"""Retrieve candidate pages and append versioned evaluation labels."""

import re

from sqlalchemy import and_, func, or_, select, tuple_
from sqlalchemy.dialects.postgresql import insert

from app.modules.identity.security import IdentityError
from app.modules.knowledge import preview_fixture, service
from app.modules.knowledge.evaluation_cases import CASES
from app.modules.knowledge.models import EvaluationDecision, SourcePdf, SourceVersion


def list_cases(db, ids):
    service.admin_actor(db, ids)
    return [{"id": key, "question": case.question} for key, case in CASES.items()]


def read_case(db, ids, case_id):
    service.admin_actor(db, ids)
    return case_evidence(db, case_id)


def preview_draft(db, ids, case_id, version_id):
    service.admin_actor(db, ids)
    case = CASES.get(case_id)
    if case is None:
        raise IdentityError(404, "CASE_NOT_FOUND", "Evaluation question not found.")
    draft = db.scalar(
        select(SourceVersion.id)
        .join(SourcePdf)
        .where(
            SourceVersion.id == version_id,
            SourceVersion.status == "draft",
            SourcePdf.state == "ready",
        )
    )
    if draft is None:
        raise IdentityError(404, "SOURCE_NOT_FOUND", "Processed draft PDF not found.")
    return {
        "keywords": case.sinhala_keywords,
        "pages": service.draft_page_matches(db, draft, case.sinhala_keywords),
    }


def contains_sinhala(text: str) -> bool:
    return any("\u0d80" <= character <= "\u0dff" for character in text)


def validate_excerpt(body, excerpt, translation):
    if excerpt not in " ".join(body.split()):
        raise IdentityError(422, "INVALID_EXCERPT", "Copy the exact wording from the page.")
    if contains_sinhala(excerpt):
        if not re.search(r"[A-Za-z]", translation) or contains_sinhala(translation):
            raise IdentityError(
                422, "TRANSLATION_REQUIRED", "Enter an English translation of the Sinhala quote."
            )
    elif translation:
        raise IdentityError(
            422, "TRANSLATION_NOT_NEEDED", "Use the exact quote for English source text."
        )


def preview_draft_answer(db, ids, case_id, data):
    result = preview_draft(db, ids, case_id, data.version_id)
    page = next((page for page in result["pages"] if page["number"] == data.page_number), None)
    if page is None:
        raise IdentityError(409, "EVIDENCE_CHANGED", "Select a matching page for this question.")
    body = db.scalar(
        select(SourcePdf.pages[data.page_number - 1].astext)
        .join(SourceVersion)
        .where(
            SourceVersion.id == data.version_id,
            SourceVersion.status == "draft",
            SourcePdf.state == "ready",
        )
    )
    if body is None:
        raise IdentityError(409, "EVIDENCE_CHANGED", "Refresh and select a matching draft page.")
    excerpt = " ".join(data.excerpt.split())
    translation = " ".join(data.english_translation.split())
    if not contains_sinhala(excerpt):
        raise IdentityError(422, "SINHALA_QUOTE_REQUIRED", "Copy a Sinhala quote from the page.")
    validate_excerpt(body, excerpt, translation)
    return {"status": "answered", "answer": translation, "citation": {**page, "excerpt": excerpt}}


def case_evidence(db, case_id):
    case = CASES.get(case_id)
    if case is None:
        raise IdentityError(404, "CASE_NOT_FOUND", "Evaluation question not found.")
    decision = EvaluationDecision
    revision = db.scalar(select(func.max(decision.revision)).where(decision.case_id == case_id))
    matches = {}
    for keywords in (case.keywords, case.sinhala_keywords):
        for page in service.published_page_matches(
            db, keywords, exclude_checksum=preview_fixture.CHECKSUM, legacy_only=True
        ):
            matches.setdefault((page["version_id"], page["number"]), page)
    latest = (
        select(func.max(decision.revision))
        .where(
            decision.case_id == case_id,
            or_(
                decision.version_id.is_(None),
                tuple_(decision.version_id, decision.page_number).in_(list(matches)),
            ),
        )
        .group_by(decision.version_id, decision.page_number)
    )
    decisions = {
        (row.version_id, row.page_number): row
        for row in db.scalars(
            select(decision).where(decision.case_id == case_id, decision.revision.in_(latest))
        )
    }
    pages = [{**page, "decision": decisions.get(key)} for key, page in matches.items()]
    suitable = any(page["decision"] and page["decision"].outcome == "suitable" for page in pages)
    return {
        "id": case_id,
        "question": case.question,
        "keywords": case.keywords,
        "sinhala_keywords": case.sinhala_keywords,
        "review_focus": case.review_focus,
        "revision": revision or 0,
        "pages": pages,
        "missing": None if suitable else decisions.get((None, None)),
    }


def save_decision(db, ids, case_id, data, request_id):
    actor = service.admin_actor(db, ids, write=True)
    if data.version_id is not None:
        published = db.scalar(
            select(SourceVersion.id)
            .where(and_(SourceVersion.id == data.version_id, SourceVersion.status == "published"))
            .with_for_update()
        )
        if published is None:
            raise IdentityError(409, "EVIDENCE_CHANGED", "Refresh and select a published page.")
    current = case_evidence(db, case_id)
    if current["revision"] != data.expected_revision:
        raise IdentityError(409, "REVIEW_CHANGED", "Refresh and review the latest decisions.")
    if data.outcome == "missing":
        if any(
            page["decision"] and page["decision"].outcome == "suitable" for page in current["pages"]
        ):
            raise IdentityError(409, "SUITABLE_EVIDENCE", "A page is still marked suitable.")
    elif not any(
        page["version_id"] == data.version_id and page["number"] == data.page_number
        for page in current["pages"]
    ):
        raise IdentityError(409, "EVIDENCE_CHANGED", "Refresh and select a retrieved page.")
    excerpt = " ".join(data.approved_excerpt.split())
    translation = " ".join(data.english_translation.split())
    if excerpt:
        source = db.get(SourceVersion, data.version_id)
        body = source.pdf.pages[data.page_number - 1]
        validate_excerpt(body, excerpt, translation)
    statement = (
        insert(EvaluationDecision)
        .values(
            case_id=case_id,
            revision=data.expected_revision + 1,
            outcome=data.outcome,
            version_id=data.version_id,
            page_number=data.page_number,
            note=data.note,
            approved_excerpt=excerpt,
            english_translation=translation,
            actor_id=actor.id,
            request_id=request_id,
        )
        .on_conflict_do_nothing(index_elements=["case_id", "revision"])
        .returning(EvaluationDecision)
    )
    saved = db.scalar(statement)
    if saved is None:
        raise IdentityError(409, "REVIEW_CHANGED", "Refresh and review the latest decisions.")
    return saved

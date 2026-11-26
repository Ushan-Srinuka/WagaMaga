"""Score reviewed quotations and gate the fixed farmer question pilot."""

import json
from hashlib import sha256

from sqlalchemy import select

from app.integrations import gemini
from app.modules.identity.security import IdentityError
from app.modules.identity.service import active_actor
from app.modules.knowledge import evaluation, service
from app.modules.knowledge.evaluation_cases import CASES
from app.modules.knowledge.models import EvaluationRun, SourcePdf, SourceVersion

MISSING_ONLY = frozenset({"CH-06", "CH-07", "CH-08", "CH-09", "CH-10"})
POLICY_VERSION = "chilli-quotes-v1"


def answer_text(page):
    decision = page["decision"]
    return decision.english_translation or decision.approved_excerpt


def prepared_case(db, settings, case_id):
    production = settings.app_env == "production"
    case = evaluation.case_evidence(db, case_id, pilot_scope=production)
    suitable = [
        page
        for page in case["pages"]
        if page["decision"] and page["decision"].outcome == "suitable"
    ]
    eligible = []
    expected = "pending"
    reason = "Save a suitable page or mark evidence missing."
    if suitable and case_id in MISSING_ONLY:
        reason = "This case tests missing evidence or context. Review its saved labels."
    elif suitable:
        if any(not page["decision"].approved_excerpt for page in suitable):
            reason = "Save an exact approved excerpt for every suitable page."
        elif any(
            evaluation.contains_sinhala(page["decision"].approved_excerpt)
            and not page["decision"].english_translation
            for page in suitable
        ):
            reason = "Save an English translation for every suitable Sinhala excerpt."
        elif any(
            page["checksum"] not in settings.gemini_approved_pdf_checksums for page in suitable
        ):
            reason = "The selected PDF needs approval for Gemini processing."
        elif settings.gemini_api_key is None:
            reason = "Configure the server’s Gemini key."
        else:
            eligible = suitable
            expected, reason = "cited", ""
    elif case["missing"]:
        expected, reason = "no_evidence", ""
    snapshot = {
        "policy": f"{POLICY_VERSION}-screened" if production else POLICY_VERSION,
        "case": case_id,
        "question": case["question"],
        "revision": case["revision"],
        "model": settings.gemini_model,
        "expected": expected,
        "candidates": [
            [str(page["version_id"]), page["number"], page["checksum"]] for page in case["pages"]
        ],
        "pages": [
            [
                str(page["version_id"]),
                page["number"],
                page["checksum"],
                page["decision"].approved_excerpt,
                *([answer_text(page)] if page["decision"].english_translation else []),
            ]
            for page in eligible
        ],
    }
    fingerprint = sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()
    return {
        "case_id": case_id,
        "question": case["question"],
        "expected": expected,
        "reason": reason,
        "fingerprint": fingerprint,
        "evidence": eligible,
    }


def previous_run(db, case):
    return db.scalar(
        select(EvaluationRun)
        .where(
            EvaluationRun.case_id == case["case_id"],
            EvaluationRun.fingerprint == case["fingerprint"],
        )
        .order_by(EvaluationRun.created_at.desc(), EvaluationRun.id.desc())
        .limit(1)
    )


def suite(db, settings):
    checks = []
    for case_id in CASES:
        case = prepared_case(db, settings, case_id)
        run = previous_run(db, case) if case["expected"] != "pending" else None
        checks.append(
            {**case, "passed": run.passed if run else None, "detail": run.detail if run else ""}
        )
    passed = all(case["passed"] is True for case in checks)
    cited = any(case["expected"] == "cited" for case in checks)
    quality_ready = quality_review_ready(settings)
    ready = passed and cited and quality_ready
    return {
        "cases": checks,
        "ready": ready,
        "released": ready and settings.farmer_advisory_enabled,
        "independent_review_pending": not quality_ready,
    }


def quality_review_ready(settings):
    review = settings.farmer_advisory_quality_review
    return settings.app_env != "production" or (
        review is not None
        and review.model == settings.gemini_model
        and review.pdf_checksums == settings.gemini_approved_pdf_checksums
        and settings.rag_embedding_pdf_checksums == review.pdf_checksums
    )


def release_configured(settings):
    return settings.farmer_advisory_enabled and quality_review_ready(settings)


def verified_quote(settings, case, on_provider_call):
    if case["expected"] != "cited":
        return None
    by_id = {f"C{index}": page for index, page in enumerate(case["evidence"], start=1)}
    passages = [{"citation_id": cid, "text": answer_text(page)} for cid, page in by_id.items()]
    on_provider_call()
    try:
        reply = gemini.select_quote(settings, case["question"], passages)
    except gemini.Unavailable:
        raise IdentityError(
            503, "GEMINI_UNAVAILABLE", "Gemini could not complete the check."
        ) from None
    page = by_id.get(reply.citation_id)
    if page is None or reply.quote != answer_text(page):
        return None
    return {**page, "excerpt": page["decision"].approved_excerpt}


def run_case(db, ids, settings, case_id, on_provider_call):
    actor = service.admin_actor(db, ids)
    case = prepared_case(db, settings, case_id)
    if case["expected"] == "pending":
        raise IdentityError(409, "CASE_NOT_READY", case["reason"])
    quote = verified_quote(settings, case, on_provider_call)
    service.admin_actor(db, ids)
    if prepared_case(db, settings, case_id)["fingerprint"] != case["fingerprint"]:
        raise IdentityError(409, "REVIEW_CHANGED", "Evidence changed. Run the check again.")
    passed = quote is not None or case["expected"] == "no_evidence"
    detail = (
        "Citation verified"
        if quote
        else ("No evidence found" if passed else "Gemini returned no verifiable approved quotation")
    )
    result = EvaluationRun(
        case_id=case_id,
        fingerprint=case["fingerprint"],
        passed=passed,
        detail=detail,
        model=settings.gemini_model if case["expected"] == "cited" else "local",
        actor_id=actor.id,
    )
    db.add(result)
    db.flush()
    return result


def require_farmer(db, ids):
    if active_actor(db, ids).role != "farmer":
        raise IdentityError(403, "FARMER_REQUIRED", "Farmer access is required.")


def farmer_questions(db, ids, settings):
    require_farmer(db, ids)
    released = release_configured(settings) and suite(db, settings)["released"]
    return {
        "released": released,
        "cases": [{"id": key, "question": case.question} for key, case in CASES.items()]
        if released
        else [],
    }


def released_case(db, ids, settings, case_id):
    require_farmer(db, ids)
    if release_configured(settings):
        current = suite(db, settings)
        if current["released"]:
            for case in current["cases"]:
                if case["case_id"] == case_id:
                    return case
            raise IdentityError(404, "CASE_NOT_FOUND", "Pilot question not found.")
    raise IdentityError(403, "PILOT_NOT_RELEASED", "Chilli answers are still being reviewed.")


def farmer_answer(db, ids, settings, case_id, on_provider_call):
    case = released_case(db, ids, settings, case_id)
    if case["expected"] == "no_evidence":
        return {"status": "no_evidence"}
    quote = verified_quote(settings, case, on_provider_call)
    if quote is None:
        raise IdentityError(502, "INVALID_CITATION", "The answer could not be verified.")
    current = released_case(db, ids, settings, case_id)
    if case["fingerprint"] != current["fingerprint"]:
        raise IdentityError(409, "REVIEW_CHANGED", "The source changed. Please try again.")
    return {"status": "answered", "answer": answer_text(quote), "citation": quote}


def farmer_page(db, ids, settings, case_id, version_id, number):
    case = released_case(db, ids, settings, case_id)
    for page in case["evidence"]:
        if page["version_id"] == version_id and page["number"] == number:
            pages = db.scalar(
                select(SourcePdf.pages)
                .join(SourceVersion, SourceVersion.id == SourcePdf.version_id)
                .where(
                    SourceVersion.id == version_id,
                    SourceVersion.status == "published",
                    SourcePdf.state == "ready",
                )
            )
            if pages is not None:
                body = (
                    page["decision"].approved_excerpt
                    if settings.app_env == "production"
                    else pages[number - 1]
                )
                return {"number": number, "text": body}
    raise IdentityError(404, "SOURCE_NOT_FOUND", "Reviewed page not found.")

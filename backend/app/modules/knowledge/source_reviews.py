"""Assign and record review of a specific immutable knowledge PDF version."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import aliased

from app.modules.identity.models import User
from app.modules.identity.security import IdentityError
from app.modules.identity.service import active_actor, require_admin
from app.modules.knowledge.models import SourcePdf, SourceReviewEvent, SourceVersion

PAGE_SIZE = 20
Event = SourceReviewEvent


def latest(db, version_id):
    return db.scalar(
        select(Event).where(Event.version_id == version_id).order_by(Event.sequence.desc()).limit(1)
    )


def missing():
    return IdentityError(404, "SOURCE_NOT_FOUND", "Assigned PDF source version not found.")


def conflict():
    return IdentityError(409, "SOURCE_REVIEW_CHANGED", "Reload the current source review.")


def draft(db, version_id, *, lock=False):
    statement = (
        select(SourceVersion)
        .join(SourcePdf)
        .where(
            SourceVersion.id == version_id,
            SourceVersion.status == "draft",
            SourcePdf.state == "ready",
        )
    )
    return db.scalar(statement.with_for_update(of=SourceVersion) if lock else statement)


def admin_review(db, ids, version_id, *, write=False):
    actor = active_actor(db, ids, lock=write)
    require_admin(actor)
    source = draft(db, version_id, lock=write)
    if source is None:
        raise missing()
    return actor, source, latest(db, source.id)


def append(db, source, current, actor_id, advisor_id, event, reason, request_id):
    row = Event(
        version_id=source.id,
        sequence=current.sequence + 1 if current else 1,
        advisor_id=advisor_id,
        actor_id=actor_id,
        event=event,
        reason=reason,
        request_id=request_id,
    )
    db.add(row)
    db.flush()
    return row


def assign(db, ids, version_id, data, request_id):
    actor, source, current = admin_review(db, ids, version_id, write=True)
    if (current.sequence if current else 0) != data.expected_sequence or (
        current and current.event in ("approved", "changes_requested")
    ):
        raise conflict()
    if data.advisor_email is None:
        if current is None or current.event != "assigned":
            raise conflict()
        return append(db, source, current, actor.id, current.advisor_id, "revoked", "", request_id)
    advisor_id = db.scalar(
        select(User.id).where(
            User.email == data.advisor_email.casefold(),
            User.role == "advisor",
            User.disabled_at.is_(None),
            User.deleted_at.is_(None),
        )
    )
    if advisor_id is None:
        raise IdentityError(422, "ADVISOR_UNAVAILABLE", "Choose an active advisor account.")
    if current and current.event == "assigned" and current.advisor_id == advisor_id:
        return current
    return append(db, source, current, actor.id, advisor_id, "assigned", "", request_id)


def advisor(db, ids, *, lock=False):
    actor = active_actor(db, ids, lock=lock)
    if actor.role != "advisor":
        raise IdentityError(403, "ADVISOR_REQUIRED", "Advisor access is required.")
    return actor


def assignment_view(db, source, review):
    assigned_at = review.created_at
    if review.event != "assigned":
        assigned_at = db.scalar(
            select(Event.created_at).where(
                Event.version_id == source.id, Event.sequence == review.sequence - 1
            )
        )
    return {
        "id": source.id,
        "title": source.title,
        "checksum": source.checksum,
        "rag_metadata": source.rag_metadata,
        "review": review,
        "assigned_at": assigned_at,
    }


def assignments(db, ids, page, view="all"):
    actor = advisor(db, ids)
    newer = aliased(Event)
    statement = (
        select(SourceVersion, Event)
        .join_from(SourceVersion, SourcePdf, SourcePdf.version_id == SourceVersion.id)
        .join_from(SourceVersion, Event, Event.version_id == SourceVersion.id)
        .where(
            SourceVersion.status == "draft",
            SourcePdf.state == "ready",
            Event.advisor_id == actor.id,
            Event.event != "revoked",
            ~select(newer.sequence)
            .where(newer.version_id == Event.version_id, newer.sequence > Event.sequence)
            .exists(),
        )
    )
    if view == "pending":
        statement = statement.where(Event.event == "assigned")
    if view == "reviewed":
        statement = statement.where(
            Event.event.in_(("approved", "changes_requested")),
            Event.created_at >= datetime.now(UTC) - timedelta(days=30),
        )
    rows = db.execute(
        statement.order_by(Event.created_at.desc(), Event.version_id)
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE + 1)
    ).all()
    return {
        "items": [assignment_view(db, source, review) for source, review in rows[:PAGE_SIZE]],
        "has_more": len(rows) > PAGE_SIZE,
    }


def assigned_draft(db, ids, version_id, *, lock=False):
    actor = advisor(db, ids, lock=lock)
    source = draft(db, version_id, lock=lock)
    current = latest(db, version_id) if source else None
    if current is None or current.advisor_id != actor.id or current.event == "revoked":
        raise missing()
    return actor, source, current


def page(db, ids, version_id, number):
    _, source, _ = assigned_draft(db, ids, version_id)
    pages = source.pdf.pages
    if number > len(pages):
        raise missing()
    return {"number": number, "text": pages[number - 1], "total": len(pages)}


def assignment_detail(db, ids, version_id):
    _, source, review = assigned_draft(db, ids, version_id)
    return assignment_view(db, source, review)


def decide(db, ids, version_id, data, request_id):
    actor, source, current = assigned_draft(db, ids, version_id, lock=True)
    if current.event != "assigned" or current.sequence != data.expected_sequence:
        raise conflict()
    return append(db, source, current, actor.id, actor.id, data.outcome, data.reason, request_id)

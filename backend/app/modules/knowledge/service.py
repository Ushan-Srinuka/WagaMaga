"""Scope the lifecycle demonstration to a server-owned fictional guide."""

from hashlib import sha256

from sqlalchemy import select, text

from app.modules.identity.security import IdentityError
from app.modules.identity.service import active_actor, require_admin
from app.modules.knowledge.models import SourceDecision, SourcePdf, SourceVersion

DEMO_TITLE = "Chilli pilot demonstration guide"
DEMO_CONTENT = (
    "This fictional guide represents a sample chilli source for Anuradhapura. "
    "The example reviewer checks that the title, crop, area and section refer to the same "
    "document version. This guide contains no cultivation instructions."
)
PAGE_SIZE = 20
TRANSITIONS = {
    "review": ("draft", "reviewed"),
    "publish": ("reviewed", "published"),
    "withdraw": ("published", "withdrawn"),
}


def admin_actor(db, ids, *, write=False):
    actor = active_actor(db, ids, lock=write)
    require_admin(actor)
    return actor


def list_sources(db, ids, page):
    admin_actor(db, ids)
    sources = db.scalars(
        select(SourceVersion)
        .where(SourceVersion.status.not_in(("discarded", "deleted")))
        .order_by(SourceVersion.created_at.desc(), SourceVersion.id)
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE + 1)
    ).all()
    return {"items": sources[:PAGE_SIZE], "has_more": len(sources) > PAGE_SIZE}


def search_published_pages(db, ids, query, *, checksum=None, exclude_checksum=None):
    admin_actor(db, ids)
    return published_page_matches(db, query, checksum=checksum, exclude_checksum=exclude_checksum)


def published_page_matches(db, query, *, checksum=None, exclude_checksum=None):
    return _page_matches(
        db, query, "published", checksum=checksum, exclude_checksum=exclude_checksum
    )


def draft_page_matches(db, version_id, query):
    return _page_matches(db, query, "draft", version_id=version_id)


def _page_matches(db, query, status, *, version_id=None, checksum=None, exclude_checksum=None):
    statement = text("""
        WITH query AS (SELECT plainto_tsquery('simple', :query) AS terms),
        matches AS (
            SELECT source.id AS version_id, source.title, source.checksum,
                page.number, page.body, query.terms,
                ts_rank_cd(to_tsvector('simple', page.body), query.terms) AS score
            FROM knowledge_demo_versions AS source
            JOIN knowledge_source_pdfs AS pdf ON pdf.version_id = source.id
            CROSS JOIN LATERAL jsonb_array_elements_text(pdf.pages)
                WITH ORDINALITY AS page(body, number)
            CROSS JOIN query
            WHERE source.status = :status AND pdf.state = 'ready'
                AND source.id = coalesce(CAST(:version_id AS uuid), source.id)
                AND source.checksum = coalesce(CAST(:checksum AS text), source.checksum)
                AND source.checksum IS DISTINCT FROM CAST(:exclude_checksum AS text)
                AND to_tsvector('simple', page.body) @@ query.terms
            ORDER BY score DESC, source.id, page.number
            LIMIT 10
        )
        SELECT version_id, title, checksum, number,
            left(ts_headline('simple', body, terms,
                'StartSel=[, StopSel=], MaxWords=28, MinWords=10, MaxFragments=2'), 600)
                AS excerpt
        FROM matches
        ORDER BY score DESC, version_id, number
    """)
    params = {
        "query": query.strip(),
        "status": status,
        "version_id": version_id,
        "checksum": checksum,
        "exclude_checksum": exclude_checksum,
    }
    return db.execute(statement, params).mappings().all()


def record_decision(db, source, actor_id, request_id):
    db.add(
        SourceDecision(
            version_id=source.id,
            revision=source.revision,
            actor_id=actor_id,
            status=source.status,
            request_id=request_id,
        )
    )
    db.flush()


def add_demo(db, ids, request_id):
    actor = admin_actor(db, ids, write=True)
    source = SourceVersion(
        title=DEMO_TITLE,
        content=DEMO_CONTENT,
        checksum=sha256(DEMO_CONTENT.encode("utf-8")).hexdigest(),
        status="draft",
        revision=1,
    )
    db.add(source)
    db.flush()
    record_decision(db, source, actor.id, request_id)
    return source


def add_pdf(db, ids, original, request_id, *, title="Uploaded sample PDF"):
    actor = admin_actor(db, ids, write=True)
    if not original.startswith(b"%PDF-"):
        raise IdentityError(422, "INVALID_PDF", "Choose a valid PDF file.")
    source = SourceVersion(
        title=title,
        content="",
        checksum=sha256(original).hexdigest(),
        status="draft",
        revision=1,
        pdf=SourcePdf(original=original, state="queued"),
    )
    db.add(source)
    db.flush()
    record_decision(db, source, actor.id, request_id)
    return source


def source_pages(db, ids, version_id):
    admin_actor(db, ids)
    source = db.get(SourceVersion, version_id)
    if source is None or source.pdf is None or source.status in ("discarded", "deleted"):
        raise IdentityError(404, "SOURCE_NOT_FOUND", "PDF source version not found.")
    if source.processing != "ready":
        raise IdentityError(409, "SOURCE_PROCESSING", "PDF text is unavailable.")
    return [
        {"number": number, "text": content}
        for number, content in enumerate(source.pdf.pages, start=1)
    ]


def transition(db, ids, version_id, action, expected_revision, request_id):
    actor = admin_actor(db, ids, write=True)
    source = db.scalar(
        select(SourceVersion)
        .where(SourceVersion.id == version_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if source is None or source.status == "discarded":
        raise IdentityError(404, "SOURCE_NOT_FOUND", "Source version not found.")
    if source.revision != expected_revision:
        raise IdentityError(409, "SOURCE_CONFLICT", "Refresh and check the current source status.")
    if action == "discard":
        if source.pdf is None or source.status not in ("draft", "reviewed"):
            raise IdentityError(409, "SOURCE_CONFLICT", "Only unpublished PDFs can be removed.")
        after = "discarded"
    elif action == "delete":
        if source.pdf is None or source.status != "withdrawn":
            raise IdentityError(
                409, "SOURCE_CONFLICT", "Only withdrawn PDFs can be permanently deleted."
            )
        if source.pdf.state not in ("ready", "failed"):
            raise IdentityError(409, "SOURCE_CONFLICT", "This PDF cannot be deleted yet.")
        after = "deleted"
    else:
        if source.processing != "ready":
            raise IdentityError(
                409, "SOURCE_PROCESSING", "PDF processing must succeed before review."
            )
        before, after = TRANSITIONS[action]
        if source.status != before:
            raise IdentityError(
                409, "SOURCE_CONFLICT", "Refresh and check the current source status."
            )
    source.status = after
    source.revision += 1
    if action == "delete":
        db.flush()
        source.pdf.original = None
        source.pdf.pages = None
        source.pdf.error = None
        source.pdf.state = "deleted"
    record_decision(db, source, actor.id, request_id)
    return source

"""Versioned PDF passages and cultivation-scoped hybrid retrieval."""

import json
from datetime import date
from typing import Literal
from uuid import UUID, uuid5

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import text

from app.integrations import embeddings
from app.modules.farms import service as farms
from app.modules.farms.models import CropType
from app.modules.identity.security import IdentityError

INDEX_VERSION = "page-900-v1"
QUESTION_WORDS = (
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "can",
    "could",
    "did",
    "do",
    "does",
    "for",
    "from",
    "give",
    "how",
    "i",
    "in",
    "is",
    "it",
    "me",
    "my",
    "of",
    "on",
    "or",
    "should",
    "show",
    "tell",
    "that",
    "the",
    "them",
    "there",
    "these",
    "they",
    "to",
    "was",
    "were",
    "what",
    "when",
    "where",
    "which",
    "who",
    "will",
    "with",
    "would",
    "you",
)


class Metadata(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    publisher: str = Field(min_length=1, max_length=160, pattern=r"^[^\x00-\x1f]+$")
    language: Literal["en", "si", "ta"]
    crop: str = Field(pattern=r"^[a-z][a-z0-9_]{0,39}$")
    region: str = Field(min_length=2, max_length=100, pattern=r"^[A-Za-z ]+$")
    published_on: date | None
    valid_until: date | None
    access: Literal["admin", "farmers"] = "admin"

    @model_validator(mode="after")
    def validate_dates(self):
        if self.published_on and self.valid_until and self.valid_until < self.published_on:
            raise ValueError("Validity must end on or after publication.")
        self.region = district_key(self.region)
        if not self.region:
            raise ValueError("Enter a region.")
        return self


class Search(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    question: str = Field(min_length=1, max_length=240, pattern=r"^[^\x00]+$")
    semantic: bool = False


class Passage(BaseModel):
    id: UUID
    version_id: UUID
    title: str
    page_number: int
    body: str
    publisher: str
    language: str


class Results(BaseModel):
    items: list[Passage]
    method: Literal["keyword", "vector", "hybrid"]


def district_key(value):
    return " ".join(value.casefold().split()).removesuffix(" district")


def district_of(location):
    parts = [district_key(part) for part in location.split(",") if part.strip()]
    if parts and parts[-1] == "sri lanka":
        parts.pop()
    return parts[-1] if parts else ""


def chunks(page):
    remaining = " ".join(page.replace("\x00", "").split())
    while len(remaining) > 900:
        end = remaining.rfind(" ", 450, 901)
        if end < 0:
            end = 900
        yield remaining[:end]
        remaining = remaining[end:].lstrip()
    if remaining:
        yield remaining


def create_passages(db, source):
    if source.rag_metadata is None or source.pdf is None:
        return
    rows = [
        {
            "id": uuid5(source.id, f"{INDEX_VERSION}:{page_number}:{ordinal}"),
            "version": source.id,
            "page": page_number,
            "ordinal": ordinal,
            "body": body,
        }
        for page_number, page in enumerate(source.pdf.pages, 1)
        for ordinal, body in enumerate(chunks(page), 1)
    ]
    if rows:
        db.execute(
            text("""
            INSERT INTO knowledge_passages (id, version_id, page_number, ordinal, body)
            VALUES (:id, :version, :page, :ordinal, :body)
        """),
            rows,
        )


ELIGIBLE = """
    v.status = 'published' AND pdf.state = 'ready'
    AND v.rag_metadata->>'access' = 'farmers'
    AND v.rag_metadata->>'crop' = :crop
    AND v.rag_metadata->>'region' IN (:region, 'sri lanka')
    AND COALESCE(CAST(v.rag_metadata->>'published_on' AS date), :today) <= :today
    AND COALESCE(CAST(v.rag_metadata->>'valid_until' AS date), :today) >= :today
"""
PASSAGE_COLUMNS = """
    p.id, p.version_id, v.title, p.page_number, p.body,
    v.rag_metadata->>'publisher' AS publisher, v.rag_metadata->>'language' AS language
"""
SOURCES = """
    FROM knowledge_passages p
    JOIN knowledge_demo_versions v ON v.id = p.version_id
    JOIN knowledge_source_pdfs pdf ON pdf.version_id = v.id
"""


def scope(db, ids, farm_id, cultivation_id):
    actor = farms.farmer(db, ids)
    farm, cultivation = farms.cultivation_for(db, actor.id, cultivation_id, farm_id=farm_id)
    return {
        "crop": db.get(CropType, cultivation.crop_type_id).code,
        "region": district_of(farm.location),
        "today": farms.local_today(db, farm),
    }


def search(
    db,
    ids,
    farm_id,
    cultivation_id,
    data,
    settings,
    on_semantic,
    *,
    mode="hybrid",
    answer_checksums=None,
    semantic_context=None,
):
    params = scope(db, ids, farm_id, cultivation_id)
    params.update(
        question=data.question,
        embedding=None,
        model=embeddings.MODEL,
        index_version=INDEX_VERSION,
        allowed=list(settings.rag_embedding_pdf_checksums),
        public_search=answer_checksums is None,
        answer_checksums=list(answer_checksums or ()),
        keyword=mode != "vector",
        stopwords=list(QUESTION_WORDS),
    )
    eligible = (
        ELIGIBLE + " AND (:public_search OR v.checksum = ANY(CAST(:answer_checksums AS text[])))"
    )
    semantic_filter = """
        p.embedding_model = :model AND p.index_version = :index_version
        AND v.checksum = ANY(CAST(:allowed AS text[]))
    """
    if mode != "keyword" and data.semantic and settings.gemini_api_key and params["allowed"]:
        has_vectors = db.scalar(
            text(f"SELECT EXISTS (SELECT 1 {SOURCES} WHERE {eligible} AND {semantic_filter})"),
            params,
        )
        if has_vectors:
            try:
                on_semantic()
                params["embedding"] = json.dumps(
                    embeddings.embed(settings, [semantic_context or data.question], query=True)[0]
                )
            except embeddings.Unavailable:
                pass
            params.update(scope(db, ids, farm_id, cultivation_id))
    # Rank inside the authorized corpus, then fuse ranks without comparing raw score scales.
    results = db.execute(
        text(f"""
        WITH query AS (
            SELECT to_tsquery('simple', coalesce(string_agg(quote_literal(word), ' | '), ''))
                AS terms
            FROM unnest(tsvector_to_array(to_tsvector('simple', :question))) AS word
            WHERE word <> ALL(CAST(:stopwords AS text[]))
        ), keyword AS (
            SELECT p.id, row_number() OVER (ORDER BY
                ts_rank_cd(to_tsvector('simple', p.body), query.terms) DESC, p.id) AS rank
            {SOURCES} CROSS JOIN query
            WHERE {eligible} AND :keyword
            AND to_tsvector('simple', p.body) @@ query.terms
            ORDER BY rank LIMIT 24
        ), semantic AS (
            SELECT p.id, row_number() OVER (ORDER BY
                p.embedding <=> CAST(:embedding AS vector), p.id) AS rank
            {SOURCES}
            WHERE {eligible} AND {semantic_filter}
            AND p.embedding <=> CAST(:embedding AS vector) < 0.70
            ORDER BY rank LIMIT 24
        ), ranked AS (
            SELECT id, sum(1.0 / (60 + rank)) AS score
            FROM (SELECT * FROM keyword UNION ALL SELECT * FROM semantic) candidates
            GROUP BY id
        )
        SELECT {PASSAGE_COLUMNS} {SOURCES} JOIN ranked r ON r.id = p.id
        ORDER BY r.score DESC, p.id LIMIT 8
    """),
        params,
    ).mappings()
    return Results(
        items=[Passage.model_validate(row) for row in results],
        method=mode if params["embedding"] else "keyword",
    )


def source_passage(db, ids, farm_id, cultivation_id, passage_id, *, answer_checksums=None):
    params = scope(db, ids, farm_id, cultivation_id) | {"passage_id": passage_id}
    result = eligible_passages(db, params, [passage_id], answer_checksums=answer_checksums)
    if passage_id not in result:
        raise IdentityError(404, "PASSAGE_NOT_FOUND", "Source passage not found.")
    return result[passage_id]


def eligible_passages(db, params, passage_ids, *, answer_checksums=None):
    row = db.execute(
        text(f"""
        SELECT {PASSAGE_COLUMNS} {SOURCES}
        WHERE {ELIGIBLE} AND p.id = ANY(CAST(:passage_ids AS uuid[]))
        AND (:public_search OR v.checksum = ANY(CAST(:answer_checksums AS text[])))
    """),
        params
        | {
            "passage_ids": passage_ids,
            "public_search": answer_checksums is None,
            "answer_checksums": list(answer_checksums or ()),
        },
    ).mappings()
    return {item["id"]: Passage.model_validate(item) for item in row}

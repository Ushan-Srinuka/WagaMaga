"""Process a bounded embedding batch from the durable passage queue."""

import json

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.integrations import embeddings
from app.modules.knowledge.rag import INDEX_VERSION


def process_batch(engine, settings):
    allowed = list(settings.rag_embedding_pdf_checksums)
    if not settings.gemini_api_key or not allowed:
        return False
    params = {
        "allowed": allowed,
        "model": embeddings.MODEL,
        "version": INDEX_VERSION,
        "limit": embeddings.MAX_BATCH,
        "screened_only": settings.app_env == "production",
    }
    with Session(engine) as db, db.begin():
        rows = (
            db.execute(
                text("""
            SELECT p.id, p.body
            FROM knowledge_passages p
            JOIN knowledge_demo_versions v ON v.id = p.version_id
            JOIN knowledge_source_pdfs pdf ON pdf.version_id = v.id
            WHERE v.status = 'published' AND pdf.state = 'ready'
            AND (NOT :screened_only OR pdf.screening_required)
            AND v.rag_metadata->>'access' = 'farmers'
            AND v.checksum = ANY(CAST(:allowed AS text[]))
            AND COALESCE(
                CAST(v.rag_metadata->>'published_on' AS date), CURRENT_DATE
            ) <= CURRENT_DATE
            AND COALESCE(CAST(v.rag_metadata->>'valid_until' AS date), CURRENT_DATE) >= CURRENT_DATE
            AND (p.embedding_model IS DISTINCT FROM :model
                 OR p.index_version IS DISTINCT FROM :version)
            ORDER BY v.created_at, p.version_id, p.page_number, p.ordinal
            LIMIT :limit FOR UPDATE OF p SKIP LOCKED
        """),
                params,
            )
            .mappings()
            .all()
        )
        if not rows:
            return False
        vectors = embeddings.embed(settings, [row["body"] for row in rows])
        db.execute(
            text("""
            UPDATE knowledge_passages p
            SET embedding = CAST(:vector AS vector),
                embedding_model = :model, index_version = :version
            FROM knowledge_demo_versions v
            WHERE p.id = :id AND v.id = p.version_id AND v.status = 'published'
        """),
            [
                {
                    "id": row["id"],
                    "vector": json.dumps(vector),
                    "model": embeddings.MODEL,
                    "version": INDEX_VERSION,
                }
                for row, vector in zip(rows, vectors, strict=True)
            ],
        )
    return True

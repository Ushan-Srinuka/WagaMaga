"""Explicit local baseline on copyright-licensed, agriculturally unapproved PDFs."""

import json
from datetime import timedelta
from hashlib import sha256
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import pytest
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.modules.farms.models import Farm
from app.modules.identity.models import RefreshSession
from app.modules.identity.service import now
from app.modules.knowledge import processing, rag
from app.modules.knowledge.models import SourcePdf, SourceVersion

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[2]


def test_chilli_candidate_keyword_baseline(accounts, farm_records):
    dataset = json.loads(
        (ROOT / "evaluation/datasets/chilli-real-pdf-candidate-v1.json").read_text(encoding="utf-8")
    )
    cases = dataset["cases"]
    assert len({case["id"] for case in cases}) >= 30
    assert {"missing", "outdated", "conflicting"} <= {case.get("gap") for case in cases}
    settings, engine, _, people = accounts
    records = farm_records["farmer"]
    farmer = people["farmer"]
    sources = {}
    expired = []
    recalls = []
    with Session(engine) as db:
        # Documents, metadata variants and authentication exist only in this transaction.
        farm = db.scalar(select(Farm).where(Farm.id == records["farm"]))
        farm.location = "Synthetic Village, Anuradhapura, Sri Lanka"
        session = RefreshSession(user_id=farmer, expires_at=now() + timedelta(hours=1))
        db.add(session)
        db.flush()
        for doc in dataset["documents"]:
            path = ROOT / ".data/knowledge-import" / doc["file"]
            assert path.is_file(), f"Place the publisher PDF at {path}"
            original = path.read_bytes()
            assert sha256(original).hexdigest() == doc["sha256"]
            extracted = processing.extract_pdf(original)
            assert "pages" in extracted, extracted.get("error")
            for valid_until in (None, "2026-01-01"):
                source = SourceVersion(
                    id=uuid5(NAMESPACE_URL, f"{dataset['id']}:{doc['id']}:{valid_until}"),
                    title=doc["id"],
                    status="published",
                    revision=3,
                    content="",
                    checksum=doc["sha256"],
                    rag_metadata={
                        "publisher": doc["publisher"],
                        "language": "en",
                        "crop": "chilli",
                        "region": "anuradhapura",
                        "access": "farmers",
                        "published_on": doc["published_on"],
                        "valid_until": valid_until,
                    },
                    pdf=SourcePdf(original=original, state="ready", pages=extracted["pages"]),
                )
                db.add(source)
                db.flush()
                rag.create_passages(db, source)
                if valid_until:
                    expired.append(source.id)
                else:
                    sources[source.id] = doc["id"]
        for case in cases:
            expired_only = case.get("corpus") == "expired"
            with db.begin_nested() as snapshot:
                if expired_only:
                    db.execute(
                        update(SourceVersion)
                        .where(SourceVersion.id.in_(sources))
                        .values(status="withdrawn", revision=4)
                    )
                result = rag.search(
                    db,
                    (farmer, session.id),
                    records["farm"],
                    records["cultivation"],
                    rag.Search(question=case["question"]),
                    settings,
                    lambda: pytest.fail("Provider call"),
                    mode="keyword",
                    answer_checksums={doc["sha256"] for doc in dataset["documents"]},
                )
                snapshot.rollback()
            assert not any(item.version_id in expired for item in result.items)
            ranked = [(sources[item.version_id], item.page_number) for item in result.items[:5]]
            expected = {tuple(value) for value in case.get("evidence", ())}
            if expected:
                score = len(expected.intersection(ranked)) / len(expected)
                recalls.append(score)
                print(f"{case['id']} recall={score:.0%} ranked={ranked}")
            else:
                print(f"{case['id']} gap={case['gap']} retrieved={len(ranked)}")
                if expired_only:
                    assert not result.items
    print(
        f"Questions={len(cases)} Answerable={len(recalls)} "
        f"Keyword Recall@5={sum(recalls) / len(recalls):.2%}"
    )

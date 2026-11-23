"""Run one durable queued PDF extraction and commit the complete result."""

import json
import os
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.knowledge.models import SourcePdf, SourceVersion

PARSER = Path(__file__).with_name("pdf_text.py")


def extract_pdf(original):
    try:
        result = subprocess.run(
            [sys.executable, "-I", str(PARSER)],
            input=original,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env={key: os.environ[key] for key in ("SYSTEMROOT", "WINDIR") if key in os.environ},
            timeout=10,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"error": "timed_out"}
    if result.returncode:
        return {"error": "parser_stopped"}
    try:
        return json.loads(result.stdout)
    except ValueError:
        return {"error": "parser_stopped"}


def process_one(engine):
    with Session(engine) as db, db.begin():
        pdf = db.scalar(
            select(SourcePdf)
            .join(SourceVersion, SourceVersion.id == SourcePdf.version_id)
            .where(SourcePdf.state == "queued", SourceVersion.status == "draft")
            .order_by(SourcePdf.version_id)
            .limit(1)
            .with_for_update(of=SourcePdf, skip_locked=True)
        )
        if pdf is None:
            return False
        original = pdf.original
        checksum = db.scalar(
            select(SourceVersion.checksum).where(SourceVersion.id == pdf.version_id)
        )
        result = (
            extract_pdf(original)
            if sha256(original).hexdigest() == checksum
            else {"error": "checksum_mismatch"}
        )
        pdf.pages = result.get("pages")
        pdf.error = result.get("error")
        pdf.state = "failed" if pdf.error else "ready"
    return True

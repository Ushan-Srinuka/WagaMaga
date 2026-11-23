"""Immutable demo source content and recorded lifecycle decisions."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, LargeBinary, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

STATUS_CHECK = "status IN ('draft','reviewed','published','withdrawn','discarded','deleted')"


class SourceVersion(Base):
    __tablename__ = "knowledge_demo_versions"
    __table_args__ = (
        CheckConstraint(STATUS_CHECK, name="knowledge_demo_status"),
        CheckConstraint("revision BETWEEN 1 AND 5", name="knowledge_demo_revision"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(120))
    content: Mapped[str] = mapped_column(Text)
    checksum: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(12))
    revision: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    pdf: Mapped[SourcePdf | None] = relationship(lazy="selectin")

    @property
    def processing(self) -> str:
        return self.pdf.state if self.pdf else "ready"

    @property
    def processing_error(self) -> str | None:
        return self.pdf.error if self.pdf else None


class SourceDecision(Base):
    __tablename__ = "knowledge_demo_decisions"
    __table_args__ = (CheckConstraint(STATUS_CHECK, name="knowledge_demo_decision_status"),)

    version_id: Mapped[UUID] = mapped_column(
        ForeignKey("knowledge_demo_versions.id", ondelete="RESTRICT"), primary_key=True
    )
    revision: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(String(12))
    request_id: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SourcePdf(Base):
    __tablename__ = "knowledge_source_pdfs"
    __table_args__ = (
        CheckConstraint(
            "original IS NULL OR octet_length(original) BETWEEN 1 AND 6291456",
            name="knowledge_pdf_size",
        ),
        CheckConstraint(
            "(state = 'queued' AND pages IS NULL AND error IS NULL) OR "
            "(state = 'ready' AND pages IS NOT NULL AND error IS NULL) OR "
            "(state = 'failed' AND pages IS NULL AND error IS NOT NULL) OR "
            "(state = 'deleted' AND original IS NULL AND pages IS NULL AND error IS NULL)",
            name="knowledge_pdf_state",
        ),
        Index("ix_knowledge_pdf_queue", "state", "version_id"),
    )

    version_id: Mapped[UUID] = mapped_column(
        ForeignKey("knowledge_demo_versions.id", ondelete="RESTRICT"), primary_key=True
    )
    original: Mapped[bytes | None] = mapped_column(LargeBinary, deferred=True)
    state: Mapped[str] = mapped_column(String(8))
    pages: Mapped[list[str] | None] = mapped_column(JSONB(none_as_null=True), deferred=True)
    error: Mapped[str | None] = mapped_column(String(24))


class EvaluationDecision(Base):
    __tablename__ = "knowledge_evaluation_decisions"
    __table_args__ = (
        CheckConstraint("revision > 0", name="knowledge_eval_revision"),
        CheckConstraint(
            "(outcome = 'missing' AND version_id IS NULL AND page_number IS NULL) OR "
            "(outcome IN ('suitable','out_of_scope') AND version_id IS NOT NULL "
            "AND page_number IS NOT NULL AND page_number BETWEEN 1 AND 100)",
            name="knowledge_eval_evidence",
        ),
        CheckConstraint(
            "english_translation = '' OR (outcome = 'suitable' AND approved_excerpt <> '')",
            name="knowledge_eval_translation",
        ),
    )

    case_id: Mapped[str] = mapped_column(String(5), primary_key=True)
    revision: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("knowledge_source_pdfs.version_id", ondelete="RESTRICT")
    )
    page_number: Mapped[int | None]
    outcome: Mapped[str] = mapped_column(String(12))
    note: Mapped[str] = mapped_column(String(500))
    approved_excerpt: Mapped[str] = mapped_column(String(500), server_default="")
    english_translation: Mapped[str] = mapped_column(String(500), server_default="")
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    request_id: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EvaluationRun(Base):
    __tablename__ = "knowledge_evaluation_runs"
    __table_args__ = (Index("ix_knowledge_run_case_fingerprint", "case_id", "fingerprint"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    case_id: Mapped[str] = mapped_column(String(5))
    fingerprint: Mapped[str] = mapped_column(String(64))
    passed: Mapped[bool]
    detail: Mapped[str] = mapped_column(String(80))
    model: Mapped[str] = mapped_column(String(77))
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

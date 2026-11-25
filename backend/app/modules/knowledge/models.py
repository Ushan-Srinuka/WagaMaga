"""Immutable demo source content and recorded lifecycle decisions."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql.base import ischema_names
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import UserDefinedType

from app.db.base import Base

STATUS_CHECK = "status IN ('draft','reviewed','published','withdrawn','discarded','deleted')"


class PassageVector(UserDefinedType):
    cache_ok = True

    def __init__(self, dimensions=768):
        self.dimensions = int(dimensions)

    def get_col_spec(self, **kw):
        return f"vector({self.dimensions})"


ischema_names["vector"] = PassageVector


class ChilliChat(Base):
    __tablename__ = "chilli_chats"
    __table_args__ = (Index("ix_chilli_chats_owner_cultivation", "owner_id", "cultivation_id"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    cultivation_id: Mapped[UUID] = mapped_column(ForeignKey("cultivations.id", ondelete="RESTRICT"))
    revision: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ChilliTurn(Base):
    __tablename__ = "chilli_chat_turns"

    chat_id: Mapped[UUID] = mapped_column(
        ForeignKey("chilli_chats.id", ondelete="CASCADE"), primary_key=True
    )
    ordinal: Mapped[int] = mapped_column(primary_key=True)
    question: Mapped[str] = mapped_column(String(240))
    outcome: Mapped[str] = mapped_column(String(20))
    quote: Mapped[str | None] = mapped_column(String(500))
    # The locator can outlive withdrawal, but the response always rechecks eligibility.
    passage_id: Mapped[UUID | None]


class ChilliJob(Base):
    __tablename__ = "chilli_jobs"
    __table_args__ = (
        Index(
            "uq_chilli_job_active_revision",
            "chat_id",
            "revision",
            unique=True,
            postgresql_where=text("state IN ('queued','running','succeeded')"),
        ),
        Index("ix_chilli_jobs_queue", "state", "lease_until", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    chat_id: Mapped[UUID] = mapped_column(ForeignKey("chilli_chats.id", ondelete="CASCADE"))
    session_id: Mapped[UUID]
    revision: Mapped[int]
    question: Mapped[str] = mapped_column(String(240))
    use_gemini: Mapped[bool]
    state: Mapped[str] = mapped_column(String(12), default="queued")
    failure_code: Mapped[str | None] = mapped_column(String(30))
    attempts: Mapped[int] = mapped_column(default=0)
    lease_token: Mapped[UUID | None]
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class KnowledgePassage(Base):
    __tablename__ = "knowledge_passages"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    version_id: Mapped[UUID] = mapped_column(
        ForeignKey("knowledge_demo_versions.id", ondelete="RESTRICT")
    )
    page_number: Mapped[int]
    ordinal: Mapped[int]
    body: Mapped[str] = mapped_column(Text)
    embedding: Mapped[object | None] = mapped_column(PassageVector())
    embedding_model: Mapped[str | None] = mapped_column(Text)
    index_version: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (
        UniqueConstraint("version_id", "page_number", "ordinal"),
        Index(
            "ix_knowledge_passages_fts",
            text("to_tsvector('simple', body)"),
            postgresql_using="gin",
        ),
    )


class SourceVersion(Base):
    __tablename__ = "knowledge_demo_versions"
    __table_args__ = (
        CheckConstraint(STATUS_CHECK, name="knowledge_demo_status"),
        CheckConstraint("revision BETWEEN 1 AND 5", name="knowledge_demo_revision"),
        Index(
            "uq_knowledge_active_replacement",
            "replaces_version_id",
            unique=True,
            postgresql_where=text("status IN ('draft','reviewed','published')"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(120))
    rag_metadata: Mapped[dict | None] = mapped_column(JSONB(none_as_null=True))
    replaces_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "knowledge_demo_versions.id", name="fk_knowledge_replacement", ondelete="RESTRICT"
        )
    )
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

    @property
    def retryable(self) -> bool:
        return bool(
            self.pdf
            and self.status == "draft"
            and self.pdf.state == "failed"
            and self.pdf.error in ("timed_out", "parser_stopped")
            and self.pdf.retry_count < 3
        )


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
    retry_count: Mapped[int] = mapped_column(server_default=text("0"))


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

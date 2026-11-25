"""Administrator HTTP entry points for the synthetic guide workflow."""

from asyncio import timeout
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from starlette.concurrency import run_in_threadpool
from starlette.requests import ClientDisconnect

from app.modules.identity.dependencies import (
    DB,
    Principal,
    administrator,
    browser_origin,
    browser_write,
    limiter,
)
from app.modules.identity.security import IdentityError
from app.modules.identity.service import Limiter
from app.modules.knowledge import (
    answers,
    evaluation,
    farmer_demo,
    local_answers,
    pilot,
    preview_fixture,
    rag,
    research,
    service,
)
from app.modules.knowledge.pdf_text import MAX_BYTES, MAX_PAGES

router = APIRouter(
    prefix="/api/v1/admin/knowledge/sources",
    tags=["Knowledge Sources"],
    dependencies=[Depends(administrator)],
)
writes = [Depends(browser_write)]
PDF_UPLOAD_PATH = "/api/v1/admin/knowledge/sources/pdf"
evaluation_router = APIRouter(
    prefix="/api/v1/admin/knowledge/evaluation",
    tags=["Knowledge Evaluation"],
    dependencies=[Depends(administrator)],
)
farmer_router = APIRouter(prefix="/api/v1/knowledge/chilli", tags=["Chilli questions"])


class AddDemo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    template: Literal["chilli-demo", "gemini-preview-pdf"]


class AnswerQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: preview_fixture.PreviewQuestion


class Transition(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    expected_revision: int = Field(ge=1, le=5)


class Source(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    rag_metadata: rag.Metadata | None = None
    replaces_version_id: UUID | None = None
    content: str
    checksum: str
    status: Literal["draft", "reviewed", "published", "withdrawn", "discarded", "deleted"]
    revision: int
    processing: Literal["queued", "ready", "failed", "deleted"]
    processing_error: str | None
    retryable: bool = False


class SourcePage(BaseModel):
    items: list[Source]
    has_more: bool


class PdfPage(BaseModel):
    number: int
    text: str


class PageMatch(BaseModel):
    version_id: UUID
    title: str
    checksum: str
    number: int
    excerpt: str


Outcome = Literal["suitable", "out_of_scope", "missing"]


class ReviewDecision(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    outcome: Outcome
    note: str
    approved_excerpt: str
    english_translation: str
    revision: int
    created_at: datetime


class ReviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: Annotated[int, Field(strict=True, ge=0, le=2147483646)]
    outcome: Outcome
    note: str = Field(default="", max_length=500, pattern=r"^[^\x00]*$")
    approved_excerpt: str = Field(default="", max_length=500, pattern=r"^[^\x00]*$")
    english_translation: str = Field(default="", max_length=500, pattern=r"^[^\x00]*$")
    version_id: UUID | None = None
    page_number: Annotated[int, Field(strict=True, ge=1, le=MAX_PAGES)] | None = None

    @model_validator(mode="after")
    def check_page(self):
        if self.approved_excerpt.strip() and self.outcome != "suitable":
            raise ValueError("An approved excerpt requires a suitable page")
        if self.english_translation.strip() and not self.approved_excerpt.strip():
            raise ValueError("An English translation requires an approved excerpt")
        has_page = self.version_id is not None and self.page_number is not None
        if self.outcome == "missing":
            if self.version_id is not None or self.page_number is not None:
                raise ValueError("Missing evidence cannot identify a page")
        elif not has_page:
            raise ValueError("Select a source version and PDF page")
        return self


class ReviewPage(PageMatch):
    decision: ReviewDecision | None


class ReviewQuestion(BaseModel):
    id: str
    question: str


class ReviewCase(ReviewQuestion):
    keywords: str
    sinhala_keywords: str
    review_focus: str
    revision: int
    pages: list[ReviewPage]
    missing: ReviewDecision | None


class DraftMatches(BaseModel):
    keywords: str
    pages: list[PageMatch]


class DraftAnswerInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    version_id: UUID
    page_number: Annotated[int, Field(strict=True, ge=1, le=MAX_PAGES)]
    excerpt: str = Field(min_length=1, max_length=500, pattern=r"^[^\x00]*$")
    english_translation: str = Field(min_length=1, max_length=500, pattern=r"^[^\x00]*$")


class ScoreCase(BaseModel):
    case_id: str
    question: str
    expected: Literal["pending", "cited", "no_evidence"]
    reason: str
    passed: bool | None
    detail: str


class ScoreSuite(BaseModel):
    cases: list[ScoreCase]
    ready: bool
    released: bool


class ScoreResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    case_id: str
    passed: bool
    detail: str
    model: str


class QuestionList(BaseModel):
    cases: list[ReviewQuestion]


class PilotQuestionList(QuestionList):
    released: bool


class PilotQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str = Field(pattern=r"^CH-(0[1-9]|10)$")


class DemoQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str = Field(min_length=1, max_length=24)


class TypedQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    question: str = Field(min_length=1, max_length=240, pattern=r"^[^\x00]*$")


@evaluation_router.get("", response_model=list[ReviewQuestion])
def evaluation_cases(db: DB, ids: Principal):
    return evaluation.list_cases(db, ids)


@evaluation_router.get("/{case_id}", response_model=ReviewCase)
def evaluation_case(case_id: str, db: DB, ids: Principal):
    return evaluation.read_case(db, ids, case_id)


@evaluation_router.get("/{case_id}/draft-matches", response_model=DraftMatches)
def draft_matches(case_id: str, version_id: UUID, db: DB, ids: Principal):
    return evaluation.preview_draft(db, ids, case_id, version_id)


@evaluation_router.post(
    "/{case_id}/decisions", response_model=ReviewDecision, status_code=201, dependencies=writes
)
def review_evidence(case_id: str, data: ReviewInput, request: Request, db: DB, ids: Principal):
    return evaluation.save_decision(db, ids, case_id, data, request.state.request_id)


class NoEvidence(BaseModel):
    status: Literal["no_evidence"]


class CitedAnswer(BaseModel):
    status: Literal["answered"]
    answer: str
    citation: PageMatch


class MatchedCitedAnswer(CitedAnswer):
    case_id: str


class LocalCitedAnswer(MatchedCitedAnswer):
    reference_only: bool = False


@evaluation_router.post("/{case_id}/draft-answer", response_model=CitedAnswer, dependencies=writes)
def draft_answer(case_id: str, data: DraftAnswerInput, request: Request, db: DB, ids: Principal):
    require_local_preview(request)
    return evaluation.preview_draft_answer(db, ids, case_id, data)


@evaluation_router.get("/scores/summary", response_model=ScoreSuite)
def score_summary(request: Request, db: DB, ids: Principal):
    service.admin_actor(db, ids)
    return pilot.suite(db, request.app.state.settings)


@evaluation_router.post(
    "/scores/{case_id}", response_model=ScoreResult, status_code=201, dependencies=writes
)
def score_case(
    case_id: str,
    request: Request,
    db: DB,
    ids: Principal,
    limits: Annotated[Limiter, Depends(limiter)],
):
    return pilot.run_case(
        db,
        ids,
        request.app.state.settings,
        case_id,
        lambda: limits.check("chilli_eval", str(ids[0]), 20, 3600),
    )


@farmer_router.get("", response_model=PilotQuestionList)
def chilli_questions(request: Request, db: DB, ids: Principal):
    return pilot.farmer_questions(db, ids, request.app.state.settings)


@farmer_router.post("/answer", response_model=CitedAnswer | NoEvidence, dependencies=writes)
def chilli_answer(
    data: PilotQuestion,
    request: Request,
    db: DB,
    ids: Principal,
    limits: Annotated[Limiter, Depends(limiter)],
):
    return pilot.farmer_answer(
        db,
        ids,
        request.app.state.settings,
        data.case_id,
        lambda: limits.check("chilli_pilot", str(ids[0]), 6, 3600),
    )


@farmer_router.get("/{case_id}/sources/{version_id}/pages/{number}", response_model=PdfPage)
def chilli_page(
    case_id: str, version_id: UUID, number: int, request: Request, db: DB, ids: Principal
):
    return pilot.farmer_page(db, ids, request.app.state.settings, case_id, version_id, number)


@farmer_router.get("/demo", response_model=QuestionList)
def demo_questions(request: Request, db: DB, ids: Principal):
    return farmer_demo.questions(db, ids, request.app.state.settings)


@farmer_router.post("/demo/answer", response_model=CitedAnswer | NoEvidence, dependencies=writes)
def demo_answer(data: DemoQuestion, request: Request, db: DB, ids: Principal):
    return farmer_demo.answer(db, ids, request.app.state.settings, data.case_id)


@farmer_router.post(
    "/demo/ask", response_model=MatchedCitedAnswer | NoEvidence, dependencies=writes
)
def ask_demo_question(data: TypedQuestion, request: Request, db: DB, ids: Principal):
    return farmer_demo.ask(db, ids, request.app.state.settings, data.question)


@farmer_router.get("/demo/{case_id}/sources/{version_id}/pages/{number}", response_model=PdfPage)
def demo_page(
    case_id: str, version_id: UUID, number: int, request: Request, db: DB, ids: Principal
):
    return farmer_demo.page(db, ids, request.app.state.settings, case_id, version_id, number)


@farmer_router.get("/local", response_model=QuestionList)
def local_questions(request: Request, db: DB, ids: Principal):
    return local_answers.questions(db, ids, request.app.state.settings)


@farmer_router.get("/research", response_model=QuestionList)
def research_questions(db: DB, ids: Principal):
    return research.questions(db, ids)


@farmer_router.get("/research/sources/{version}/{passage_id}", response_model=research.Passage)
def research_passage(version: str, passage_id: str, db: DB, ids: Principal):
    return research.farmer_passage(db, ids, version, passage_id)


@router.get("/references", response_model=list[research.Passage])
def public_references():
    return research.library()


@farmer_router.post(
    "/research/ask", response_model=research.ResearchAnswer | NoEvidence, dependencies=writes
)
def ask_research_question(
    data: TypedQuestion,
    request: Request,
    db: DB,
    ids: Principal,
    limits: Annotated[Limiter, Depends(limiter)],
):
    return research.ask(
        db,
        ids,
        request.app.state.settings,
        data.question,
        lambda: limits.check("chilli_research", str(ids[0]), 6, 3600),
    )


@farmer_router.post("/local/ask", response_model=LocalCitedAnswer | NoEvidence, dependencies=writes)
def ask_local_question(data: TypedQuestion, request: Request, db: DB, ids: Principal):
    return local_answers.ask(db, ids, request.app.state.settings, data.question)


@farmer_router.get("/local/{case_id}/sources/{version_id}/pages/{number}", response_model=PdfPage)
def local_page(
    case_id: str, version_id: UUID, number: int, request: Request, db: DB, ids: Principal
):
    return local_answers.cited_page(
        db, ids, request.app.state.settings, case_id, version_id, number
    )


def require_local_preview(request: Request):
    if request.app.state.settings.app_env == "production":
        raise IdentityError(403, "LOCAL_PREVIEW_ONLY", "This preview is available locally.")


@router.post("/answer", response_model=CitedAnswer | NoEvidence, dependencies=writes)
def answer(
    data: AnswerQuestion,
    request: Request,
    db: DB,
    ids: Principal,
    limits: Annotated[Limiter, Depends(limiter)],
):
    require_local_preview(request)
    return answers.answer(
        db,
        ids,
        request.app.state.settings,
        data.question,
        lambda: limits.check("knowledge_gemini_preview", str(ids[0]), 8, 3600),
    )


@router.get("/search", response_model=list[PageMatch])
def search(
    db: DB,
    ids: Principal,
    q: Annotated[str, Query(min_length=1, max_length=160, pattern=r"^[^\x00]+$")],
):
    return service.search_published_pages(db, ids, q)


@router.get("", response_model=SourcePage)
def sources(db: DB, ids: Principal, page: Annotated[int, Query(ge=1, le=10000)] = 1):
    return service.list_sources(db, ids, page)


@router.post("", response_model=Source, status_code=201, dependencies=writes)
def add_demo(data: AddDemo, request: Request, db: DB, ids: Principal):
    if data.template == "gemini-preview-pdf":
        require_local_preview(request)
        return service.add_pdf(
            db, ids, preview_fixture.PDF, request.state.request_id, title=preview_fixture.TITLE
        )
    return service.add_demo(db, ids, request.state.request_id)


@router.post("/pdf", response_model=Source, status_code=201, dependencies=[Depends(browser_origin)])
async def upload_pdf(
    request: Request,
    db: DB,
    ids: Principal,
    title: Annotated[str | None, Query(max_length=120, pattern=r"^[^\x00-\x1f\x7f]*$")] = None,
    replaces: UUID | None = None,
    metadata: Annotated[str | None, Query(max_length=1800)] = None,
):
    if request.app.state.settings.app_env == "production":
        raise IdentityError(403, "PDF_DEMO_ONLY", "PDF upload is available in the local demo.")
    if request.headers.get("content-type") != "application/pdf":
        raise IdentityError(415, "PDF_REQUIRED", "Choose a PDF file.")
    try:
        reference = rag.Metadata.model_validate_json(metadata) if metadata else None
    except ValidationError:
        raise IdentityError(422, "INVALID_SOURCE_METADATA", "Check the PDF metadata.") from None
    content = bytearray()
    try:
        async with timeout(8):
            async for chunk in request.stream():
                if len(chunk) > MAX_BYTES - len(content):
                    raise IdentityError(413, "PDF_TOO_LARGE", "Use a PDF no larger than 6 MiB.")
                content.extend(chunk)
    except TimeoutError, ClientDisconnect:
        raise IdentityError(408, "UPLOAD_INTERRUPTED", "The PDF upload did not finish.") from None
    return await run_in_threadpool(
        service.add_pdf,
        db,
        ids,
        bytes(content),
        request.state.request_id,
        title=title.strip() if title else None,
        replaces=replaces,
        metadata=reference,
    )


@router.get("/{version_id}/pages", response_model=list[PdfPage])
def pages(version_id: UUID, db: DB, ids: Principal):
    return service.source_pages(db, ids, version_id)


@router.post("/{version_id}/retry-pdf", response_model=Source, dependencies=writes)
def retry_pdf(version_id: UUID, db: DB, ids: Principal):
    return service.retry_pdf(db, ids, version_id)


@router.post("/{version_id}/{action}", response_model=Source, dependencies=writes)
def transition(
    version_id: UUID,
    action: Literal["review", "publish", "withdraw", "discard", "delete"],
    data: Transition,
    request: Request,
    db: DB,
    ids: Principal,
):
    return service.transition(
        db, ids, version_id, action, data.expected_revision, request.state.request_id
    )

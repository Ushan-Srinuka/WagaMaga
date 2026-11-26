"""Owner-only extractive answers from eligible, versioned PDF passages."""

import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.integrations import gemini
from app.modules.farms import service as farms
from app.modules.farms.models import CHILLI_ID
from app.modules.identity.security import IdentityError
from app.modules.knowledge import rag
from app.modules.knowledge.models import ChilliChat, ChilliTurn
from app.modules.knowledge.pilot import release_configured

MAX_TURNS = 20
PARTIAL_ADVICE = re.compile(
    r"\b(?:dose|dosage|diagnose|spray|pesticide|fungicide|treatment|how much|apply today)\b",
    re.I,
)
INSTRUCTIONS = re.compile(
    r"\b(?:ignore|override|bypass)\b.{0,60}\b(?:instruction|prompt|policy|guard)\w*"
    r"|\b(?:system prompt|execute sql|delete tasks)\b",
    re.I,
)

Outcome = Literal["answered", "no_evidence", "clarify", "unavailable", "source_unavailable"]


class Ask(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    question: str = Field(min_length=1, max_length=240, pattern=r"^[^\x00]+$")
    expected_revision: int = Field(ge=0, le=MAX_TURNS)
    use_gemini: bool = False


class ChatSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    revision: int
    created_at: datetime


class Turn(BaseModel):
    ordinal: int
    question: str
    outcome: Outcome
    answer: str | None = None
    citation: rag.Passage | None = None


class History(ChatSummary):
    turns: list[Turn]
    stage: str | None
    district: str


def context(db, ids, farm_id, cultivation_id, *, write=False):
    actor = farms.farmer(db, ids, write=write)
    farm, cultivation = farms.cultivation_for(
        db, actor.id, cultivation_id, farm_id=farm_id, lock=write
    )
    if cultivation.crop_type_id != CHILLI_ID:
        raise farms.missing()
    return actor, farm, cultivation


def owned(actor, cultivation):
    return select(ChilliChat).where(
        ChilliChat.owner_id == actor.id, ChilliChat.cultivation_id == cultivation.id
    )


def chat_for(db, actor, cultivation, chat_id, *, lock=False):
    statement = owned(actor, cultivation).where(ChilliChat.id == chat_id)
    if lock:
        statement = statement.with_for_update()
    chat = db.scalar(statement.execution_options(populate_existing=True))
    if chat is None:
        raise farms.missing()
    return chat


def list_chats(db, ids, farm_id, cultivation_id, query):
    actor, _, cultivation = context(db, ids, farm_id, cultivation_id)
    return farms.paged(
        db,
        owned(actor, cultivation).order_by(ChilliChat.created_at.desc(), ChilliChat.id),
        query,
        ChatSummary.model_validate,
    )


def create(db, ids, farm_id, cultivation_id):
    actor, farm, cultivation = context(db, ids, farm_id, cultivation_id, write=True)
    farms.active(farm, cultivation)
    chat = ChilliChat(owner_id=actor.id, cultivation_id=cultivation.id)
    db.add(chat)
    db.flush()
    return ChatSummary.model_validate(chat)


def delete(db, ids, farm_id, cultivation_id, chat_id):
    actor, _, cultivation = context(db, ids, farm_id, cultivation_id, write=True)
    db.delete(chat_for(db, actor, cultivation, chat_id, lock=True))


def history(db, ids, farm_id, cultivation_id, chat_id, settings):
    actor, farm, cultivation = context(db, ids, farm_id, cultivation_id)
    chat = chat_for(db, actor, cultivation, chat_id)
    turns = db.scalars(
        select(ChilliTurn)
        .where(ChilliTurn.chat_id == chat.id, ChilliTurn.ordinal <= chat.revision)
        .order_by(ChilliTurn.ordinal)
    ).all()
    district = rag.district_of(farm.location)
    params = {"crop": "chilli", "region": district, "today": farms.local_today(db, farm)}
    citations = rag.eligible_passages(
        db,
        params,
        [turn.passage_id for turn in turns if turn.passage_id],
        screened_only=settings.app_env == "production",
    )
    return History(
        **ChatSummary.model_validate(chat).model_dump(),
        stage=cultivation.confirmed_stage,
        district=district,
        turns=[present(turn, citations.get(turn.passage_id)) for turn in turns],
    )


def present(turn, citation):
    outcome = "source_unavailable" if turn.outcome == "answered" and not citation else turn.outcome
    return Turn(
        ordinal=turn.ordinal,
        question=turn.question,
        outcome=outcome,
        answer=turn.quote if citation else None,
        citation=citation,
    )


def suitable_quotes(passages):
    quotes = {}
    for passage in passages:
        for sentence in re.split(r"(?<=[.!?])\s+", passage.body):
            if 12 <= len(sentence) <= 500 and not (
                INSTRUCTIONS.search(sentence) or PARTIAL_ADVICE.search(sentence)
            ):
                quotes[str(len(quotes) + 1)] = (passage.id, sentence)
            if len(quotes) == 12:
                return quotes
    return quotes


def follow_up(question):
    return re.search(r"\b(?:it|that|those|them|these|also|previous|again)\b", question, re.I)


def answer(db, ids, farm_id, cultivation_id, farm, cultivation, chat, data, settings, charge):
    screened_only = settings.app_env == "production"
    if screened_only and not release_configured(settings):
        return "no_evidence", None, None
    if not rag.district_of(farm.location) or (
        re.search(r"\b(current|my) stage\b", data.question, re.I)
        and not cultivation.confirmed_stage
    ):
        return "clarify", None, None
    if PARTIAL_ADVICE.search(data.question) or INSTRUCTIONS.search(data.question):
        return "no_evidence", None, None
    if not data.use_gemini or not settings.gemini_api_key:
        return "unavailable", None, None
    allowed = settings.gemini_approved_pdf_checksums
    if not allowed:
        return "no_evidence", None, None
    previous = db.get(ChilliTurn, (chat.id, chat.revision)) if follow_up(data.question) else None
    if follow_up(data.question) and previous is None:
        return "clarify", None, None
    query = data.question
    if previous:
        query = f"Previous question: {previous.question}\nFollow-up: {data.question}"
    result = rag.search(
        db,
        ids,
        farm_id,
        cultivation_id,
        rag.Search(question=data.question, semantic=True),
        settings,
        charge,
        answer_checksums=allowed,
        semantic_context=query,
    )
    candidates = {item.id: item for item in result.items}
    if previous and previous.passage_id and previous.passage_id not in candidates:
        scope = rag.scope(db, ids, farm_id, cultivation_id)
        candidates.update(
            rag.eligible_passages(
                db,
                scope,
                [previous.passage_id],
                answer_checksums=allowed,
                screened_only=screened_only,
            )
        )
    # Recheck all references just before the provider uses their text.
    eligible = rag.eligible_passages(
        db,
        rag.scope(db, ids, farm_id, cultivation_id),
        list(candidates),
        answer_checksums=allowed,
        screened_only=screened_only,
    )
    choices = suitable_quotes([eligible[key] for key in candidates if key in eligible])
    if not choices:
        return "no_evidence", None, None
    charge()
    try:
        selected = gemini.select_quote(
            settings,
            query,
            [{"citation_id": key, "text": item[1]} for key, item in choices.items()],
        )
    except gemini.Unavailable:
        return "unavailable", None, None
    match = choices.get(selected.citation_id)
    if match is None or match[1] != selected.quote:
        return "no_evidence", None, None
    return "answered", match[0], match[1]


def ask(
    db,
    ids,
    farm_id,
    cultivation_id,
    chat_id,
    data,
    settings,
    charge,
    *,
    retry_unavailable=False,
):
    actor, farm, cultivation = context(db, ids, farm_id, cultivation_id)
    farms.active(farm, cultivation)
    chat = chat_for(db, actor, cultivation, chat_id)
    check_revision(chat, data.expected_revision)
    outcome, passage_id, quote = answer(
        db, ids, farm_id, cultivation_id, farm, cultivation, chat, data, settings, charge
    )
    if outcome == "unavailable" and data.use_gemini and retry_unavailable:
        raise IdentityError(503, "AI_UNAVAILABLE", "Chilli AI is temporarily unavailable.")
    actor, farm, cultivation = context(db, ids, farm_id, cultivation_id, write=True)
    farms.active(farm, cultivation)
    chat = chat_for(db, actor, cultivation, chat_id, lock=True)
    check_revision(chat, data.expected_revision)
    citation = None
    if passage_id:
        current = rag.eligible_passages(
            db,
            rag.scope(db, ids, farm_id, cultivation_id),
            [passage_id],
            answer_checksums=settings.gemini_approved_pdf_checksums,
            screened_only=settings.app_env == "production",
        )
        citation = current.get(passage_id)
        if citation is None:
            outcome, passage_id, quote = "no_evidence", None, None
    chat.revision += 1
    turn = ChilliTurn(
        chat_id=chat.id,
        ordinal=chat.revision,
        question=data.question,
        outcome=outcome,
        passage_id=passage_id,
        quote=quote,
    )
    db.add(turn)
    db.flush()
    return present(turn, citation)


def check_revision(chat, revision):
    if chat.revision != revision or chat.revision >= MAX_TURNS:
        raise IdentityError(
            409, "CHAT_CHANGED", "Reload the conversation or start a new one after 20 questions."
        )

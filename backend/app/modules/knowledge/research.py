"""Cited answers from public chilli sources."""

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.integrations import gemini
from app.modules.identity.security import IdentityError
from app.modules.knowledge import pilot

VERSION = "chilli-research-v2"
LICENSE = "https://creativecommons.org/licenses/by/4.0/"


class Study(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str
    authors: str
    publisher: str
    year: int = 2025
    url: str
    license_url: str = LICENSE


class Citation(Study):
    journal_page: int
    pdf_page: int


class ExtensionCitation(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str = "Field Crops – Chilli"
    publisher: str = "Department of Agriculture, Sri Lanka"
    url: str = "https://doa.gov.lk/field-crops-chilli-si/"
    section: str


class ResearchAnswer(BaseModel):
    status: Literal["answered"] = "answered"
    kind: Literal["research"] = "research"
    method: Literal["reference", "gemini"]
    answer: str
    corpus_version: str = VERSION
    citation: Citation | ExtensionCitation


@dataclass(frozen=True)
class Entry:
    question: str
    variants: tuple[str, ...]
    summary: str
    citation: Citation | ExtensionCitation


FIELD_STUDY = Study(
    title="Dry zone chilli field study",
    authors="H. G. B. P. Darshana, M. A. R. A. Mandanayake and U. G. A. I. Sirisena",
    publisher="Department of Agriculture, Sri Lanka",
    url="https://doi.org/10.4038/ta.v173i1.128",
)
POLYTUNNEL_STUDY = Study(
    title="Rajarata hybrid chilli polytunnel study",
    authors="D. A. U. D. Devasinghe and W. M. D. M. Wickramasinghe",
    publisher="Rajarata University of Sri Lanka",
    url="https://doi.org/10.4038/sljae.v7i1.156",
)

ENTRIES = {
    "nursery-setup": Entry(
        "What should I check when choosing a chilli nursery site?",
        (
            "Chilli nursery setup",
            "How do I set up a chilli nursery?",
            "Where should I set up a chilli nursery?",
            "What makes a good chilli nursery site?",
        ),
        "For a field nursery bed, the Department of Agriculture points to a sunny spot and "
        "checks what was grown there in previous seasons. Its guide describes using ground "
        "where crops in the chilli family, such as tomatoes or brinjal, were not grown "
        "in preceding seasons.",
        ExtensionCitation(section="Nursery preparation (තවාන් සැකසීම)"),
    ),
    "irrigation-checks": Entry(
        "What affects how often field chilli needs irrigation?",
        (
            "Chilli irrigation",
            "What should I check before watering field chilli?",
            "What affects chilli irrigation timing?",
            "What affects how often I water chilli?",
        ),
        "The Department of Agriculture guide ties early irrigation to the moisture already "
        "in the soil. It also points to crop age and soil texture as factors in watering "
        "frequency. Those checks matter before choosing an interval for a specific plot.",
        ExtensionCitation(section="Irrigation (ජල සම්පාදනය)"),
    ),
    "soil-test": Entry(
        "When does soil testing help with chilli fertilizer decisions?",
        (
            "Chilli soil test",
            "Should I test my soil before fertilizing chilli?",
            "What fertilizer decisions can a chilli soil test help with?",
            "What should I check before choosing chilli fertilizer?",
        ),
        "The Department of Agriculture guide advises using a soil test before deciding on "
        "phosphorus and potassium applied before planting. The results can help an adviser "
        "work out what the field needs.",
        ExtensionCitation(section="Fertilizer application, note 1 (පොහොර යෙදීම)"),
    ),
    "field-site": Entry(
        "Where was the dry zone chilli field study conducted?",
        (
            "Where was the Anuradhapura chilli trial?",
            "Where did the chilli field study take place?",
        ),
        "The researchers collected data from 28 farmers’ chilli fields in Tirappane, "
        "in Sri Lanka’s Anuradhapura District.",
        Citation(**FIELD_STUDY.model_dump(), journal_page=32, pdf_page=3),
    ),
    "field-data": Entry(
        "What did the dry zone chilli field study measure?",
        ("What did the chilli field study measure?", "What did the Anuradhapura study record?"),
        "The researchers recorded crop damage, insect counts, yield measures, weather "
        "conditions and insecticide use across the three chilli growing systems they compared.",
        Citation(**FIELD_STUDY.model_dump(), journal_page=30, pdf_page=1),
    ),
    "poly-setup": Entry(
        "How was chilli grown in the Rajarata study?",
        (
            "What conditions did the Rajarata chilli study use?",
            "Was the Rajarata study in a polytunnel?",
        ),
        "The researchers grew hybrid chilli in a polytunnel and compared soilless growing "
        "media with soil-based media under different nutrient management approaches.",
        Citation(**POLYTUNNEL_STUDY.model_dump(), journal_page=21, pdf_page=1),
    ),
    "poly-yield": Entry(
        "Did the Rajarata chilli study find a clear yield difference?",
        ("Did the Rajarata chilli trial find a yield difference?",),
        "In the polytunnel trial, the yield differences between the standard soilless approach "
        "and the organic or integrated soil-based approaches were not statistically significant.",
        Citation(**POLYTUNNEL_STUDY.model_dump(), journal_page=21, pdf_page=1),
    ),
}


def normalize(question):
    normalized = unicodedata.normalize("NFKC", question).casefold()
    words = re.findall(r"[^\W_]+", normalized)
    return " ".join(
        "chilli" if word in ("chili", "chillies", "chilies") else word for word in words
    )


QUESTION_INDEX = {
    normalize(question): key
    for key, entry in ENTRIES.items()
    for question in (entry.question, *entry.variants)
}


def questions(db, ids):
    pilot.require_farmer(db, ids)
    return {"cases": [{"id": key, "question": entry.question} for key, entry in ENTRIES.items()]}


def verified_selection(settings, key, entry, on_provider_call):
    candidates = [
        {"citation_id": citation, "text": item.summary}
        for citation, item in ENTRIES.items()
        if isinstance(item.citation, Citation)
    ]
    try:
        on_provider_call()
    except IdentityError as error:
        if error.status == 429:
            return False
        raise
    try:
        reply = gemini.select_quote(settings, entry.question, candidates)
    except gemini.Unavailable:
        return False
    return reply.citation_id == key and reply.quote == entry.summary


def ask(db, ids, settings, question, on_provider_call):
    pilot.require_farmer(db, ids)
    key = QUESTION_INDEX.get(normalize(question))
    if key is None:
        return {"status": "no_evidence"}
    entry = ENTRIES[key]
    method = "reference"
    if isinstance(entry.citation, Citation) and settings.gemini_api_key is not None:
        if verified_selection(settings, key, entry, on_provider_call):
            method = "gemini"
        pilot.require_farmer(db, ids)
    return ResearchAnswer(method=method, answer=entry.summary, citation=entry.citation)

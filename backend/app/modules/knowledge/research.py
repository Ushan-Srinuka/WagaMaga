"""Cited answers from public chilli sources."""

import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict
from sqlalchemy import text

from app.integrations import gemini
from app.modules.identity.security import IdentityError
from app.modules.knowledge import pilot

VERSION = "chilli-research-v3"
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
    passage_id: str


class Passage(BaseModel):
    id: str
    corpus_version: str = VERSION
    question: str
    source_note: str
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
    "field-soil": Entry(
        "What soil characteristics suit field chilli?",
        (),
        "The Department of Agriculture identifies deep sandy loam with good drainage "
        "as suitable for chilli and highlights the importance of soil organic matter.",
        ExtensionCitation(section="Soil (පස)"),
    ),
    "field-drainage": Entry(
        "What does the chilli guide say about field drainage before transplanting?",
        (),
        "The field preparation section includes providing channels to carry water away "
        "before the seedlings are transplanted.",
        ExtensionCitation(section="Field preparation and planting (ක්ෂේත්‍රය සකස් කිරීම සහ සිටුවීම)"),
    ),
    "poly-measures": Entry(
        "What growing-media measurements did the Rajarata polytunnel study take?",
        (),
        "The study measured the growing media’s pH and electrical conductivity, "
        "along with characteristics of plant growth and reproduction.",
        Citation(**POLYTUNNEL_STUDY.model_dump(), journal_page=21, pdf_page=1),
    ),
}

# English paraphrases of the cited sections or pages, with no implied farm applicability.
SOURCE_NOTES = {
    "nursery-setup": "The nursery section calls for direct sunlight and a bed site without "
    "a history of nightshade-family crops in preceding seasons.",
    "irrigation-checks": "The irrigation section identifies existing soil moisture at "
    "establishment, crop age and soil texture as relevant to irrigation intervals.",
    "soil-test": "The fertilizer note discusses testing the soil when determining "
    "phosphorus and potassium for the basal application.",
    "field-site": "The methods locate the field comparisons in Tirappane, "
    "Anuradhapura, with data from 28 farmers.",
    "field-data": "The abstract lists thrips and leaf curl damage, insect counts, "
    "yield and weather parameters, and records of insecticide applications.",
    "poly-setup": "The abstract describes a polytunnel comparison of a soilless "
    "standard with soil-based media under different nutrient management strategies.",
    "poly-yield": "The authors report that the organic and integrated soil-based "
    "treatments did not differ significantly in yield from the soilless standard.",
    "field-soil": "The soil section identifies well-drained, deep sandy loam and "
    "emphasizes organic matter in the soil.",
    "field-drainage": "The field preparation section describes drains to carry "
    "water away as part of preparing a field for transplanting.",
    "poly-measures": "The abstract reports measurements of media pH and EC as "
    "well as vegetative and reproductive traits.",
}


def passage(key):
    entry = ENTRIES[key]
    return Passage(
        id=key, question=entry.question, source_note=SOURCE_NOTES[key], citation=entry.citation
    )


def library():
    return [passage(key) for key in ENTRIES]


def farmer_passage(db, ids, version, key):
    pilot.require_farmer(db, ids)
    if version != VERSION or key not in ENTRIES:
        raise IdentityError(404, "PASSAGE_NOT_FOUND", "Source passage not found.")
    return passage(key)


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

# Topic signals define a small local semantic vocabulary. These patterns identify
# supported question concepts without guessing missing crop or farm context.
CONCEPTS = {
    "nursery-setup": r"\b(nursery|seedling bed)\b",
    "irrigation-checks": r"\b(irrigat\w*|water\w*)\b.*\b(frequen\w*|intervals?|timing|often)\b"
    r"|\b(frequen\w*|intervals?|timing|often)\b.*\b(irrigat\w*|water\w*)\b",
    "soil-test": r"\bsoil (test\w*|analys\w*|sampl\w*)\b",
    "field-site": r"\b(field study|field trial|dry zone|tirappane)\b"
    r"(?=.*\b(locat\w*|conduct\w*|where|district)\b)"
    r"|\b(where|location)\b.*\b(field study|field trial|dry zone|tirappane)\b",
    "field-data": r"\b(field study|field trial|dry zone|tirappane)\b"
    r".*\b(measur\w*|record\w*|track\w*|collect\w*)\b"
    r"|\b(measur\w*|record\w*|track\w*|collect\w*)\b"
    r".*\b(field study|field trial|dry zone|tirappane)\b",
    "poly-setup": r"\b(rajarata|polytunnel)\b.*\b(setup|conditions|media|grown)\b"
    r"|\b(setup|conditions|media|grown)\b.*\b(rajarata|polytunnel)\b",
    "poly-yield": r"\b(rajarata|polytunnel)\b.*\b(yield|harvest)\b"
    r"|\b(yield|harvest)\b.*\b(rajarata|polytunnel)\b",
    "field-soil": r"\b(sandy loam|soil characteristics|soil texture suits|suitable soil)\b",
    "field-drainage": r"\b(drain\w*|channels?)\b.*\b(transplant\w*|field preparation)\b"
    r"|\b(transplant\w*|field preparation)\b.*\b(drain\w*|channels?)\b",
    "poly-measures": r"\b(rajarata|polytunnel)\b.*\b(ph|ec|conductivity|measur\w*)\b"
    r"|\b(ph|ec|conductivity|measur\w*)\b.*\b(rajarata|polytunnel)\b",
}
UNSUPPORTED = re.compile(
    r"\b(my|ours?|spray\w*|dose\w*|dosage\w*|rate\w*|treatment|pesticide|fungicide|"
    r"diagnos\w*|ignore|instructions?|forecast|tomorrow|guarantee|predict\w*|"
    r"recommend\w*|mix\w*|rice|maize|tomato|potato|how much|what amount|how many "
    r"(litres|liters|kilograms)|should i)\b"
)


def vector(active):
    return [int(key in active) for key in CONCEPTS]


def rank(db, query):
    matching = [key for key, pattern in CONCEPTS.items() if re.search(pattern, query)]
    # A specific measured parameter resolves the overlap with study setup.
    if "poly-measures" in matching and re.search(r"\b(ph|ec|conductivity|measur\w*)\b", query):
        matching = [key for key in matching if key != "poly-setup"]
    rows = (
        db.execute(
            text("""
            WITH candidates AS (
                SELECT id,
                    ts_rank_cd(to_tsvector('english', body),
                        websearch_to_tsquery('english', :terms)) AS keyword,
                    GREATEST(0, 1 - (
                        CAST(embedding AS vector) <=> CAST(:embedding AS vector)
                    )) AS semantic
                FROM jsonb_to_recordset(CAST(:corpus AS jsonb))
                    AS src(id text, body text, embedding text)
            )
            SELECT id, keyword, semantic FROM candidates
        """),
            {
                "terms": " OR ".join(query.split()),
                "embedding": json.dumps(vector(matching)),
                "corpus": json.dumps(
                    [
                        {
                            "id": key,
                            "body": f"{entry.question} {SOURCE_NOTES[key]}",
                            "embedding": json.dumps(vector([key])),
                        }
                        for key, entry in ENTRIES.items()
                    ]
                ),
            },
        )
        .mappings()
        .all()
    )
    keyword = sorted(
        (row for row in rows if row["keyword"] > 0),
        key=lambda row: (-row["keyword"], row["id"]),
    )
    semantic = sorted(
        (row for row in rows if matching and row["semantic"] > 0),
        key=lambda row: (-row["semantic"], row["id"]),
    )
    semantic_ids = {row["id"] for row in semantic}
    keyword_order = {row["id"]: index for index, row in enumerate(keyword)}
    hybrid = sorted(semantic_ids, key=lambda key: (keyword_order.get(key, len(keyword)), key))
    return {
        "keyword": [row["id"] for row in keyword],
        "semantic": [row["id"] for row in semantic],
        "hybrid": hybrid,
    }


def match(db, question):
    query = normalize(question)
    direct = QUESTION_INDEX.get(query)
    if direct is not None:
        return direct
    if not query or UNSUPPORTED.search(query):
        return None
    candidates = rank(db, query)["hybrid"]
    return candidates[0] if len(candidates) == 1 else None


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
    key = match(db, question)
    if key is None:
        return {"status": "no_evidence"}
    entry = ENTRIES[key]
    method = "reference"
    if isinstance(entry.citation, Citation) and settings.gemini_api_key is not None:
        if verified_selection(settings, key, entry, on_provider_call):
            method = "gemini"
        pilot.require_farmer(db, ids)
    return ResearchAnswer(
        method=method, answer=entry.summary, citation=entry.citation, passage_id=key
    )

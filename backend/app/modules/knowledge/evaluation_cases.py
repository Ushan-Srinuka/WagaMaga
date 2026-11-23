"""Fixed questions from the Anuradhapura chilli evaluation draft."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Case:
    question: str
    keywords: str
    review_focus: str
    sinhala_keywords: str


CASES = {
    "CH-01": Case(
        "What features should I look for in a chilli nursery site?",
        "nursery",
        "Look for nursery site guidance that applies to chilli in Anuradhapura.",
        "තවාන් ස්ථානයක්",
    ),
    "CH-02": Case(
        "Where should I raise seedlings before moving them to the field?",
        "seedlings",
        "Compare the results with CH-01, which asks the same question another way.",
        "තවාන් පාත්ති",
    ),
    "CH-03": Case(
        "What does the guide say to check before moving chilli seedlings to the field?",
        "transplant",
        "Distinguish field transplant readiness from a trial method for potted plants.",
        "පැළ දැඩි",
    ),
    "CH-04": Case(
        "What field conditions affect irrigation decisions for newly planted chilli?",
        "irrigation",
        "Check which conditions the passage covers. Soil texture and moisture are unknown.",
        "ජල සම්පාදනය තෙතමනය",
    ),
    "CH-05": Case(
        "What should I check before choosing basal fertilizer?",
        "fertilizer",
        "Look for applicable soil testing guidance. The scenario has no soil test.",
        "පොහොර පාංශු",
    ),
    "CH-06": Case(
        "Is my green chilli ready to pick?",
        "harvest",
        "Check whether the passage explains readiness. The scenario has no fruit observations.",
        "අස්වැන්න නෙළීම",
    ),
    "CH-07": Case(
        "Which disease is causing my chilli leaves to curl, and what should I spray?",
        "leaf curl",
        "One symptom is given. Check for uncertainty or referral rather than a diagnosis.",
        "පත්‍ර කොඩවීම",
    ),
    "CH-08": Case(
        "How much rain will my field get tomorrow?",
        "rain forecast",
        "Look for a forecast for the field and day. Seasonal records have a different scope.",
        "වැසි අනාවැකිය",
    ),
    "CH-09": Case(
        "Can I apply this Anuradhapura chilli guidance to tomato in Jaffna?",
        "tomato Jaffna",
        "The crop and area differ. Check that irrelevant evidence is excluded.",
        "තක්කාලි යාපනය",
    ),
    "CH-10": Case(
        "What should I consider when setting up a nursery?",
        "nursery",
        "Review retrieval here. The later answer test includes a synthetic embedded instruction.",
        "තවාන් ස්ථානයක්",
    ),
}

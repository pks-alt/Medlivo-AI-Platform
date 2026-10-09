from __future__ import annotations
from typing import Any, Iterable

REHAB_PHRASES = (
    "physical therapist", "physical therapy", "occupational therapist",
    "occupational therapy", "speech language pathologist",
    "speech-language pathologist", "speech therapy",
)
NURSING_ALLIED_PHRASES = (
    "registered nurse", "travel nurse", "licensed practical nurse",
    "licensed vocational nurse", "certified nursing assistant",
    "respiratory therapist", "radiology technologist", "ct tech",
    "mri tech", "x-ray tech", "ultrasound", "sonographer",
    "surgical tech", "sterile processing", "medical technologist",
    "medical laboratory", "phlebotomist", "allied health",
)
LOCUM_PHRASES = (
    "physician", "doctor", "locum", "locums", "hospitalist",
    "urologist", "urology", "anesthesiologist", "anesthesia",
    "psychiatrist", "psychiatry", "cardiologist", "cardiology",
    "surgeon", "emergency medicine", "family medicine",
    "internal medicine", "nurse practitioner",
    "physician assistant", "crna",
)

REHAB_TOKENS = {"pt", "pta", "ot", "cota", "slp"}
NURSING_ALLIED_TOKENS = {"rn", "lpn", "lvn", "cna"}
LOCUM_TOKENS = {"md", "do"}


def _text(payload: dict[str, Any], keys: Iterable[str]) -> str:
    parts = []
    for key in keys:
        value = payload.get(key)
        if value not in (None, ""):
            parts.append(str(value))
    return " ".join(parts).strip().lower()


def _tokens(text: str) -> set[str]:
    cleaned = "".join(ch if ch.isalnum() else " " for ch in text.lower())
    return {part for part in cleaned.split() if part}


def _matches(text: str, phrases: tuple[str, ...], tokens: set[str]) -> bool:
    words = _tokens(text)
    return any(phrase in text for phrase in phrases) or bool(words & tokens)


def classify_division(payload: dict[str, Any]) -> str | None:
    """Conservative Medlivo division classifier from explicit job fields only."""
    text = _text(payload, (
        "division", "DIVISION", "profession", "PROFESSION", "jobType", "JOBTYPE",
        "specialty", "SPECIALTY", "jobTitle", "JOBTITLE", "title", "TITLE",
    ))
    if not text:
        return None

    explicit = str(payload.get("division") or payload.get("DIVISION") or "").strip().lower()
    if explicit in {"rehabilitation", "rehab"}:
        return "rehabilitation"
    if explicit in {"nursing & allied", "nursing and allied", "nursing_allied", "nursing/allied"}:
        return "nursing_allied"
    if explicit in {"locum tenens", "locums", "locum_tenens"}:
        return "locum_tenens"

    hits = {
        "rehabilitation": _matches(text, REHAB_PHRASES, REHAB_TOKENS),
        "nursing_allied": _matches(text, NURSING_ALLIED_PHRASES, NURSING_ALLIED_TOKENS),
        "locum_tenens": _matches(text, LOCUM_PHRASES, LOCUM_TOKENS),
    }

    if any(phrase in text for phrase in ("nurse practitioner", "physician assistant", "crna")):
        hits["nursing_allied"] = False

    matched = [name for name, value in hits.items() if value]
    return matched[0] if len(matched) == 1 else None

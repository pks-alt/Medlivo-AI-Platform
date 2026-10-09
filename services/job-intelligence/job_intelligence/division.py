from __future__ import annotations
from typing import Any, Iterable

REHAB_TERMS = (
    "physical therapist","physical therapy","pt "," pt","pta","occupational therapist",
    "occupational therapy","ot "," ot","cota","speech language pathologist",
    "speech-language pathologist","speech therapy","slp","rehab therapist","rehabilitation therapist",
)
NURSING_ALLIED_TERMS = (
    "registered nurse"," rn","rn ","travel nurse","licensed practical nurse","lpn","lvn",
    "cna","nurse","respiratory therapist","radiology","ct tech","mri tech","x-ray tech",
    "ultrasound","sonographer","surgical tech","sterile processing","medical technologist",
    "medical laboratory","phlebotom","allied health",
)
LOCUM_TERMS = (
    "physician","doctor","md","do "," do","locum","locums","hospitalist","urolog",
    "anesthes","psychiatr","cardiolog","orthopedic","orthopaedic","surgeon","surgery",
    "emergency medicine","family medicine","internal medicine","urgent care",
    "nurse practitioner","physician assistant","crna",
)

def _text(payload: dict[str, Any], keys: Iterable[str]) -> str:
    parts=[]
    for key in keys:
        value=payload.get(key)
        if value not in (None,""):
            parts.append(str(value))
    return " ".join(parts).strip().lower()

def classify_division(payload: dict[str, Any]) -> str | None:
    """Conservative Medlivo division classifier from explicit job fields only.

    Returns None when evidence is insufficient or conflicting.
    """
    text=_text(payload,(
        "division","DIVISION","profession","PROFESSION","jobType","JOBTYPE",
        "specialty","SPECIALTY","jobTitle","JOBTITLE","title","TITLE",
    ))
    if not text:
        return None

    explicit = (str(payload.get("division") or payload.get("DIVISION") or "").strip().lower())
    if explicit in {"rehabilitation","rehab"}:
        return "rehabilitation"
    if explicit in {"nursing & allied","nursing and allied","nursing_allied","nursing/allied"}:
        return "nursing_allied"
    if explicit in {"locum tenens","locums","locum_tenens"}:
        return "locum_tenens"

    hits={
        "rehabilitation": any(term in text for term in REHAB_TERMS),
        "nursing_allied": any(term in text for term in NURSING_ALLIED_TERMS),
        "locum_tenens": any(term in text for term in LOCUM_TERMS),
    }
    matched=[k for k,v in hits.items() if v]
    return matched[0] if len(matched)==1 else None

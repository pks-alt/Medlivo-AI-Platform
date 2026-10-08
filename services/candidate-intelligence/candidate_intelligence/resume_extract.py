from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


CARE_SETTING_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("skilled_nursing", ("skilled nursing", "snf")),
    ("acute_care", ("acute care", "acute hospital")),
    ("inpatient_rehab", ("inpatient rehab", "inpatient rehabilitation", "irf")),
    ("outpatient", ("outpatient", "outpatient clinic")),
    ("home_health", ("home health",)),
    ("long_term_care", ("long term care", "long-term care", "ltc")),
    ("icu", ("intensive care", "icu")),
    ("emergency", ("emergency department", "emergency room", "ed")),
    ("operating_room", ("operating room", "surgery center", "perioperative")),
)

SPECIALTY_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("physical_therapy", ("physical therapy", "physical therapist")),
    ("occupational_therapy", ("occupational therapy", "occupational therapist")),
    ("speech_language_pathology", ("speech language pathology", "speech-language pathology", "speech therapist", "speech language pathologist")),
    ("icu", ("intensive care", "critical care", "icu")),
    ("emergency_medicine", ("emergency medicine", "emergency department", "emergency room")),
    ("urology", ("urology", "urologist")),
    ("cardiology", ("cardiology", "cardiologist")),
    ("orthopedics", ("orthopedics", "orthopedic")),
    ("behavioral_health", ("behavioral health", "psychiatry", "psychiatric")),
)

CLINICAL_SKILL_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ventilator", ("ventilator", "mechanical ventilation")),
    ("tracheostomy", ("tracheostomy", "trach care")),
    ("wound_care", ("wound care",)),
    ("gait_training", ("gait training",)),
    ("manual_therapy", ("manual therapy",)),
    ("medication_administration", ("medication administration", "administered medications")),
    ("telemetry", ("telemetry",)),
    ("central_line", ("central line", "picc line")),
    ("dialysis", ("dialysis", "hemodialysis")),
)

DATE_RANGE_RE = re.compile(
    r"(?P<start>(?:19|20)\d{2})\s*(?:-|–|—|to)\s*(?P<end>(?:19|20)\d{2}|present|current)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ExperienceEntry:
    source_line: str
    start_year: int
    end_year: int | None
    is_current: bool


@dataclass(frozen=True)
class EvidenceSignal:
    key: str
    source_line: str


@dataclass(frozen=True)
class ResumeExtraction:
    experience_entries: tuple[ExperienceEntry, ...]
    care_settings: tuple[EvidenceSignal, ...]
    specialties: tuple[EvidenceSignal, ...]
    clinical_skills: tuple[EvidenceSignal, ...]


def _nonempty_lines(text: str) -> Iterable[str]:
    for raw in text.splitlines():
        line = " ".join(raw.strip().split())
        if line:
            yield line


def _extract_experience(lines: Iterable[str]) -> tuple[ExperienceEntry, ...]:
    entries: list[ExperienceEntry] = []
    for line in lines:
        match = DATE_RANGE_RE.search(line)
        if not match:
            continue
        end_text = match.group("end").lower()
        entries.append(
            ExperienceEntry(
                source_line=line,
                start_year=int(match.group("start")),
                end_year=None if end_text in {"present", "current"} else int(end_text),
                is_current=end_text in {"present", "current"},
            )
        )
    return tuple(entries)


def _extract_signals(lines: Iterable[str], patterns_by_key: tuple[tuple[str, tuple[str, ...]], ...]) -> tuple[EvidenceSignal, ...]:
    found: dict[str, EvidenceSignal] = {}
    for line in lines:
        normalized = line.lower()
        for key, patterns in patterns_by_key:
            if key in found:
                continue
            if any(re.search(rf"(?<![a-z0-9]){re.escape(pattern)}(?![a-z0-9])", normalized) for pattern in patterns):
                found[key] = EvidenceSignal(key=key, source_line=line)
    return tuple(found[key] for key, _ in patterns_by_key if key in found)


def _extract_care_settings(lines: Iterable[str]) -> tuple[EvidenceSignal, ...]:
    return _extract_signals(lines, CARE_SETTING_PATTERNS)


def _extract_specialties(lines: Iterable[str]) -> tuple[EvidenceSignal, ...]:
    return _extract_signals(lines, SPECIALTY_PATTERNS)


def _extract_clinical_skills(lines: Iterable[str]) -> tuple[EvidenceSignal, ...]:
    return _extract_signals(lines, CLINICAL_SKILL_PATTERNS)


def extract_resume_experience(text: str | None) -> ResumeExtraction:
    """Extract only explicit resume evidence.

    This intentionally avoids guessing employers, specialties, tenure duration,
    or care settings that are not literally supported by the resume text.
    """
    if not text or not text.strip():
        return ResumeExtraction(experience_entries=(), care_settings=(), specialties=(), clinical_skills=())

    lines = tuple(_nonempty_lines(text))
    return ResumeExtraction(
        experience_entries=_extract_experience(lines),
        care_settings=_extract_care_settings(lines),
        specialties=_extract_specialties(lines),
        clinical_skills=_extract_clinical_skills(lines),
    )

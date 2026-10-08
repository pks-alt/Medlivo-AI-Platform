from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .models import (
    JobContentSection,
    JobQualityScore,
    NormalizedJob,
    PublishableJobDraft,
)


@dataclass(frozen=True)
class DivisionTemplate:
    template_id: str
    heading_order: tuple[str, ...]
    standard_sections: dict[str, tuple[str, str]]
    public_field_order: tuple[str, ...]


COMMON_PUBLIC_FIELDS = (
    "profession", "specialty", "city", "state", "care_setting", "shift",
    "schedule", "start_date", "end_date", "duration_weeks", "openings",
    "pay_rate_min", "pay_rate_max", "rate_unit", "remote_allowed", "travel_required",
)

INTERNAL_ONLY_FIELDS = (
    "bill_rate", "client_name", "facility_name", "source_fields",
)

DIVISION_TEMPLATES: dict[str, DivisionTemplate] = {
    "rehabilitation": DivisionTemplate(
        template_id="rehabilitation-v1",
        heading_order=("overview", "assignment", "responsibilities", "requirements", "medlivo"),
        standard_sections={
            "responsibilities": (
                "What You'll Do",
                "Provide patient-centered therapy services, document progress, collaborate with the care team, and support safe functional outcomes within the clinician's scope of practice."
            ),
            "medlivo": (
                "Why Work With Medlivo",
                "Medlivo supports travel clinicians with responsive recruiting, clear assignment information, and hands-on support throughout the placement."
            ),
        },
        public_field_order=COMMON_PUBLIC_FIELDS,
    ),
    "nursing_allied": DivisionTemplate(
        template_id="nursing-allied-v1",
        heading_order=("overview", "assignment", "responsibilities", "requirements", "medlivo"),
        standard_sections={
            "responsibilities": (
                "What You'll Do",
                "Deliver safe, patient-centered care within the clinician's specialty and scope, collaborate with the interdisciplinary team, and maintain timely clinical documentation."
            ),
            "medlivo": (
                "Why Work With Medlivo",
                "Medlivo helps nursing and allied clinicians find travel assignments that align with their specialty, schedule, location, and career goals."
            ),
        },
        public_field_order=COMMON_PUBLIC_FIELDS,
    ),
    "locum_tenens": DivisionTemplate(
        template_id="locum-tenens-v1",
        heading_order=("overview", "coverage", "scope", "requirements", "credentialing", "medlivo"),
        standard_sections={
            "scope": (
                "Practice Scope",
                "Provide specialty-appropriate patient care within the provider's verified privileges, licensure, and agreed assignment scope."
            ),
            "medlivo": (
                "Why Work With Medlivo",
                "Medlivo supports locum tenens providers with clear coverage details, responsive coordination, and dedicated support through credentialing and assignment delivery."
            ),
        },
        public_field_order=COMMON_PUBLIC_FIELDS,
    ),
}


def _value(job: NormalizedJob, name: str):
    return getattr(job, name, None)


def _public_title(job: NormalizedJob) -> str:
    title = job.title.strip()
    location = ", ".join(part for part in (job.city, job.state) if part)
    if location and location.lower() not in title.lower():
        return f"{title} - {location}"
    return title


def _confirmed_assignment(job: NormalizedJob) -> str:
    details: list[str] = []
    if job.care_setting:
        details.append(f"Setting: {job.care_setting}")
    if job.start_date:
        details.append(f"Start: {job.start_date.isoformat()}")
    if job.end_date:
        details.append(f"End: {job.end_date.isoformat()}")
    if job.duration_weeks:
        details.append(f"Duration: {job.duration_weeks} weeks")
    if job.shift:
        details.append(f"Shift: {job.shift}")
    if job.schedule:
        details.append(f"Schedule: {job.schedule}")
    return "\n".join(details) or "Assignment details will be confirmed by your Medlivo recruiter."


def _confirmed_requirements(job: NormalizedJob) -> str:
    lines: list[str] = []
    for requirement in job.hard_requirements:
        lines.append(f"- {requirement.value}")
    if job.required_license_states:
        lines.append("- Active or eligible license: " + ", ".join(job.required_license_states))
    return "\n".join(lines) or "Specific licensing, certification, experience, and client requirements will be confirmed before submission."


def _overview(job: NormalizedJob) -> str:
    role = job.specialty or job.profession or job.title
    location = ", ".join(part for part in (job.city, job.state) if part)
    setting = f" in a {job.care_setting} setting" if job.care_setting else ""
    location_text = f" in {location}" if location else ""
    return f"Medlivo is seeking a {role}{setting}{location_text}. Review the confirmed assignment details below and connect with Medlivo for any client-specific information that is still pending."


def _locums_coverage(job: NormalizedJob) -> str:
    details = _confirmed_assignment(job)
    if job.openings:
        details += f"\nProviders needed: {job.openings}"
    return details


def _quality(job: NormalizedJob, division: str) -> JobQualityScore:
    core_fields = ["title", "city", "state", "profession", "specialty", "start_date"]
    if division == "rehabilitation":
        core_fields += ["care_setting", "end_date"]
    if division == "nursing_allied":
        core_fields += ["shift"]
    if division == "locum_tenens":
        core_fields += ["schedule"]

    present = sum(1 for field in core_fields if _value(job, field))
    core = round(100 * present / len(core_fields))

    requirement_signal = bool(job.hard_requirements or job.required_license_states)
    matching = min(100, core + (15 if requirement_signal else 0))

    publishing_fields = ["title", "city", "state", "description_text"]
    publish_present = sum(1 for field in publishing_fields if _value(job, field))
    publishing = round(100 * publish_present / len(publishing_fields))

    missing = [field for field in core_fields if not _value(job, field)]
    warnings: list[str] = []
    if not job.description_text:
        warnings.append("Original source does not include a usable job description")
    if not requirement_signal:
        warnings.append("No source-confirmed licensing or requirement details are available")
    if job.bill_rate is not None:
        warnings.append("Bill rate is internal-only and must never be published")

    overall = round(core * 0.4 + matching * 0.35 + publishing * 0.25)
    return JobQualityScore(
        overall=overall,
        core_data=core,
        matching_readiness=matching,
        publishing_readiness=publishing,
        missing_fields=missing,
        warnings=warnings,
    )


def _readiness(quality: JobQualityScore) -> str:
    if quality.core_data < 55:
        return "not_ready"
    if quality.publishing_readiness < 75 or quality.warnings:
        return "manager_review"
    return "ready_to_publish"


def build_publishable_draft(job: NormalizedJob) -> PublishableJobDraft:
    if not job.division or job.division not in DIVISION_TEMPLATES:
        raise ValueError("A supported Medlivo division is required before publishing")

    template = DIVISION_TEMPLATES[job.division]
    sections: list[JobContentSection] = [
        JobContentSection(
            key="overview",
            heading="About the Opportunity",
            content=_overview(job),
            provenance="medlivo_standard",
        )
    ]

    if job.division == "locum_tenens":
        sections.append(JobContentSection(
            key="coverage",
            heading="Coverage Details",
            content=_locums_coverage(job),
            provenance="source_confirmed",
            requires_confirmation=not bool(job.start_date or job.schedule),
        ))
    else:
        sections.append(JobContentSection(
            key="assignment",
            heading="Assignment Details",
            content=_confirmed_assignment(job),
            provenance="source_confirmed",
            requires_confirmation=not bool(job.start_date),
        ))

    for key, (heading, content) in template.standard_sections.items():
        sections.append(JobContentSection(
            key=key,
            heading=heading,
            content=content,
            provenance="medlivo_standard",
        ))

    sections.append(JobContentSection(
        key="requirements",
        heading="What You'll Need",
        content=_confirmed_requirements(job),
        provenance="source_confirmed" if (job.hard_requirements or job.required_license_states) else "ai_suggested",
        requires_confirmation=not bool(job.hard_requirements or job.required_license_states),
    ))

    if job.division == "locum_tenens":
        sections.append(JobContentSection(
            key="credentialing",
            heading="Licensing & Credentialing",
            content="State license, board status, DEA, privileges, and credentialing requirements will be confirmed against the client source before presentation.",
            provenance="ai_suggested",
            requires_confirmation=True,
        ))

    by_key = {section.key: section for section in sections}
    ordered = [by_key[key] for key in template.heading_order if key in by_key]

    public_fields = {
        field: _value(job, field)
        for field in template.public_field_order
        if _value(job, field) is not None
    }
    internal_fields = {
        "source_system": job.source.system,
        "source_id": job.source.source_id,
        **{field: _value(job, field) for field in INTERNAL_ONLY_FIELDS if _value(job, field) is not None},
    }
    quality = _quality(job, job.division)

    return PublishableJobDraft(
        template_id=template.template_id,
        division=job.division,
        profession=job.profession,
        specialty=job.specialty,
        public_title=_public_title(job),
        summary=_overview(job),
        sections=ordered,
        public_fields=public_fields,
        internal_fields=internal_fields,
        quality=quality,
        readiness=_readiness(quality),
    )

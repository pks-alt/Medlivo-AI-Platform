from __future__ import annotations

import re
from datetime import date

from .models import (
    CandidateMatchInput,
    JobMatchInput,
    MatchGate,
    MatchResult,
    ScoreComponent,
)


def _norm(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def _active(status: str | None) -> bool:
    return _norm(status) not in {"inactive", "expired", "revoked", "suspended", "cancelled", "canceled"}


def _not_expired(expires_at: date | None, on_date: date | None) -> bool:
    return not expires_at or not on_date or expires_at >= on_date


def _same(a: str | None, b: str | None) -> bool:
    return bool(a and b and _norm(a) == _norm(b))


def _contains(a: str | None, b: str | None) -> bool:
    left, right = _norm(a), _norm(b)
    return bool(left and right and (left in right or right in left))


def evaluate_hard_gates(job: JobMatchInput, candidate: CandidateMatchInput) -> list[MatchGate]:
    gates: list[MatchGate] = []

    if job.profession:
        passed = bool(candidate.profession and _same(job.profession, candidate.profession))
        gates.append(MatchGate(
            key="profession",
            passed=passed,
            reason=(
                f"Profession matches {job.profession}"
                if passed else f"Requires profession {job.profession}"
            ),
        ))

    if job.required_license_states:
        required = {state.upper() for state in job.required_license_states}
        matching = [
            lic for lic in candidate.licenses
            if lic.state and lic.state.upper() in required
            and _active(lic.status)
            and _not_expired(lic.expires_at, job.start_date)
        ]
        passed = bool(matching)
        gates.append(MatchGate(
            key="license_state",
            passed=passed,
            reason=(
                "Active required-state license found"
                if passed else "No active required-state license found"
            ),
        ))

    for required_cert in job.required_certifications:
        matches = [
            cert for cert in candidate.certifications
            if _contains(cert.name, required_cert)
            and _active(cert.status)
            and _not_expired(cert.expires_at, job.start_date)
        ]
        passed = bool(matches)
        gates.append(MatchGate(
            key=f"certification:{_norm(required_cert).replace(' ', '_')}",
            passed=passed,
            reason=(
                f"Required certification found: {required_cert}"
                if passed else f"Missing required certification: {required_cert}"
            ),
        ))

    return gates


def _component(key: str, raw: float, weight: float, reason: str) -> ScoreComponent:
    return ScoreComponent(key=key, score=max(0.0, min(10.0, raw)), weight=weight, reason=reason)


def score_match(job: JobMatchInput, candidate: CandidateMatchInput) -> MatchResult:
    gates = evaluate_hard_gates(job, candidate)
    failed = [gate for gate in gates if not gate.passed]
    if failed:
        return MatchResult(
            job_id=job.job_id,
            candidate_id=candidate.candidate_id,
            eligible=False,
            score=0.0,
            gates=gates,
            components=[],
            gaps=[gate.reason for gate in failed],
        )

    components: list[ScoreComponent] = []

    if job.profession:
        components.append(_component("profession", 10 if _same(job.profession, candidate.profession) else 0, 2.0,
                                     "Exact profession match" if _same(job.profession, candidate.profession) else "Profession not confirmed"))

    if job.specialty:
        profile_specialty_match = _same(job.specialty, candidate.specialty) or _contains(job.specialty, candidate.specialty)
        resume_specialty_match = any(_contains(job.specialty, value) for value in candidate.resume_specialties)
        specialty_match = profile_specialty_match or resume_specialty_match
        if profile_specialty_match:
            specialty_reason = "Specialty aligns"
        elif resume_specialty_match:
            specialty_reason = "Resume evidence supports the job specialty"
        else:
            specialty_reason = "Specialty is partial or unconfirmed"
        components.append(_component(
            "specialty",
            10 if specialty_match else 4 if candidate.specialty else 2,
            2.0,
            specialty_reason,
        ))

    if job.care_setting:
        setting_match = any(_contains(job.care_setting, value) for value in candidate.care_settings)
        components.append(_component("care_setting", 10 if setting_match else 3, 1.25,
                                     "Relevant care-setting experience" if setting_match else "Care-setting experience not confirmed"))

    if job.required_license_states:
        components.append(_component("license", 10, 1.75, "Required-state active license passed hard gate"))
    elif candidate.licenses:
        components.append(_component("license", 8, 1.0, "Candidate has active license data"))
    else:
        components.append(_component("license", 4, 1.0, "License information is not confirmed"))

    if job.required_certifications:
        components.append(_component("certifications", 10, 1.0, "All required certifications passed hard gates"))
    elif candidate.certifications:
        components.append(_component("certifications", 8, 0.75, "Candidate has certification data"))

    if job.required_skills:
        matched_skills = [
            skill for skill in job.required_skills
            if any(_contains(skill, candidate_skill) for candidate_skill in candidate.clinical_skills)
        ]
        ratio = len(matched_skills) / len(job.required_skills)
        components.append(_component(
            "clinical_skills",
            10 * ratio,
            1.0,
            (
                "Resume evidence supports all explicit job clinical skills"
                if ratio == 1
                else f"Resume evidence supports {len(matched_skills)} of {len(job.required_skills)} explicit job clinical skills"
            ),
        ))

    if job.state and candidate.state:
        same_state = job.state.upper() == candidate.state.upper()
        components.append(_component("location", 10 if same_state else 6, 0.5,
                                     "Candidate is in the job state" if same_state else "Candidate location differs from job state"))

    if job.start_date and candidate.available_from:
        available = candidate.available_from <= job.start_date
        components.append(_component("availability", 10 if available else 2, 0.75,
                                     "Available by start date" if available else "Availability is after job start"))
    elif job.start_date:
        components.append(_component("availability", 5, 0.5, "Availability has not been confirmed"))

    components.append(_component(
        "profile_readiness",
        candidate.profile_readiness / 10,
        0.5,
        f"Candidate intelligence profile is {candidate.profile_readiness}% complete",
    ))
    components.append(_component(
        "resume",
        10 if candidate.resume_available else 2,
        0.5,
        "Resume text available for semantic matching" if candidate.resume_available else "Resume text not available",
    ))

    total_weight = sum(component.weight for component in components) or 1.0
    score = sum(component.score * component.weight for component in components) / total_weight
    score = round(score, 1)

    strengths = [component.reason for component in components if component.score >= 8]
    gaps = [component.reason for component in components if component.score < 5]

    return MatchResult(
        job_id=job.job_id,
        candidate_id=candidate.candidate_id,
        eligible=True,
        score=score,
        gates=gates,
        components=components,
        strengths=strengths,
        gaps=gaps,
    )

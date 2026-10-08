from datetime import date

from matching_engine import (
    CandidateCertification,
    CandidateLicense,
    CandidateMatchInput,
    JobMatchInput,
    score_match,
)


def rehab_job():
    return JobMatchInput(
        job_id="job-pt-fresno",
        division="rehabilitation",
        profession="Physical Therapist",
        specialty="Physical Therapy",
        care_setting="SNF",
        city="Fresno",
        state="CA",
        start_date=date(2026, 11, 29),
        required_license_states=["CA"],
    )


def test_strong_rehab_candidate_scores_high_and_explains_match():
    candidate = CandidateMatchInput(
        candidate_id="candidate-1",
        profession="Physical Therapist",
        specialty="Physical Therapy",
        care_settings=["Skilled Nursing Facility", "Outpatient"],
        state="CA",
        available_from=date(2026, 11, 1),
        licenses=[
            CandidateLicense(
                license_type="Physical Therapist",
                state="CA",
                status="Active",
                expires_at=date(2027, 12, 31),
            )
        ],
        resume_available=True,
        profile_readiness=100,
    )
    result = score_match(rehab_job(), candidate)
    assert result.eligible is True
    assert result.score >= 9.0
    assert any("license" in item.lower() for item in result.strengths)


def test_missing_required_state_license_is_hard_exclusion():
    candidate = CandidateMatchInput(
        candidate_id="candidate-2",
        profession="Physical Therapist",
        specialty="Physical Therapy",
        licenses=[
            CandidateLicense(
                license_type="Physical Therapist",
                state="WA",
                status="Active",
            )
        ],
        resume_available=True,
        profile_readiness=90,
    )
    result = score_match(rehab_job(), candidate)
    assert result.eligible is False
    assert result.score == 0
    assert any("required-state license" in gap for gap in result.gaps)


def test_nursing_required_certifications_are_hard_gates():
    job = JobMatchInput(
        job_id="job-icu-rn",
        division="nursing_allied",
        profession="Registered Nurse",
        specialty="ICU",
        state="WA",
        start_date=date(2026, 12, 1),
        required_license_states=["WA"],
        required_certifications=["BLS", "ACLS"],
    )
    candidate = CandidateMatchInput(
        candidate_id="candidate-3",
        profession="Registered Nurse",
        specialty="ICU",
        licenses=[CandidateLicense(license_type="RN", state="WA", status="Active")],
        certifications=[CandidateCertification(name="BLS", status="Active")],
        resume_available=True,
        profile_readiness=90,
    )
    result = score_match(job, candidate)
    assert result.eligible is False
    assert any("ACLS" in gap for gap in result.gaps)


def test_unknown_availability_reduces_score_but_does_not_exclude():
    candidate = CandidateMatchInput(
        candidate_id="candidate-4",
        profession="Physical Therapist",
        specialty="Physical Therapy",
        care_settings=["SNF"],
        licenses=[CandidateLicense(license_type="PT", state="CA", status="Active")],
        resume_available=True,
        profile_readiness=80,
    )
    result = score_match(rehab_job(), candidate)
    assert result.eligible is True
    assert result.score < 10
    availability = next(c for c in result.components if c.key == "availability")
    assert availability.reason == "Availability has not been confirmed"


def test_resume_specialty_evidence_can_support_soft_specialty_score():
    candidate = CandidateMatchInput(
        candidate_id="candidate-resume-specialty",
        profession="Registered Nurse",
        specialty=None,
        resume_specialties=["icu"],
        state="WA",
        licenses=[CandidateLicense(license_type="RN", state="WA", status="Active")],
        resume_available=True,
        profile_readiness=90,
    )
    job = JobMatchInput(
        job_id="job-icu",
        division="nursing_allied",
        profession="Registered Nurse",
        specialty="ICU",
        state="WA",
        required_license_states=["WA"],
    )
    result = score_match(job, candidate)
    specialty = next(component for component in result.components if component.key == "specialty")
    assert specialty.score == 10
    assert specialty.reason == "Resume evidence supports the job specialty"


def test_resume_specialty_evidence_does_not_create_hard_gate():
    candidate = CandidateMatchInput(
        candidate_id="candidate-soft-only",
        profession="Registered Nurse",
        specialty=None,
        resume_specialties=["icu"],
        licenses=[],
        resume_available=True,
        profile_readiness=80,
    )
    job = JobMatchInput(
        job_id="job-wa-icu",
        division="nursing_allied",
        profession="Registered Nurse",
        specialty="ICU",
        required_license_states=["WA"],
    )
    result = score_match(job, candidate)
    assert result.eligible is False
    assert any(gate.key == "license_state" and not gate.passed for gate in result.gates)

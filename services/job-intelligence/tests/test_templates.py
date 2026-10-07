from decimal import Decimal
from job_intelligence import NormalizedJob, SourceRef, JobRequirement, build_publishable_draft


def rehab_job(**overrides):
    values = dict(
        source=SourceRef(system="excel", source_id="2026-135775"),
        status="open",
        title="Contract PT - Maternity Leave Coverage",
        division="rehabilitation",
        profession="Physical Therapist",
        specialty="Physical Therapy",
        care_setting="SNF",
        client_name="Internal Customer",
        facility_name="The Terraces at San Joaquin Gardens",
        city="Fresno",
        state="CA",
        required_license_states=["CA"],
        start_date="2026-11-29",
        end_date="2027-02-28",
        duration_weeks=13,
        bill_rate=Decimal("85"),
        travel_required=True,
        hard_requirements=[
            JobRequirement(kind="license", value="Active California PT license", required=True),
        ],
        description_text="Customer supplied PT maternity leave coverage in SNF.",
    )
    values.update(overrides)
    return NormalizedJob(**values)


def test_rehab_template_uses_medlivo_structure_and_hides_internal_bill_rate():
    draft = build_publishable_draft(rehab_job())
    assert draft.template_id == "rehabilitation-v1"
    assert draft.public_title.endswith("Fresno, CA")
    assert "bill_rate" not in draft.public_fields
    assert draft.internal_fields["bill_rate"] == Decimal("85")
    assert any(section.heading == "What You'll Do" for section in draft.sections)
    assert any(section.provenance == "source_confirmed" for section in draft.sections)
    assert any(section.provenance == "medlivo_standard" for section in draft.sections)


def test_incomplete_rehab_job_requires_manager_review():
    draft = build_publishable_draft(rehab_job(
        specialty=None,
        care_setting=None,
        description_text=None,
        hard_requirements=[],
        required_license_states=[],
    ))
    assert draft.readiness in {"not_ready", "manager_review"}
    assert draft.quality.publishing_readiness < 100
    assert any("job description" in warning.lower() for warning in draft.quality.warnings)
    requirements = next(section for section in draft.sections if section.key == "requirements")
    assert requirements.requires_confirmation is True
    assert requirements.provenance == "ai_suggested"


def test_nursing_allied_has_its_own_template():
    job = rehab_job(
        source=SourceRef(system="jobdiva", source_id="rn-100"),
        title="Travel ICU RN",
        division="nursing_allied",
        profession="Registered Nurse",
        specialty="ICU",
        care_setting="Acute Care",
        shift="Night",
        hard_requirements=[
            JobRequirement(kind="license", value="Active state RN license", required=True),
            JobRequirement(kind="certification", value="BLS", required=True),
            JobRequirement(kind="certification", value="ACLS", required=True),
        ],
    )
    draft = build_publishable_draft(job)
    assert draft.template_id == "nursing-allied-v1"
    assert draft.division == "nursing_allied"
    assert any(section.heading == "What You'll Do" for section in draft.sections)


def test_locums_has_coverage_and_credentialing_sections():
    job = rehab_job(
        source=SourceRef(system="excel", source_id="kaiser-anesthesia"),
        title="Pediatric Anesthesiologist Locums",
        division="locum_tenens",
        profession="Physician",
        specialty="Pediatric Anesthesiology",
        care_setting="Hospital",
        schedule="Weekday shifts plus night/weekend call",
        openings=2,
        hard_requirements=[
            JobRequirement(kind="license", value="California medical license", required=True),
            JobRequirement(kind="credential", value="Hospital privileges", required=True),
        ],
    )
    draft = build_publishable_draft(job)
    assert draft.template_id == "locum-tenens-v1"
    keys = [section.key for section in draft.sections]
    assert "coverage" in keys
    assert "credentialing" in keys
    credentialing = next(section for section in draft.sections if section.key == "credentialing")
    assert credentialing.requires_confirmation is True

from decimal import Decimal

from job_intelligence import NormalizedJob, SourceRef, analyze_job


def make_job(**overrides):
    values = dict(
        source=SourceRef(system="direct_customer", source_id="row-1"),
        status="open",
        title="Travel Physical Therapist",
        division="rehabilitation",
        profession="Physical Therapist",
        specialty="Physical Therapy",
        city="Seattle",
        state="WA",
        start_date="2026-11-01",
        description_text=None,
    )
    values.update(overrides)
    return NormalizedJob(**values)


def test_missing_bill_rate_stays_unknown_and_recruiting_can_be_ready():
    result = analyze_job(make_job())
    assert result.bill_rate_state == "unknown"
    assert result.recruiting_readiness == "ready"
    assert result.commercial_readiness == "review"


def test_source_bill_rate_is_confirmed():
    result = analyze_job(make_job(bill_rate=Decimal("92.00")))
    assert result.bill_rate_state == "confirmed"
    assert result.commercial_readiness == "ready"


def test_missing_required_job_data_routes_to_review():
    result = analyze_job(make_job(start_date=None))
    assert result.recruiting_readiness == "review"
    assert "start_date" in result.missing_fields


def test_title_profession_conflict_is_detected():
    result = analyze_job(make_job(profession="Registered Nurse"))
    assert result.recruiting_readiness == "review"
    assert any(x.code == "profession_title_conflict" for x in result.conflicts)


def test_standardized_internal_jd_is_created_without_inventing_bill_rate():
    result = analyze_job(make_job())
    jd = result.standardized_internal_jd
    assert jd["job_title"].startswith("Travel Physical Therapist")
    assert jd["source_description"] is None
    serialized = str(jd).lower()
    assert "what you'll do" not in serialized
    assert "patient-centered" not in serialized
    assert jd["commercial"]["bill_rate_state"] == "unknown"
    assert "bill_rate" not in jd["commercial"]
    assert "$" not in serialized


def test_provenance_marks_source_confirmed_fields():
    result = analyze_job(make_job())
    rows = {x.field: x for x in result.provenance}
    assert rows["title"].source_type == "source_confirmed"
    assert rows["title"].source_reference == "direct_customer:row-1"

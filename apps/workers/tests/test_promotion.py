from datetime import date

import pytest

from jobdiva_sync import promote_candidate_payload, promote_job_payload


def test_job_promotion_requires_source_id_and_title():
    with pytest.raises(ValueError, match="Source job ID"):
        promote_job_payload({"JOBTITLE": "Synthetic PT"})
    with pytest.raises(ValueError, match="Job title"):
        promote_job_payload({"JOBID": 101})


def test_job_promotion_maps_only_explicit_conservative_fields():
    result = promote_job_payload({
        "JOBID": 101,
        "JOBTITLE": "Synthetic Physical Therapist",
        "STATUS": "Open",
        "PROFESSION": "Physical Therapist",
        "SPECIALTY": "Physical Therapy",
        "CITY": "Fresno",
        "STATE": "ca",
        "STARTDATE": "11/29/2026",
        "UNREVIEWED_CUSTOM_FIELD": "preserved only in raw source",
    })

    assert result.source_id == "101"
    assert result.title == "Synthetic Physical Therapist"
    assert result.status == "open"
    assert result.profession == "Physical Therapist"
    assert result.specialty == "Physical Therapy"
    assert result.city == "Fresno"
    assert result.state == "CA"
    assert result.start_date == date(2026, 11, 29)
    assert result.normalized_payload["source_system"] == "jobdiva"
    assert "UNREVIEWED_CUSTOM_FIELD" in result.normalized_payload["source_fields_present"]
    assert "care_setting" not in result.normalized_payload


def test_unknown_job_status_stays_unknown():
    result = promote_job_payload({
        "JOBID": 102,
        "JOBTITLE": "Synthetic OT",
        "STATUS": "Custom Workflow State",
    })
    assert result.status == "unknown"


def test_candidate_promotion_requires_source_id():
    with pytest.raises(ValueError, match="Source candidate ID"):
        promote_candidate_payload({"FIRSTNAME": "Synthetic"})


def test_candidate_promotion_maps_explicit_identity_without_invention():
    result = promote_candidate_payload({
        "CANDIDATEID": 201,
        "FIRSTNAME": "Synthetic",
        "LASTNAME": "Clinician",
        "EMAIL": "synthetic@example.test",
        "MOBILEPHONE": "555-0100",
        "PROFESSION": "Registered Nurse",
        "SPECIALTY": "ICU",
        "CITY": "Seattle",
        "STATE": "wa",
    })

    assert result.source_id == "201"
    assert result.canonical_name == "Synthetic Clinician"
    assert result.primary_email == "synthetic@example.test"
    assert result.primary_phone == "555-0100"
    assert result.profession == "Registered Nurse"
    assert result.specialty == "ICU"
    assert result.city == "Seattle"
    assert result.state == "WA"
    assert result.canonical_profile["promotion_scope"] == "delta_explicit_fields_only"


def test_candidate_missing_fields_remain_none():
    result = promote_candidate_payload({"CANDIDATEID": 202})
    assert result.canonical_name is None
    assert result.primary_email is None
    assert result.primary_phone is None
    assert result.profession is None
    assert result.specialty is None
    assert result.city is None
    assert result.state is None


def test_invalid_state_is_not_promoted():
    job = promote_job_payload({"JOBID": 103, "JOBTITLE": "Synthetic Job", "STATE": "California"})
    candidate = promote_candidate_payload({"CANDIDATEID": 203, "STATE": "Washington"})
    assert job.state is None
    assert candidate.state is None


def test_open_jobs_selection_is_promoted_as_open_and_keeps_division():
    result = promote_job_payload({
        "JOBID": 104,
        "JOBTITLE": "Travel RN ICU",
        "PROFESSION": "Registered Nurse",
        "SPECIALTY": "ICU",
        "_medlivo_selection_source": "jobdiva_open_jobs",
    })
    assert result.status == "open"
    assert result.division == "nursing_allied"

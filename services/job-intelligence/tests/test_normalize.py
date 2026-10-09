from decimal import Decimal
import pytest

from job_intelligence import normalize_job


def test_jobdiva_style_payload_normalizes_without_losing_source_fields():
    payload = {
        "JOBID": 12345,
        "JOBTITLE": "Travel RN - ICU",
        "STATUS": "Open",
        "CITY": "Seattle",
        "STATE": "wa",
        "SHIFT": "Night",
        "BILLRATE": "$98.50",
        "OPENINGS": "2",
        "STARTDATE": "10/20/2026",
        "SPECIALTY": "ICU",
        "customField17": "Synthetic source-specific value",
    }
    job = normalize_job(payload)
    assert job.source.source_id == "12345"
    assert job.title == "Travel RN - ICU"
    assert job.status == "open"
    assert job.state == "WA"
    assert job.bill_rate == Decimal("98.50")
    assert job.openings == 2
    assert job.specialty == "ICU"
    assert job.source_fields["customField17"] == "Synthetic source-specific value"


def test_unknown_status_is_not_guessed():
    job = normalize_job({"JOBID": 1, "JOBTITLE": "Synthetic Role", "STATUS": "Pending Review"})
    assert job.status == "unknown"


@pytest.mark.parametrize("payload", [
    {"JOBTITLE": "Missing ID"},
    {"JOBID": 1},
])
def test_source_id_and_title_are_required(payload):
    with pytest.raises(ValueError):
        normalize_job(payload)


def test_bad_optional_values_do_not_corrupt_record():
    job = normalize_job({
        "JOBID": 1,
        "JOBTITLE": "Synthetic Role",
        "BILLRATE": "not-a-rate",
        "STARTDATE": "not-a-date",
        "STATE": "Washington",
    })
    assert job.bill_rate is None
    assert job.start_date is None
    assert job.state is None


@pytest.mark.parametrize(("payload","expected"), [
    ({"JOBID": 10, "JOBTITLE": "Travel RN - ICU", "PROFESSION": "Registered Nurse"}, "nursing_allied"),
    ({"JOBID": 11, "JOBTITLE": "Physical Therapist", "PROFESSION": "Physical Therapist"}, "rehabilitation"),
    ({"JOBID": 12, "JOBTITLE": "Locum Urologist", "PROFESSION": "Physician", "SPECIALTY": "Urology"}, "locum_tenens"),
])
def test_job_division_is_classified_from_explicit_healthcare_fields(payload, expected):
    assert normalize_job(payload).division == expected


def test_ambiguous_job_division_is_not_guessed():
    job = normalize_job({
        "JOBID": 13,
        "JOBTITLE": "Clinical Program Manager",
        "PROFESSION": "Healthcare",
    })
    assert job.division is None


def test_filled_and_closed_jobdiva_statuses_are_preserved_as_closed():
    assert normalize_job({"JOBID": 20, "JOBTITLE": "Synthetic RN", "STATUS": "Filled"}).status == "closed"
    assert normalize_job({"JOBID": 21, "JOBTITLE": "Synthetic PT", "STATUS": "Closed"}).status == "closed"


def test_cancelled_jobdiva_status_is_preserved():
    assert normalize_job({"JOBID": 22, "JOBTITLE": "Synthetic Locum", "STATUS": "Cancelled"}).status == "cancelled"

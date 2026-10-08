import pytest

from jobdiva_sync.job_enrichment import build_job_intelligence, explicit_requirements
from jobdiva_sync.job_enrichment_runner import enrich_pending_jobs


class FakeJobClient:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    async def job_detail(self, job_id):
        self.calls.append(str(job_id))
        return self.rows


def test_explicit_requirements_ignore_free_text_credentials():
    requirements = explicit_requirements({
        "DESCRIPTION": "BLS and ACLS preferred. California license may be needed.",
    })
    assert requirements == []


def test_explicit_requirements_create_only_source_backed_requirements():
    requirements = explicit_requirements({
        "REQUIREDLICENSESTATE": "CA",
        "REQUIREDCERTIFICATIONS": "BLS, ACLS",
        "CARESETTING": "SNF",
    })

    assert [(r.kind, r.value) for r in requirements] == [
        ("license", "CA"),
        ("certification", "BLS"),
        ("certification", "ACLS"),
        ("setting", "SNF"),
    ]
    assert all(r.required for r in requirements)


@pytest.mark.asyncio
async def test_build_job_intelligence_uses_matching_detail_record():
    client = FakeJobClient([
        {"JOBID": 999, "JOBTITLE": "Wrong Job"},
        {
            "JOBID": 101,
            "JOBTITLE": "Synthetic Physical Therapist",
            "STATUS": "Open",
            "PROFESSION": "Physical Therapist",
            "SPECIALTY": "Physical Therapy",
            "CITY": "Fresno",
            "STATE": "CA",
            "STARTDATE": "11/29/2026",
            "CARESETTING": "SNF",
            "REQUIREDLICENSESTATE": "CA",
        },
    ])

    job, stats = await build_job_intelligence(client, source_job_id="101")

    assert client.calls == ["101"]
    assert job.source.source_id == "101"
    assert job.title == "Synthetic Physical Therapist"
    assert job.profession == "Physical Therapist"
    assert job.state == "CA"
    assert job.required_license_states == ["CA"]
    assert [(r.kind, r.value) for r in job.hard_requirements] == [
        ("license", "CA"),
        ("setting", "SNF"),
    ]
    assert stats.detail_records == 2
    assert stats.requirements == 2


@pytest.mark.asyncio
async def test_job_detail_without_records_is_rejected():
    with pytest.raises(ValueError, match="no records"):
        await build_job_intelligence(FakeJobClient([]), source_job_id="101")


@pytest.mark.asyncio
async def test_ambiguous_job_detail_is_rejected():
    client = FakeJobClient([
        {"JOBID": 201, "JOBTITLE": "Synthetic One"},
        {"JOBID": 202, "JOBTITLE": "Synthetic Two"},
    ])
    with pytest.raises(ValueError, match="ambiguous"):
        await build_job_intelligence(client, source_job_id="101")


class FakeStore:
    def __init__(self):
        self.persisted = []
        self.errors = []
        self.pending = [{
            "source_record_id": "src-job-1",
            "job_id": "job-1",
            "source_job_id": "101",
            "source_updated_at": None,
            "source_record_updated_at": None,
        }]

    async def pending_sources(self, *, tenant_id, limit):
        assert tenant_id == "tenant-1"
        return self.pending[:limit]

    async def persist(self, **kwargs):
        self.persisted.append(kwargs)

    async def mark_error(self, **kwargs):
        self.errors.append(kwargs)


@pytest.mark.asyncio
async def test_job_enrichment_runner_persists_intelligence():
    store = FakeStore()
    client = FakeJobClient([{
        "JOBID": 101,
        "JOBTITLE": "Synthetic RN",
        "STATUS": "Open",
        "PROFESSION": "Registered Nurse",
        "SPECIALTY": "ICU",
        "STATE": "WA",
        "REQUIREDCERTIFICATIONS": "BLS, ACLS",
    }])

    result = await enrich_pending_jobs(client, store, tenant_id="tenant-1")

    assert result == {"pending": 1, "enriched": 1, "failed": 0}
    assert len(store.persisted) == 1
    intelligence = store.persisted[0]["intelligence"]
    assert intelligence.profession == "Registered Nurse"
    assert {r.value for r in intelligence.hard_requirements} == {"BLS", "ACLS"}
    assert store.errors == []


@pytest.mark.asyncio
async def test_job_enrichment_runner_records_error_without_throwing_batch():
    store = FakeStore()
    client = FakeJobClient([])

    result = await enrich_pending_jobs(client, store, tenant_id="tenant-1")

    assert result == {"pending": 1, "enriched": 0, "failed": 1}
    assert store.persisted == []
    assert store.errors[0]["error_code"] == "ValueError"

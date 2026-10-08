from datetime import datetime, timezone

import pytest

from jobdiva_sync.enrichment import build_candidate_intelligence, fetch_candidate_bundle
from jobdiva_sync.enrichment_runner import enrich_pending_candidates


class FakeDetailClient:
    def __init__(self):
        self.resume_text_calls = []

    async def candidate_profile(self, candidate_id):
        assert candidate_id == "1001"
        return [{
            "CANDIDATEID": 1001,
            "FIRSTNAME": "Synthetic",
            "LASTNAME": "Nurse",
            "EMAIL": "candidate@example.test",
            "PROFESSION": "Registered Nurse",
            "SPECIALTY": "ICU",
            "CITY": "Seattle",
            "STATE": "WA",
        }]

    async def candidate_licenses(self, candidate_id):
        return [{
            "LICENSEID": 11,
            "LICENSETYPE": "RN",
            "STATE": "WA",
            "LICENSENUMBER": "SYNTHETIC-1",
            "STATUS": "Active",
            "EXPIRATIONDATE": "12/31/2027",
        }]

    async def candidate_certifications(self, candidate_id):
        return [
            {"CERTIFICATIONID": 21, "CERTIFICATIONNAME": "BLS", "STATUS": "Active"},
            {"CERTIFICATIONID": 22, "CERTIFICATIONNAME": "ACLS", "STATUS": "Active"},
        ]

    async def candidate_resumes(self, candidate_id):
        return [
            {"RESUMEID": 31, "RESUMEDATE": "09/01/2026"},
            {"RESUMEID": 32, "RESUMEDATE": "10/01/2026"},
            {"RESUMEID": 33, "RESUMEDATE": "10/02/2026"},
        ]

    async def resume_text(self, resume_id):
        self.resume_text_calls.append(str(resume_id))
        return [{"RESUMETEXT": f"Synthetic resume text {resume_id}"}]


@pytest.mark.asyncio
async def test_fetch_candidate_bundle_bounds_resume_text_reads():
    client = FakeDetailClient()
    bundle, stats = await fetch_candidate_bundle(
        client,
        source_candidate_id="1001",
        source_updated_at=datetime(2026, 10, 8, tzinfo=timezone.utc),
        max_resumes=2,
    )
    assert bundle.candidate_id == "1001"
    assert len(bundle.profile_records) == 1
    assert len(bundle.license_records) == 1
    assert len(bundle.certification_records) == 2
    assert len(bundle.resume_records) == 3
    assert set(bundle.resume_text_records) == {"31", "32"}
    assert client.resume_text_calls == ["31", "32"]
    assert stats.resume_records == 3
    assert stats.resume_text_records == 2


@pytest.mark.asyncio
async def test_build_candidate_intelligence_reuses_shared_normalizer():
    intelligence, stats = await build_candidate_intelligence(
        FakeDetailClient(),
        source_candidate_id="1001",
        max_resumes=3,
    )
    assert intelligence.source_candidate_id == "1001"
    assert intelligence.full_name == "Synthetic Nurse"
    assert intelligence.profession == "Registered Nurse"
    assert intelligence.specialty == "ICU"
    assert intelligence.state == "WA"
    assert len(intelligence.licenses) == 1
    assert {item.name for item in intelligence.certifications} == {"BLS", "ACLS"}
    assert intelligence.primary_resume_id == "33"
    assert intelligence.matching_readiness.score == 100
    assert stats.profile_records == 1


class FakeStore:
    def __init__(self):
        self.persisted = []
        self.errors = []
        self.pending = [{
            "source_record_id": "src-1",
            "candidate_id": "can-1",
            "source_candidate_id": "1001",
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
async def test_enrichment_runner_persists_normalized_intelligence():
    store = FakeStore()
    result = await enrich_pending_candidates(
        FakeDetailClient(),
        store,
        tenant_id="tenant-1",
        limit=10,
        max_resumes=2,
    )
    assert result == {"pending": 1, "enriched": 1, "failed": 0}
    assert len(store.persisted) == 1
    intelligence = store.persisted[0]["intelligence"]
    assert intelligence.full_name == "Synthetic Nurse"
    assert intelligence.matching_readiness.resume_available is True
    assert store.errors == []


class FailingDetailClient(FakeDetailClient):
    async def candidate_profile(self, candidate_id):
        raise RuntimeError("synthetic connector failure")


@pytest.mark.asyncio
async def test_enrichment_runner_records_failure_and_continues():
    store = FakeStore()
    result = await enrich_pending_candidates(
        FailingDetailClient(),
        store,
        tenant_id="tenant-1",
    )
    assert result == {"pending": 1, "enriched": 0, "failed": 1}
    assert store.persisted == []
    assert store.errors[0]["error_code"] == "RuntimeError"


@pytest.mark.asyncio
async def test_resume_text_limit_is_validated_before_reads():
    client = FakeDetailClient()
    with pytest.raises(ValueError, match="max_resumes"):
        await fetch_candidate_bundle(
            client,
            source_candidate_id="1001",
            max_resumes=0,
        )
    assert client.resume_text_calls == []

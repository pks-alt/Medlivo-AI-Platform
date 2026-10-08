from datetime import date

import pytest

from jobdiva_sync.matching_adapter import candidate_match_input, job_match_input
from jobdiva_sync.matching_runner import activate_matching
from matching_engine import MatchResult, MatchGate, ScoreComponent


def test_job_match_input_uses_only_explicit_hard_gates():
    job = {
        "id": "job-1",
        "division": None,
        "profession": "Registered Nurse",
        "specialty": "ICU",
        "city": "Seattle",
        "state": "WA",
        "start_date": date(2026, 12, 1),
        "normalized_payload": {"care_setting": "Acute Care"},
    }
    requirements = [
        {"canonical_key": "license_state", "value": {"value": "WA"}, "is_hard_gate": True},
        {"canonical_key": "certification", "value": {"value": "BLS"}, "is_hard_gate": True},
        {"canonical_key": "setting", "value": {"value": "Acute Care"}, "is_hard_gate": False},
    ]
    result = job_match_input(job, requirements=requirements)

    assert result.division is None
    assert result.profession == "Registered Nurse"
    assert result.required_license_states == ["WA"]
    assert result.required_certifications == ["BLS"]
    assert result.care_setting == "Acute Care"


def test_candidate_match_input_uses_enriched_credentials_and_resume_readiness():
    candidate = {
        "id": "candidate-1",
        "profession": "Registered Nurse",
        "specialty": "ICU",
        "city": "Seattle",
        "state": "WA",
        "profile_freshness": 100,
        "resume_care_settings": ["acute_care", "icu"],
        "resume_specialties": ["icu"],
        "resume_clinical_skills": ["telemetry"],
    }
    result = candidate_match_input(
        candidate,
        licenses=[{"license_type": "RN", "state": "WA", "status": "Active", "expires_at": date(2027, 1, 1)}],
        certifications=[{"certification_name": "BLS", "status": "Active", "expires_at": None}],
        availability={"available_from": date(2026, 11, 1)},
        resume_available=True,
    )

    assert result.profession == "Registered Nurse"
    assert result.licenses[0].state == "WA"
    assert result.certifications[0].name == "BLS"
    assert result.resume_available is True
    assert result.profile_readiness == 100
    assert result.care_settings == ["acute_care", "icu"]
    assert result.resume_specialties == ["icu"]
    assert result.clinical_skills == ["telemetry"]


class FakeMatchingStore:
    def __init__(self, result_mode="eligible"):
        self.persisted = []
        self.result_mode = result_mode

    async def pending_pairs(self, *, tenant_id, limit):
        assert tenant_id == "tenant-1"
        return [{"job_id": "job-1", "candidate_id": "candidate-1"}]

    async def load_job(self, *, tenant_id, job_id):
        return ({
            "id": job_id,
            "division": "Nursing & Allied",
            "profession": "Registered Nurse",
            "specialty": "ICU",
            "city": "Seattle",
            "state": "WA",
            "start_date": date(2026, 12, 1),
            "normalized_payload": {"care_setting": "Acute Care"},
        }, [
            {"canonical_key": "license_state", "value": {"value": "WA"}, "is_hard_gate": True},
            {"canonical_key": "certification", "value": {"value": "BLS"}, "is_hard_gate": True},
        ])

    async def load_candidate(self, *, tenant_id, candidate_id):
        licenses = [{"license_type": "RN", "state": "WA", "status": "Active", "expires_at": None}]
        certs = [{"certification_name": "BLS", "status": "Active", "expires_at": None}]
        if self.result_mode == "excluded":
            certs = []
        return ({
            "id": candidate_id,
            "profession": "Registered Nurse",
            "specialty": "ICU",
            "city": "Seattle",
            "state": "WA",
            "profile_freshness": 100,
        }, licenses, certs, {"available_from": date(2026, 11, 1)}, True)

    async def persist_result(self, *, tenant_id, result):
        self.persisted.append(result)


@pytest.mark.asyncio
async def test_matching_activation_persists_eligible_match():
    store = FakeMatchingStore("eligible")
    result = await activate_matching(store, tenant_id="tenant-1", limit=10)

    assert result == {"pending": 1, "evaluated": 1, "eligible": 1, "excluded": 0, "failed": 0}
    assert len(store.persisted) == 1
    persisted = store.persisted[0]
    assert persisted.eligible is True
    assert persisted.score >= 9.0
    assert any(gate.key == "license_state" and gate.passed for gate in persisted.gates)


@pytest.mark.asyncio
async def test_matching_activation_persists_exclusion_when_hard_gate_fails():
    store = FakeMatchingStore("excluded")
    result = await activate_matching(store, tenant_id="tenant-1", limit=10)

    assert result == {"pending": 1, "evaluated": 1, "eligible": 0, "excluded": 1, "failed": 0}
    persisted = store.persisted[0]
    assert persisted.eligible is False
    assert persisted.score == 0
    assert any("BLS" in gap for gap in persisted.gaps)


class FailingStore(FakeMatchingStore):
    async def load_candidate(self, **kwargs):
        raise RuntimeError("synthetic candidate load failure")


@pytest.mark.asyncio
async def test_matching_activation_counts_pair_failure_without_stopping_batch():
    store = FailingStore()
    result = await activate_matching(store, tenant_id="tenant-1", limit=10)
    assert result == {"pending": 1, "evaluated": 0, "eligible": 0, "excluded": 0, "failed": 1}
    assert store.persisted == []


class RetrievalOrderingStore(FakeMatchingStore):
    async def pending_pairs(self, *, tenant_id, limit):
        return [
            {"job_id": "job-1", "candidate_id": "candidate-med-surg"},
            {"job_id": "job-1", "candidate_id": "candidate-icu"},
        ]

    async def load_candidate(self, *, tenant_id, candidate_id):
        specialty = "ICU" if candidate_id == "candidate-icu" else "Medical Surgical"
        return ({
            "id": candidate_id,
            "profession": "Registered Nurse",
            "specialty": specialty,
            "city": "Seattle",
            "state": "WA",
            "profile_freshness": 100,
        }, [
            {"license_type": "RN", "state": "WA", "status": "Active", "expires_at": None},
        ], [
            {"certification_name": "BLS", "status": "Active", "expires_at": None},
        ], {"available_from": date(2026, 11, 1)}, True)


@pytest.mark.asyncio
async def test_matching_activation_uses_retrieval_to_prioritize_eligible_candidates():
    store = RetrievalOrderingStore()
    result = await activate_matching(store, tenant_id="tenant-1", limit=10)

    assert result == {"pending": 2, "evaluated": 2, "eligible": 2, "excluded": 0, "failed": 0}
    assert [item.candidate_id for item in store.persisted] == [
        "candidate-icu",
        "candidate-med-surg",
    ]


class MixedGateStore(RetrievalOrderingStore):
    async def load_candidate(self, *, tenant_id, candidate_id):
        payload = await super().load_candidate(tenant_id=tenant_id, candidate_id=candidate_id)
        if candidate_id == "candidate-med-surg":
            candidate, licenses, certs, availability, resume = payload
            return candidate, licenses, [], availability, resume
        return payload


@pytest.mark.asyncio
async def test_retrieval_integration_still_persists_hard_gate_exclusions():
    store = MixedGateStore()
    result = await activate_matching(store, tenant_id="tenant-1", limit=10)

    assert result == {"pending": 2, "evaluated": 2, "eligible": 1, "excluded": 1, "failed": 0}
    excluded = next(item for item in store.persisted if item.candidate_id == "candidate-med-surg")
    assert excluded.eligible is False
    assert any("BLS" in gap for gap in excluded.gaps)


def test_explicit_care_settings_argument_overrides_resume_evidence():
    candidate = {
        "id": "candidate-override",
        "profession": "Physical Therapist",
        "profile_freshness": 80,
        "resume_care_settings": ["skilled_nursing"],
    }
    result = candidate_match_input(
        candidate,
        licenses=[],
        certifications=[],
        availability=None,
        resume_available=True,
        care_settings=["outpatient"],
    )
    assert result.care_settings == ["outpatient"]


def test_candidate_match_input_passes_documented_experience_years():
    candidate = {
        "id": "candidate-exp",
        "profession": "Physical Therapist",
        "profile_freshness": 80,
        "documented_experience_years": 5,
    }
    result = candidate_match_input(
        candidate,
        licenses=[],
        certifications=[],
        availability=None,
        resume_available=True,
    )
    assert result.documented_experience_years == 5

from datetime import date

from matching_engine import (
    CandidateLicense,
    CandidateMatchInput,
    JobMatchInput,
    cosine_similarity,
    lexical_similarity,
    retrieve_candidates,
)


def job():
    return JobMatchInput(
        job_id="job-1",
        division="rehabilitation",
        profession="Physical Therapist",
        specialty="Physical Therapy",
        care_setting="SNF",
        state="CA",
        start_date=date(2026, 11, 15),
        required_license_states=["CA"],
    )


def candidate(candidate_id: str, *, state: str = "CA", specialty: str = "Physical Therapy"):
    return CandidateMatchInput(
        candidate_id=candidate_id,
        profession="Physical Therapist",
        specialty=specialty,
        care_settings=["Skilled Nursing Facility"],
        state=state,
        licenses=[CandidateLicense(license_type="PT", state=state, status="Active")],
        resume_available=True,
        profile_readiness=90,
    )


def test_lexical_similarity_rewards_shared_clinical_terms():
    strong = lexical_similarity("physical therapist skilled nursing", "physical therapist skilled nursing facility")
    weak = lexical_similarity("physical therapist skilled nursing", "registered nurse intensive care")
    assert strong > weak


def test_cosine_similarity_handles_missing_or_zero_vectors():
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0
    assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) is None
    assert cosine_similarity(None, [1.0]) is None


def test_hard_gate_failure_never_reaches_semantic_shortlist():
    good = candidate("good")
    wrong_license = candidate("wrong-license", state="WA")

    hits = retrieve_candidates(
        job(),
        [wrong_license, good],
        job_embedding=[1.0, 0.0],
        candidate_embeddings={
            "wrong-license": [1.0, 0.0],
            "good": [0.5, 0.5],
        },
    )

    assert [hit.candidate_id for hit in hits] == ["good"]


def test_hybrid_retrieval_uses_vector_and_lexical_evidence():
    first = candidate("first")
    second = candidate("second")

    hits = retrieve_candidates(
        job(),
        [second, first],
        job_text="geriatric rehabilitation contract",
        candidate_texts={
            "first": "geriatric rehabilitation skilled nursing contract",
            "second": "outpatient orthopedics",
        },
        job_embedding=[1.0, 0.0],
        candidate_embeddings={
            "first": [0.95, 0.05],
            "second": [0.0, 1.0],
        },
    )

    assert hits[0].candidate_id == "first"
    assert hits[0].vector_score is not None
    assert "hybrid retrieval" in hits[0].reason


def test_lexical_only_fallback_is_deterministic():
    hits = retrieve_candidates(
        job(),
        [candidate("b"), candidate("a")],
        candidate_texts={"a": "physical therapy SNF", "b": "physical therapy"},
    )
    assert hits[0].retrieval_score >= hits[1].retrieval_score

from candidate_intelligence import JobDivaCandidateBundle, normalize_candidate


def test_normalizes_jobdiva_candidate_without_inventing_missing_facts():
    profile = {
        "candidateId": 101,
        "firstName": "Synthetic",
        "lastName": "Therapist",
        "email": "synthetic@example.test",
        "profession": "Physical Therapist",
        "specialty": "Physical Therapy",
        "city": "Seattle",
        "state": "wa",
    }
    bundle = JobDivaCandidateBundle(
        candidate_id="101",
        profile_records=[profile],
        license_records=[{
            "licenseId": "L1",
            "licenseType": "Physical Therapist",
            "state": "WA",
            "licenseNumber": "SYNTHETIC",
            "status": "Active",
            "expirationDate": "12/31/2027",
        }],
        certification_records=[],
        resume_records=[{
            "resumeId": "R1",
            "resumeDate": "10/01/2026",
        }],
        resume_text_records={
            "R1": [{"resumeText": "Synthetic resume text for testing only."}]
        },
    )
    result = normalize_candidate(bundle)

    assert result.source_system == "jobdiva"
    assert result.source_candidate_id == "101"
    assert result.full_name == "Synthetic Therapist"
    assert result.state == "WA"
    assert result.licenses[0].state == "WA"
    assert result.primary_resume_id == "R1"
    assert result.matching_readiness.score == 100
    assert result.matching_readiness.resume_available is True
    assert result.source_profile == profile


def test_missing_jobdiva_data_stays_missing_and_lowers_readiness():
    result = normalize_candidate(JobDivaCandidateBundle(
        candidate_id="102",
        profile_records=[{"candidateId": 102, "firstName": "Synthetic"}],
    ))

    assert result.email is None
    assert result.phone is None
    assert result.profession is None
    assert result.specialty is None
    assert result.licenses == []
    assert result.certifications == []
    assert result.resumes == []
    assert result.matching_readiness.score == 20
    assert set(result.matching_readiness.missing_fields) == {"contact", "profession", "resume"}


def test_latest_resume_is_selected_as_primary():
    result = normalize_candidate(JobDivaCandidateBundle(
        candidate_id="103",
        profile_records=[{
            "fullName": "Synthetic RN",
            "email": "rn@example.test",
            "profession": "Registered Nurse",
        }],
        resume_records=[
            {"resumeId": "OLD", "resumeDate": "01/01/2025"},
            {"resumeId": "NEW", "resumeDate": "09/30/2026"},
        ],
        resume_text_records={
            "OLD": [{"text": "old resume"}],
            "NEW": [{"text": "new resume"}],
        },
    ))
    assert result.primary_resume_id == "NEW"
    assert result.resumes[0].text == "new resume"

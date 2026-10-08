from candidate_intelligence import JobDivaCandidateBundle, extract_resume_experience, normalize_candidate


def test_extracts_only_explicit_resume_experience_and_care_settings():
    text = """
    Physical Therapist
    Axiom Rehab | 2022 - Present | Skilled Nursing Facility
    Prior role | 2019 - 2021 | Outpatient clinic
    """
    result = extract_resume_experience(text)

    assert len(result.experience_entries) == 2
    assert result.experience_entries[0].start_year == 2022
    assert result.experience_entries[0].end_year is None
    assert result.experience_entries[0].is_current is True
    assert [signal.key for signal in result.care_settings] == ["skilled_nursing", "outpatient"]


def test_does_not_invent_experience_from_undated_generic_text():
    result = extract_resume_experience("Experienced clinician with strong communication skills.")
    assert result.experience_entries == ()
    assert result.care_settings == ()


def test_normalized_resume_keeps_source_lines_for_auditability():
    candidate = normalize_candidate(JobDivaCandidateBundle(
        candidate_id="200",
        profile_records=[{
            "fullName": "Synthetic Therapist",
            "email": "synthetic@example.test",
            "profession": "Physical Therapist",
        }],
        resume_records=[{"resumeId": "R1", "resumeDate": "10/01/2026"}],
        resume_text_records={
            "R1": [{
                "resumeText": "Axiom Rehab | 2022 - Present | Skilled Nursing Facility\n"
                              "Clinic Role | 2020 - 2022 | Outpatient"
            }]
        },
    ))

    resume = candidate.resumes[0]
    assert resume.experience_entries[0].source_line.startswith("Axiom Rehab")
    assert resume.care_settings[0].key == "skilled_nursing"
    assert "Skilled Nursing Facility" in resume.care_settings[0].source_line


def test_extracts_explicit_specialty_and_clinical_skill_signals():
    result = extract_resume_experience(
        "ICU Registered Nurse with telemetry, ventilator management, and central line care."
    )
    assert [signal.key for signal in result.specialties] == ["icu"]
    assert [signal.key for signal in result.clinical_skills] == ["ventilator", "telemetry", "central_line"]


def test_operating_room_detector_does_not_match_plain_word_or():
    result = extract_resume_experience("Worked in inpatient rehab or outpatient therapy.")
    assert all(signal.key != "operating_room" for signal in result.care_settings)

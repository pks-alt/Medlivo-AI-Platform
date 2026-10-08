from app.repositories.recruiting import MATCH_STRONG_THRESHOLD, _match_signals, _why_matched


def test_match_scale_uses_zero_to_ten_threshold():
    assert MATCH_STRONG_THRESHOLD == 8.0


def test_match_signals_include_hard_gates_and_score_components():
    signals = _match_signals(
        {
            "gates": [
                {"key": "profession", "passed": True, "reason": "Profession matches Registered Nurse"},
                {"key": "license_state", "passed": False, "reason": "No active required-state license found"},
            ]
        },
        [
            {"key": "specialty", "score": 10, "evidence": {"reason": "Specialty aligns"}},
            {"key": "availability", "score": 5, "evidence": {"reason": "Availability has not been confirmed"}},
        ],
    )
    assert [(s.key, s.status) for s in signals] == [
        ("profession", "passed"),
        ("license_state", "failed"),
        ("specialty", "strong"),
        ("availability", "review"),
    ]


def test_why_matched_uses_strengths_and_exclusion_reasons():
    assert _why_matched(
        {"strengths": ["Exact profession match", "Specialty aligns", "Required-state active license passed hard gate"]},
        "shortlisted",
    ) == "Exact profession match; Specialty aligns; Required-state active license passed hard gate"

    assert _why_matched(
        {"gaps": ["Missing required certification: ACLS"]},
        "excluded",
    ) == "Excluded: Missing required certification: ACLS"

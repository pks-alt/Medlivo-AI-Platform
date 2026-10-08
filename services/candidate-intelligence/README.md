# Candidate Intelligence

Canonical clinician identity, resume versions, normalization, freshness, evidence, license/readiness, and identity resolution.


## Resume experience extraction

Resume text remains sourced from JobDiva. Candidate Intelligence now extracts only explicit, auditable evidence:
- dated experience lines
- current vs completed date ranges
- recognized healthcare care settings such as SNF, acute care, inpatient rehab, outpatient, home health, LTC, ICU, emergency, and operating room

Every extracted signal retains the original source line. Missing or ambiguous facts remain unknown rather than being inferred.

- explicit specialty signals such as ICU, emergency medicine, urology, cardiology, orthopedics, behavioral health, and core therapy disciplines
- explicit clinical skills such as ventilator management, telemetry, wound care, gait training, manual therapy, central-line care, and dialysis

These signals are vocabulary matches only. They are evidence for matching and recruiter review, not automatic proof of competency.


## Matching handoff

Primary-resume parsed evidence is persisted with the resume version. Matching currently consumes source-backed care-setting signals as soft evidence for retrieval and scoring. Resume specialty and clinical-skill signals remain available for future calibrated scoring and are not promoted into hard gates automatically.

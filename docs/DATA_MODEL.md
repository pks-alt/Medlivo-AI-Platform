# Canonical Data Model

Core entities:
- Tenant
- User
- RecruiterProfile
- Team
- Customer
- Job
- JobSourceRecord
- Candidate
- CandidateSourceRecord
- ResumeVersion
- License
- Certification
- Evidence
- Match
- Conversation
- Qualification
- Submission
- Assignment
- AuditEvent

## Candidate source trust
1. externally verified
2. clinician-confirmed
3. ATS structured
4. resume text
5. AI inferred

## Identity resolution
High-confidence duplicates may auto-resolve into one canonical clinician while preserving every source record. Lower-confidence cases require review.

## Match persistence
Persist only operationally meaningful matches. Do not create billions of candidate-job relationship records.

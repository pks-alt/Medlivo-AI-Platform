# Developer Start Here

## Purpose

This guide is the entry point for engineers joining the Medlivo AI Platform.

The immediate goal is to understand what is being built, what already exists, how the major services fit together, and which architecture rules must remain intact.

For initial familiarization, do **not** redesign or rebuild existing modules.

---

## 1. What Medlivo AI is

Medlivo AI sits above JobDiva.

### JobDiva owns

- candidate records
- resumes
- jobs
- submissions
- interviews
- placements
- ATS workflow history
- source ownership where represented

### Medlivo AI owns

- Job Intelligence
- Candidate Intelligence
- evidence/provenance
- deterministic hard gates
- explainable matching
- semantic/hybrid retrieval
- recruiter prioritization
- Candidate → Best Jobs
- Job → Best Candidates
- recruiter notes/follow-ups/activity
- manager visibility
- match-quality feedback
- Candidate Validation & Readiness

**Do not build a second ATS inside Medlivo AI.**

---

## 2. One platform, three rule sets

The platform supports:

- Nursing & Allied
- Rehabilitation
- Locum Tenens

These are not three separate systems.

All three divisions share:

- authentication and RBAC
- canonical job/candidate models
- JobDiva integration
- resume intelligence
- matching engine
- recruiter workspace
- manager/admin foundation
- provenance
- auditability

Division-specific rules are layered on top.

### Nursing & Allied

Key concepts:

- profession
- specialty
- care setting
- required state license
- required certifications
- experience
- clinical skills
- shift
- travel/location
- availability

No per-diem workflow is part of the current agreed model.

### Rehabilitation

Key concepts:

- PT / PTA / OT / COTA / SLP
- state license
- care setting
- therapy experience
- therapy skills
- travel willingness
- contract duration

Rehab is travel/contract staffing, typically 13 weeks or longer. No per-diem workflow.

### Locum Tenens

Key concepts:

- provider specialty
- state license
- DEA
- board status
- exact availability
- call coverage
- clinic/surgical coverage
- privileging
- credentialing lead time
- procedure/case evidence

---

## 3. The shared Phase 1 lifecycle

1. Job enters from JobDiva or an approved intake source.
2. Job Intelligence normalizes the source data.
3. Candidate Intelligence normalizes candidate facts and resume evidence.
4. Hard gates determine baseline eligibility.
5. Eligible candidates receive an explainable deterministic score.
6. Retrieval orders relevant candidates/jobs.
7. Recruiter reviews evidence, gaps, ownership, and next action.
8. Candidate Validation & Readiness confirms missing/conflicting job-specific information.
9. Recruiter receives the candidate with context and a clear next action.
10. Managers see workload, goals, follow-ups, and match-quality feedback.

---

## 4. What is already built

### Data foundation

- jobs delta landing
- candidates delta landing
- resumable historical backfill foundation
- source-record promotion
- candidate canonical identity
- job canonical identity
- candidate profile reads
- license reads
- certification reads
- resume metadata reads
- resume text reads
- job detail reads

### Candidate intelligence

- dated experience extraction
- current/completed experience
- documented experience years
- care-setting evidence
- specialty evidence
- clinical-skill evidence
- source-line provenance

### Matching

- profession hard gate
- required state license hard gate
- required certification hard gate
- explainable deterministic 0–10 score
- specialty alignment
- care-setting alignment
- clinical-skill alignment
- documented-experience alignment
- location/availability/profile-readiness signals
- hybrid semantic retrieval
- persisted matches
- Job → Best Candidates
- Candidate → Best Jobs
- strengths / gaps / hard-gate explanations

### Recruiter productivity

- private recruiter workspace
- My Work
- Daily Priorities
- Recruiter Dashboard
- recruiter-wide Follow-ups queue
- Match Queue
- Strong / Good / Needs Review filters
- Hide My Reviewed
- Candidate Best Jobs
- match-quality feedback
- structured negative reasons
- recommended next action
- notes
- activity history
- ownership protection

### Manager/admin

- team workload
- weekly goals
- goal-vs-actual review
- weekly CSV export
- same-team reassignment with reason/audit
- direct-customer XLSX intake
- customer mappings
- job approval
- match-quality summary
- user/team/admin foundations

---

## 5. Current JobDiva state

The dedicated JobDiva integration user is enabled for the Phase 1 read functions.

Current implemented read paths include:

- authentication
- OpenJobsList
- NewUpdatedJobRecords
- NewUpdatedCandidateRecords
- JobsDetail
- CandidatesProfileDetail
- CandidatesLicensesDetail
- CandidatesCertificationsDetails
- CandidatesResumesDetail
- ResumesTextDetail

The connector is intentionally GET-only.

Current development is validating the full read contract safely before the first persistence-enabled real-data pilot.

---

## 6. What is intentionally not enabled

Do not enable or implement these casually:

- candidate/job write-back to JobDiva
- submission creation
- ATS ownership/status changes
- autonomous outreach
- email/SMS sending
- voice outreach
- AI interviewing
- AI hiring decisions
- AI reranking
- recruiter ranking from clinician feedback

These require later approvals, policy controls, or real-data evidence.

---

## 7. Read these documents in order

### Product understanding

1. `docs/PHASE_1_PRODUCT_SPEC.md`
2. `FEATURES.md`
3. `ROADMAP.md`

### Architecture

4. `ARCHITECTURE.md`
5. `CODEBASE.md`
6. `docs/SYSTEM_ARCHITECTURE.md`
7. `docs/TECH_STACK_DECISION.md`

### JobDiva / data

8. `docs/JOBDIVA_INTEGRATION.md`
9. `services/jobdiva-connector/README.md`
10. `docs/DATA_MODEL.md`
11. `docs/DATA_MODEL_DECISIONS.md`

### Intelligence and matching

12. `services/candidate-intelligence/README.md`
13. `services/job-intelligence/README.md`
14. `docs/MATCHING_ENGINE.md`
15. `services/matching-engine/README.md`

### Security / operations

16. `docs/SECURITY_AND_ACCESS.md`
17. `docs/TEAM_SIGNIN_STAGING.md`
18. `STAGING_REAL_DATA_PILOT.md`
19. `docs/PHASE3_ROLLBACK_RUNBOOK.md`

---

## 8. Browser preview

For product familiarization, open:

https://pks-alt.github.io/Medlivo-AI-Platform/workspace-preview/

The preview is:

- synthetic
- JobDiva-independent
- not production authentication
- not connected to Cloud Run
- not connected to email/SMS
- not connected to real candidates

Use it to understand navigation and recruiter workflow concepts, not as the source of truth for implementation status.

---

## 9. Architecture rules to preserve

1. JobDiva remains the ATS/system of record.
2. `main` is the canonical branch.
3. One shared platform serves all three divisions.
4. Division-specific behavior is layered through rules/configuration.
5. Hard gates remain deterministic.
6. Deterministic scoring remains authoritative until real recruiter feedback supports a change.
7. Unknown, No, and Missing Evidence are different states.
8. Important facts retain provenance.
9. Recruiter feedback is measurement-only for now.
10. Candidate Validation is screening/validation, not interviewing.
11. No write-back without explicit JobDiva authorization.
12. No outreach without consent, approval, and duplicate-contact safeguards.

---

## 10. What developers should do first

Before modifying code:

1. Read the product storyboard/spec.
2. Open the browser preview.
3. Review `FEATURES.md`.
4. Review `CODEBASE.md`.
5. Identify the service relevant to your assigned area.
6. Read that service's tests before changing behavior.
7. Confirm the intended Phase 1 behavior before introducing new state, APIs, or data models.

Questions or perceived gaps should be reviewed before architecture is changed.

---

## 11. Current next technical milestone

The next milestone is not a new dashboard or a new AI feature.

It is:

**Validate the complete JobDiva Phase 1 read contract → run a bounded real-data pilot → inspect real Nursing & Allied / Rehab / Locums data → measure match quality with recruiters → tune only where evidence shows a problem.**

That keeps implementation aligned with the product and prevents premature redesign.

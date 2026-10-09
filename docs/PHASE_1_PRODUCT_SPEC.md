# Phase 1 Product Specification

## Outcome

Give Medlivo recruiters and managers one intelligent workspace that increases the number of high-quality candidates a recruiter can work while reducing manual search, duplicate review, and uncertainty.

Phase 1 should help a recruiter answer:

- What jobs need my attention?
- Which candidates should I work first?
- Why did the system recommend or exclude this candidate?
- What information is missing or conflicting?
- Has the candidate been validated for this job?
- Who owns the candidate/work item?
- What should I do next?

Managers should be able to understand team workload, overdue work, weekly goals, and match-quality feedback without building separate spreadsheets.

## Core product model

Phase 1 is **one shared Medlivo AI platform** supporting:

- Nursing & Allied
- Rehabilitation
- Locum Tenens

These are division-specific rule sets on top of shared identity, data, intelligence, matching, workflow, audit, and manager/admin foundations.

JobDiva remains the ATS and operational system of record.

Medlivo AI is the:

- Job Intelligence layer
- Candidate Intelligence layer
- matching/ranking layer
- recruiter productivity layer
- Candidate Validation & Readiness layer
- manager visibility layer

Phase 1 must not create a second ATS.

## Phase 1 release scope

### Access and administration

- Google identity foundation
- explicitly provisioned users
- recruiter / manager / admin RBAC
- tenant/team isolation
- users and teams
- direct-customer XLSX job intake
- customer-specific mappings
- job approval foundation
- auditability

### JobDiva read integration

- authentication
- jobs delta read
- candidates delta read
- job detail
- candidate profile
- candidate licenses
- candidate certifications
- candidate resumes
- resume text
- historical/backfill foundation
- source ID preservation
- canonical promotion
- sync health

Phase 1 remains GET-only against JobDiva until separately authorized write APIs are accepted.

### Candidate Intelligence

- canonical candidate identity
- resume evidence
- dated experience
- documented experience years
- care settings
- specialties
- clinical skills
- licenses
- certifications
- source provenance
- freshness/readiness signals

### Job Intelligence

- division
- profession
- specialty
- location
- start date
- shift/schedule
- required license
- required certifications
- experience requirements
- care setting
- clinical skills
- source provenance
- job readiness

### Matching

- profession hard gate
- required state license hard gate
- required certification hard gate
- explainable deterministic 0–10 score
- specialty alignment
- care-setting alignment
- clinical-skill alignment
- documented-experience alignment
- location / availability / readiness signals
- hybrid semantic retrieval
- persisted matches
- Job → Best Candidates
- Candidate → Best Jobs
- strengths, gaps, and exclusion reasons

### Recruiter productivity

- My Work
- Daily Priorities
- Jobs
- Candidates
- Match Queue
- Strong / Good / Needs Review triage
- Hide My Reviewed
- Candidate Best Jobs
- recruiter-wide Follow-ups queue
- notes
- activity history
- ownership protection
- recommended next action
- recruiter dashboard
- recruiter match-quality feedback

### Manager productivity

- Team Overview
- recruiter workload
- open and overdue follow-ups
- weekly recruiter goals
- goal vs actual
- weekly review
- CSV export
- same-team workflow reassignment with reason/audit
- match-quality summary
- negative-reason analysis

### Candidate Validation & Readiness foundation

Phase 1 establishes the shared validation state and question-selection model.

The platform should be able to distinguish:

- Not Screened
- Screening Started
- Information Missing
- Candidate Confirmed
- Recruiter Review Needed
- Ready for Recruiter

The AI-assisted validation behavior should:

- not ask again when data is authoritative
- briefly confirm information when confirmation is needed
- ask when required information is missing
- avoid irrelevant division/job questions
- surface conflicts rather than silently overwrite evidence

This is screening/validation, **not AI interviewing**.

## Division rule sets

### Nursing & Allied

Focus on:

- profession
- specialty
- care setting
- required license
- certifications
- experience
- clinical skills
- shift
- location/travel
- availability

No per-diem workflow is part of the current agreed model.

### Rehabilitation

Focus on:

- PT / PTA / OT / COTA / SLP
- state license
- care setting
- therapy experience
- therapy clinical skills
- travel willingness
- contract length
- availability

Rehab is travel/contract staffing, typically 13 weeks or longer. No per-diem workflow.

### Locum Tenens

Focus on:

- provider specialty
- state license
- DEA
- board status
- exact availability
- clinic/surgical coverage
- call coverage
- credentialing
- privileging
- procedure/case evidence

## Evidence and trust

Important facts should retain provenance such as:

- Source Confirmed
- Resume Evidence
- Candidate Confirmed
- Medlivo Standard
- AI Suggested

Unknown is not the same as No.

Conflicting evidence must be surfaced for recruiter review rather than silently overwritten.

## Pilot

Use a mixed recruiter group across:

- Nursing & Allied
- Rehabilitation
- Locum Tenens

Measure:

- time to first strong match
- recruiter agreement by score band
- top Weak / Not-a-Match reasons
- false hard-gate exclusions
- recruiter time saved
- candidate review throughput
- submissions
- interviews
- placements

Real-data pilot evidence should determine whether matching vocabularies/rules need tuning.

AI reranking remains deferred until recruiter feedback demonstrates a specific ranking problem.

## Deliberately deferred beyond Phase 1

- recruiter-approved email/SMS engagement
- two-way conversation state
- consent/preferences and opt-out
- duplicate-outreach prevention
- voice outreach
- scheduling automation
- submission readiness
- compliance package generation
- autonomous submissions
- authorized JobDiva write-back
- candidate portal
- broader Ask Medlivo platform integration
- clinician recruiter feedback ranking
- production-grade geo/proximity intelligence
- marketplace UX

## Phase 1 success definition

Phase 1 is successful when recruiters can start their day in Medlivo AI, understand what deserves attention, trust why a candidate was recommended/excluded, validate the right missing information, and take the next action without creating a parallel ATS.

Managers should be able to review team progress, workload, follow-ups, goals, and match quality without manual spreadsheets.

The platform should be validated with representative real JobDiva data across all three divisions before production acceptance.

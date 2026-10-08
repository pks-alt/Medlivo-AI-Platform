# Medlivo AI Platform — Development Roadmap

## Phase 0 — Consolidation
Goal: one understandable, testable codebase.

Exit criteria:
- one canonical repository
- `main` is source of truth
- no stacked long-lived feature branches
- FEATURES.md current
- ARCHITECTURE.md current
- CODEBASE.md current
- Phase 1 acceptance checklist defined
- CI green
- legacy PRs closed or merged
- unique security/connector safeguards preserved

## Phase 1 — Data Foundation
Goal: reliable real JobDiva data.

Scope:
- JobDiva jobs sync
- candidate sync
- resume metadata/text sync
- licenses/certifications
- candidate merges
- checkpointed historical backfill
- delta sync
- webhook reconciliation
- healthcare taxonomy
- normalized job/candidate profiles

Exit criteria:
- approved real test dataset syncs reproducibly
- source IDs are stable
- re-runs are idempotent
- no duplicate canonical identities from the same source
- sync failures are observable and retryable

## Phase 2 — Matching
Goal: reliable two-way matching.

Scope:
- job → best candidates
- candidate → best jobs
- hard gates
- deterministic score
- semantic/vector retrieval
- AI reranking
- explanations
- recruiter feedback on match quality

Exit criteria:
- representative cases across Rehab, Nursing & Allied, Locums
- hard-gate false positives are controlled
- top-match quality measured against recruiter review
- reasons are understandable and evidence-backed

## Phase 3 — Recruiter Productivity
Goal: make the platform useful every day.

Scope:
- Match Queue
- candidate best-jobs view
- daily priorities
- recruiter dashboard
- tasks/follow-ups
- ownership protection
- weekly goals
- manager review
- team workload

Exit criteria:
- recruiters can start their day in Medlivo AI
- managers can review team progress without manual spreadsheets
- no ATS duplication

Acceptance checklist: `PHASE3_ACCEPTANCE.md`

## Phase 4 — Engagement
Goal: recruiter-approved scalable candidate engagement.

Scope:
- email
- SMS
- voice
- scheduling
- AI qualification
- recruiter handoff

Exit criteria:
- consent/preferences enforced
- duplicate outreach prevented
- recruiter can approve/control outreach
- activity is reflected back to JobDiva where authorized

## Phase 5 — Submission Intelligence
Goal: accelerate high-quality submittals.

Scope:
- submission readiness
- credential gaps
- client-specific requirements
- submission package
- approved JobDiva write-back

Exit criteria:
- recruiter can see exactly what blocks submission
- submission package is evidence-backed
- write-back tested against authorized JobDiva endpoints

## Phase 6 — External Experience
Goal: connect the platform safely to customers and clinicians.

Scope:
- public jobs
- Apply
- candidate portal
- Ask Medlivo
- clinician recruiter feedback
- client staffing request intelligence

Exit criteria:
- no duplicated business logic outside platform APIs
- website Apply lands in JobDiva
- public data is manager-approved and public-safe

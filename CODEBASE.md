# Medlivo AI Platform — Canonical Codebase

## Single source of truth

**Repository:** `pks-alt/Medlivo-AI-Platform`

**Default / production branch:** `main`

**Current consolidation branch:** `feat/phase1-job-intake-weekly-review-20261007`

**Current consolidation PR:** #4

Until PR #4 is merged, all new AI Platform work must be made only on the consolidation branch above. Do not start new product features from older feature branches.

After PR #4 is merged, `main` becomes the only canonical starting point for all work.

## Architecture boundary

### JobDiva
JobDiva remains the ATS and operational system of record for:
- candidate records
- resumes
- jobs/requisitions
- recruiter ownership where represented in JobDiva
- submissions, interviews, placements and ATS workflow status
- operational ATS history

### Medlivo AI Platform
Medlivo AI Platform is the intelligence and workflow-assist layer for:
- Job Intelligence
- Candidate Intelligence
- resume parsing / normalization
- license and certification intelligence
- hard-gate matching
- explainable candidate ranking
- recruiter Match Queue
- recruiter/manager productivity views
- weekly goals and performance review
- direct-customer job intake / normalization
- manager approval of Medlivo-enhanced job content
- public approved Career Jobs API
- future recruiter-approved outreach / qualification

The platform must not become a second ATS.

## Active Phase 1 components

| Path | Status | Purpose |
| --- | --- | --- |
| `apps/recruiter-web` | ACTIVE | Recruiter and manager web application |
| `apps/api` | ACTIVE | Public/platform API surface |
| `services/team-workspace` | ACTIVE | Authenticated recruiter/manager workspace, RBAC, goals, intake, approvals |
| `services/jobdiva-connector` | ACTIVE, READ-ONLY | JobDiva ingestion and authoritative source reads |
| `services/job-intelligence` | ACTIVE | Canonical job normalization, templates, quality/readiness |
| `services/candidate-intelligence` | ACTIVE | Canonical candidate facts and evidence |
| `services/matching-engine` | ACTIVE | Hard gates and explainable deterministic scoring |
| `apps/workers` | ACTIVE SCAFFOLD | Background sync/processing workers |
| `services/outreach` | FUTURE / DISABLED | Outreach only after consent, policy and write-path approval |
| `packages/*` | SHARED | Auth, taxonomy, data models and UI building blocks |
| `infrastructure/*` | ACTIVE | Deployment/staging infrastructure |

## Explicitly not part of the architecture

Do not introduce:
- a second candidate ATS record maintained independently of JobDiva
- a second permanent resume repository as the operational source of truth
- a parallel application/submission workflow that replaces JobDiva
- automatic candidate outreach without recruiter-approved policy
- candidate or job write-back to JobDiva until exact write APIs are confirmed and tested

Temporary secure file staging is allowed only when technically required for transfer into JobDiva and must have explicit retention/deletion controls.

## Branch / PR consolidation

### PR #4
**CANONICAL CONSOLIDATION PR.**

It contains the private team workspace plus current Phase 1 intelligence and recruiter workflow work. It should target `main`.

### PR #3
**MERGED INTO `main`.** The private team workspace foundation is now part of the canonical base.

### PR #1
**CLOSED / SUPERSEDED.** Its Cloud Run service-to-service authentication safeguards have been reconciled into PR #4.

### PR #2
**CLOSED / SUPERSEDED.** Its relevant read-only JobDiva safety controls have been reconciled into the active connector in PR #4.

## Required before merging PR #4 to main

1. Run all current CI suites.
2. Confirm no parallel ATS application/resume persistence remains.
3. Confirm JobDiva write paths remain disabled.
4. Confirm recruiter/manager RBAC and tenant isolation.
5. Confirm public Career API exposes approved public fields only.
6. Update this document if any component changes status.

## Development rule after consolidation

Every new feature must follow:

`main` → one short-lived feature branch → one PR → tests → merge to `main` → delete/retire feature branch.

Do not stack long-lived feature branches on top of other feature branches.

## Product roadmap status

### Built / active foundation
- private recruiter/manager workspace
- Google sign-in/session/RBAC foundation
- JobDiva read connector
- Job Intelligence
- Candidate Intelligence
- hard-gate matching
- explainable score
- Match Queue
- direct-customer Excel job intake
- weekly recruiter goals/review
- manager job-content approval
- approved public Career Jobs API

### Next, only after consolidation
- candidate-to-best-jobs view
- full JobDiva sync/backfill pipeline
- semantic/vector retrieval
- AI reranking
- recruiter-approved outreach
- qualification workflow
- JobDiva write-back, only after vendor API authorization and acceptance testing

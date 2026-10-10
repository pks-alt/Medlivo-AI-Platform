# Medlivo AI Platform — Canonical Codebase

## Single source of truth

**Repository:** `pks-alt/Medlivo-AI-Platform`

**Default / production branch:** `main`

**Current development baseline:** latest green `main`

All new AI Platform work must start from the latest green `main`.

Historical feature branches and pull requests are reference material only. Do not start new product development from them.

For current implementation status and the next slice, read:

- `docs/ENGINEERING_OPERATING_MODEL.md`
- `docs/CURRENT_PLATFORM_STATE.md`
- `docs/PHASE1_COMPLETION_MATRIX.md`
- `docs/NEXT_DEVELOPMENT_SLICE.md`
- `RELEASE_STATE.json`

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

## Historical consolidation note

Earlier consolidation PRs are historical context only. They are not development baselines.

Current work follows the permanent rule:

`latest green main → short-lived feature branch → coherent PR → tests → staging/browser validation as applicable → merge to main → update platform control files`

## Permanent development rule

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

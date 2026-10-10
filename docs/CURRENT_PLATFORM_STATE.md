# Current Platform State

**Updated:** 2026-10-10  
**Canonical repository:** `pks-alt/Medlivo-AI-Platform`  
**Canonical branch:** `main`  
**Baseline SHA when this document was created:** `2fbfe8a5bdfd5674a94b7b2627073ea177daa80b`

Read this document before starting new product development.

## Governing model

The permanent development strategy is defined in:

- `docs/ENGINEERING_OPERATING_MODEL.md`

If a requested change conflicts with that document, stop and resolve the conflict explicitly rather than drifting the architecture.

## Product boundary

### JobDiva remains system of record for

- candidate identity
- resumes
- ATS jobs/requisitions
- ATS submissions
- interviews
- placements
- ATS status/history
- ATS ownership where represented

Phase 1 JobDiva access remains read-only unless separately authorized and tested.

### Medlivo owns

- canonical normalization and intelligence
- evidence/provenance
- hard gates and explainable matching
- operational priority overlays
- direct intake before ATS creation
- recruiter/manager workflow overlays
- pay package and projected margin economics
- submission templates and package preparation
- AI submission drafting policy/provenance
- start readiness and start-risk overlays
- analytics and audit
- public-safe approved job content

## Current roles

### Executive / Top Management

- company-wide strategic visibility
- major exceptions
- negative-GM exception authority
- company-wide funnel and margin visibility

### Delivery Manager

- operational control of managed teams
- assignment, priority, intake, workload, start risk
- operational/commercial guidance when needed
- does not own ordinary recruiter rate finalization

### Recruiter

- executes assigned recruiting work
- owns final rate decisions within company guidelines
- search/match/contact/stage/follow-up/submission preparation
- interview/offer/start workflow execution
- package review and finalization

### System Admin

Capability rather than hierarchy:

- users/access
- teams
- integrations
- master configuration
- submission templates
- economic assumptions/rules
- audit/reference data

## Division/channel rules

### Rehabilitation

Supports both:

- Direct Customer
- MSP/VMS

Template precedence may layer:

`Medlivo default → Rehab default/channel → customer/program → profession/specialty → job override`

### Nursing & Allied

**MSP/VMS only.**

No direct-customer/per-diem operating model is part of the current agreed platform.

### Locum Tenens

**MSP/VMS only.**

Submission is treated as a document-heavy credential presentation. Credential copy and primary-source verification are distinct evidence types.

## Major completed capabilities

### Foundation and integration

- canonical job/candidate models
- JobDiva read connector
- delta/backfill foundations
- provenance/evidence
- tenant/RBAC foundations
- private recruiter/manager workspace

### Intelligence and matching

- Job Intelligence
- Candidate Intelligence
- deterministic hard gates
- explainable deterministic score
- persisted Job → Best Candidates
- Candidate → Best Jobs
- match-quality feedback

### Operational workflow

- Daily Priorities
- Match Queue
- recruiter follow-ups
- notes/activity
- manager workload
- assignment and priority overlays
- direct XLSX intake
- weekly goals/review

### Pay Package & Gross Margin

Completed and merged.

Current profiles:

- `nursing_allied_ca_w2`
- `nursing_allied_national_w2`
- `rehabilitation_ca_w2`
- `rehabilitation_national_w2`
- `locums_ca_w2`
- `locums_national_1099`

Recruiter owns normal rate finalization within guidelines. Negative GM requires Executive exception.

### Submission Studio

Completed foundation includes:

- versioned templates
- Rehab direct + MSP/VMS model
- Nursing & Allied MSP/VMS-only model
- Locums MSP/VMS-only model
- candidate document assets
- verification freshness/jurisdiction metadata
- deterministic package readiness
- required-item gating
- recruiter review/finalization
- package version history
- nontechnical template manager

### AI Submission Composer

Merged capability includes:

- source-grounded Vertex AI/Gemini adapter
- candidate-presentation drafting
- Medlivo-formatted resume drafting
- recruiter review required
- minimized/redacted model context
- no unsupported-fact invention
- secure GCS-only supporting-document resolution
- combined PDF + separate-file ZIP package generation
- recruiter-only finalized download
- manifest/version metadata

Environment features remain fail-closed unless explicitly configured.

### Submission → Start

Merged capability includes:

- read-only JobDiva-backed submission/interview/offer/placement projections
- Medlivo start-readiness overlay
- risk, owner, next action, due date
- readiness items
- required-item gate before Ready
- role-scoped Funnel Board
- Start Readiness detail UI
- manager funnel visibility
- at-risk-start prioritization

## Deployment state

Private staging services:

- API service: `medlivo-team-api-staging`
- Web service: `medlivo-team-web-staging`
- Region: `us-west1`
- Project: `medlivo-ai-platform`

At baseline creation:

- API revision: `medlivo-team-api-staging-00013-ss8`
- Web revision: `medlivo-team-web-staging-00015-pgc`
- Web origin: `https://medlivo-team-web-staging-brgq5tymca-uw.a.run.app`
- API origin: `https://medlivo-team-api-staging-brgq5tymca-uw.a.run.app`
- `TEAM_WORKSPACE_ENABLED=true`

The staging web deployment now uses the full `apps/recruiter-web` application image.

## Current known issue / in-progress item

PR #80 is in progress to add a full-app authentication gate so unauthenticated protected routes redirect to `/team` instead of rendering raw `/me HTTP 401` errors.

The first PR #80 browser run showed that the OAuth flow itself completed successfully; its failing assertion was a timing check after callback and was updated to wait for the authorized workspace.

Until PR #80 is green, merged, and redeployed, staging login/browser review is not considered fully stabilized.

## Do not do next

Do not start another major feature while staging authentication/browser acceptance is unresolved.

Do not infer current architecture by reading historical feature branches first.

Do not treat the old static preview or old isolated staging container as the implementation source of truth.

## Immediate next move

See:

- `docs/NEXT_DEVELOPMENT_SLICE.md`

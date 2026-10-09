# Medlivo AI Platform

Medlivo AI is the intelligence and recruiter-productivity layer for Medlivo healthcare staffing.

> **JobDiva remains the ATS and operational system of record.**
> Medlivo AI adds normalized job/candidate intelligence, evidence-backed matching, recruiter workflow, candidate validation/readiness, and manager visibility.

## Start here

New developers should read:

1. [Developer Start Here](docs/DEVELOPER_START_HERE.md)
2. [Phase 1 Product Specification](docs/PHASE_1_PRODUCT_SPEC.md)
3. [Architecture](ARCHITECTURE.md)
4. [Codebase Guide](CODEBASE.md)
5. [JobDiva Integration](docs/JOBDIVA_INTEGRATION.md)
6. [Matching Engine](docs/MATCHING_ENGINE.md)
7. [Feature Status](FEATURES.md)
8. [Roadmap](ROADMAP.md)
9. [Security and Access](docs/SECURITY_AND_ACCESS.md)

## Product model

Medlivo AI is **one shared platform** with three healthcare-specific rule sets:

- Nursing & Allied
- Rehabilitation
- Locum Tenens

The divisions share the same identity, data, canonical models, matching engine, recruiter workspace, audit layer, and manager/admin foundation.

## Phase 1 focus

Phase 1 centers on:

- JobDiva read integration
- canonical job and candidate intelligence
- resume evidence extraction
- profession/license/certification hard gates
- explainable deterministic 0–10 matching
- semantic/hybrid retrieval
- Job → Best Candidates
- Candidate → Best Jobs
- recruiter Daily Priorities
- Match Queue
- Follow-ups
- recruiter dashboard
- manager workload / weekly review / match-quality visibility
- Candidate Validation & Readiness foundation
- full auditability and source provenance

## Important boundaries

Phase 1 does **not** authorize:

- autonomous submissions
- automatic JobDiva write-back
- automatic recruiter ownership changes
- uncontrolled candidate outreach
- AI interviewing or hiring decisions
- AI reranking before real recruiter feedback
- separate core applications for each division

## Current development status

The recruiter-productivity foundation is implemented in the repository. Current work is focused on **real JobDiva read-contract validation and real-data acceptance**.

The active JobDiva integration remains GET-only. Write paths stay disabled until JobDiva explicitly authorizes exact endpoints and Medlivo completes separate acceptance testing.

## Browser preview

A public, synthetic recruiter-workspace preview is available for product familiarization:

[Open the browser preview](https://pks-alt.github.io/Medlivo-AI-Platform/workspace-preview/)

The preview is sample-only and is not connected to JobDiva, Cloud Run, email, SMS, or production candidate data.

## Source of truth

- `main` is the canonical branch.
- Start new development from `main`.
- Use short-lived feature branches and PRs.
- Do not rebuild an existing module before reviewing `FEATURES.md`, `CODEBASE.md`, and the relevant service README.

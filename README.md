# Medlivo AI Platform

Standalone AI recruiting platform for Medlivo.

> **Canonical codebase:** see [CODEBASE.md](CODEBASE.md). Until the current consolidation PR is merged, all new platform work belongs on the documented consolidation branch. After merge, all work starts from `main`.

## Phase 1
Build the internal recruiter and manager platform for `recruit.medlivo.com`.

Core goals:
- ingest JobDiva jobs and approximately 1M historical resumes
- create canonical candidate and job intelligence profiles
- selective hybrid matching with configurable hard gates
- explainable candidate ranking with evidence
- recruiter-approved SMS and email outreach
- AI qualification and submission-readiness
- recruiter command center and basic manager dashboard
- full auditability and JobDiva write-back where supported

## Product surfaces
- `www.medlivo.com` — public site
- `recruit.medlivo.com` — recruiter/manager platform
- `talent.medlivo.com` — clinician portal after recruiter workflow stabilizes

## Browser prototype
The repository root contains a static recruiter UX prototype intended for GitHub Pages review.

## Architecture principle
**Agents decide. Services compute. Databases retrieve. Humans approve consequential actions.**

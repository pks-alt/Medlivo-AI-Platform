# Current Platform State

**Evidence review:** 2026-10-12  
**Canonical repository:** `pks-alt/Medlivo-AI-Platform`  
**Canonical branch:** `main`  
**Source baseline inspected:** `4b77fbf016166764c44516cc16be3a62a43ba4dc`

## Governing model

`docs/ENGINEERING_OPERATING_MODEL.md` and accepted architecture decisions remain authoritative. Keep this repository; repair current-workflow blockers, not a broad rewrite or folder reorganization. Architecture, ownership, security, providers and launch-scope changes require PK approval and impact review. No production go-live before Phase 2 and acceptance approval.

## Verified release blocker

The inspected private staging release run `38205046744`, job `114666565678`, failed at **Verify staging migration identity**. Migration and API/web rollout steps were skipped. This is not a successful staging release and not an authenticated browser acceptance result.

The previous shell check hid its error and called every failed lookup a missing resource. Google documents that service-account describe can return PERMISSION_DENIED for an absent account OR insufficient permission. Neither that log message nor prior chat establishes that a resource must be recreated.

The proposed targeted fix reports safe error classes, checks both resources, and can list metadata names in the same staging project. It does not read secret values or inspect the database. The manual diagnostics-only mode cannot build, migrate, deploy or promote traffic. A successful metadata preflight does not establish migration privileges or a ready schema.

Configured references are still the existing release references; no alternative is adopted automatically:
- `medlivo-team-schema-staging@medlivo-ai-platform.iam.gserviceaccount.com`
- `medlivo-team-staging-migration-database-url`

Current serving revisions, applied migration level, actual DB grants and cloud inventory remain **not verified**. The October 10 recorded API/web revisions were historical observations, not current proof. The old PR #80 next-step entry is superseded by this evidence-driven release investigation; it is not a claim that live authentication was retested.

## GitHub controls observed

The branch response reports `protected=false`; the repository ruleset listing is empty. The detailed branch-protection endpoint returned HTTP 403, `Resource not accessible by integration`. No protection setting was changed. Repository-administrator action is required; code changes or this document do not enforce settings. Review the eligible independent reviewer and applicable required checks before activation. Do not create a self-approval deadlock or make path-filtered checks unconditionally required without a tested gate.

## Product and authority boundaries retained

### JobDiva remains system of record

ATS jobs, candidate identities, resumes, submissions, interviews, placements and source ownership/history remain JobDiva-owned. Phase 1 JobDiva access remains read-only unless separately authorized and tested. Medlivo owns canonical intelligence, evidence, direct intake before authorized ATS creation, operational overlays, pay packages, projected economics, submission preparation, readiness and public-safe approved content.

### Roles and divisions

Executive visibility and negative-GM exceptions remain distinct from System Admin configuration authority. Delivery Managers control assigned-team work and intake. Recruiters finalize ordinary pay within guidelines and review submission packages. Division/team/tenant boundaries apply on the server.

- Rehabilitation: recorded Direct Customer plus MSP/VMS channels; travel contracts of 13 weeks or longer, no per-diem. Conflicting source assignments require review, not rewritten dates.
- Nursing & Allied: recorded MSP/VMS only; no per-diem. Do not infer direct-customer authority from a dropdown.
- Locum Tenens: recorded MSP/VMS only; preserve applicable call, per-diem and credentialing/privileging distinctions.

## Existing capabilities retained, not newly certified

The source baseline contains job/candidate intelligence and matching foundations; recruiter priorities, follow-ups and manager goals; pay-package/GM profiles; Submission Studio, grounded drafting and package generation; Submission → Start projections and readiness overlays. These are reuse candidates, not proof of live data completeness or accepted deployment.

Module 01 known gaps remain tracked: intake-only standards resolution and exact role matching; six-month import ending before detail enrichment; matching selection requiring JobDiva enrichment for both records. Fix these after the release is proved; do not create another engine or a fabricated JobDiva identity for direct jobs.

Google/Zoom clarification and account tests remain communication dependencies. No live messaging, bulk import, automatic publication or JobDiva writeback is authorized by this release-diagnostic change. Master and Module 01 artifacts remain review drafts until explicitly approved.

## Next step and evidence

See `docs/NEXT_DEVELOPMENT_SLICE.md`. The next deliverable is verified release evidence, not a new product module.

References:
- Inspected run: https://github.com/pks-alt/Medlivo-AI-Platform/actions/runs/38205046744
- Branch metadata: https://api.github.com/repos/pks-alt/Medlivo-AI-Platform/branches/main
- Rulesets: https://api.github.com/repos/pks-alt/Medlivo-AI-Platform/rulesets?includes_parents=true
- Lookup semantics: https://docs.cloud.google.com/sdk/gcloud/reference/iam/service-accounts/describe

# ADR 001: JobDiva Remains the ATS System of Record

**Status:** Accepted  
**Date:** 2026-10-10

## Decision

JobDiva remains the operational ATS/system of record for candidate identity, resumes, ATS jobs/requisitions, submissions, interviews, placements, ATS status/history, and ATS ownership where represented.

Medlivo AI remains the intelligence and workflow-assist layer.

## Medlivo-owned domains

Medlivo may own:

- canonical normalization/intelligence
- evidence/provenance
- hard-gate and match intelligence
- operational overlays
- direct intake before ATS creation
- recruiter/manager workflow overlays
- pay package and projected margin
- submission templates/package preparation
- start readiness and risk
- analytics/audit
- approved public job projection

## Consequence

Do not build a second ATS by silently creating competing operational ownership for JobDiva-owned records.

Any future change to this boundary requires a superseding ADR, migration plan, and explicit approval.

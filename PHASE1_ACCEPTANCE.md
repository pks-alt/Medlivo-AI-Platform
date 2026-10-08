# Phase 1 Acceptance Checklist

A feature may be marked **PRODUCTION READY** only after every applicable section passes.

## Architecture
- [ ] JobDiva remains the ATS/system of record.
- [ ] No duplicate operational candidate/resume/submission store was introduced.
- [ ] Data ownership is documented.
- [ ] Consequential actions require the intended human approval.

## Security
- [ ] Authentication and authorization tested.
- [ ] Recruiter/manager/admin access scoped correctly.
- [ ] Cross-team and cross-tenant access denied.
- [ ] Secrets are not committed or logged.
- [ ] Public APIs expose only approved public fields.

## JobDiva integration
- [ ] Exact vendor endpoint/method/parameter contract verified.
- [ ] Connector remains read-only unless write authorization is explicitly approved.
- [ ] Rate limits and retries are bounded.
- [ ] Source IDs and merged-candidate behavior handled.
- [ ] Sync/backfill is checkpointed and idempotent.
- [ ] Candidate payloads are not exposed in logs.

## Job Intelligence
- [ ] Rehab representative jobs pass.
- [ ] Nursing & Allied representative jobs pass.
- [ ] Locum Tenens representative jobs pass.
- [ ] Source-confirmed / Medlivo-standard / AI-suggested provenance preserved.
- [ ] Internal fields never leak into public payload.

## Candidate Intelligence
- [ ] Candidate ID maps back to JobDiva.
- [ ] Resume source/version is traceable.
- [ ] License/certification evidence is traceable.
- [ ] Unknown data remains unknown.
- [ ] Matching-readiness gaps are visible.

## Matching
- [ ] Profession hard gate tested.
- [ ] Required-state license hard gate tested.
- [ ] Required certifications hard gates tested.
- [ ] Strong matches have evidence-backed explanations.
- [ ] Failed hard gates cannot receive a misleading high score.
- [ ] Representative recruiter review completed.

## Recruiter / Manager UI
- [ ] Recruiter sees only permitted work.
- [ ] Manager sees only managed teams.
- [ ] Mobile and desktop flows tested.
- [ ] Read-only screens do not perform hidden ATS mutations.
- [ ] Errors are understandable and recoverable.

## Operations
- [ ] CI is green.
- [ ] Staging deployment tested.
- [ ] Real-data acceptance test completed with approved records.
- [ ] Monitoring/logging exists for critical failures.
- [ ] Rollback path documented.
- [ ] Owner for production support identified.

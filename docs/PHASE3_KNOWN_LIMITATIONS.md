# Phase 3 Known Limitations

This document records the known limits of the Medlivo AI Recruiter Productivity implementation before production acceptance.

## Environment and acceptance

- Private staging deployment has not yet completed real Google Workspace OAuth and two-browser recruiter/manager acceptance.
- The deployed read-only staging probe is implemented, but it still requires configured staging service URLs, IAM, and operator execution.
- Phase 3 rollback/recovery is documented but must still be exercised in staging with synthetic data.
- Phase 3 alert policies are implemented as opt-in Terraform but have not yet been applied to staging notification channels.

## JobDiva

- JobDiva API permissions and exact live endpoint behavior still require vendor confirmation.
- Candidate/resume/job write-back remains disabled.
- No submission, interview, placement, ownership, or status write-back is authorized from Phase 3.
- The staging JobDiva pilot is manual, bounded, read-only, and unscheduled.
- Real-data acceptance across Rehabilitation, Nursing & Allied, and Locum Tenens has not yet been completed.

## Matching

- Hard gates and deterministic 0–10 scoring are authoritative.
- Resume evidence extraction uses evidence-backed deterministic vocabularies that still require tuning against real Medlivo data.
- Hybrid semantic retrieval is integrated, but production embedding/vector-store infrastructure has not yet been accepted with real data.
- AI reranking remains disabled until recruiter feedback demonstrates a specific problem the deterministic ranking cannot solve.
- Recruiter match feedback is measurement-only; it does not retrain or override scores.

## Recruiter workflow

- Phase 3 does not send email, SMS, or voice outreach.
- Phase 3 does not automatically schedule candidates.
- Phase 3 does not submit candidates to clients or JobDiva.
- Follow-ups are internal shared workflow tasks only; they do not send reminders to candidates.
- Recommended next actions are guidance only and do not trigger downstream actions.
- Nursing & Allied and Rehabilitation workflows do not include per-diem staffing.

## Monitoring and operations

- Workspace readiness, JobDiva sync health, and sanitized failure signals are implemented.
- Alert policies are definitions only until an operator supplies approved staging notification channels and applies the Terraform plan.
- Production operational ownership, escalation routing, and on-call response are not yet accepted.
- Production scheduling for background sync remains pending real-data acceptance.

## External and later-phase capabilities

The following are intentionally outside Phase 3 and remain later-phase work:

- recruiter-approved email/SMS outreach
- voice outreach
- AI qualification
- scheduling automation
- submission readiness and submission packages
- approved JobDiva write-back
- candidate portal
- Ask Medlivo external integration
- clinician recruiter feedback
- production-grade geo/proximity intelligence and broader SeekOut-style data intelligence

These items should not be treated as missing Phase 3 defects unless the roadmap is explicitly changed.

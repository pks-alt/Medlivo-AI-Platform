# Phase 3 Acceptance — Recruiter Productivity

Goal: confirm that Medlivo AI is useful for daily recruiter work without duplicating JobDiva or enabling unapproved engagement/write-back.

## Acceptance status

Code-complete does not equal production-ready. Phase 3 remains in acceptance until the private staging deployment, real JobDiva-backed data, recruiter pilot feedback, monitoring, and rollback expectations are verified.

## Recruiter workflow

- [ ] Recruiter can sign in through approved Google Workspace authentication in private staging.
- [ ] Recruiter sees only authorized tenant/team/work ownership.
- [ ] My Work loads assigned work items without cross-recruiter leakage.
- [ ] Daily Priorities surfaces overdue follow-ups before due-soon follow-ups, then unreviewed strong/good matches.
- [ ] Recruiter Dashboard shows weekly goal vs actual plus current workload.
- [ ] Follow-ups queue shows all assigned open/completed tasks with overdue items surfaced first.
- [ ] Follow-up completion/reopen remains version-checked, idempotent, and audited.
- [ ] Match Queue shows only authorized owned/managed jobs.
- [ ] Match Queue supports Strong / Good / Needs Review triage without changing persisted score.
- [ ] “Hide my reviewed matches” uses recruiter-specific feedback state only.
- [ ] Candidate detail shows ranked current Best Jobs from persisted matches.
- [ ] Candidate Best Jobs supports direct canonical-job review and match-quality feedback.
- [ ] Recommended next action is visible where expected.
- [ ] No recruiter workflow silently changes JobDiva ownership, status, candidate data, or submissions.

## Matching behavior

- [ ] Hard gates remain deterministic and authoritative.
- [ ] Explainable 0–10 score remains authoritative.
- [ ] Resume-backed care setting, specialty, clinical skill, and documented experience evidence render correctly on representative cases.
- [ ] Hybrid retrieval influences review ordering only and does not override hard gates or deterministic score.
- [ ] Recruiter Strong / Good / Weak / Not-a-match feedback is measurement-only.
- [ ] Weak / Not-a-match requires a structured reason.
- [ ] AI reranking remains disabled until the real-data pilot demonstrates a specific need.

## Manager workflow

- [ ] Team Overview shows only managed-team workload.
- [ ] Manager can see active recruiters, work items, open follow-ups, and overdue follow-ups.
- [ ] Weekly Review compares recruiter targets with synchronized actuals.
- [ ] Weekly CSV export matches the displayed review.
- [ ] Match-quality pilot summary reports agreement by score band/division and top negative reasons.
- [ ] Reassignment is same-team only, version-checked, reason-required, and audited.
- [ ] Reassignment changes Medlivo workflow ownership only; it does not rewrite JobDiva ownership.

## JobDiva boundary

- [ ] JobDiva remains ATS/system of record for jobs, candidates, resumes, submissions, interviews, placements, and workflow history.
- [ ] Recruiter Productivity surfaces use synchronized canonical data rather than creating a second ATS.
- [ ] JobDiva candidate/resume/job write-back remains disabled.
- [ ] No outreach or submission action is available from Phase 3 surfaces.
- [ ] Live JobDiva API permissions/endpoints are vendor-confirmed before any write path is enabled.

## Staging and real-data pilot

- [ ] Private staging deployment is reachable only through approved authentication and Cloud Run IAM.
- [ ] Representative Rehab cases validated.
- [ ] Representative Nursing & Allied cases validated.
- [ ] Representative Locum Tenens cases validated.
- [ ] Recruiters review a representative sample of real matches and record feedback.
- [ ] Top-match agreement is measured by score band and division.
- [ ] False hard-gate exclusions are reviewed and controlled.
- [ ] Resume evidence is traceable to source text for sampled candidates.
- [ ] Job requirements are traceable to explicit source fields for sampled jobs.
- [ ] Candidate ownership and job ownership behavior matches operating expectations.

## Operations

- [ ] Required CI workflows are green on canonical `main`.
- [ ] No staging test uses production credentials or production mutation.
- [ ] Authentication, authorization denial, and workspace-service failures are observable. Workspace event-only logs and `/ready` database reachability are implemented; staging log-based metrics/alerts still require configuration.
- [ ] JobDiva sync health and failed runs are observable.
- [ ] Pilot rollback procedure is documented and tested. See `docs/PHASE3_ROLLBACK_RUNBOOK.md`.
- [ ] Staging configuration/secrets are reviewed and reproducible.
- [ ] Known limitations are documented for recruiters and managers.

## Phase 3 exit criteria

Phase 3 can be called accepted when:

1. Recruiters can start their day in Medlivo AI using Daily Priorities, Dashboard, Follow-ups, Match Queue, and Candidate Best Jobs.
2. Managers can review team workload, weekly goals/actuals, ownership, and match-quality pilot results without manual spreadsheets.
3. Real-data behavior is validated across Rehabilitation, Nursing & Allied, and Locum Tenens.
4. JobDiva remains the ATS and no duplicate ATS workflow has been introduced.
5. All required CI, staging security, monitoring, and rollback checks are green.

Until those conditions are met, individual Phase 3 features may be marked BUILT or IN DEVELOPMENT, but Phase 3 as a whole is not PRODUCTION READY.

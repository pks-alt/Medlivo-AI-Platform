# Next Development Slice

**Current next slice:** Stabilize staging authentication and complete real browser acceptance.

## Why this is next

The current product has enough Phase 1 capability that adding another major feature before validating the deployed browser experience would create unnecessary risk and architectural drift.

The immediate goal is to prove that the current full application works as one coherent system.

## Scope

1. Finish PR #80 authentication gate.
2. Confirm protected routes redirect unauthenticated users to `/team`.
3. Confirm Google sign-in callback returns to an authenticated full application session.
4. Verify staging uses the full `apps/recruiter-web` image.
5. Verify the exact staging web origin and API origin.
6. Run recruiter browser walkthrough.
7. Run Delivery Manager browser walkthrough.
8. Verify Executive/Admin entry points.
9. Verify no unexpected JobDiva writeback or outreach path is enabled.
10. Capture usability issues from the browser review.
11. Fix only the issues required for a coherent nontechnical user experience.
12. Update `CURRENT_PLATFORM_STATE.md`, `PHASE1_COMPLETION_MATRIX.md`, and `RELEASE_STATE.json` when the slice is complete.

## Browser walkthrough

### Recruiter

`Sign In → Today → Jobs → Candidate Match → Pay Package → Submission Studio → AI Draft/Review → Finalize/Download → Submission to Start → Start Readiness`

### Delivery Manager

`Sign In → Manager → Team Workload → Submission to Start → At-Risk Starts → Start Readiness`

### Executive / System Admin

Verify:

- company-wide margin view
- negative-GM exception visibility
- company-wide funnel visibility
- GM configuration
- Submission Studio template administration
- access/admin boundaries

## Exit criteria

This slice is complete only when:

- CI is green
- current `main` is deployed to private staging
- authentication works in the real browser
- recruiter and manager walkthroughs complete without critical workflow breaks
- known issues are documented
- platform-state and release-state files are current

## What follows

Only after this slice is complete should the next major functional capability begin.

The next capability should be selected from the current product roadmap based on highest operational value and user feedback, while following `docs/ENGINEERING_OPERATING_MODEL.md`.

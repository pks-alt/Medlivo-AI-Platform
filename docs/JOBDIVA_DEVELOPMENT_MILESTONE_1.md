# JobDiva development milestone 1: read-only connector

## Delivery boundary

The connector scaffold is now a testable client library with reviewed-contract gates,
server-side authentication/token handling, small explicit-ID reads, rate/retry controls,
resume-version selection, and a count-only dry-run/live pilot command.
The public recruiter app and its mock data are untouched. The separate Cloud Run
authentication repair in PR #1 still needs its own merge and deployment verification.

## Next acceptance test

After the official request schemas have been reviewed and secrets are configured on a
private worker, retrieve 5–10 approved test jobs, 20–50 approved test candidate profiles,
and a few representative resume texts. Compare actual fields with JobDiva. Do not infer
credential verification or contact consent from a field's presence.

No full database sync, production data load, or automatic write-back is authorized by this
code delivery. Recruiter authentication/authorization and data-use review must precede
live candidate information appearing in screens or being sent to an AI provider.

## Evidence

Isolated connector tests run locally with synthetic records and a mock HTTP transport.
GitHub's new PR test workflow verifies Python 3.12/3.13 without JobDiva or GCP credentials.
See the PR for observed test counts and CI status. An added workflow is not evidence that
its remote run passed. No full API/frontend build or authenticated JobDiva request has
been verified as part of this milestone.

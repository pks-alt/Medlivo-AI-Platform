# Team workspace milestone: shared backend before JobDiva

Delivered as a separate, disabled-by-default backend with a narrow shared-workflow
scope. It is based on the current main branch and does not merge PR #1 or PR #2,
change Cloud Run, or replace the public GitHub Pages sample.

## Included
- Google identity-token verification and explicitly provisioned user bindings.
- Server-owned tenant/role/team authorization with immediate next-request denial
  for deactivated users. A demo persona cannot grant server permissions.
- Database-persisted notes and follow-up tasks for assigned job/candidate cases.
- Same-team manager reassignment with a reason, preserving shared history.
- Atomic activity records, idempotent writes and stale-update protection.
- PostgreSQL migration and least-privilege grant template; offline and CI tests.

## Not yet a live sign-in/shared workspace
The Google login page, BFF with private service identity, secure browser session,
shared-draft/approval persistence, user provisioning interface, integration with
the sample UI and live Cloud SQL deployment are separate acceptance steps.
The sample site's browser-local actions still stay browser-local.

## Validation at packaging
70 local tests passed and 4 PostgreSQL-only tests were skipped. The local test
runtime was Python 3.13.5, FastAPI 0.128.2, SQLAlchemy 2.0.50, PyJWT 2.13.0 and
SQLite with foreign keys enabled. RSA signatures were verified with generated test
keys. No real Google login, JWKS request, Cloud SQL, JobDiva or messaging call ran.
CI adds an ephemeral PostgreSQL service for migration, concurrent updates and audit
trigger verification. Remote CI status must be read separately, not inferred from
this file or from creating the workflow.

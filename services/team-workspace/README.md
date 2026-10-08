# Private team workspace: identity and shared-workflow foundation

This milestone adds a **separate, disabled-by-default backend service**. It does
not change the public GitHub Pages sample, the existing Cloud Run API/web app,
JobDiva, or the earlier pending PRs. It is not a completed production sign-in UI.

## Implemented

- Server-side verification of Google-issued RS256 ID tokens: trusted signing keys,
  issuer, exact OAuth audience, expiry, issue time, verified email and configured
  Workspace hosted domain. Google `sub`, not email or a submitted user ID, selects
  an explicitly provisioned identity binding.
- Roles, tenant, activation status and team scope read from Medlivo's database on
  every request. Token-supplied role/email/tenant values do not grant permissions.
- Recruiter: assigned workflow cases only. Manager: cases in teams they manage.
  Administrator: cases in their own tenant only. Operations role is deliberately
  denied until its workflow policy is separately specified. No self-registration.
- Shared append-only notes, open/done follow-up tasks, and same-team manager
  reassignment with an explanation. Tasks follow the workflow case's owner.
- Mutation and audit record committed in one transaction. All writes require a
  client-generated UUID `Idempotency-Key`; a repeated identical request returns
  its original result, while a changed request with that key is rejected.
- Version checks prevent stale task edits and stale ownership changes. PostgreSQL
  row locks serialize changes to a case. Current authorization is rechecked even
  when returning an earlier request receipt.
- Bounded/cursor-paginated lists, 16 KiB JSON request limit, strict input fields,
  timezone-aware deadlines, sanitized errors, no CORS grants, no-store responses.
- PostgreSQL migration with tenant-preserving composite foreign keys and an
  append-only audit trigger. No DDL, sample seeding or account creation at startup.

## Architecture boundary

The intended private production flow is:

`recruit.medlivo.com BFF -> private team-workspace service -> Cloud SQL PostgreSQL`

The browser-facing backend (BFF) needs **two different credentials** when calling
Cloud Run: `X-Serverless-Authorization: Bearer <service-account ID token>` with the
receiving Cloud Run service URL as audience, and `Authorization: Bearer <Google
user ID token>` with the approved Google OAuth client ID as audience. The first
proves service identity to Cloud Run; this service validates the second to identify
the recruiter. Never copy a personal token into a deployment environment variable.

There is intentionally no browser access token in localStorage, no password form,
no public proxy route, no wildcard domain acceptance, and no forged-user header
option in this service. Google JWKS retrieval has a five-second timeout and bounded
cache lifetime. Tests use a generated RSA key and no Google network calls.

**Not yet implemented:** Google browser sign-in/OIDC login flow, state/nonce/CSRF,
secure HttpOnly sessions and logout/revocation UX, the same-origin BFF, frontend
wiring, self-service user invitations, shared draft/approval storage, background
reminders, messaging, JobDiva sync, production deployment or end-to-end sign-in.
An ID-token expiry is enforced; it is not a substitute for a complete session flow.
The public sample persona switcher remains a demo, not production authorization.

## Existing data model

This code maps the relevant columns of the existing `tenant`, `app_user`, `team`,
`recruiter_profile`, `job` and `candidate` tables. It does **not** introduce a second
user directory or replace canonical jobs/candidates. New `ws_*` tables hold
identity bindings, workflow cases, notes, tasks, operation receipts and audit rows.

A workflow case is a shared job/candidate work item, not the canonical job owner.
Reassignment changes that case's owner and its follow-ups; it does **not** rewrite
`job.owner_user_id`, candidate source ownership or JobDiva. Cross-team case transfer
is intentionally not available in this milestone.

An administrator must provision identity bindings and workflow cases after a
verified identity and team/record review. No public endpoint can bind itself to an
existing email address or set its own tenant/role. Existing app_user/recruiter_profile
and team manager assignments are authoritative. User deactivation removes access
on the next request, even when the Google token has not expired.

## Routes

All `/api/v1/team/*` routes require a valid Google bearer token plus an active,
provisioned database account. The service itself must also require Cloud Run IAM.

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Configuration liveness, not a database or sign-in test |
| GET | `/api/v1/team/me` | Database-backed member name and role |
| GET | `/api/v1/team/cases` | Assigned/managed cases, `limit` and `after` cursor |
| GET | `/api/v1/team/daily-priorities` | Recruiter-only read-only priorities: overdue/due-soon follow-ups and strong unreviewed matches |
| GET | `/api/v1/team/recruiter/follow-ups` | Recruiter-wide follow-up queue across assigned work items |
| GET | `/api/v1/team/recruiter/dashboard` | Recruiter-only read-only scorecard for weekly goals, actuals, and workload |
| GET | `/api/v1/team/cases/{id}` | Authorized workflow case |
| GET | `/api/v1/team/cases/{id}/notes` | Shared note history |
| POST | `/api/v1/team/cases/{id}/notes` | Append `{body}` |
| GET | `/api/v1/team/cases/{id}/tasks` | Shared follow-ups |
| POST | `/api/v1/team/cases/{id}/tasks` | Create `{title, due_at}` |
| PATCH | `/api/v1/team/cases/{id}/tasks/{task_id}` | `{status, expected_version}` |
| GET | `/api/v1/team/cases/{id}/audit` | Scoped activity history |
| GET | `/api/v1/team/cases/{id}/eligible-owners` | Active same-team recruiters for managers/admins |
| POST | `/api/v1/team/cases/{id}/reassign` | `{owner_user_id, reason, expected_version}` |

All mutation requests need `Content-Type: application/json` and a UUID
`Idempotency-Key`. A permission failure never reveals whether a hidden case exists.
Notes are plain text and returned as JSON. The eventual UI must render them as
text, never as unsanitized HTML. No send, submit, delete-note or modify-audit route
exists. Cursor ordering is by UUID; clients may sort a displayed page by date.

## Run offline development tests

From this directory, with Python 3.12 or 3.13:

```bash
python -m pip install '.[test]'
python -m pytest -q
python -m compileall -q workspace_api
```

Tests use synthetic tenants, users and work items only. SQLite file persistence,
separate application/engine instances and generated RSA tokens are used locally.
PostgreSQL-specific tests are skipped without a disposable PostgreSQL test database.

To run those tests, set `WORKSPACE_TEST_DATABASE_URL` to an **ephemeral test-only**
PostgreSQL URL. The suite creates and drops isolated `ws_test_*` schemas. NEVER
point this test variable at the production Cloud SQL database. GitHub CI provides
its own temporary PostgreSQL 16 service and no GCP, JobDiva or OAuth credentials.

## Staging enablement gates, not an instruction to change production now

1. Review this PR and the PostgreSQL CI results. Review the OAuth/BFF and session
   integration as a separate change before any real recruiter signs in.
2. Apply the existing canonical schema and `migrations/001_workspace.sql` to a
   disposable/staging database using a migration-only role. The migration adds
   four canonical unique indexes plus the six new workspace tables. It does not
   overwrite the original tables. Plan/index-review the migration for large tables.
3. Give a separate runtime database role only the needed access. A template is in
   `migrations/runtime-grants.psql`; configure its role name and review it first.
   It must not own the tables or inherit broad production permissions.
4. Provision approved identity bindings and synthetic cases for the staging pilot.
   Do not guess Google `sub` values or substitute email addresses.
5. Create the OAuth client for the approved recruiter origin and configure these
   server-only values through the project's reviewed deployment/Secret Manager:
   `WORKSPACE_ENABLED=true`, `WORKSPACE_DATABASE_URL` (PostgreSQL+psycopg URL),
   `WORKSPACE_GOOGLE_CLIENT_ID`, `WORKSPACE_GOOGLE_HOSTED_DOMAIN`.
6. Deploy the separate service privately and grant only the approved BFF service
   account invocation permission. Do not disable Cloud Run IAM as a workaround.
7. Verify end-to-end sign-in, expiry/logout, disabled-member denial, cross-team and
   cross-tenant denial, duplicate writes, concurrent edits and activity records.

The existing `/api/v1/jobs`, `/candidates` and other legacy routes have NOT been
made safe for real data by this new service. Keep the original preview in mock
mode until all legacy read paths have been authenticated and tenant-scoped.

## Operational limitations

Application-level scoping plus composite foreign keys are implemented here; a
PostgreSQL row-level security policy is not. The audit trigger and least-privilege
grants prevent application updates/deletes, not tampering by a database owner.
Identity updates, administrative provisioning, secret management, backups,
retention/removal workflows, authentication/denial telemetry and shared rate
limiting need an operational review before production use. No note bodies,
tokens, SQL parameters or database connection strings should be captured by APM.
The Docker runner disables Uvicorn access logs; platform logs must also avoid
Authorization-header/body capture. Secrets must never be pasted into chat.

## Official references used

- Google ID-token validation: https://developers.google.com/identity/gsi/web/guides/verify-google-id-token
- Cloud Run two-layer service/user identity: https://docs.cloud.google.com/run/docs/authenticating/service-to-service
- PyJWT key retrieval and claims validation: https://pyjwt.readthedocs.io/en/stable/usage.html
- Composite database constraints: https://docs.sqlalchemy.org/en/20/core/constraints.html


## Candidate best jobs

The candidate detail surface includes a read-only **Best current jobs** panel sourced from the canonical `match` table.

- It does not run a separate scoring algorithm.
- It displays persisted score, hard-gate status, strengths, gaps, JobDiva job reference, and recommended next review action.
- Excluded matches are not placed in the ranked recommendation list; their count is shown separately.
- Recruiter ownership and manager team scope are enforced.
- No outreach, submission, ownership change, or JobDiva mutation is performed from this panel.


## Daily priorities

For recruiters, the top of **My work** now provides a read-only start-of-day priority list. It orders overdue follow-ups first, then follow-ups due within 24 hours, then strong unreviewed matches on jobs owned by that recruiter. The list is planning and review only: it does not send outreach, create submissions, change ownership, or mutate JobDiva.


## Recruiter dashboard

The recruiter dashboard combines the selected week's goals and synchronized actual activity with current workload pressure: owned work items, open and overdue follow-ups, active priority jobs, and unreviewed strong/good matches. It is read-only and uses existing canonical/workspace data; it does not create a second ATS record, send outreach, or mutate JobDiva.


## Candidate Best Jobs review UX

The candidate detail surface now summarizes ranked persisted matches by score band and lets recruiters review the same evidence, next action, and match-quality feedback used in Match Queue. A recruiter can open the matched canonical job directly from the candidate view. The surface remains review-only for recruiting operations: it does not send outreach, submit candidates, change ownership, or mutate JobDiva.


## Match Queue triage

Recruiters can filter the Match Queue by Strong (9+), Good (8–8.9), or Needs Review (<8) without changing the underlying persisted score. Recruiter-specific review state is returned with the queue, allowing an optional “hide my reviewed matches” workflow. Saving match-quality feedback updates the visible queue state immediately; it remains measurement-only and never retrains or overrides the authoritative score.


## Recruiter follow-ups queue

Recruiters have one Follow-ups view across all work items assigned to them. Open items are ordered by due date so overdue tasks surface first, with filters for Open, Completed, or All. Recruiters can open the underlying work item or mark the task done/reopen it using the existing version-checked, idempotent, audited task mutation. The queue does not send reminders, messages, submissions, or JobDiva updates.


## Staging observability

The private workspace exposes two operational endpoints:

- `GET /health` is configuration liveness only. It intentionally does not query the database.
- `GET /ready` performs a bounded `SELECT 1` database reachability check and returns only booleans. It never returns a connection string, SQL, tenant, user, candidate, or job data.

The workspace emits event-only application log messages for:

- `workspace_authentication_denied`
- `workspace_authorization_denied`
- `workspace_validation_rejected`
- `workspace_database_unavailable`
- `workspace_readiness_database_unavailable`

These messages deliberately omit token values, request/response bodies, SQL text, database parameters, candidate/job identifiers, and exception strings. Staging should convert these event names and Cloud Run 5xx/revision health signals into log-based metrics and alerts. Alert delivery configuration remains an operational staging task, not an application-code permission to log more data.

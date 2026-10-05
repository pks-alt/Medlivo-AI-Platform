# Team staging delivery package

This package prepares a separate, initially private **staging** deployment. It does
not deploy resources, apply migrations, read secret values, change IAM, merge PRs,
load JobDiva records, or replace the public GitHub Pages preview. It extends PR #3.

## Implemented now

1. A **team-only Next.js container** built from the existing `/team`, `/api/team/*`
   and `lib/team` source. The legacy homepage/jobs/candidates routes, static sample,
   test login provider and test data are NOT copied into this image. `/` redirects
   to `/team`. The runner is non-root. The existing application Dockerfile is unchanged.
2. A standard-library Python manifest generator. Fixed staging service names and
   runtime identities cannot be replaced by production names. Images must use
   immutable digest references; secrets are numeric-version references, never
   credential values. BOTH services retain the Cloud Run invocation IAM check,
   including the configured mode. Ingress `all` means network reachability, not
   anonymous authorization; service and inherited IAM still require review.
3. A metadata-only inventory using the existing GitHub deployment identity when
   that identity's current permissions allow it. Permission-denied is `unknown`,
   never evidence that a resource is absent. The tool reads only enabled API,
   service, service-account, SQL-instance and secret metadata, plus service IAM.
   It does NOT read database records, access secret versions, create OAuth clients,
   or request additional permissions. Reports never declare the environment ready.
4. CI tests for the manifest/inventory logic plus a real Docker-built standalone
   Next.js runtime. HTTP tests check setup/no-cache/CSP, disabled API behavior and
   missing legacy/source/test routes. An actual browser checks the rendered setup.
   These do not constitute real Google sign-in or a deployed-cloud acceptance test.

## Proposed staging resources (not a statement that they exist)

| Resource | Name |
|---|---|
| Project / region | `medlivo-ai-platform` / `us-west1` |
| Private team API | `medlivo-team-api-staging` |
| Team login frontend | `medlivo-team-web-staging` |
| Separate PostgreSQL instance | `medlivo-team-staging` |
| API runtime identity | `medlivo-team-api-staging@medlivo-ai-platform.iam.gserviceaccount.com` |
| Browser runtime identity | `medlivo-team-web-staging@medlivo-ai-platform.iam.gserviceaccount.com` |

The new SQL instance requires an operator's cost/region/backup review before creation.
Do not reuse the existing `medlivo-ai-postgres` connection or production database
secret just to make staging start. A separate staging project could provide stronger
isolation but would need its own reviewed configuration, not bypassing these guards.

## What the operator does next

**First inspect, do not enable.** From an authorized checkout/Cloud Shell, run:

```bash
python3 infrastructure/team-staging/staging.py inventory
```

This outputs only a selected metadata checklist, not secret values. Missing setup is
reported as such and is not called a failed deployment. Existing branch restrictions
on the Workload Identity Federation provider must not be relaxed for this inventory.
Use the existing authorized administrator context instead when necessary.

Build images from the reviewed PR commit and record the resulting Artifact Registry
digests. The frontend build command from repository root is:

```bash
docker build -f infrastructure/team-staging/Dockerfile.web -t medlivo-team-web-staging .
```

Build the API using `services/team-workspace/Dockerfile` and that directory as context.
No image is pushed or deployed by this package's workflows. Configure dedicated
stage service accounts and the approved registry read permissions. Bootstrap each
service with disabled application flags and Cloud Run IAM enforcement to obtain
its actual `status.url`. Do not invent or precompute service URLs.

The manifest generator expects a JSON object with `project`, `region`, `environment`
(all fixed as above), and `images: {api: <digest-reference>, web: <digest-reference>}`.
Use paths under `us-west1-docker.pkg.dev/medlivo-ai-platform/medlivo-ai-containers/`
with image names equal to the staging service names and an `@sha256:<64-hex>` digest.
No filled example with fake digests is supplied as a deployable configuration.

```bash
python3 infrastructure/team-staging/staging.py render \
  --mode bootstrap --config /secure/staging.json --output-dir /secure/bootstrap-output
```

The two JSON files are valid YAML service specifications. Review them first. Google
Cloud's `gcloud run services replace FILE --dry-run --project=medlivo-ai-platform
--region=us-west1` validates without applying a change. The generator deliberately
has no `--apply` option. A later operator-approved deployment is separate.

Before configured mode, complete `docs/TEAM_SIGNIN_STAGING.md`: use staging-only
migration/runtime database roles, create the OAuth WEB client and register the exact
`<web status.url>/api/team/auth/callback`, configure the four staging secrets in
Secret Manager, and provision verified approved Google subject IDs plus synthetic
work items. Authentication requires both a verified Google identity and an active
explicitly provisioned account. Company-domain email alone is not enough.

Configured JSON adds `app_origin`, `api_url`, `google_client_id`, `secret_versions`
(with the four environment-variable keys below, each mapped to a numeric version
string), and a `reviewed` object whose four flags must literally be `true`:
`staging_database_and_grants`, `oauth_callback_registered`, `synthetic_users_only`,
`callback_logs_redacted`. These flags record operator attestation, not automated
proof. Values are validated locally but credentials are never included.

| Variable | Secret ID in the staging project |
|---|---|
| WORKSPACE_DATABASE_URL | medlivo-team-staging-api-database-url |
| TEAM_SESSION_DATABASE_URL | medlivo-team-staging-session-database-url |
| TEAM_GOOGLE_CLIENT_SECRET | medlivo-team-staging-google-client-secret |
| TEAM_SESSION_KEY | medlivo-team-staging-session-key |

The API URL uses `postgresql+psycopg://`; the session URL uses `postgresql://`.
Both must point to the reviewed staging database through its Cloud SQL Unix socket
or properly verified TLS; separate roles remain mandatory. The manifest references
cannot prove what a secret contains. An administrator must verify this privately.
Secrets access is per named secret, not project-wide. Never grant the browser runtime
read access to canonical candidate tables or the API database credential.

Configured mode keeps both services IAM-protected. Before allowing the **login
frontend only** to be reached by approved browser users, review logging redaction,
real OAuth settings and edge access/abuse controls. The private API must retain IAM
checks; grant only the designated web service identity invocation rights at that
API service. Do not expose both services or grant `allUsers` on the API. This package
does not automate public-access changes or assume an internal ingress setting is
compatible with an unconfigured Cloud Run-to-Cloud Run network route.

Repeat real acceptance with two authorized browsers: shared note/task, reassignment,
previous-owner denial, preserved history, logout, expiry, disabled-member and
cross-team/tenant denial. Container tests in this package only establish **disabled
bootstrap readiness**, not that these enabled cloud operations have passed.

## Keep the existing deployment separate

PR #3 remains unmerged. Its earlier frontend changes would match the current
`deploy.yml` main-branch trigger. That workflow targets the OLD web/API services,
not the new staging services, and the separate authentication repair in PR #1 is
still relevant. Do not merge PR #3 merely to obtain a staging deployment. Review
that release path before any merge; this package does not alter it automatically.

## Test and operational limits

```bash
python3 -m unittest discover -s infrastructure/team-staging/tests -v
```

No Google credentials are needed for these tests. CI creates a local Docker image,
not a cloud service. Dependency ranges in the source manifest and tagged base images
must be resolved/pinned and scanned as part of a production release; pinned deployment
image digests do not by themselves make every build input reproducible. Two maximum
instances per revision is a staging configuration target, not a billing guarantee.

Inventory visibility is limited by the invoking identity. It checks direct service
bindings but does not prove effective permissions inherited from projects/folders,
organization-policy compatibility, certificate/callback setup, database contents,
secret versions or DB grants. Those remain explicit deployment gates.

Official references (reviewed 2026-10-05):
- https://docs.cloud.google.com/run/docs/deploying
- https://docs.cloud.google.com/sdk/gcloud/reference/run/services/replace
- https://docs.cloud.google.com/run/docs/authenticating/public
- https://docs.cloud.google.com/run/docs/configuring/services/secrets
- https://docs.cloud.google.com/sql/docs/postgres/connect-run
- https://developers.google.com/identity/protocols/oauth2/web-server

# Team staging release strategy

This is the release contract for Medlivo Recruit AI staging.

## Principle

A merged pull request is **not** considered deployed. A feature is considered available in staging only after the release workflow completes and the running API and web services both report the exact merge commit SHA.

## Release sequence

1. Pull request CI must pass.
2. Merge to `main`.
3. Build immutable API and web images tagged with the merge SHA.
4. If the release introduces a reviewed schema migration:
   - run it with the dedicated **migration-only database role**
   - use the dedicated Cloud Run migration service account
   - never use the application runtime database credential for DDL
5. Deploy the API as a no-traffic candidate revision.
6. The candidate must pass `/ready`, including required-schema checks.
7. Promote the API revision.
8. Deploy the web image from the same merge SHA.
9. Verify both Cloud Run services carry `MEDLIVO_RELEASE_SHA=<merge SHA>`.
10. Browser acceptance verifies the expected feature and release SHA.
11. Only then is the feature marked **staging ready**.

## One-time staging prerequisites

Create and review these dedicated resources:

- Service account: `medlivo-team-schema-staging@medlivo-ai-platform.iam.gserviceaccount.com`
- Secret: `medlivo-team-staging-migration-database-url`
- The secret must contain the staging database URL for a **migration-only DB owner/role**, separate from `medlivo-team-staging-api-database-url`.
- The migration service account needs only:
  - Cloud SQL Client for `medlivo-ai-postgres`
  - Secret Manager Secret Accessor on the migration secret
  - permission to run the migration Cloud Run Job
- The API runtime service account remains least-privilege and must not receive schema-owner rights.

## Release visibility

The private API `/health` response includes `release_sha`.
The Job Intake footer displays the first 12 characters of the running release SHA.

This makes stale staging immediately visible and prevents “merged” from being confused with “deployed”.

## Failure behavior

If migration, readiness, release-SHA verification, or browser acceptance fails:

- do not promote the new release as staging-ready
- keep the last known-good revision serving traffic
- fix the failed gate and rerun the release
- never weaken `/ready`, disable IAM, or grant DDL rights to the runtime account as a workaround

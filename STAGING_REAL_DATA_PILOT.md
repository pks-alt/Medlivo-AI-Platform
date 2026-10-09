# Staging Real-Data Pilot Runbook

## Purpose

Run a controlled, read-only JobDiva pilot in Google Cloud staging so Medlivo recruiters can review real match results and collect match-quality feedback.

This runbook does **not** authorize JobDiva write-back, outreach, submissions, production deployment, or automatic scheduling.

## Architecture

Cloud Run Job:

`medlivo-jobdiva-pilot-staging`

Project / region:

`medlivo-ai-platform / us-west1`

Runtime identity:

`medlivo-ai-workers@medlivo-ai-platform.iam.gserviceaccount.com`

Pipeline per explicit run:

1. JobDiva jobs delta read
2. JobDiva candidates delta read
3. canonical source promotion
4. JobDiva JobsDetail enrichment
5. candidate profile / license / certification / resume-text enrichment
6. deterministic matching
7. persisted match results consumed by Recruiter Match Queue

## Safety controls

- `PILOT_ENABLED=false` by default
- `JOBDIVA_LIVE_ENABLED=false` unless the operator explicitly enables the pilot
- no JobDiva write endpoints exist in the pilot runtime
- one Cloud Run task only
- parallelism = 1
- retries = 0
- 15-minute execution timeout
- bounded per-run sync, enrichment, promotion and matching limits
- resume text reads limited to two resume versions in staging
- no scheduler is created in this slice
- database and JobDiva credentials are Secret Manager references only
- the deploy workflow never prints secret values
- deployment does not automatically execute the Cloud Run Job

## Required GitHub environment configuration

Environment:

`staging-real-data-pilot`

Recommended: configure required reviewers for this environment.

Required repository/environment variables:

- `GCP_WORKLOAD_IDENTITY_PROVIDER`
- `GCP_DEPLOY_SERVICE_ACCOUNT`
- `PILOT_TENANT_ID`
- `PILOT_DATABASE_SECRET` — Secret Manager secret ID containing the staging canonical database URL
- `JOBDIVA_CLIENT_ID_SECRET`
- `JOBDIVA_USERNAME_SECRET`
- `JOBDIVA_PASSWORD_SECRET`

These variables contain resource identifiers, not credential values.

## First deployment

Run GitHub workflow:

`Deploy JobDiva real-data pilot to staging`

Inputs:

- `enable_pilot = false`
- `confirm_read_only = READ_ONLY`

This builds the worker image and deploys the Cloud Run Job in disabled mode.

Inspect:

- Cloud Run Job service account
- Cloud SQL attachment
- Secret Manager references
- task count = 1
- parallelism = 1
- timeout
- environment flags

Do not execute the job while disabled.

## Full read-contract diagnostic

Before the first persistence-enabled pilot run, enable diagnostics-only mode:

- `PILOT_ENABLED=true`
- `JOBDIVA_LIVE_ENABLED=true`
- `PILOT_DIAGNOSTICS_ONLY=true`

The diagnostic authenticates and verifies the enabled Phase 1 read contract without persisting JobDiva payloads. It checks:

- OpenJobsList
- NewUpdatedJobRecords
- NewUpdatedCandidateRecords
- JobsDetail when a sample job is available
- CandidatesProfileDetail when a sample candidate is available
- CandidatesLicensesDetail
- CandidatesCertificationsDetails
- CandidatesResumesDetail
- ResumesTextDetail when a sample resume is available

Only endpoint status and record counts are emitted. Candidate/job payloads, credentials, tokens and resume text are not logged.

The diagnostic reports:

- `verified` when every enabled read path was exercised successfully
- `partial` when no safe sample record was available for one or more detail endpoints
- `failed` when an enabled endpoint returns authorization/HTTP/connector failure

Do not proceed to persistence-enabled pilot execution until the read contract is `verified`.

When `diagnostics_only=true`, the staging deploy workflow now executes the diagnostics-only Cloud Run Job automatically and uploads a sanitized `jobdiva-read-contract-diagnostic` artifact. This auto-execution applies only to diagnostics. Persistence-enabled pilot execution remains manual.

## First real-data execution

After database migrations 002 through 007 are applied to the staging canonical database and secret/IAM checks are complete:

Run the deploy workflow again with:

- `enable_pilot = true`
- `confirm_read_only = READ_ONLY`

Then an authorized operator explicitly executes:

`gcloud run jobs execute medlivo-jobdiva-pilot-staging --project=medlivo-ai-platform --region=us-west1 --wait`

The deploy workflow intentionally does not execute this command.

## Initial bounded staging limits

- sync page size: 50
- promotion: 100 source records per entity stream
- job enrichment: 10
- candidate enrichment: 10
- matching pairs: 200
- resume text versions: 2

These are staging safety bounds, not throughput targets.

## Acceptance after each run

Check:

1. JobDiva sync health endpoint shows no error state.
2. Sync checkpoints advanced only on successful delta windows.
3. Canonical source records were linked without duplicate JobDiva source IDs.
4. Job/candidate enrichment error counts are reviewed.
5. Matching produced persisted eligible/excluded records.
6. Recruiter Match Queue shows real records only to authorized users.
7. No JobDiva write activity occurred.
8. Match-quality pilot feedback can be recorded.
9. Logs contain counts and error classes, not candidate payloads or credentials.

## Stop / kill switch

Deploy with:

- `enable_pilot = false`
- `confirm_read_only = READ_ONLY`

This changes both `PILOT_ENABLED` and `JOBDIVA_LIVE_ENABLED` to false.

Because no scheduler exists, there is no recurring execution to disable in this slice.

## Expansion rule

Do not increase batch sizes or add a scheduler until multiple bounded runs complete cleanly and recruiter feedback confirms the results are useful.

Do not add semantic retrieval or AI reranking until the real-data match-quality pilot provides enough evidence to justify it.


## Six-month JobDiva job import

For the initial Medlivo job history, prefer the bounded six-calendar-month job import instead of a full-history job pull.

Workflow inputs:

- `enable_pilot = true`
- `confirm_read_only = READ_ONLY`
- `diagnostics_only = false`
- `active_jobs_by_division = false`
- `six_month_jobs = true`

Behavior:

1. Calculates exactly six calendar months before execution time.
2. Reads `NewUpdatedJobRecords` in replay-safe windows of no more than 14 days.
3. Imports all statuses returned in that six-month history, including open, on-hold, closed/filled and cancelled jobs.
4. Captures the exact JobDiva source IDs returned within the six-month windows.
5. Promotes only those source IDs into the canonical job table, avoiding accidental promotion of older historical records already present in staging.
6. Preserves JobDiva status in canonical form: open/active/opened -> open; hold -> on_hold; closed/filled -> closed; cancelled/canceled -> cancelled.
7. Reports imported counts by canonical status and Medlivo division.

Important: `NewUpdatedJobRecords` defines this historical scope by jobs changed within the six-month window. A job created earlier but updated during the window can therefore appear, which is expected for JobDiva delta-history semantics.

Do not combine `six_month_jobs=true` with diagnostics-only or the 100-active-jobs-per-division sampler.

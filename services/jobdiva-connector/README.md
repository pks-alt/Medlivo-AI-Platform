# JobDiva Connector

JobDiva is the first ATS connector for Medlivo AI Platform.

## Current verified facts

The JobDiva API portal exposes V2 methods/models and webhook configuration. JobDiva documents webhook support for most data entities, with Insert/Create, Update, and Delete operations. Webhook setup requires an endpoint URL and a signature key.

## What we are intentionally not guessing

The public portal does not currently expose enough detail to safely hard-code:
- authentication/token request
- production API base URL
- candidate endpoint paths
- resume endpoint paths
- job endpoint paths
- pagination/rate limits
- write-back endpoints
- webhook signature algorithm/header contract

Those remain explicit integration-contract TODOs until JobDiva provides the technical documentation requested by Medlivo.

## Connector responsibilities

1. authenticate using JobDiva's documented mechanism
2. ingest controlled job/candidate/resume samples
3. preserve JobDiva source IDs and timestamps
4. support incremental sync
5. validate webhook events
6. publish normalized source events to the platform
7. retry safely and idempotently
8. write back only through documented supported operations

## Security

Never place JobDiva credentials in source code, GitHub Actions variables committed to the repo, test fixtures, or frontend code.

Production credentials belong in Google Secret Manager.

## Proof sequence

1. Confirm auth contract
2. Fetch 5-10 active jobs
3. Fetch 20-50 candidates
4. Fetch representative resumes
5. Inspect actual fields and custom fields
6. Map source IDs into canonical records
7. Test incremental sync
8. Test one webhook entity in a non-destructive way
9. Only then design the large-scale backfill

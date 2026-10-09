# Workers

Background/event-driven workers for ingestion, normalization, embeddings, reranking triggers, outreach workflows, and JobDiva synchronization.

## Current active slice: JobDiva Data Foundation

The JobDiva delta worker provides a replay-safe landing layer for the canonical database:

- durable per-tenant/per-stream checkpoints
- durable sync-run history
- jobs and candidates delta windows
- five-minute overlap replay protection
- safety lag for in-flight vendor updates
- idempotent source-record upserts using existing unique JobDiva source IDs
- checkpoint advancement only after the entire window succeeds
- failed runs retain the previous checkpoint so the next run safely replays the window

The landing layer intentionally stores raw JobDiva source records first. Promotion into normalized canonical `job` and `candidate` records happens only after the real payload mapping is verified.

JobDiva remains read-only in Phase 1.


## Historical backfill

Historical jobs/candidates are processed in chronological windows of at most 14 days. Completed windows are recorded in `integration_sync_run` with `mode='backfill'` and are skipped on a restart.

Backfill never updates the live delta watermark.

## Sync health

The private platform API exposes:

`GET /api/v1/integrations/jobdiva/health`

It returns only operational metadata such as watermark freshness, last success, last error, and latest record counts. It does not return JobDiva job/candidate payloads.


## Canonical promotion

Landed JobDiva source records are promoted into the canonical `job` and `candidate` tables through a separate promotion step.

Rules:
- JobDiva source IDs remain the stable external identity.
- A source record links to exactly one canonical job/candidate.
- New and changed source records are eligible for promotion.
- Promotion is versioned and audited.
- Jobs require an explicit source ID and title.
- Candidate delta records only seed explicit identity/contact/profession/location fields.
- Missing candidate fields never erase richer canonical values.
- Unknown JobDiva custom fields remain in the raw source payload until their mapping is verified.
- Promotion never writes back to JobDiva.


## Candidate detail enrichment

Canonical candidates linked to JobDiva are enriched from the authorized JobDiva detail endpoints:

- candidate profile
- licenses
- certifications
- resume metadata
- bounded resume text reads

The existing `candidate-intelligence` package performs normalization. The worker persists normalized intelligence into canonical candidate, credential, resume-version and evidence tables.

Rules:
- JobDiva remains the candidate/resume system of record.
- Medlivo stores normalized intelligence and resume text/reference, not a second authoritative resume file.
- Candidate detail may fill missing canonical fields but does not erase richer values with nulls.
- JobDiva-sourced credentials are refreshed transactionally.
- Resume versions are upserted by JobDiva resume ID.
- Enrichment is versioned and retryable per candidate source record.


## Job detail enrichment

Canonical jobs linked to JobDiva are enriched from the authorized `JobsDetail` read.

The existing `job-intelligence` package performs normalization. The worker persists verified job detail into the canonical `job` table and source-backed requirements into `job_requirement`.

Rules:
- JobDiva remains the job/requisition system of record.
- Free-text job descriptions never create hard gates automatically.
- Explicit license states and explicitly required certifications may become hard gates.
- Care setting is matching evidence, not an automatic exclusion gate.
- Unknown/custom JobDiva fields remain in the raw source payload until their mapping is verified.
- Enrichment is versioned and retryable per source record.
- No JobDiva write-back is performed.


## Matching activation

Enriched canonical jobs and candidates are evaluated through the shared `matching-engine` package.

Rules:
- Only enriched JobDiva-linked jobs and candidates are eligible for this activation slice.
- Candidate pools are prefiltered by confirmed profession before full scoring.
- A pair is recomputed only when it is new, either canonical record changed, or the rules version changed.
- Hard-gate failures are persisted as excluded matches plus explicit exclusion reasons.
- Eligible matches persist score components, strengths and gaps for the Match Queue.
- The Match Queue remains read-only and consumes persisted match records.
- Matching never writes to JobDiva.
- Division is not invented when the source has not yet established it.


## JobDiva full read-contract diagnostic

The staging pilot supports `PILOT_DIAGNOSTICS_ONLY=true` to validate all enabled Phase 1 JobDiva read permissions before any source records are persisted. The diagnostic uses a bounded 14-day delta window and page size 5, selects at most one sample job/candidate/resume for detail checks, and logs only endpoint status/count metadata.

A `partial` result means no safe sample record was available to exercise every detail endpoint. A `failed` result means an endpoint returned authorization, HTTP, or connector failure. Only `verified` should be treated as permission-complete for the real-data pilot.

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

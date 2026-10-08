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

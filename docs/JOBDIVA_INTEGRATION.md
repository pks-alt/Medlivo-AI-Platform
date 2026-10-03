# JobDiva Integration

JobDiva is the first connector, not the canonical platform database.

Awaiting technical confirmation for:
- auth/token
- jobs
- candidates
- resumes
- activities
- submissions
- placements
- custom fields
- webhooks
- write-back
- pagination/rate limits
- permitted AI/indexing usage

## Security
Never commit JobDiva credentials. Use Google Secret Manager.

## Ingestion
Start with a controlled slice, validate normalization and matching, then scale to the approximately 1M-resume backfill.

Preferred update path:
JobDiva webhook/event -> connector -> Pub/Sub -> normalization -> canonical DB -> search index -> affected-match recalculation.

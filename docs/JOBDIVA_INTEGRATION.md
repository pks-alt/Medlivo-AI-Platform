# JobDiva Integration

JobDiva is the first ATS connector for Medlivo AI Platform. JobDiva remains the ATS and operational system of record; Medlivo AI is the intelligence, matching, recruiter-productivity and validation layer.

## Confirmed Phase 1 read contract

The dedicated JobDiva integration user is enabled for the Phase 1 read functions. Phase 1 remains read-only.

Confirmed V2 endpoints currently implemented:

- `GET /apiv2/v2/authenticate`
- `GET /apiv2/bi/OpenJobsList`
- `GET /apiv2/bi/NewUpdatedJobRecords`
- `GET /apiv2/bi/NewUpdatedCandidateRecords`
- `GET /apiv2/bi/JobsDetail`
- `GET /apiv2/bi/CandidatesProfileDetail`
- `GET /apiv2/bi/CandidatesLicensesDetail`
- `GET /apiv2/bi/CandidatesCertificationsDetails`
- `GET /apiv2/bi/CandidatesResumesDetail`
- `GET /apiv2/bi/ResumesTextDetail`

Authentication requires Client ID, API username and API password. Credentials and tokens must never be committed or logged.

## Phase 1 safety boundary

- GET-only connector
- live reads disabled by default
- allowlisted endpoints only
- bounded request budgets, retries, response sizes and timeouts
- no redirects
- no response-body logging on connector errors
- no JobDiva candidate/job/submission/ownership/status write-back
- no outreach side effects

## Current ingestion sequence

1. Authenticate through the confirmed V2 auth endpoint.
2. Read a bounded OpenJobsList sample.
3. Read narrow NewUpdatedJobRecords windows.
4. Enrich jobs through JobsDetail.
5. Read narrow NewUpdatedCandidateRecords windows.
6. Enrich candidates with profile, license, certification and resume metadata/text.
7. Promote source records into canonical Medlivo job/candidate intelligence.
8. Run deterministic matching and persist eligible/excluded results.
9. Let authorized recruiters review results in Match Queue and Candidate Best Jobs.
10. Collect recruiter match-quality feedback for real-data acceptance.

## Historical and delta behavior

NewUpdatedCandidateRecords and NewUpdatedJobRecords are the primary delta feeds. Historical backfill remains checkpointed and bounded. Candidate merges must preserve JobDiva source IDs and canonical identity history.

## Webhooks

Webhook events are treated as change notifications. The JobDiva API remains the authoritative read path. Webhooks should trigger or accelerate reconciliation, not replace delta reads.

## Production rule

Do not enable JobDiva write APIs until JobDiva explicitly authorizes the exact endpoint(s), Medlivo implements a narrow allowlist, and staging acceptance proves the behavior.

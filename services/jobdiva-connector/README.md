# JobDiva Connector

JobDiva is the first ATS connector for Medlivo AI Platform.

## Confirmed Phase 1 contract

Medlivo Phase 1 is read-only. JobDiva has enabled the dedicated integration user for the requested read functions and additional functions remain disabled until requested.

Confirmed V2 paths now implemented:
- `GET /apiv2/v2/authenticate`
- `GET /apiv2/bi/OpenJobsList`
- `GET /apiv2/bi/NewUpdatedJobRecords`
- `GET /apiv2/bi/NewUpdatedCandidateRecords`

Authentication requires:
- Client ID
- API username
- API password

The JobDiva delta endpoints use `MM/dd/yyyy HH:mm:ss` timestamps and support page number/page size parameters.

## Safety rules

- Never commit JobDiva credentials or tokens.
- Keep credentials in Google Secret Manager for deployed workloads.
- Phase 1 performs GET requests only.
- No candidate/job write-back, outreach, submissions, or destructive operations are enabled.
- Do not print access tokens, credentials, full authentication URLs, or candidate payloads in logs.

## Safe connectivity probe

For a one-time Cloud Shell test, export credentials only into the current shell session, run the probe, and then unset them. Prefer reading the password silently so it does not enter shell history.

```bash
cd ~/Medlivo-AI-Platform/services/jobdiva-connector
export JOBDIVA_CLIENT_ID='<client id>'
export JOBDIVA_USERNAME='<api username>'
read -s -p 'JobDiva API password: ' JOBDIVA_PASSWORD && export JOBDIVA_PASSWORD && echo
python probe.py
unset JOBDIVA_PASSWORD JOBDIVA_USERNAME JOBDIVA_CLIENT_ID
```

The probe prints only:
- authentication success/failure
- OpenJobsList count
- up to five job IDs/titles/statuses

It intentionally does not print candidate data, credentials, tokens, or raw auth responses.

## Sync sequence

1. Authenticate.
2. Fetch a small OpenJobsList sample.
3. Fetch a narrow NewUpdatedJobRecords window.
4. Inspect actual response shape and normalize job IDs/status/location/rates/specialty.
5. Fetch a narrow NewUpdatedCandidateRecords window.
6. Add candidate detail, resume, license, and certification calls after the source shape is verified.
7. Add 14-day checkpointed historical backfill.
8. Add webhook receiver for near-real-time change notification.
9. Reconcile webhooks with scheduled API delta sync because JobDiva drops webhook events after its retry limit.

## Historical and merge behavior

JobDiva has confirmed:
- NewUpdatedCandidateRecords is the primary candidate delta feed.
- NewUpdatedJobRecords is the primary job delta feed.
- MergedCandidates V2 accepts a maximum two-week date range per call.
- CANDIDATEID is the merged-away record.
- MERGEDTOCANDIDATEID is the surviving record.

A complete inventory of very old candidate IDs is still an open integration question; do not assume the delta feed alone represents all historical candidates.

## Webhooks

Webhook configuration is managed on the Medlivo side. The Client URL will point to a dedicated Medlivo receiver. Webhook events are treated as change notifications; the JobDiva API remains the authoritative read path.

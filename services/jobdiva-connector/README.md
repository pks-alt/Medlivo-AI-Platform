# Read-only JobDiva connector pilot

This is an isolated server-side development module, **not a live synchronization service**.
It does not change the public recruiter preview, deploy infrastructure, modify JobDiva,
write to PostgreSQL, send outreach, or contact an AI provider. No production credentials
or candidate data belong in this repository.

## Implemented

- Explicitly enabled authentication using a reviewed request contract and environment secrets.
- One cached 24-hour JWT, refreshed five minutes early; one refresh on a read's HTTP 401.
- A strict allowlist for OpenJobsList, JobsDetail, CandidatesProfileDetail,
  CandidatesLicensesDetail, CandidatesCertificationsDetails, CandidatesResumesDetail,
  and ResumesTextDetail. A POST is allowed only when it is the reviewed reporting read.
- Explicit IDs, deduplication, serial batches of at most 100 IDs, and reviewed JSON wrappers.
- A per-process pilot budget of at most 6 requests/minute and 1,000/rolling day,
  including authentication and retries. These are conservative **local caps**, not
  a guarantee of vendor quota compliance; limits for some methods remain unconfirmed.
- Bounded retries on 429 and selected 5xx statuses. Retry-After longer than 60 seconds
  stops the pilot rather than being shortened. Network failures stop safely.
- HTTPS origin allowlist, no redirects, total request deadlines, bounded response size,
  sanitized errors and no HTTP client INFO log of the authentication URL.
- A resume-version selector using RESUMEID and DATECREATED. Date format/time zone must
  be confirmed; missing, conflicting, or daylight-saving-ambiguous dates require review.
- A count-only pilot CLI: dry-run by default, 1–50 explicit IDs, no payload output or storage.
- Synthetic tests and a separate pull-request CI workflow, with no cloud credentials.

## Run tests now, with no JobDiva account access

Use Python 3.12 or newer from this directory:

```bash
python -m pip install .
python -m unittest discover -s tests -v
python -m compileall -q jobdiva_connector
```

The test request formats are explicitly **synthetic**, not confirmed vendor schemas.
A contract marked `purpose="test"` is refused unless an HTTPX MockTransport is supplied.
Importing `jobdiva_connector.config` no longer instantiates settings or requires secrets.

## Before any real request

Review the actual JobDiva Swagger for the Medlivo account and build a local contract JSON
using `JobDivaContract` in `contracts.py`. The support email establishes operation names,
batching, and token lifetime; it does not by itself establish exact request serialization
or response wrappers. The dynamically loaded official schemas were not retrieved during
this implementation, so no unverified authentication/request contract is enabled here.

A pilot contract needs `purpose="pilot"`, `reviewed=true`, and `evidence` identifying
who reviewed which official Swagger version. Specify:

1. Authentication path, GET/POST, query/JSON/form location, exact credential parameter
   names, token response path, and whether the Authorization value needs `Bearer `.
2. For each selected read: exact path/method/location, ID parameter name and serialization
   (`csv`, `repeated`, or JSON array), integer/string ID type, optional/required parameter
   names, and JSON path to the record array. No undeclared request parameters are allowed.
3. Confirm all required production parameters in Swagger, including any UserFields names.
   The local contract is a deliberate, reviewed subset, not an automatic OpenAPI client.

Configure a dedicated private pilot worker with `JOBDIVA_LIVE_ENABLED=true`,
`JOBDIVA_CLIENT_ID`, `JOBDIVA_USERNAME`, `JOBDIVA_PASSWORD`, and `JOBDIVA_API_BASE_URL`.
The API origin must be an approved HTTPS `api.jobdiva.com` or `next.jobdiva.com` origin.
Confirm the correct origin with JobDiva; the documentation portal is not assumed to be
an API endpoint. Credentials belong in Google Secret Manager and server-side injection,
never in chat, repository files, frontend variables, or a public deployment.

Keep HTTP wire tracing, query-string logging, and APM request-body capture disabled or
redacted: the reviewed authentication contract may put credentials in query parameters.
The connector itself does not print request URLs, tokens, passwords, or record values.

## Controlled pilot invocation (developer only)

Store the reviewed contract, approved synthetic/test IDs and optional parameters outside
Git. First run without `--execute`; this validates the plan and makes no network calls:

```bash
python -m jobdiva_connector \
  --contract /secure/jobdiva-contract.json \
  --operation JobsDetail \
  --ids-file /secure/test-job-ids.json
```

The ID file is a JSON array of 1–50 explicitly approved numeric JobDiva test record IDs.
Only after settings, permissions, schemas, and test records are approved, repeat with
`--execute`. The output includes counts only. A dry-run is not authentication validation.
The CLI deliberately excludes OpenJobsList because its bounded pagination/filter
contract has not yet been confirmed. The SDK supports a reviewed call to that method.
For protected candidate data, do not add a proxy route to the public mock-data web app.

## Not implemented or enabled in this milestone

- Full candidate-ID enumeration, 300,000-record backfill, cursors or durable checkpoints.
- Shared/distributed quotas, persistent daily budgets, or scheduled synchronization.
- Vendor field-to-canonical-database mappings or database writes.
- Webhook ingestion or signature verification; the existing webhook stub is unchanged.
- Merges/deletions/removal reconciliation or incremental-change coverage.
- Recruiter login, tenant/role authorization, live screen data, embeddings, or matching.
- Submittals, placements, credential verification, contact automation, or any write-back.

Do not scale or restart workers to evade local budgets. A shared limiter, durable cursors,
and vendor-confirmed quotas are required before bulk or multi-worker use.
Use the API response status as data access evidence, not proof of all fields or completeness.

## Source and remaining confirmations

JobDiva Support, 5 October 2026, supplied in the project discussion: 24-hour JWT, up to 100 IDs for named detail reads, resume text workflow,
and preference against bulk original resume downloads. No email addresses, account IDs,
credentials or candidate values are included in fixtures.

Official documentation entry points:
- https://next.jobdiva.com/api-management/updates
- https://documenter.getpostman.com/view/10552582/VUr1GsLj

Obtain the exact Swagger schemas and field samples through the authorized account before
live verification. Pending confirmations include new/changed/deleted record discovery,
credential fields and verification status, rate-limit scope, webhook delivery guarantees,
and permissions/restrictions for indexing and AI processing.

# JobDiva Connector Proof

## Goal

Prove the minimum reliable data contract before building the approximately 1M-resume ingestion pipeline.

## Acceptance criteria

### Authentication
- official auth flow documented
- credentials stored in Secret Manager
- token lifetime/refresh behavior understood
- no personal secrets in GitHub

### Jobs
Retrieve a controlled set of active jobs and capture:
- JobDiva job ID
- status
- title
- profession/specialty
- client/facility
- location
- start date
- schedule/shift
- requirements
- recruiter/owner
- rate fields where permitted
- custom fields
- created/updated timestamps

### Candidates
Retrieve a controlled set and capture:
- JobDiva candidate ID
- contact fields
- location
- profession/specialty
- skills
- licenses/certifications
- availability/preferences
- recruiter ownership
- status
- custom fields
- created/updated timestamps

### Resumes
Determine whether JobDiva returns:
- original file
- parsed text
- parsed sections
- resume version/update date
- multiple resume records

### History
Confirm access to:
- notes/activity
- submissions
- interviews
- placements/assignments
- assignment end dates

### Webhooks
Confirm:
- supported entities
- event schema
- signature validation contract
- retries
- deduplication/event IDs
- logs

## Output of this proof

The proof should produce real sample payloads with sensitive values redacted, followed by a final canonical-schema mapping. We should not finalize the production candidate/job schema from assumptions.

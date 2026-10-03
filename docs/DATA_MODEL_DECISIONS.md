# Data Model Decisions

## Canonical vs source data
JobDiva and future ATS/VMS integrations are source systems. Medlivo AI Platform owns canonical candidate and job identities.

## Candidate identity
A canonical candidate may map to multiple ATS records and multiple resume versions.

## Job identity
A canonical job may map to multiple source records in future integrations.

## Provenance
Normalized and AI-inferred facts must retain source evidence and confidence.

## Matching
The platform does not precompute every candidate-job pair. It applies hard gates and retrieval first, then persists operationally meaningful matches.

## Readiness
Near Ready and Submission Ready are distinct workflow states.

## Human control
Recruiter approval remains required for submission in Phase 1.

## Multi-tenancy
Tenant IDs are explicit from day one, even though Medlivo is the only Phase 1 customer.

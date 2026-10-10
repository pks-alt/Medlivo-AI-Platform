# Architecture Decision Records

Accepted architecture decisions live in this directory.

## Rules

- Do not silently override an accepted ADR in feature code.
- If a future requirement conflicts with an ADR, add a new ADR that explicitly supersedes the old decision.
- A superseding ADR must explain the reason, migration impact, security/RBAC/audit implications, and rollback plan.
- The permanent engineering process is governed by `docs/ENGINEERING_OPERATING_MODEL.md`.

## Current decisions

1. `001-jobdiva-system-of-record.md`
2. `002-role-and-rate-ownership.md`
3. `003-ai-human-decision-boundary.md`
4. `004-division-channel-model.md`
5. `005-submission-vs-start-readiness.md`

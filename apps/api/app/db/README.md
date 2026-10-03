# Database Migrations

Phase 1 begins with plain SQL migrations so the canonical model remains transparent while the JobDiva contract is still being discovered.

## Rules
- Never use source-system IDs as primary keys.
- All operational entities use UUIDs.
- Every source record preserves source system + source ID.
- Inferred facts keep evidence/provenance.
- Tenant scope is explicit.
- Matching persists only meaningful candidate-job relationships.

## Migration order
1. 001_initial_schema.sql
2. future additive migrations

The production migration runner will be added before Cloud SQL deployment.

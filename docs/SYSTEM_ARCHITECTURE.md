# System Architecture

## Product surfaces
- www.medlivo.com: public website
- recruit.medlivo.com: recruiter/manager platform
- talent.medlivo.com: clinician portal after recruiter workflow stabilizes

## Phase 1 stack direction
Google Cloud first, portable services.

Core components:
- Cloud Run
- Cloud SQL PostgreSQL
- Pub/Sub
- Secret Manager
- Cloud Storage
- BigQuery
- dedicated hybrid/vector search after evaluation
- Neo4j designed for now, added later

## Data flow
JobDiva -> connector -> raw/source ingest -> identity resolution -> normalization -> enrichment -> embeddings/indexing -> readiness -> selective matching.

## Matching
Hard gates -> hybrid retrieval -> deterministic scoring -> small shortlist -> LLM rerank/explanation.

No brute-force matching across all candidates and jobs.

## Agent Factory
Agents orchestrate services rather than replacing deterministic systems.

Principle: Agents decide. Services compute. Databases retrieve. Humans approve consequential actions.

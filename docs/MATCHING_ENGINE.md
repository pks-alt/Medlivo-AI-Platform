# Matching Engine

## Core rule
No unnecessary matching.

## Stage 1: hard gates
Configurable by division/client/job:
- profession/specialty
- relevant experience
- location or travel willingness
- active license or realistic license readiness before start
- required certification where truly mandatory
- basic availability compatibility
- contactability
- client exclusions

## Stage 2: retrieval
Structured filters + lexical/BM25 + vector similarity.

## Stage 3: deterministic scoring
Dimensions:
- clinical fit
- location/travel
- license readiness
- availability
- compensation
- prior positive client history
- engagement likelihood
- readiness

## Stage 4: AI
Only the small shortlist reaches LLM reasoning for nuance, explanations, and summary.

## Evidence
Every material match factor must link to its source.


## Hybrid retrieval implementation

The current retrieval layer:
- applies deterministic hard gates before any semantic ranking
- combines lexical clinical-term overlap with optional cosine similarity
- falls back to lexical-only ranking when embeddings are unavailable
- emits retrieval evidence for auditability
- does not change the authoritative deterministic match score

A production vector store/embedding provider remains a deployment decision. Retrieval can be connected to that infrastructure without changing hard-gate behavior.


## Worker pipeline integration

The matching worker now groups pending pairs by job, persists hard-gate exclusions first, and uses hybrid retrieval to prioritize the remaining eligible candidates before deterministic scoring. If retrieval fails, the worker falls back to stable deterministic processing so retrieval cannot block matching.


## Resume evidence in soft scoring

Source-backed resume specialty signals may strengthen the existing specialty component when the canonical profile specialty is missing or incomplete. Resume clinical-skill signals are available to retrieval but are not yet scored unless an explicit job-side skill requirement exists. Resume evidence never creates a hard gate on its own.


## Explicit clinical-skill alignment

Job-side clinical skills are accepted only from explicit source requirement fields. They are persisted as non-hard-gate skill requirements. Matching compares those explicit job skills with resume-backed clinical-skill evidence as a soft component; missing skill evidence lowers the component but never excludes the candidate.

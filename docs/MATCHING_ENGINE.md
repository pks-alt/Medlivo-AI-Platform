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

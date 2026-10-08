# Real Data Matching Acceptance Pilot

## Purpose

Validate the current deterministic Medlivo matching engine on real recruiting work before adding semantic retrieval or AI reranking.

Recruiter feedback is **measurement only** during the pilot. It does not automatically change match scores, hard gates, ownership, outreach, submissions, or JobDiva data.

## Recruiter feedback

For an eligible persisted match in the Match Queue, the recruiter can record one of:

- **Strong match** — would actively prioritize this candidate for the job
- **Good match** — worth recruiter follow-up / qualification
- **Weak match** — technically possible but not compelling
- **Not a match** — recruiter would not pursue this match

Optional notes may be stored through the API for detailed analysis.

## Pilot targets

Minimum recommended sample:

- **100 total recruiter match reviews**
- **25 or more reviews per Medlivo division** where sufficient real volume exists
- Representative roles from Rehabilitation, Nursing & Allied, and Locum Tenens
- Mix of scores, especially 9.0+, 8.0–8.9, and lower eligible matches

Initial quality goal:

- **9.0+ matches: at least 80% Strong + Good agreement**

This is a working acceptance threshold, not a permanent model KPI. We will adjust it after observing real recruiter decisions and sample balance.

## Management view

Managers can review:

- total pilot feedback count
- Strong / Good / Weak / Not-a-match distribution
- positive agreement rate by score band
- positive agreement rate by division

Managers see only feedback within their authorized team scope. Admin can see tenant-level pilot data.

## Decision rule after pilot

Do not add AI reranking merely because it is available.

Use pilot evidence to determine whether gaps come from:

1. incomplete JobDiva source data,
2. normalization/taxonomy gaps,
3. hard-gate rules,
4. deterministic weights,
5. missing semantic similarity,
6. genuinely ambiguous recruiter judgment.

Fix data and rules first. Add semantic/vector retrieval or AI reranking only where the pilot demonstrates measurable value.

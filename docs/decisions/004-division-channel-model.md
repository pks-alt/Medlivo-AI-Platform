# ADR 004: Division and Customer-Channel Model

**Status:** Accepted  
**Date:** 2026-10-10

## Decision

Medlivo is one shared platform with division-specific rules.

### Rehabilitation

Supports both:

- Direct Customer
- MSP/VMS

Rehab template/rule precedence may layer:

`Medlivo default → Rehab channel/default → customer/program → profession/specialty → job override`

Rehab staffing is travel/contract-oriented, typically 13 weeks or longer. No per-diem workflow is part of the agreed model.

### Nursing & Allied

MSP/VMS only.

No direct-customer branch and no per-diem/individual-shift workflow in the current operating model.

### Locum Tenens

MSP/VMS only.

Submission is document-heavy and may include credential evidence at submission stage. Credential copy and primary-source verification remain distinct.

## Consequence

Do not build separate platforms per division. Layer rules/configuration on the shared architecture.

Any channel-model change requires an explicit ADR update.

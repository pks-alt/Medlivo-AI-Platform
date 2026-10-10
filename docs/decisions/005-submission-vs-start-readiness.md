# ADR 005: Submission Readiness and Start Readiness Are Separate

**Status:** Accepted  
**Date:** 2026-10-10

## Decision

Medlivo maintains two distinct readiness concepts.

### Submission Ready

Answers:

**Is there enough verified/reviewed information and documentation to present this candidate to the customer/MSP/VMS?**

Submission readiness is owned by Submission Studio and may include:

- resume/CV
- candidate/provider presentation
- licenses/certifications
- skills checklist
- references
- customer/program forms
- other submission-stage requirements

### Start Ready

Answers:

**Can this clinician/provider safely and operationally begin the assignment?**

Start readiness may include:

- credentialing/compliance completion
- background/drug/immunization requirements
- privileging
- onboarding items
- client-specific start requirements
- operational risk, owner, next action, due date

## Consequence

A candidate can be Submission Ready without being Start Ready.

Do not collapse the two states into one status or use submission completion as proof of start compliance.

Any future automation must preserve this distinction unless a superseding ADR explicitly changes it.

# Canonical Data Model

Phase 1 keeps source-system records separate from canonical Medlivo entities.

## Core tenancy and users
- tenant
- user
- team
- recruiter_profile
- customer
- customer_assignment

## Jobs
- job
- job_source_record
- job_requirement
- job_assignment

## Candidates
- candidate
- candidate_source_record
- resume_version
- candidate_preference
- candidate_availability
- candidate_license
- candidate_certification
- candidate_evidence

## Matching
- match
- match_score_component
- match_exclusion
- match_feedback

## Engagement
- conversation
- conversation_participant
- message
- qualification
- qualification_answer

## Submission workflow
- submission
- submission_requirement
- submission_evidence
- assignment

## Governance
- consent_profile
- audit_event
- external_identity
- integration_cursor

## Design rules
1. Never use ATS IDs as canonical primary keys.
2. Preserve every source-system ID.
3. Every inferred/normalized fact should retain provenance.
4. Hard requirements and scoring components must be versioned.
5. Do not persist low-value candidate-job relationships.
6. Tenant boundaries are explicit on operational tables.

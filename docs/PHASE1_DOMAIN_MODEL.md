# Medlivo AI Platform — Phase 1 Canonical Domain Model

**Status:** Governing Phase 1 domain model  
**Repository:** `pks-alt/Medlivo-AI-Platform`  
**Parent architecture:** `docs/ENTERPRISE_ARCHITECTURE_PHASE1.md`

This document defines the canonical business entities, ownership boundaries, relationships, lifecycle states, provenance, and implementation ownership for Phase 1.

It is intentionally aligned to the current repository and existing models/migrations. New implementation must extend these domains rather than create parallel records.

---

## 1. Domain-model principles

1. **JobDiva remains the ATS system of record** for ATS-owned jobs, candidates, resumes, submissions, interviews, placements, and ATS workflow history.
2. **Medlivo owns the intelligence and operational overlay**, not a duplicate ATS.
3. **Direct-customer jobs are temporarily Medlivo-owned before ATS creation/write-back is authorized.**
4. **Every derived or AI-assisted fact must preserve provenance.**
5. **Business workflow state and source-system state are separate.**
6. **Permissions attach to actions/capabilities, not pages.**
7. **All consequential approvals are auditable.**
8. **Projected financial values and actual/accounting values are separate. QuickBooks remains the accounting system.**

---

## 2. Existing implementation foundations

The current codebase already contains Phase 1 foundations that must be preserved:

### Job Intelligence
`services/job-intelligence/job_intelligence/models.py`

Existing important models:
- `SourceRef`
- `JobRequirement`
- `JobPreference`
- `NormalizedJob`
- `JobContentSection`
- `JobQualityScore`
- `PublishableJobDraft`

These remain the base for canonical job intelligence.

### Candidate Intelligence
`services/candidate-intelligence/candidate_intelligence/models.py`

Existing important models:
- `CandidateEvidence`
- `LicenseIntelligence`
- `CertificationIntelligence`
- `ResumeIntelligence`
- `MatchingReadiness`
- `CandidateIntelligence`
- `JobDivaCandidateBundle`

These remain the base for canonical candidate intelligence.

### Team Workspace
`services/team-workspace/migrations/005_phase1_operations.sql`

Existing Phase 1 operational tables:
- `ws_job_intake_batch`
- `ws_job_intake_item`
- `ws_customer_job_mapping`
- `ws_weekly_recruiter_goal`
- `ws_weekly_recruiter_snapshot`

These should be extended, not replaced.

---

# 3. Core bounded contexts

Phase 1 uses the following bounded contexts:

1. Identity & Organization
2. Client / Customer
3. Job Intelligence
4. Direct Job Intake
5. Candidate Intelligence
6. Matching
7. Operational Workflow
8. Submission / Interview / Offer Projection
9. Compliance / Start Readiness
10. Assignment / Placement Projection
11. Margin & Economics
12. Approval
13. Provenance / AI Suggestion
14. Audit / Governance

---

# 4. Identity & Organization

## 4.1 Tenant
**Owner:** Team Workspace  
**System of record:** Medlivo AI

Represents the Medlivo operating tenant.

Key fields:
- `tenant_id`
- `name`
- `status`
- timestamps

## 4.2 App User
**Owner:** Team Workspace  
**System of record:** Medlivo AI identity layer

Key fields:
- `user_id`
- `tenant_id`
- `email`
- `display_name`
- `role`
- `team_id`
- `identity_bound`
- `is_active`

Primary business roles:
- Executive
- Delivery Manager
- Recruiter
- Compliance
- System Admin
- Read Only / Observer

A user may hold more than one capability set where explicitly granted.

## 4.3 Team
**Owner:** Team Workspace

Key fields:
- `team_id`
- `tenant_id`
- `name`
- `division`
- `manager_user_id`
- `status`

Primary divisions:
- Nursing & Allied
- Rehabilitation
- Locum Tenens
- Non-Clinical / IT where applicable

---

# 5. Client / Customer domain

## 5.1 Client Account
**Owner:** Team Workspace / Job Intelligence  
**System of record:** Medlivo AI operational master, while accounting details remain in QuickBooks

Purpose:
- normalize customer identity across JobDiva, MSP/VMS, and direct-customer sources
- hold operational defaults and recruiting rules

Key fields:
- `client_id`
- `tenant_id`
- `canonical_name`
- `source_type` = direct | msp_vms | mixed
- `jobdiva_client_id` where available
- `msp_name`
- `vms_name`
- `default_division`
- `default_team_id`
- `default_priority`
- `status`

## 5.2 Client Operational Configuration
**Owner:** Team Workspace  
**System of record:** Medlivo AI

Key fields:
- `client_id`
- `saved_intake_mapping_id`
- `approved_rate_card_reference`
- `default_duration_weeks`
- `default_schedule_patterns`
- `known_msp_fee`
- `required_job_fields`
- `credential_rules`
- `default_recruiter_id`
- `default_team_id`
- `default_priority`
- `public_posting_policy`
- `version`
- `effective_from`
- `effective_to`
- `updated_by`

All customer defaults must be versioned.

---

# 6. Job Intelligence domain

## 6.1 Canonical Job
**Owner:** Job Intelligence  
**System of record:** JobDiva for JobDiva-origin jobs; Medlivo temporarily for direct jobs before ATS creation

The canonical job extends the existing `NormalizedJob`.

Required conceptual fields:

### Identity
- `canonical_job_id`
- `tenant_id`
- `source_system`
- `source_job_id`
- `source_updated_at`

### Classification
- `division`
- `profession`
- `specialty`
- `care_setting`

### Client / location
- `client_id`
- `client_name`
- `facility_name`
- `city`
- `state`
- `postal_code`

### Assignment
- `shift`
- `schedule`
- `start_date`
- `end_date`
- `duration_weeks`
- `openings`

### Commercial source fields
- `bill_rate`
- `bill_rate_state` = confirmed | suggested | unknown
- `rate_unit`
- `pay_rate_min`
- `pay_rate_max`

### Requirements
- `hard_requirements`
- `preferences`
- `required_license_states`

### Content
- `raw_description_text`
- `standardized_internal_jd`
- `public_job_draft`

### Readiness
- `recruiting_readiness`
- `commercial_readiness`
- `public_readiness`
- `job_quality_score`

### Source lineage
- `source_fields`
- `source_document_reference`
- `provenance_summary`

## 6.2 Job Requirement
Existing `JobRequirement` remains authoritative.

Kinds include:
- license
- certification
- experience
- skill
- setting
- schedule
- education
- credential
- other

Additional Phase 1 attributes to consider:
- `provenance_id`
- `confidence`
- `review_status`

## 6.3 Job Preference
Existing `JobPreference` remains authoritative.

## 6.4 Standardized Job Description
**Owner:** Job Intelligence

Three content layers must remain separate:

1. **Raw Source JD**
2. **Medlivo Standardized Internal JD**
3. **Approved Public JD**

Key fields:
- `job_id`
- `content_version`
- `template_id`
- `sections`
- `generated_by` = rule | ai | human
- `model_version` where AI is used
- `review_status`
- `approved_by`
- `approved_at`

---

# 7. Direct Job Intake domain

## 7.1 Job Intake Batch
**Existing table:** `ws_job_intake_batch`

Purpose:
- one uploaded customer file/import event

Existing fields remain:
- batch ID
- tenant/team
- uploaded by
- customer
- division
- filename
- mapping
- row counts
- status

Recommended extensions:
- `client_id`
- `source_type`
- `mapping_version`
- `ai_processing_status`
- `review_owner_user_id`
- `approved_by`
- `approved_at`
- `source_file_hash`
- `correlation_id`

## 7.2 Job Intake Item
**Existing table:** `ws_job_intake_item`

Represents one source row.

Existing fields remain:
- source row
- normalized job
- validation errors
- duplicate job
- status
- created job

Recommended extensions:
- `extracted_values`
- `ai_suggestions`
- `conflicts`
- `missing_fields`
- `final_approved_values`
- `standardized_jd_version`
- `bill_rate_state`
- `recruiting_readiness`
- `commercial_readiness`
- `reviewed_by`
- `reviewed_at`

## 7.3 Customer Job Mapping
**Existing table:** `ws_customer_job_mapping`

Purpose:
- reusable mapping between customer spreadsheet columns and Medlivo canonical job fields

Recommended additions:
- `mapping_version`
- `sample_headers_hash`
- `approved_by`
- `effective_from`
- `is_active`

---

# 8. Candidate Intelligence domain

## 8.1 Canonical Candidate
**Owner:** Candidate Intelligence  
**System of record:** JobDiva

Extends the existing `CandidateIntelligence`.

Conceptual fields:
- `canonical_candidate_id`
- `source_candidate_id`
- `source_updated_at`
- full name
- contact data
- profession
- specialty
- city/state
- licenses
- certifications
- resumes
- primary resume
- care settings
- clinical skills
- experience evidence
- availability evidence
- travel/location evidence
- rate expectation where available
- matching readiness
- freshness
- evidence
- provenance

## 8.2 Candidate Evidence
Existing `CandidateEvidence` remains the canonical evidence primitive.

Phase 1 provenance types should be expanded to support:
- jobdiva_profile
- jobdiva_license
- jobdiva_certification
- jobdiva_resume
- candidate_confirmation
- recruiter_confirmation
- manager_confirmation
- approved_internal_rule

## 8.3 License / Certification Intelligence
Existing models remain authoritative.

---

# 9. Matching domain

## 9.1 Match Result
**Owner:** Matching Engine  
**System of record:** Medlivo AI

Key fields:
- `match_id`
- `job_id`
- `candidate_id`
- `score`
- `band`
- `hard_gate_status`
- `hard_gate_failures`
- `component_scores`
- `strengths`
- `gaps`
- `missing_information`
- `explanation`
- `model/rules version`
- `calculated_at`

No AI reranker may override a confirmed hard-gate failure.

## 9.2 Recruiter Match Feedback
Key fields:
- `match_id`
- `recruiter_user_id`
- `feedback` = good_match | possible | not_fit
- `reason_code`
- `notes`
- timestamp

This is operational learning data, not an ATS candidate status.

---

# 10. Operational Workflow domain

## 10.1 Job Operational Overlay
**Owner:** Team Workspace  
**System of record:** Medlivo AI

This is critical because it separates Medlivo operational control from JobDiva source state.

Key fields:
- `job_id`
- `client_priority` = high | normal | low
- `job_priority` = hot | priority | standard | hold
- `priority_reason`
- `team_id`
- `recruiter_user_id`
- `manager_note`
- `next_action`
- `due_at`
- `operational_status`
- `assigned_by`
- `assigned_at`
- `version`

## 10.2 Work Item
Represents a concrete actionable unit.

Key fields:
- `work_item_id`
- `object_type` = job | candidate | submission | interview | offer | start | assignment | intake | margin
- `object_id`
- `owner_user_id`
- `team_id`
- `priority`
- `action_type`
- `due_at`
- `status`
- `completed_at`
- `created_from` = rule | manager | system | ai_recommendation
- `reason`

## 10.3 Ownership History
Key fields:
- object type/id
- previous owner
- new owner
- changed by
- reason
- timestamp

Ownership changes must never be silent.

---

# 11. Submission / Interview / Offer projection domain

These are **projections of JobDiva ATS records**, not independent Medlivo ATS workflows.

## 11.1 Submission Projection
System of record: JobDiva

Fields:
- source submission ID
- job ID
- candidate ID
- recruiter
- submitted at
- source status
- client/MSP status
- age in stage
- next action metadata from Medlivo overlay

## 11.2 Interview Projection
System of record: JobDiva

Fields:
- source interview ID
- submission/job/candidate
- scheduled/completed timestamps
- source status
- outcome
- outcome pending flag
- next action metadata

## 11.3 Offer Projection
System of record: JobDiva where represented

Fields:
- source offer ID
- job/candidate
- offer date
- response status
- accepted/declined/pending
- decline reason where available
- expected start

Medlivo may maintain operational next-action metadata separately.

---

# 12. Compliance & Start Readiness domain

## 12.1 Start Readiness Record
**Owner:** Team Workspace / Compliance workflow  
**Source facts:** JobDiva and approved Medlivo operational inputs

Key fields:
- `start_readiness_id`
- `candidate_id`
- `job_id`
- `placement_id` where available
- `expected_start_date`
- `readiness_status` = ready | in_progress | at_risk | blocked | started
- `readiness_percent`
- `critical_blocker_count`
- `next_action_owner_id`

## 12.2 Readiness Requirement
Key fields:
- requirement type
- required/optional
- status = complete | pending | missing | expiring
- due date
- source/provenance
- blocker flag
- owner

Readiness status takes precedence over percentage.

---

# 13. Assignment / Placement projection domain

## 13.1 Placement / Assignment Projection
**System of record:** JobDiva

Key fields:
- source placement/assignment ID
- candidate
- job
- client
- recruiter
- start date
- expected end date
- actual end date
- status = starting | active | extension_pending | ending_soon | completed | ended_early | cancelled
- extension status
- end reason where available

Medlivo owns only derived operational alerts and next-action metadata.

---

# 14. Margin & Economics domain

## 14.1 Cost Assumption Set
**Owner:** Margin/Economics domain  
**System of record:** Medlivo AI

Versioned configuration:
- `assumption_set_id`
- `version`
- `effective_from`
- `effective_to`
- payroll burden assumptions
- workers’ compensation assumptions
- insurance allocation
- factoring assumptions where used
- MSP/VMS fee rules
- other direct-cost rules
- margin thresholds
- approval thresholds
- commission rule version
- created/approved by

Delivery Managers may view and apply these. Only authorized Executive/System Admin users may change master assumptions.

## 14.2 Margin Calculation Snapshot
**Owner:** Margin Engine

Key fields:
- `margin_snapshot_id`
- `job_id`
- `candidate_id`
- `recruiter_user_id`
- `version`
- `assumption_set_id`
- `bill_rate`
- `bill_rate_state`
- pay package fields
- projected hours
- loaded cost
- projected profit per unit
- projected assignment profit
- margin percentage
- commissionable net profit basis
- projected recruiter commission
- status = draft | negotiated | approval_required | approved | finalized | superseded
- created by
- created at

Prior versions are immutable.

## 14.3 Commission Record
Phase 1 should distinguish:
- projected commission
- approved/earned commission

Key fields:
- recruiter
- placement/assignment
- commissionable net profit
- rate = 3%
- projected amount
- approved amount
- quarter
- approval state

QuickBooks remains outside this domain.

---

# 15. Approval domain

## 15.1 Approval Request
**Owner:** Team Workspace

Generic approval entity.

Key fields:
- `approval_id`
- `approval_type`
- `object_type`
- `object_id`
- `requested_by`
- `required_authority` = delivery_manager | executive | system_admin
- `status` = pending | approved | rejected | cancelled
- `reason`
- `decision_notes`
- `decided_by`
- `decided_at`

Approval types include:
- direct_job_release
- standardized_jd_exception
- missing_data_acceptance
- suggested_bill_rate
- margin_manager_exception
- margin_executive_exception
- recruiter_reassignment
- public_job_release
- future ATS writeback

---

# 16. AI Suggestion & Provenance domain

## 16.1 Provenance Record
Key fields:
- `provenance_id`
- `object_type`
- `object_id`
- `field_path`
- `value_hash/reference`
- `source_type`
- `source_reference`
- `confidence`
- `captured_at`

Trust labels:
- source_confirmed
- extracted_from_source_jd
- customer_spreadsheet
- resume_evidence
- historical_approved_rule
- ai_suggested
- manager_approved
- candidate_confirmed
- recruiter_confirmed
- unknown
- conflict

## 16.2 AI Suggestion
Key fields:
- `suggestion_id`
- target object/field
- suggested value
- source basis
- confidence
- model/provider/version
- prompt/policy version reference
- created at
- status = proposed | accepted | modified | rejected | expired
- reviewed by
- reviewed at

AI suggestions never become authoritative solely because they were generated.

---

# 17. Audit domain

## 17.1 Audit Event
**Owner:** Team Workspace / platform governance

Key fields:
- `audit_event_id`
- `tenant_id`
- actor user
- actor role
- action
- object type
- object ID
- before summary
- after summary
- reason
- source IP/session correlation where appropriate
- correlation ID
- timestamp

Audit events required for:
- direct job approval
- job priority change
- hot-job change
- recruiter assignment/reassignment
- JD approval
- bill-rate suggestion approval
- margin approval
- cost-assumption changes
- user/role changes
- JobDiva write-back when eventually enabled

---

# 18. Entity relationship summary

```
Tenant
 ├── Teams
 │    └── App Users
 │
 ├── Client Accounts
 │    ├── Client Operational Config Versions
 │    └── Customer Job Mappings
 │
 ├── Canonical Jobs
 │    ├── Job Requirements / Preferences
 │    ├── Standardized JD Versions
 │    ├── Job Operational Overlay
 │    ├── Work Items
 │    ├── Match Results
 │    ├── Margin Snapshots
 │    ├── Approval Requests
 │    └── Provenance / AI Suggestions
 │
 ├── Canonical Candidates
 │    ├── Licenses
 │    ├── Certifications
 │    ├── Resume Intelligence
 │    ├── Evidence
 │    ├── Match Results
 │    └── Work Items
 │
 ├── Intake Batches
 │    └── Intake Items
 │         └── Approved Canonical Job
 │
 ├── JobDiva Projections
 │    ├── Submissions
 │    ├── Interviews
 │    ├── Offers
 │    └── Placements / Assignments
 │
 ├── Start Readiness
 │    └── Readiness Requirements
 │
 └── Audit Events
```

---

# 19. System-of-record matrix

| Entity / Fact | Authoritative System |
| --- | --- |
| Candidate identity | JobDiva |
| Candidate resume | JobDiva |
| Candidate license/cert source facts | JobDiva |
| JobDiva-origin job | JobDiva |
| Direct customer job before ATS creation | Medlivo AI |
| Submission | JobDiva |
| Interview | JobDiva |
| Offer where available | JobDiva |
| Placement / assignment | JobDiva |
| Canonical normalized job intelligence | Medlivo AI |
| Canonical candidate intelligence | Medlivo AI |
| Match score / explanation | Medlivo AI |
| Hot / priority job overlay | Medlivo AI |
| Recruiter assignment overlay | Medlivo AI |
| Direct intake mapping / review | Medlivo AI |
| Standardized internal JD | Medlivo AI |
| Public approved JD | Medlivo AI |
| Margin calculation snapshot | Medlivo AI |
| Company cost assumptions | Medlivo AI |
| Invoice / A/R / accounting | QuickBooks |
| Approval history | Medlivo AI |
| Audit history | Medlivo AI |

---

# 20. Lifecycle states

## Canonical Job
Source state:
- open
- on_hold
- closed
- cancelled
- unknown

Medlivo operational state:
- unreviewed
- recruiting_ready
- priority
- hot
- hold
- closed

Do not collapse source status and Medlivo operational status into one field.

## Direct Intake Item
- ready
- review
- duplicate
- approved
- synced
- rejected
- failed

## Bill Rate
- confirmed
- suggested
- unknown

## Recruiting Readiness
- not_ready
- review
- ready

## Commercial Readiness
- not_ready
- review
- ready

## Approval
- pending
- approved
- rejected
- cancelled

## Margin Snapshot
- draft
- negotiated
- approval_required
- approved
- finalized
- superseded

---

# 21. RBAC ownership by entity

| Domain | Executive | Delivery Manager | Recruiter | Compliance | System Admin |
| --- | --- | --- | --- | --- | --- |
| Canonical Job source facts | View | Review exceptions | View | View | Configure system |
| Customer priority | View/strategic | Set | View | View | Admin override |
| Hot-job priority | View | Set | View | View | Admin override |
| Recruiter assignment | View | Set/reassign | Own work | View | Admin override |
| Direct intake | View | Create/review/approve | No | View if needed | Admin |
| Standardized JD | View | Review exceptions | Consume | View | Admin |
| Candidate intelligence | View | Team view | Assigned/allowed | Relevant view | Admin |
| Match results | View | Team view | Use/feedback | Limited | Admin |
| Start readiness | Exception view | Team control | Assigned starts | Primary operational role where assigned | Admin |
| Margin calculation | Summary | Review/approve | Create/negotiate | No | Configure |
| Master cost assumptions | View | View | No | No | Edit; Executive authorization |
| Margin executive exception | Approve | Escalate | Request | No | Admin |
| Audit | View permitted scope | Operational scope | Own actions | Own scope | Full |

Server-side permission checks are mandatory.

---

# 22. Recommended database implementation sequence

Do not build all entities at once.

### Migration A — Operational overlays
Add:
- client account / operational config
- job operational overlay
- ownership history
- generic work item
- approval request
- provenance / AI suggestion

### Migration B — Intake extensions
Extend:
- `ws_job_intake_batch`
- `ws_job_intake_item`
- `ws_customer_job_mapping`

### Migration C — Margin domain
Add:
- cost assumption set
- margin snapshot
- commission record

### Migration D — Readiness domain
Add:
- start readiness
- readiness requirements

Each migration must include:
- tenant-safe foreign keys
- indexes
- check constraints
- runtime grants
- tests
- audit hooks where applicable

---

# 23. API ownership

Suggested service/API ownership:

| Resource | Owning Service |
| --- | --- |
| Canonical jobs | Job Intelligence |
| Standardized JD | Job Intelligence |
| Canonical candidates | Candidate Intelligence |
| Matches | Matching Engine |
| Client operational config | Team Workspace |
| Job priority / hot overlay | Team Workspace |
| Direct intake | Team Workspace + Job Intelligence |
| Work items | Team Workspace |
| Approvals | Team Workspace |
| Margin calculations | Margin domain service/module |
| Executive aggregates | Team Workspace / API projection |
| Delivery Manager aggregates | Team Workspace |
| Recruiter queue | Team Workspace |
| Public jobs | Apps API |

---

# 24. Immediate implementation slice

The first enterprise vertical slice after this document should be:

## Priority Job + Direct Intake foundation

### Source
- JobDiva job or direct intake item

### Data model
- Canonical Job
- Job Operational Overlay
- Client Account
- Intake Batch / Item
- Provenance
- Approval Request

### Business rules
- source status separate from Medlivo priority
- Delivery Manager can mark Hot/Priority/Standard/Hold
- direct intake requires manager approval
- AI suggestion remains non-authoritative until accepted
- bill rate may remain unknown
- standardized JD preserves source provenance

### API
- get canonical job
- update Medlivo priority
- assign recruiter
- review intake item
- approve intake item
- get provenance / conflicts

### RBAC
- Delivery Manager primary action authority
- Executive visibility
- Recruiter read/assigned scope

### Audit
- priority change
- assignment
- intake approval
- AI suggestion acceptance/rejection

### Acceptance tests
- JobDiva-origin job
- direct-customer job
- missing bill rate
- missing JD
- conflicting license/specialty
- duplicate row
- recruiter reassignment
- unauthorized recruiter attempt

Only after this vertical slice is implemented should its production UI be considered complete.

---

# 25. Definition of done

The Phase 1 domain model is considered implemented only when:

- canonical entity IDs are stable
- system-of-record ownership is enforced
- source and derived data are separable
- provenance is queryable
- AI suggestions are reviewable
- Delivery Manager approvals are persisted
- RBAC is server-side
- audit events exist
- migrations are tested
- APIs expose domain resources
- UI consumes APIs rather than embedded/sample logic

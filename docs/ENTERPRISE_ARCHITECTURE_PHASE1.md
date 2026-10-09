# Medlivo AI Platform — Enterprise Architecture

**Status:** Phase 1 governing architecture  
**Repository:** `pks-alt/Medlivo-AI-Platform`  
**Purpose:** Define the enterprise platform boundary, systems of record, services, workflows, data ownership, AI governance, RBAC, APIs, auditability, and implementation rules before additional UI work.

---

## 1. Architecture principles

### 1.1 JobDiva remains the operational ATS system of record
JobDiva remains authoritative for:
- candidate identity
- resumes
- jobs/requisitions originating in JobDiva
- recruiter ownership where represented in JobDiva
- submissions
- interviews
- placements
- ATS statuses
- ATS operational history

Medlivo AI must not become a second ATS.

### 1.2 Medlivo AI is the intelligence, control, and workflow layer
Medlivo AI owns:
- canonical normalization
- Job Intelligence
- Candidate Intelligence
- evidence and provenance
- matching and ranking
- Medlivo internal priority
- hot-job designation
- manager review and approvals
- direct-customer job intake before ATS creation
- standardized Medlivo job descriptions
- recruiter/manager work queues
- margin calculation snapshots
- approval workflows
- analytics and operational dashboards
- public-safe approved job content
- platform audit and AI decision trace

### 1.3 Human approval governs consequential actions
AI may:
- extract
- normalize
- classify
- summarize
- identify gaps
- identify conflicts
- suggest values
- draft standardized JDs
- rank
- recommend
- prioritize

Humans approve:
- direct-job publication/release to recruiters
- authoritative correction of uncertain job data
- ownership changes
- submissions
- pay-package finalization where policy requires
- below-threshold margin exceptions
- JobDiva write-back
- public job publication
- other consequential recruiting actions

### 1.4 Build vertical slices, not disconnected pages
Every feature must be implemented end to end:

`source → ingestion → normalization → business rules → permissions → API → workflow/UI → audit → tests → deployment`

A UI panel without the underlying service, data model, permissions, and API is not considered implemented.

---

## 2. Enterprise operating model

Medlivo has four distinct access layers.

### 2.1 Executive Management
Typical users: PK, Rey, Vamsi, Lael.

Primary responsibility:
- company-wide visibility
- strategic focus
- major exceptions
- executive approvals
- division/client/recruiter oversight

Primary experience:
- Medlivo Command Center

Executives should not normally perform day-to-day job intake, recruiter reassignment, or candidate follow-up.

### 2.2 Delivery Manager
Primary responsibility:
- operational control
- customer/MSP focus
- hot-job designation
- recruiter workload
- recruiter assignment/reassignment
- direct-customer job intake
- AI intake/JD exception review
- margin approval within authority
- operational escalations
- start-risk management

Primary experience:
- Delivery Manager Workspace

### 2.3 Recruiter
Primary responsibility:
- execute assigned work
- search/match candidates
- engage candidates
- maintain next action/due date
- submit qualified candidates
- coordinate interviews/offers
- negotiate pay
- use the margin engine
- support candidate through start

Primary experience:
- Recruiter Daily Workspace

### 2.4 System Administrator
This is a permission role, not a business hierarchy level.

Responsibilities:
- users/access
- role mappings
- integration configuration
- platform settings
- margin master assumptions
- audit access
- environment/system controls

An Executive user may also hold System Admin permissions.

---

## 3. Permanent architecture layers

### Layer A — Source Systems and External Inputs

#### JobDiva
Primary ATS source.

Phase 1 mode:
- read-only
- historical backfill
- delta synchronization
- reconciliation
- webhook-triggered refresh where supported

Future write-back:
- only after exact JobDiva APIs are authorized and acceptance-tested

#### Direct Customer Inputs
Supported Phase 1 sources:
- XLSX
- CSV
- manual single-job entry

Typical contents:
- job title
- customer/facility
- location
- openings
- start date
- shift/schedule
- duration
- license/certifications
- experience
- bill rate
- notes
- external job ID

#### QuickBooks
Remains the accounting system for:
- invoicing
- A/R
- collections
- accounting
- financial statements

Medlivo AI must not duplicate QuickBooks.

#### Website / External Experience
Consumes approved platform APIs.  
No recruiting business logic should live independently in the website repository.

---

### Layer B — Integration and Ingestion

Primary components:
- `services/jobdiva-connector`
- `apps/workers`
- direct-job intake service inside `services/team-workspace` and/or dedicated intake service

Responsibilities:
- source authentication
- read-only JobDiva ingestion
- delta synchronization
- historical backfill
- retry and checkpointing
- source-ID preservation
- duplicate-source protection
- direct file ingestion
- secure staging of uploaded files
- ingestion event emission
- failure telemetry

Requirements:
- idempotent sync
- stable source IDs
- no duplicate canonical records from repeat ingestion
- raw source payload retained only according to defined retention/security rules
- no sensitive source payloads written to logs

---

### Layer C — Canonical Data and Intelligence

Primary components:
- `services/job-intelligence`
- `services/candidate-intelligence`
- `packages/taxonomy`

#### Job Intelligence responsibilities
- canonical job model
- source-field normalization
- healthcare taxonomy
- division/profession/specialty normalization
- requirement extraction
- care-setting normalization
- schedule normalization
- location normalization
- rate field normalization
- required vs preferred distinction
- source provenance
- missing-field detection
- conflict detection
- job readiness
- JD standardization
- public-safe job projection

#### Candidate Intelligence responsibilities
- canonical candidate model
- profession/specialty normalization
- resume evidence
- license intelligence
- certification intelligence
- setting/experience evidence
- availability evidence
- location/travel evidence
- rate expectation where available
- profile freshness
- provenance
- missing-data indicators

Unknown data must remain unknown unless policy explicitly permits suggestion/inference.

---

### Layer D — AI Intelligence Services

AI is embedded inside controlled domain services, not implemented as an isolated chatbot.

#### AI Job Intake
For direct-customer spreadsheet uploads:
1. detect customer template
2. map source columns to Medlivo fields
3. reuse saved customer mappings
4. extract job values
5. normalize values
6. identify duplicates
7. identify conflicts
8. identify missing fields
9. provide defensible suggestions
10. generate standardized JD
11. route exceptions to Delivery Manager
12. require approval before authoritative release

#### AI JD Standardization
Maintain three representations:

1. **Raw Source JD**
   - unchanged source evidence

2. **Medlivo Standardized Internal JD**
   - structured, consistent recruiter/manager representation

3. **Public Job Description**
   - separately approved public-safe content

AI may generate a standardized JD from structured source facts when the JD is missing.

AI must not invent:
- bill rates
- licenses
- certifications
- guaranteed hours
- start dates
- experience requirements
- client requirements

unless a value is explicitly marked as a suggestion and subsequently approved.

#### AI Missing-Data Suggestions
Suggestion sources may include:
- approved customer rate card
- previous approved jobs from the same customer
- same specialty/location
- saved customer rules
- authoritative historical Medlivo data

Every suggestion must retain:
- suggestion value
- source basis
- confidence
- timestamp
- model/version
- reviewer decision

#### Bill Rate Policy
Possible states:
- Confirmed
- Suggested
- Unknown

If no defensible source exists:
- leave Bill Rate unknown
- never invent a number

Separate:
- **Recruiting Ready**
- **Commercially Ready**

A job may be Recruiting Ready while Bill Rate remains pending, but final pay-package approval cannot occur without an approved commercial basis.

---

### Layer E — Matching and Ranking

Primary component:
- `services/matching-engine`

Pipeline:
1. hard gates
2. deterministic scoring
3. semantic/vector retrieval
4. AI reranking
5. explanation
6. shortlist

Hard gates may include:
- profession
- required specialty
- required state license
- required certification
- other confirmed non-negotiable constraints

AI cannot silently override a confirmed hard-gate failure.

Each match should expose:
- score
- band
- reasons
- missing information
- hard-gate result
- evidence/provenance

---

### Layer F — Operational Workflow and Collaboration

Primary components:
- `services/team-workspace`
- `apps/recruiter-web`

The workflow service owns Medlivo-specific operating context that should not be forced into JobDiva.

#### Medlivo Operational Metadata
Examples:
- customer priority
- job priority
- hot-job flag
- recruiter/team assignment
- manager note
- next action
- due date
- review state
- approval state
- Medlivo ownership metadata
- intake batch state
- standardized JD approval
- margin approval state

#### MSP/VMS Job Flow
`JobDiva → ingestion → canonical job → Medlivo priority overlay → Delivery Manager focus/assignment → recruiter queue`

JobDiva remains source of the job.  
Medlivo priority is a separate internal layer.

#### Direct Customer Job Flow
`XLSX/CSV/manual entry → AI extraction → normalization → saved customer mapping → duplicate/conflict checks → missing-data suggestions → standardized JD → Delivery Manager review → approval → recruiter queue → future JobDiva creation/write-back when authorized`

---

## 4. Delivery Manager architecture

The Delivery Manager Workspace is a business workflow, not merely a dashboard.

Core capabilities:
- priority customers
- MSP/VMS focus
- hot jobs
- unassigned jobs
- recruiter workload
- recruiter reassignment
- jobs with no submission
- strong matches waiting
- direct-job intake
- AI intake review
- AI JD review
- missing bill-rate review
- operational exceptions
- margin approvals
- start-risk visibility
- ending-soon assignment visibility

### Delivery Manager authority
Can:
- set customer priority
- set job priority
- mark Hot / Priority / Standard / Hold
- assign/reassign recruiters
- approve direct-customer job intake
- approve AI normalized/standardized job data
- correct direct-job operational details
- close/hold/cancel direct jobs
- approve margin within configured authority

Cannot:
- change master company cost assumptions unless separately granted System Admin permission
- silently override Executive-only margin thresholds
- bypass audit
- write to JobDiva unless an explicitly approved write-back capability exists

---

## 5. Executive architecture

The Executive Command Center aggregates operational data from domain APIs.

It should consume, not own, business logic.

Core views:
- company operating health
- recruiter performance
- job aging
- candidate pipeline
- client/MSP responsiveness
- compliance/start readiness
- submissions/interviews/offers
- starts/assignments
- margin summaries
- major exceptions
- division comparisons

Executives may drill into Delivery Manager and Recruiter workflows based on RBAC.

---

## 6. Recruiter architecture

Recruiter Daily Workspace consumes assigned operational records.

Core workflow:
`priorities → jobs → candidates → match → engagement → submission → interview → offer → pay negotiation → margin check → start`

Recruiters should not:
- bulk-upload direct customer jobs
- approve their own below-threshold margin exceptions
- edit master client configuration
- reassign other recruiters’ work without authority
- edit company-wide cost assumptions

---

## 7. Margin and economics architecture

The margin engine is not a spreadsheet embedded in a page. It is a versioned business service.

### Inputs
Examples:
- bill rate
- MSP/VMS fee
- pay rate
- OT assumptions
- stipends where applicable
- guaranteed/projected hours
- payroll burden
- workers’ compensation
- insurance allocation where applicable
- compliance/direct costs
- factoring assumptions where used
- other approved direct costs

### Outputs
- loaded cost
- projected profit
- margin %
- projected assignment profit
- commissionable net profit basis
- projected recruiter commission

### Versioning
Every negotiation calculation must create a snapshot:
- version
- input values
- assumptions version
- output values
- actor
- timestamp
- status
- approval

Never overwrite prior calculation history.

### Approval bands
Example governance:
- within policy → recruiter can finalize
- warning band → Delivery Manager approval
- below manager authority → Executive approval

### Commission
Recruiter commission:
- 3% of approved commissionable net profit basis
- projected commission and approved/earned commission must remain distinct

### Configuration ownership
Delivery Manager:
- high visibility
- approval usage
- exception handling

Executive/System Admin:
- master thresholds
- master burden assumptions
- company-wide cost assumptions
- commission rules

---

## 8. RBAC and authorization

Required roles:
- Executive
- Delivery Manager
- Recruiter
- Compliance
- System Admin
- Read Only / Executive Observer where needed

Permissions must be capability-based, not page-based.

Examples:
- `job.priority.set`
- `job.direct.create`
- `job.direct.approve`
- `job.reassign`
- `job.jd.approve`
- `margin.review`
- `margin.approve.manager`
- `margin.approve.executive`
- `user.provision`
- `config.margin.update`
- `integration.jobdiva.manage`

Server-side authorization is mandatory.  
Hiding a UI control is not authorization.

---

## 9. Core data domains

### Canonical Job
Key concepts:
- canonical_job_id
- source_system
- source_job_id
- client/facility
- division
- profession
- specialty
- location
- schedule
- start date
- duration
- openings
- required qualifications
- preferred qualifications
- bill-rate state/value
- raw JD reference
- standardized JD
- public JD projection
- readiness states
- provenance
- created/updated timestamps

### Canonical Candidate
Key concepts:
- canonical_candidate_id
- JobDiva candidate ID
- profession/specialty
- location
- licenses
- certifications
- experience
- settings
- availability evidence
- rate expectation
- resume evidence
- provenance
- freshness

### Operational Job Overlay
Medlivo-owned:
- customer priority
- job priority
- hot flag
- team assignment
- recruiter assignment
- manager note
- next action
- due date
- hold/close state
- review state

### Intake Batch
- customer
- source file
- source row
- mapping version
- extracted values
- AI suggestions
- conflicts
- final approved values
- reviewer
- approval timestamp

### Margin Snapshot
- job
- candidate
- recruiter
- calculation version
- assumptions version
- bill rate
- pay package
- loaded cost
- margin
- projected profit
- commission basis
- approval state

### Audit Event
- actor
- role
- action
- object type
- object ID
- before/after summary
- reason
- timestamp
- correlation ID

---

## 10. Provenance model

Every material job/candidate fact should carry provenance.

Suggested trust labels:
- Source Confirmed
- Extracted from Source JD
- Customer Spreadsheet
- Resume Evidence
- Historical Approved Rule
- AI Suggested
- Manager Approved
- Candidate Confirmed
- Unknown
- Conflict

The UI may simplify labels, but the underlying data model must preserve the full evidence chain.

---

## 11. API architecture

### Internal APIs
Internal APIs should expose domain resources, not raw database tables.

Examples:
- `/jobs`
- `/jobs/{id}`
- `/jobs/{id}/priority`
- `/jobs/{id}/standardized-jd`
- `/jobs/{id}/approvals`
- `/candidates/{id}`
- `/matches`
- `/intake/batches`
- `/intake/batches/{id}/review`
- `/margin/calculations`
- `/margin/approvals`
- `/manager/focus`
- `/manager/workload`
- `/executive/overview`

### Public APIs
Public APIs expose only approved public-safe projections.

No internal commercial terms, manager notes, source payloads, or private candidate data.

---

## 12. Event and worker architecture

Use background workers for:
- JobDiva backfill
- JobDiva delta sync
- candidate enrichment
- resume processing
- job normalization
- JD standardization
- match recalculation
- large intake batch processing
- derived analytics
- retryable downstream updates

Events should include:
- correlation ID
- source ID
- canonical ID
- event type
- timestamp
- version

Workers must be idempotent.

---

## 13. Security and privacy

Required controls:
- Google Workspace authentication for internal users
- server-side RBAC
- least privilege
- private internal services where appropriate
- no secrets in client code
- no sensitive payloads in logs
- TLS in transit
- encrypted storage
- audit logs
- session expiry/revocation
- disabled-user denial
- tenant/team boundary enforcement
- controlled file-upload retention
- no uncontrolled AI access to source credentials

---

## 14. Observability

The platform must make failures visible without exposing technical noise to business users.

Engineering observability:
- sync success/failure
- latency
- queue depth
- retry counts
- worker failures
- ingestion throughput
- API errors
- AI service failures
- match calculation failures
- audit anomalies

Business visibility:
- “JobDiva data delayed”
- “6 direct jobs need review”
- “3 pay packages awaiting approval”
- “2 starts at risk”

Do not expose low-level infrastructure errors to recruiters/managers.

---

## 15. Data quality and readiness

Each job should have at least two readiness concepts.

### Recruiting Readiness
Enough information exists to begin recruiting.

### Commercial Readiness
Enough approved commercial information exists to finalize compensation/margin.

Possible additional readiness:
- Submission Ready
- Start Ready
- Public Ready

Readiness is rule-based and explainable.

---

## 16. Customer-specific configuration

Customer profile may contain:
- source type
- default division
- saved spreadsheet mapping
- standard duration
- standard schedule patterns
- approved rate card
- known MSP/VMS fee
- required fields
- credential rules
- default team
- default recruiter
- default priority
- JD template preferences
- public-posting rules

All customer defaults must be versioned and auditable.

---

## 17. Direct-customer job governance

Delivery Manager / designated Operations user:
- uploads file
- reviews AI extraction
- resolves conflicts
- approves final job
- assigns priority
- assigns recruiter/team

AI:
- assists
- never becomes final authority

Original source file and row lineage must remain recoverable according to retention policy.

---

## 18. JobDiva governance

For JobDiva jobs:
- ingest source job
- preserve source IDs
- normalize canonical job
- create Medlivo standardized JD
- add Medlivo priority overlay
- do not overwrite JobDiva source data in Phase 1
- route only low-confidence/conflicting jobs to Delivery Manager review

High-confidence standardization should not require human approval for every JobDiva job.

---

## 19. Public job governance

A public job is a projection, not the canonical internal job.

Before publication:
- manager approval
- public-safe content
- confidential fields excluded
- commercial/internal notes excluded
- source lineage retained

Website consumes the approved Career Jobs API.

---

## 20. Testing strategy

Every vertical slice requires:

### Unit tests
- normalization rules
- hard gates
- margin formulas
- approval logic
- permissions

### Integration tests
- JobDiva ingestion
- direct file intake
- API/service boundaries
- worker retries
- RBAC
- audit creation

### Acceptance tests
Representative workflows across:
- Nursing & Allied
- Rehabilitation
- Locum Tenens

### Security tests
- unauthorized access
- cross-team access
- disabled user
- expired session
- duplicate/replay submissions
- malicious file input
- injection and unsafe redirects
- AI prompt/data isolation where applicable

---

## 21. Deployment architecture

Current target:
- Google Cloud
- Cloud Run services
- Cloud SQL/PostgreSQL
- secure secrets management
- CI/CD from canonical GitHub repository
- environment separation

Environments:
- local/dev
- staging
- production

No production behavior should depend on static preview HTML.

---

## 22. Repository ownership

Current canonical components:

| Path | Responsibility |
| --- | --- |
| `apps/recruiter-web` | Executive, Delivery Manager, Recruiter web experiences |
| `apps/api` | Platform/public API surface |
| `services/jobdiva-connector` | JobDiva read integration |
| `services/job-intelligence` | Job normalization, JD standardization, readiness |
| `services/candidate-intelligence` | Candidate canonical intelligence |
| `services/matching-engine` | Hard gates, ranking, explanation |
| `services/team-workspace` | RBAC, operational workflow, priorities, approvals |
| `apps/workers` | Background processing |
| `packages/taxonomy` | Healthcare normalization |
| `packages/*` | Shared models/auth/UI/contracts |
| `infrastructure/*` | Deployment and cloud infrastructure |

---

## 23. Phase 1 architecture boundary

Phase 1 should deliver the enterprise foundation required for trusted operations.

Included:
- JobDiva read integration
- canonical job/candidate intelligence
- direct-customer job intake
- AI spreadsheet mapping
- missing/conflict detection
- standardized JD
- provenance
- Delivery Manager review/approval
- customer/job priority
- hot jobs
- recruiter assignment
- recruiter workload
- matching foundation
- operational follow-ups
- margin engine and approval workflow
- Executive/Delivery Manager/Recruiter RBAC
- audit
- observability

Not required for Phase 1:
- autonomous candidate outreach
- autonomous submission
- unrestricted JobDiva write-back
- predictive drop-off models
- fully autonomous priority changes
- replacing QuickBooks
- replacing JobDiva

---

## 24. Enterprise implementation rule

Before any new page or widget is added, document:

1. system of record
2. canonical data model
3. owning service
4. API contract
5. RBAC permission
6. business rules
7. AI policy
8. approval policy
9. audit event
10. acceptance test

Only then should the UI be implemented.

This document is the governing architecture for future Phase 1 product work.

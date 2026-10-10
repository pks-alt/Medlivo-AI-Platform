# Medlivo AI Platform — Architecture

> Permanent engineering operating model: `docs/ENGINEERING_OPERATING_MODEL.md`  
> Current platform state: `docs/CURRENT_PLATFORM_STATE.md`  
> Phase 1 governing enterprise blueprint: `docs/ENTERPRISE_ARCHITECTURE_PHASE1.md`

## Product boundary

### JobDiva is the ATS and operational system of record
JobDiva owns operational recruiting records:
- candidates
- resumes
- jobs/requisitions
- recruiter ownership where represented
- submissions
- interviews
- placements
- ATS statuses and operational history

### Medlivo AI Platform is the intelligence and workflow-assist layer
Medlivo AI owns:
- canonical normalization
- Job Intelligence
- Candidate Intelligence
- evidence/provenance
- hard-gate eligibility
- matching and ranking
- explanations
- recruiter prioritization
- manager review and approvals
- analytics and productivity views
- public-safe approved job content

It must not become a second ATS.

## Permanent layers

### 1. ATS Integration
Path: `services/jobdiva-connector`, `apps/workers`

Responsibilities:
- authenticated read-only JobDiva access in Phase 1
- delta sync
- historical backfill
- merge/deletion reconciliation
- webhook-triggered refresh
- future approved write-back only after vendor acceptance

### 2. Intelligence
Paths:
- `services/job-intelligence`
- `services/candidate-intelligence`
- `packages/taxonomy`

Responsibilities:
- normalize source fields
- preserve evidence
- healthcare taxonomy
- infer only where policy explicitly permits
- mark unknown information as unknown

### 3. Matching
Path: `services/matching-engine`

Pipeline:
1. hard gates
2. deterministic scoring
3. hybrid/semantic retrieval
4. AI reranking
5. explanation
6. shortlist

AI must never override a confirmed hard-gate failure silently.

### 4. Recruiter Workflow
Paths:
- `apps/recruiter-web`
- `services/team-workspace`

Responsibilities:
- Match Queue
- Jobs
- Candidates
- shared work context
- follow-ups
- ownership visibility
- future recruiter-approved outreach and qualification

### 5. Manager Workflow
Paths:
- `apps/recruiter-web`
- `services/team-workspace`

Responsibilities:
- job intake
- job quality review
- publishing approval
- weekly goals/review
- team workload
- exceptions
- future match-quality and feedback analytics

### 6. External Experience
Paths:
- `apps/api`
- Medlivo website repository

Responsibilities:
- public approved jobs
- search/detail
- future Apply orchestration into JobDiva
- future candidate/client experiences

External experiences consume platform APIs. They must not contain separate recruiting business logic.

## Data ownership rules

| Data | System of record |
| --- | --- |
| Candidate identity | JobDiva |
| Resume file | JobDiva |
| Job/requisition | JobDiva unless direct-customer intake is awaiting ATS creation |
| Submission | JobDiva |
| Interview / placement | JobDiva |
| Canonical candidate intelligence | Medlivo AI |
| Canonical job intelligence | Medlivo AI |
| Match score / explanation | Medlivo AI |
| Manager approval of Medlivo public content | Medlivo AI |
| Recruiter goals / manager review | Medlivo AI |
| Public approved job projection | Medlivo AI |

## Consequential-action policy

AI may:
- rank
- summarize
- identify gaps
- recommend
- draft
- prioritize

Humans approve:
- outreach
- submissions
- publication
- ownership changes
- JobDiva write-back
- other consequential recruiting actions

Automation can increase only after measured trust and explicit policy approval.

## Development pattern

Every product change must be implemented as a vertical slice:

source data → normalization → business logic → API → UI → acceptance test → merge.

Do not build disconnected UI or isolated AI logic that cannot be exercised end-to-end.

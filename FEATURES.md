# Medlivo AI Platform — Feature Status

Status values:
- **PLANNED** — approved for roadmap, not started
- **IN DEVELOPMENT** — actively being built or integrated
- **BUILT** — code exists and automated tests cover the core behavior
- **PRODUCTION READY** — real-data acceptance, security, deployment, monitoring, rollback and operational ownership are complete
- **DISABLED** — intentionally not enabled

> JobDiva remains the ATS and operational system of record. Medlivo AI is the intelligence and recruiter workflow-assist layer.

| Area | Feature | Status | Source of truth / notes |
| --- | --- | --- | --- |
| Access | Google sign-in | BUILT | Private workspace foundation; staging acceptance still required |
| Access | Recruiter / manager / admin RBAC | BUILT | Team and tenant scoping implemented |
| Access | Production OAuth / Cloud Run acceptance | IN DEVELOPMENT | Must be validated in private staging |
| JobDiva | Read-only jobs sync | IN DEVELOPMENT | Delta landing, resumable backfill and conservative canonical job promotion implemented; production scheduling/real-data acceptance pending |
| JobDiva | Candidate profile read | BUILT | Read-only connector method |
| JobDiva | License read | BUILT | Read-only connector method |
| JobDiva | Certification read | BUILT | Read-only connector method |
| JobDiva | Resume metadata read | BUILT | Read-only connector method |
| JobDiva | Resume text read | BUILT | Read-only connector method |
| JobDiva | Historical backfill | IN DEVELOPMENT | Resumable 14-day backfill orchestration implemented; production scheduling and real-data acceptance pending |
| JobDiva | Delta / near-real-time sync | IN DEVELOPMENT | Replay-safe jobs/candidates delta landing worker implemented; deployment/webhook reconciliation still pending |
| JobDiva | Candidate / resume / job write-back | DISABLED | Enable only after vendor API authorization and acceptance testing |
| Intelligence | Job normalization | BUILT | Division-aware model plus conservative JobDiva source-to-canonical promotion |
| Intelligence | Rehabilitation job template | BUILT | PT/PTA/OT/COTA/SLP oriented |
| Intelligence | Nursing & Allied job template | BUILT | Profession / specialty / shift / credential oriented |
| Intelligence | Locum Tenens job template | BUILT | Schedule / call / license / credentialing oriented |
| Intelligence | Source provenance | BUILT | source_confirmed / medlivo_standard / ai_suggested |
| Intelligence | Job quality/readiness scoring | BUILT | Core / matching / publishing readiness |
| Intelligence | Candidate Intelligence | BUILT | Canonical candidate facts + evidence; JobDiva delta identity fields can now seed canonical candidates conservatively |
| Intelligence | Resume parsing / deep experience extraction | IN DEVELOPMENT | Basic resume text available; richer structured extraction still needed |
| Matching | Profession hard gate | BUILT | Deterministic |
| Matching | State license hard gate | BUILT | Deterministic |
| Matching | Required certification hard gate | BUILT | Deterministic |
| Matching | Explainable 0–10 score | BUILT | Deterministic base layer |
| Matching | Semantic/vector retrieval | PLANNED | Phase after sync foundation |
| Matching | AI reranking | PLANNED | Must sit on top of deterministic gates/scoring |
| Recruiter | Private recruiter workspace | BUILT | Notes, follow-ups, activity, ownership |
| Recruiter | Match Queue | BUILT | Read-only priority jobs + top candidates |
| Recruiter | Candidate → best jobs | PLANNED | Next vertical slice after consolidation |
| Recruiter | Recommended next action | BUILT | Read-only recommendation in Match Queue |
| Recruiter | Automated outreach | DISABLED | Human approval, consent and policy required |
| Recruiter | SMS / email outreach | PLANNED | After data foundation and consent controls |
| Recruiter | Voice outreach | PLANNED | Later phase |
| Recruiter | Qualification workflow | PLANNED | Later phase |
| Recruiter | Submission readiness | PLANNED | Later phase |
| Manager | Direct-customer XLSX intake | BUILT | Mapping, validation, duplicate flags |
| Manager | Customer-specific mappings | BUILT | Saved mapping layer |
| Manager | Job approval | BUILT | Recruiting + website approvals separated |
| Manager | Weekly recruiter goals | BUILT | Monday targets |
| Manager | Goal vs Actual review | BUILT | Friday/weekly manager review |
| Manager | CSV weekly export | BUILT | Current review export |
| Manager | Team workload view | BUILT | Current private workspace |
| External | Approved public Career Jobs API | BUILT | Public-safe fields only |
| External | Website Search Jobs production integration | IN DEVELOPMENT | UI integration exists but not consolidated/production-ready |
| External | Website Apply → JobDiva | PLANNED | Must write to JobDiva, not a parallel ATS |
| External | Candidate portal | PLANNED | Later phase |
| External | Ask Medlivo integration | PLANNED | Later phase |
| External | Clinician recruiter feedback | PLANNED | Anonymous clinician feedback; management first |
| Platform | Background workers | IN DEVELOPMENT | JobDiva checkpointed delta worker is now implemented; production scheduling/deployment pending |
| Platform | Auditability | BUILT | Workspace and approval audit foundations |
| Platform | Monitoring / alerting | IN DEVELOPMENT | Read-only JobDiva sync health API implemented; alert delivery still pending |
| Platform | Rollback / runbooks | PLANNED | Required before production readiness |

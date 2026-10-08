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
| JobDiva | Read-only jobs sync | IN DEVELOPMENT | Delta landing, backfill, canonical promotion and JobsDetail enrichment implemented; production scheduling/real-data acceptance pending |
| JobDiva | Candidate profile read | BUILT | Read-only connector method feeding Candidate Intelligence enrichment |
| JobDiva | License read | BUILT | Read-only connector method with normalized canonical persistence |
| JobDiva | Certification read | BUILT | Read-only connector method with normalized canonical persistence |
| JobDiva | Resume metadata read | BUILT | Read-only connector method with versioned canonical resume references |
| JobDiva | Resume text read | BUILT | Bounded resume-text enrichment; JobDiva remains authoritative resume store |
| JobDiva | Historical backfill | IN DEVELOPMENT | Resumable 14-day backfill orchestration implemented; production scheduling and real-data acceptance pending |
| JobDiva | Delta / near-real-time sync | IN DEVELOPMENT | Replay-safe jobs/candidates delta landing plus disabled-by-default Cloud Run pilot runtime; real staging execution still requires operator approval |
| JobDiva | Candidate / resume / job write-back | DISABLED | Enable only after vendor API authorization and acceptance testing |
| Intelligence | Job normalization | IN DEVELOPMENT | Division-aware model plus JobDiva JobsDetail enrichment and source-backed license/certification/setting/skill/minimum-experience requirements; real-data field acceptance pending |
| Intelligence | Rehabilitation job template | BUILT | PT/PTA/OT/COTA/SLP oriented |
| Intelligence | Nursing & Allied job template | BUILT | Profession / specialty / shift / credential oriented |
| Intelligence | Locum Tenens job template | BUILT | Schedule / call / license / credentialing oriented |
| Intelligence | Source provenance | BUILT | source_confirmed / medlivo_standard / ai_suggested |
| Intelligence | Job quality/readiness scoring | BUILT | Core / matching / publishing readiness |
| Intelligence | Candidate Intelligence | IN DEVELOPMENT | Canonical candidate facts + evidence plus JobDiva profile/license/cert/resume enrichment; production scheduling and real-data acceptance pending |
| Intelligence | Resume parsing / deep experience extraction | IN DEVELOPMENT | Evidence-backed dated experience, care-setting, specialty, and clinical-skill extraction implemented; primary-resume care-setting evidence now feeds matching; real-data acceptance and vocabulary tuning pending |
| Matching | Profession hard gate | BUILT | Deterministic and now active in persisted canonical matching |
| Matching | State license hard gate | BUILT | Deterministic and persisted as match exclusions when failed |
| Matching | Required certification hard gate | BUILT | Deterministic and persisted as match exclusions when failed |
| Matching | Explainable 0–10 score | IN DEVELOPMENT | Deterministic scoring consumes source-backed care-setting, resume specialty, explicit job-skill, and documented-experience alignment; real-data quality acceptance pending |
| Matching | Real-data acceptance pilot | IN DEVELOPMENT | Recruiter Strong/Good/Weak/Not-a-match feedback with manager score-band/division agreement summary |
| Matching | Semantic/vector retrieval | IN DEVELOPMENT | Hybrid retrieval is integrated into worker processing priority behind hard gates; production embedding/vector-store integration and real-data acceptance pending |
| Matching | AI reranking | PLANNED | Deferred until the real-data acceptance pilot identifies where deterministic ranking needs help |
| Recruiter | Private recruiter workspace | BUILT | Notes, follow-ups, activity, ownership |
| Recruiter | Daily priorities | IN DEVELOPMENT | My Work now prioritizes overdue/due-soon follow-ups and strong unreviewed matches; staging recruiter acceptance pending |
| Recruiter | Recruiter dashboard | IN DEVELOPMENT | Weekly goal-vs-actual plus owned workload, follow-ups, priority jobs, and unreviewed matches; staging recruiter acceptance pending |
| Recruiter | Match Queue | IN DEVELOPMENT | Persisted matching now includes score-band triage, hide-reviewed workflow, explainable evidence, and recruiter feedback; real-data UX acceptance pending |
| Recruiter | Candidate → best jobs | IN DEVELOPMENT | Ranked persisted matches now include score-band summary, direct job opening, explanations, next action, and recruiter feedback; real-data UX acceptance pending |
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
| Platform | Background workers | IN DEVELOPMENT | JobDiva pipeline has a Cloud Run Job staging runtime and manual-only deployment path; scheduled production operation remains pending |
| Platform | Auditability | BUILT | Workspace and approval audit foundations |
| Platform | Monitoring / alerting | IN DEVELOPMENT | Read-only JobDiva sync health API implemented; alert delivery still pending |
| Platform | Rollback / runbooks | PLANNED | Required before production readiness |

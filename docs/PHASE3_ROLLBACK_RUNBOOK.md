# Phase 3 Rollback and Recovery Runbook

## Purpose

Provide a controlled rollback path for the Medlivo AI Recruiter Productivity pilot before real recruiter traffic is treated as production-ready.

This runbook applies to the private recruiter workspace, Phase 3 recruiter-productivity surfaces, and the bounded read-only JobDiva staging pilot.

It does **not** authorize JobDiva write-back, outreach, submissions, production data mutation, or deletion of audit history.

## Rollback principles

1. Disable risky execution before changing code.
2. Preserve canonical data, workspace notes/tasks, feedback, and audit history.
3. Do not "fix" a recruiter issue by enabling an alternate write path or bypassing authorization.
4. JobDiva remains the ATS and system of record.
5. Roll back application revisions before rolling back database schema unless the incident is clearly schema-driven.
6. Re-enable only after the same staging smoke checks that would be required for a fresh deployment.

## Immediate stop conditions

Stop the Phase 3 pilot if any of the following occurs:

- unauthorized tenant/team/candidate/job visibility
- incorrect ownership access after reassignment
- unexpected JobDiva write activity
- repeated authentication or session isolation failures
- persistent cross-user data leakage
- hard-gate behavior that exposes clearly ineligible candidates as eligible
- corrupted or duplicated canonical source linkage
- inability to identify which recruiter performed a workspace mutation
- logging of credentials, tokens, candidate payloads, or other sensitive request bodies
- workspace/API deployment causing repeated recruiter-blocking failures

## Immediate containment

### 1. Disable the JobDiva staging pilot

Use the existing staging pilot deployment workflow with:

- `enable_pilot = false`
- `confirm_read_only = READ_ONLY`

Verify both runtime flags are false:

- `PILOT_ENABLED=false`
- `JOBDIVA_LIVE_ENABLED=false`

Because the current pilot has no scheduler, no recurring execution should remain after this change.

Do not execute the Cloud Run Job while disabled.

### 2. Disable recruiter workspace entry if authorization is in doubt

Set the recruiter browser workspace to disabled mode by setting:

- `TEAM_WORKSPACE_ENABLED=false`

The disabled workspace must fail closed and show the setup/unavailable state rather than exposing a fallback data surface.

Do not make the private workspace API public as a workaround.

### 3. Preserve state

Do not delete:

- canonical jobs or candidates
- source-record links
- persisted matches
- recruiter match feedback
- workspace notes
- follow-up tasks
- reassignment history
- audit records
- weekly goals/snapshots

If data integrity is in doubt, stop writes to the affected Medlivo workspace surface and preserve the database for investigation.

## Application rollback

### Recruiter web

Identify the last known-good Cloud Run revision for the recruiter web service.

Before routing traffic back:

1. Confirm the revision was built from a known `main` commit.
2. Confirm its server configuration still points to the intended private workspace API.
3. Confirm no retired or test service URL is referenced.
4. Confirm `TEAM_WORKSPACE_ENABLED` has the intended value.

Route staging traffic to the last known-good revision using the normal Cloud Run revision/traffic mechanism.

Do not rebuild an old commit merely to recreate a previous revision if the existing known-good revision is available and verifiable.

### Private workspace API

If the regression is in API behavior or authorization:

1. Disable recruiter workspace access first.
2. Identify the last known-good private API revision.
3. Confirm the API remains private behind Cloud Run IAM.
4. Confirm the runtime service account and Secret Manager bindings are unchanged.
5. Route staging traffic to the known-good revision.
6. Re-run authorization smoke tests before re-enabling the browser workspace.

## Database rollback

Database rollback is **not** the default response to a UI/API regression.

Use schema rollback only when:

- a migration itself caused the failure,
- the migration has a reviewed reverse procedure,
- data written under the new schema is understood,
- reverting will not destroy required audit/history data.

Before any schema reversal:

1. Stop the recruiter workspace and JobDiva pilot.
2. Take/confirm the staging backup or recovery point.
3. Record the current migration level.
4. Review every affected table and foreign-key dependency.
5. Preserve audit/history records.
6. Verify that the prior application revision is compatible with the target schema.

Never point rollback testing at production.

## JobDiva safety verification

After any incident involving sync or matching, verify:

- no JobDiva candidate write occurred
- no JobDiva resume write occurred
- no JobDiva job write occurred
- no submission was created
- no interview or placement state was changed
- no candidate ownership was changed in JobDiva
- no outreach was triggered from Phase 3 surfaces

If any unexpected write is observed, keep the pilot disabled and treat the issue as a boundary breach requiring explicit investigation before further staging execution.

## Data integrity checks

Before recovery, sample the affected tenant and verify:

- JobDiva source IDs remain unique and stable
- canonical candidate/job links remain intact
- no duplicate canonical identity was created from the same source record
- persisted match rows still reference valid jobs/candidates
- hard-gate exclusions remain explainable
- recruiter feedback remains attached to the correct match
- workspace cases still point to valid candidate/job records
- open/done follow-up state is intact
- reassignment and audit history are complete

## Recovery smoke tests

After routing to the recovered revision, keep the JobDiva live pilot disabled and perform synthetic/private staging checks first.

### Recruiter

- sign in with an approved staged recruiter account
- confirm only assigned work is visible
- open My Work
- open Daily Priorities
- open Dashboard
- open Follow-ups
- open Match Queue
- open Candidate Best Jobs
- save a synthetic note
- create and complete/reopen a synthetic follow-up
- confirm unauthorized work is denied

### Manager

- sign in with an approved staged manager account
- confirm only managed-team data is visible
- review Team Overview
- review Weekly Review
- test same-team reassignment with a reason
- confirm former owner loses access and new owner gains access
- verify activity history remains intact

### Browser/session

- logout invalidates the session
- expired/revoked membership denies access
- no token is visible in HTML, JS, localStorage, or sessionStorage
- cross-origin mutation attempts fail
- mobile workspace has no horizontal overflow

## Re-enable sequence

Only after synthetic smoke tests pass:

1. Re-enable `TEAM_WORKSPACE_ENABLED=true` in private staging.
2. Keep JobDiva live pilot disabled.
3. Confirm recruiter/manager staging access.
4. Enable the JobDiva pilot only through the controlled deployment workflow.
5. Execute one bounded read-only run.
6. Review sync health, enrichment errors, canonical linkage, matches, and logs.
7. Confirm no write activity.
8. Let approved recruiters review a small real-data sample.
9. Expand only after clean bounded runs and acceptable recruiter feedback.

## Rollback verification record

For each rollback/recovery event, record:

- date/time
- triggering symptom
- affected environment
- affected commit/revision
- operator
- containment action
- revision rolled back to
- database migration level
- JobDiva pilot enabled/disabled state
- validation results
- decision to remain disabled or re-enable
- follow-up owner

Do not place credentials, tokens, raw resumes, or candidate payloads in the incident record.

## Phase 3 acceptance linkage

The Phase 3 acceptance item:

- `Pilot rollback procedure is documented and tested`

is satisfied only after this runbook is reviewed **and** exercised in staging using synthetic data.

Documentation alone does not make Phase 3 production-ready.

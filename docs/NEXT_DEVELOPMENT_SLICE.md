# Next Development Slice

## M0: prove the existing staging release

Keep `pks-alt/Medlivo-AI-Platform`. No new repository, broad rewrite, provider replacement or altered release boundary. Start from the current source baseline and identify blockers with evidence. Application-test success and successful deployment are separate states.

### Current targeted change

Replace the misleading migration-resource error with safe metadata diagnostics. Add `diagnostics_only` to the existing manual workflow, defaulting to true. Run offline regression tests in the existing unfiltered `platform-control` job. This changes error reporting and introduces a no-change inspection mode, not a migration bypass.

### Review and execution order

1. Review this scoped PR and its exact-head checks. Do not merge failed tests or present the PR as deployed.
2. A repository administrator reviews main-branch enforcement: require PRs and independent approval, dismiss stale approvals, require resolved review conversations, block force pushes/deletion, and review bypass rights. Inspect existing check names and path triggers before selecting required checks. The current connection's administration read returned HTTP 403; settings have NOT been applied.
3. Confirm an independent eligible reviewer. GitHub authors cannot approve their own PRs. PK's product approval is not a fabricated GitHub review from another account.
4. Before merging, after review, use **Deploy private team staging → Run workflow → fix/staging-preflight-evidence → diagnostics_only=true**. The existing workflow already supports manual dispatch on main; select the reviewed branch to use this proposed diagnostic input. The existing WIF connection runs fixed metadata reads only. No build, migration, deployment or traffic update runs in this mode. A failed diagnostic remains red and reports why; a green diagnostic is NOT a deployed release.
5. Review both resource lookups and visible inventories. Permission/unavailable/unknown results are not proof of absence. Alternative names require verification and an approved mapping, not automatic substitution or recreation.
6. Establish the actual migration-only database role, grants and schema state through authorized operator evidence. A manual SQL action does not bypass a remaining release preflight. Do not use runtime credentials for DDL.
7. Keep the PR unmerged until prerequisites and review controls are resolved: merging still triggers the existing normal deployment on a main push. Only after prerequisites are verified, approve merge and the existing deployment path (`diagnostics_only=false` for a manual deploy). Keep migration, readiness, same-release API/web and traffic gates.
8. Record actual serving revisions, image digests, commit, schema checks and authenticated recruiter/manager browser acceptance. Environment-variable SHA agreement alone is not complete proof.
9. Update the control records with the observed evidence. Do not ask users to reupload workbooks to diagnose a failed deployment.

## Running the reviewed diagnostic branch

An authorized operator with existing GitHub CLI access can run:

```sh
gh workflow run deploy-team-staging.yml \
  --repo pks-alt/Medlivo-AI-Platform \
  --ref fix/staging-preflight-evidence \
  -f diagnostics_only=true
```

Do not paste access tokens into chat. If existing WIF trust prevents a non-main diagnostic run, do not expand that trust or merge just to bypass it. An authorized operator can review and run the same fixed metadata-only Python script in the existing Google Cloud Shell session. Capture the sanitized report; neither route creates resources. This PR does not change WIF policy or repository visibility.

Official manual-dispatch reference: https://docs.github.com/actions/managing-workflow-runs/manually-running-a-workflow

## Required-check activation caveat

`platform-control` runs on every PR and main push and now includes offline preflight regression tests. Other application workflows may be path-filtered; this check is not a substitute for all applicable app tests. Review and implement an appropriate always-emitted gate before making conditional checks universally required. GitHub settings changes must be verified by readback and an authorized blocked-merge/direct-push test; a checklist is not enforcement.

## Exit criteria

- Authorized main-branch controls are verified, not only proposed.
- Migration prerequisite failure is explained without guessing.
- No unnecessary accounts, secrets or databases are recreated.
- Reviewed schema execution and actual serving release are evidenced.
- Recruiter and manager protected browser paths pass on that release.
- No unapproved JobDiva mutation, live messaging or publication is enabled.

## After M0

Complete Module 01 in the same codebase: approved real-data scope → source identity and full enrichment → shared Job Content Standards → source-independent matching readiness → both matching directions → browser acceptance. The master and module documents remain product review drafts, not an automatic launch approval. No production launch before Phase 2.

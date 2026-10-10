# Medlivo Engineering Operating Model

**Status:** Governing and permanent unless explicitly changed through the change-control process below.

## Principle

The Medlivo product will continue to expand. The engineering operating model should not be reinvented every time a new capability is added.

**Stable architecture discipline + continuously expanding product capabilities.**

New features, agents, analytics, integrations, workflows, and future marketplace capabilities are expected. They must plug into the same disciplined platform rather than creating parallel systems.

## Permanent development rules

1. **`main` is the only canonical development baseline.**
   - Every new feature branch starts from the latest green `main`.
   - Historical PRs and old branches are reference material only.
   - Never start new product development from an old feature or deployment branch.

2. **One coherent capability per PR.**
   - Use a short-lived feature branch.
   - Complete the capability end to end.
   - Merge only after required tests pass.
   - Retire the feature branch after merge.

3. **Build vertical slices, not disconnected pieces.**

   Every product capability follows:

   `system of record → canonical data → owning service → API → RBAC → business rules → AI policy → approval/review → audit → acceptance tests → UI → staging → browser review → merge`

4. **System-of-record boundaries are explicit.**
   - JobDiva remains the ATS/system of record for ATS-owned recruiting records until a future approved architecture decision changes that boundary.
   - Medlivo owns intelligence, workflow overlays, configuration, readiness, economics, audit, and other explicitly assigned Medlivo domains.
   - Do not create a second ATS accidentally.

5. **Human consequential decisions remain explicit.**
   - AI may extract, normalize, summarize, draft, explain, rank, recommend, and identify gaps.
   - Humans own consequential recruiting decisions unless a later policy explicitly authorizes automation.
   - AI may not silently invent unsupported facts or override confirmed hard-gate failures.

6. **RBAC, audit, security, and tests are part of the feature.**
   - They are not cleanup work to be added later.
   - A UI without its authoritative backend path is not a completed feature.

7. **Staging mirrors the real application architecture.**
   - Staging and production should promote the same application architecture with environment-specific configuration.
   - Do not preserve obsolete special containers that omit current product routes unless an explicit security decision requires them.

8. **The current platform state is updated with every meaningful capability merge.**
   - `docs/CURRENT_PLATFORM_STATE.md` is the first operational reference.
   - `docs/PHASE1_COMPLETION_MATRIX.md` tracks scope completion.
   - `docs/NEXT_DEVELOPMENT_SLICE.md` names the immediate next slice.
   - `RELEASE_STATE.json` records the currently understood release/deployment state.

9. **Architecture decisions are deliberate.**
   - Permanent boundaries and policies belong in `docs/decisions/`.
   - If a future need conflicts with an existing decision, create a superseding ADR instead of quietly changing behavior.

10. **Product expansion is expected.**
    - Outreach agents, scheduling, compliance, redeployment, extensions, candidate experience, customer intelligence, predictive analytics, and marketplace capabilities may all be added later.
    - New capabilities extend the platform; they do not replace the operating model.

## Change control for this operating model

This operating model is not changed casually.

A proposed change requires all of the following:

1. A concrete problem that the current model cannot solve safely or efficiently.
2. An Architecture Decision Record describing the proposed change and alternatives.
3. Impact review covering data ownership, security, RBAC, audit, integrations, staging, migration, and rollback.
4. Explicit approval from Medlivo leadership/product owner.
5. A migration plan if existing behavior or ownership boundaries change.
6. Updated platform-state and release-state documents in the same capability PR.

Until those steps are complete, this operating model remains authoritative.

## When direction is drifting

If a requested implementation conflicts with this model, the engineer or AI assistant should say so before proceeding and explain the conflict. Examples include:

- starting from an old branch instead of current `main`
- duplicating JobDiva-owned records into a competing operational source of truth
- bypassing RBAC or audit to move faster
- making customer-required documents recruiter-waivable without policy
- adding AI-generated facts without evidence
- shipping a UI whose backend path is not complete
- allowing staging to use obsolete application architecture
- enabling write-back or autonomous outreach without the required approvals

The goal is not to block product evolution. The goal is to keep expansion controlled, understandable, and reversible.

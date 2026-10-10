# Recruiter Web

Target: `recruit.medlivo.com`

Phase 1 recruiter/manager application.

The current static UX prototype lives at the repository root for GitHub Pages review. This folder will become the production recruiter app once the frontend stack is selected.


## Staging authentication diagnostics

Private staging validates the browser gateway OAuth client/domain against the private API validation client/domain during deployment without exposing credentials. The canonical callback is derived from `TEAM_APP_ORIGIN` as `/api/team/auth/callback`.

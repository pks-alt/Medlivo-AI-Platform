# Security and Access

## Authentication
Recruiter/admin: enterprise SSO first, passwordless fallback for smaller future tenants.

## Authorization
RBAC hierarchy:
Company -> Division -> Team -> Recruiter.

Recruiters default to assigned customers/jobs. Managers see broader team/division scope.

## Secrets
All external credentials belong in Google Secret Manager. Never store passwords or tokens in GitHub.

## Audit
All AI and recruiter actions are auditable. Sensitive actions capture stronger context and approval evidence.

## Candidate communication
Maintain centralized contactability/consent by channel, source, opt-out state, preferred channel, and allowed contact windows.

## Human approval
Phase 1 requires recruiter approval before candidate submission.

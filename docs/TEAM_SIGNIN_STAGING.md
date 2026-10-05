# Team sign-in and connected notes/follow-ups

## What is implemented

The existing Next.js app gains `/team`, a browser-facing team workspace with Medlivo's
navy/lime visual language. This is not a replacement for the public GitHub Pages sample.
The connected scope is assigned work items, shared notes, follow-ups, activity and
manager reassignment. Other sample screens are not silently presented as live features.

The flow is Google authorization code + PKCE S256 + single-use state and nonce, then a
Google ID-token signature/issuer/audience/expiry/hosted-domain check. The private workspace
API must also confirm an explicitly provisioned active member before a session is created.
Google email alone never provisions or grants access.

The browser receives a random opaque `__Host-medlivo-team` cookie with HttpOnly, Secure,
SameSite=Lax and Path=/. Its hash, not its raw value, is stored in PostgreSQL. Google ID
tokens and CSRF secrets are AES-256-GCM encrypted in server storage with record-bound
additional authenticated data. No Google or session token is sent to JavaScript or browser
storage. Separate application instances share the same session store.

Sessions end after 30 minutes of inactivity or at the earlier of 55 minutes and the Google
ID token's expiry minus 30 seconds. There are no background keepalives, offline scopes or
refresh tokens. The first staging pilot deliberately requires signing in again rather than
silently extending a credential. Google scopes are only `openid email`. Logging out deletes
the server session and cookie; it does not sign the person out of their Google account.

All mutations require exact trusted Origin, matching session CSRF token, JSON, and a UUID
idempotency key. The proxy only allows the existing private workspace routes; arbitrary
URLs, unapproved methods, credentials from the browser and unbounded queries are rejected.
The UI preserves an unconfirmed save's key for retries without changing its payload. After
an ambiguous save and a full page reload, inspect the existing record before submitting
again. This is not a claim of end-to-end exactly-once delivery under all browser failures.

The gateway sends TWO credentials to the private Cloud Run API: the user ID token in
Authorization and the gateway's metadata-issued service token in X-Serverless-Authorization.
Cloud Run validates the service identity; the API validates the user and current database
permissions. Role changes, disabled users and case assignments are not cached in the cookie.
The gateway will not send credentials to a browser-supplied origin or follow redirects.

## Configuration and deployment status

Disabled by default (`TEAM_WORKSPACE_ENABLED` is not true). The new `/team` route shows a
clear setup notice until its server configuration is available; API requests fail closed.
No credentials or fake-user environment switch are included. Importing or building the app
does not create accounts, execute migrations or activate a live JobDiva connection.

No existing Cloud Run service, IAM binding, OAuth client, database or public preview is
changed by this code review. This PR extends the private-workspace backend already in PR #3;
it does not merge the other pending Cloud Run/API or JobDiva connector changes.

## Private staging checklist

1. Choose the browser's HTTPS origin for staging, using a separate test deployment. Do not
   point this work at the production recruiter environment until review is complete.
2. Create/approve a Google OAuth WEB application for the Medlivo organization. Register
   the EXACT redirect URI `https://<approved-origin>/api/team/auth/callback`. The real
   client ID must match `WORKSPACE_GOOGLE_CLIENT_ID` on the private API. A Google `hd`
   request hint is not authorization; both gateway and private API validate the claim.
3. Apply migration `001_workspace.sql` (previous milestone) to the staging canonical DB.
   Apply `002_browser_sessions.sql` to the staging session DB. They may share a Cloud SQL
   instance, but use separate least-privilege runtime DB accounts.
4. Grant the gateway DB role only SELECT/INSERT/UPDATE/DELETE on `wb_login` and `wb_session`.
   It must not own tables or read/modify canonical candidates, identity bindings or roles.
   The private API continues to use its separately reviewed runtime grants.
5. Provision only approved, verified Google `sub` bindings and synthetic staging cases.
   There is no self-registration and no unverified-email account linking in the app.
6. Keep the team API PRIVATE with invoker IAM checks. Grant only the designated gateway
   service account `roles/run.invoker` on that service. The public browser login is not
   a reason to make the API unauthenticated. The old `/api/v1/jobs` service is not a
   substitute for the new private team-workspace service.
7. Set the gateway's server-only configuration below. Put all secrets in Secret Manager;
   inject them only into the staging runtime. Do not paste values into chat, public issues,
   repo files, NEXT_PUBLIC variables, shell command history or browser storage.
8. Run the real staging checks listed below before adding any real candidate data.

| Gateway setting | Meaning |
|---|---|
| TEAM_WORKSPACE_ENABLED | `true` only after staging setup is approved |
| TEAM_APP_ORIGIN | HTTPS browser origin, no trailing slash/path |
| TEAM_API_URL | Canonical HTTPS root URL of private team Cloud Run API |
| TEAM_GOOGLE_CLIENT_ID | Approved Google OAuth web client ID |
| TEAM_GOOGLE_CLIENT_SECRET | Secret Manager value |
| TEAM_GOOGLE_HOSTED_DOMAIN | Exact approved Workspace domain, default `medlivo.com` |
| TEAM_SESSION_KEY | Secret Manager: base64 encoding of 32 cryptographically random bytes |
| TEAM_SESSION_DATABASE_URL | Secret Manager: PostgreSQL URL with Cloud SQL socket or verified TLS |

The gateway runtime expects Cloud Run's `K_SERVICE` and metadata service identity. It has
no personal-token fallback. Direct TCP PostgreSQL URLs require `sslmode=verify-full` and
an appropriate trusted CA; do not use `rejectUnauthorized=false`. Cloud SQL socket URLs
use a `host=/cloudsql/<project:region:instance>` query parameter. Rotating TEAM_SESSION_KEY
currently signs out existing sessions; a multi-key seamless rotation scheme is not included.

Use the existing project `medlivo-ai-platform` and region `us-west1`, but confirm service and
OAuth names from the actual staging setup. No new service URL or client ID is invented here.

## Tests and their limits

- Native Node tests exercise the production gateway with injected OAuth/API/session doubles:
  state/nonce use, PKCE, callback replay, cookie rotation, encrypted sessions, expiry, origin/
  CSRF, key validation, path restrictions, logout and sanitized upstream failures.
- JOSE tests verify real RSA signatures using synthetic local keys and reject wrong issuer,
  audience, nonce, domain, signature and other invalid claims. No Google account is used.
- PostgreSQL tests check single-use login consumption under concurrent requests, storage
  sharing between gateway instances, expiry and revocation on a disposable database.
- Browser CI uses the REAL private backend code and PostgreSQL browser sessions. Google is a
  loopback test simulation. Recruiter, manager and second recruiter use separate contexts.
  It tests saved notes, completion, reassignment, access removal, logout, and mobile layout.
- The existing Next.js production build is compiled in CI, including the new route adapters.
  Browser integration uses a test HTTPS harness around the same gateway/UI, not a deployed
  Next.js/Cloud Run origin. Only a real staging test can verify OAuth registration, metadata,
  service invocation, secret injection and the deployed Next request/response path together.

All test fixtures are under `tests/team`; no production route imports them. Do not publish
or deploy the test harness. It binds only loopback and uses only synthetic data. Tests must
never be pointed at the production database; temporary schemas are created and dropped.

## Real staging acceptance checks

Approved recruiter signs in, sees only assigned synthetic work, saves a note and follow-up;
a manager signs in from another browser and sees both; manager reassigns with a reason;
previous owner is denied and the new owner sees the preserved history. Then test invalid
Google domain, unprovisioned member, disabled member with an existing session, session expiry,
logout/replayed cookie, simultaneous edits, network retry and cross-origin save attempts.
Verify browser/Google/API/service-account tokens are not exposed in HTML, JS, logs or storage.
Confirm all other legacy read endpoints remain mock-only until separately secured.

## Operational controls before production

The login store has a 120-starts/minute shared safety ceiling and removes expired rows at
login, not a full internet-facing abuse-management system. Add edge/per-client rate limiting,
periodic expired-row cleanup, safe authentication telemetry, database backups/retention and
alerts. Review Log Router/APM/edge configuration to omit OAuth callback query strings and
Authorization/Cookie headers, and never log request/response bodies containing credentials.
The OAuth code arrives in the callback query by protocol; it must not become a durable log.
No generic exception handler prints raw token-exchange or database error details.

## Official implementation references

- https://developers.google.com/identity/openid-connect/openid-connect
- https://developers.google.com/identity/openid-connect/reference
- https://developers.google.com/identity/gsi/web/guides/verify-google-id-token
- https://docs.cloud.google.com/run/docs/authenticating/service-to-service
- https://nextjs.org/docs/app/guides/authentication
- https://github.com/panva/jose
- https://node-postgres.com/features/queries

# Sign-in testing notes and scope corrections

The first browser runs exposed an isolation defect in the test harness: Playwright's
interception did not replace a redirected request to Google's authorization endpoint.
Google rejected the synthetic client ID. No Medlivo account credentials or candidate
records were involved. Those failed runs are NOT evidence of successful Google login
or of zero external requests.

The revised harness runs a synthetic provider on 127.0.0.1 and the browser app on localhost.
The test server rewrites only its own outgoing authorization redirect after checking the
production gateway selected the official Google origin. This exercises a cross-site,
secure-cookie callback without contacting Google. Production code has no provider override,
actor-cookie switch or fake-login path. Request events are checked for unexpected domains.
The API is the actual private-workspace implementation using synthetic SQLite records;
the browser session store is real disposable PostgreSQL. No production deployment is tested.

Correction to the staging guide's operational shorthand: the login store's ceiling bounds
recently created OUTSTANDING login flows, not all sign-in attempts per minute. Consumed flows
are removed. A real edge/per-client login-attempt limiter is still required for production.

The sign-in implementation, encrypted server sessions and connected notes/tasks/ownership
screens extend PR #3. They are not merged or deployed. Google OAuth registration, approved
identity provisioning and live Cloud Run/Cloud SQL integration remain staging acceptance
steps. Read actual workflow results rather than inferring success from this document.

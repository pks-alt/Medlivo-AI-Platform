/** Verify the actual standalone image, not an injected HTTP harness. No login. */
import assert from 'node:assert/strict';
const base = 'http://127.0.0.1:18080';
async function get(path) { return fetch(base + path, {redirect:'manual',signal:AbortSignal.timeout(10000)}); }
let ready=false;
for(let i=0;i<40;i++) {
  try { if((await get('/team')).status===200) {ready=true;break;} } catch {}
  await new Promise(resolve=>setTimeout(resolve,1000));
}
assert.ok(ready,'Standalone staging image did not start');
const root=await get('/');
assert.equal(root.status,303); assert.equal(root.headers.get('location'),'/team');
const page=await get('/team');
assert.equal(page.status,200); assert.match(page.headers.get('cache-control'),/no-store/);
assert.ok(page.headers.get('content-security-policy'),'Sign-in document must have CSP');
assert.match(await page.text(),/login-layout/);
const blocked=await get('/api/team/session');
assert.equal(blocked.status,503); assert.match(blocked.headers.get('cache-control'),/no-store/);
assert.match((await blocked.json()).detail,/not configured/);
// Check canonical paths: Next.js normalizes trailing slashes before route lookup.
for(const path of ['/jobs','/jobs/sample','/candidates/sample','/api/v1/jobs','/workspace-preview','/lib/team/core.mjs','/tests/team/fixture-server.mjs','/.env']) {
  assert.equal((await get(path)).status,404,`${path} must not be present in the staging-only image`);
}
// Allow only the exact expected normalization, never an arbitrary redirect.
// Fetches remain manual; a redirect alone is NOT evidence that a route is absent.
const previewSlash=await get('/workspace-preview/');
assert.equal(previewSlash.status,308,'Expected trailing-slash normalization');
assert.equal(previewSlash.headers.get('location'),'/workspace-preview','Unexpected preview redirect target');
assert.equal((await get('/workspace-preview')).status,404,'Preview redirect destination must remain unavailable');
console.log('PASS: staging web setup, security headers, disabled session endpoint, and unavailable legacy/source/test routes verified (preview: 308 then 404).');

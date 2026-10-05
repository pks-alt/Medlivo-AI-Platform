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
for(const path of ['/jobs','/jobs/sample','/candidates/sample','/api/v1/jobs','/workspace-preview/','/lib/team/core.mjs','/tests/team/fixture-server.mjs','/.env']) {
  assert.equal((await get(path)).status,404,`${path} must not be present in the staging-only image`);
}
console.log('PASS: actual Next.js staging image renders team setup; credentials absent; all legacy, source and test paths return 404.');

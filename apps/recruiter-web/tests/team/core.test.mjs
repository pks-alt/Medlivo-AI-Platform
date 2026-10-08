import test from 'node:test';
import assert from 'node:assert/strict';
import {randomBytes} from 'node:crypto';
import {harness,mutation,ORIGIN,CASE,MemoryStore} from './helpers.mjs';
import {hash,seal,unseal,SESSION_COOKIE,LOGIN_COOKIE,validateConfig,SafeError} from '../../lib/team/core.mjs';
import {createPrivateApi} from '../../lib/team/private-api.mjs';
import {renderTeam} from '../../lib/team/ui.mjs';

test('disabled configuration needs no credentials',()=>assert.equal(validateConfig({}),null));
test('live configuration rejects insecure origins, invalid keys and database TLS',()=>{
 const env={TEAM_WORKSPACE_ENABLED:'true',TEAM_APP_ORIGIN:ORIGIN,TEAM_API_URL:'https://team.run.app',TEAM_GOOGLE_CLIENT_ID:'test.apps.googleusercontent.com',TEAM_GOOGLE_CLIENT_SECRET:'synthetic',TEAM_SESSION_KEY:randomBytes(32).toString('base64'),TEAM_SESSION_DATABASE_URL:'postgresql://test:synthetic@db.example.test/staging?sslmode=verify-full'};
 assert.ok(validateConfig(env));
 for(const change of [{TEAM_APP_ORIGIN:'http://workspace.example.test'},{TEAM_APP_ORIGIN:ORIGIN+'/path'},{TEAM_API_URL:'https://attacker.example'},{TEAM_SESSION_KEY:'short'},{TEAM_SESSION_DATABASE_URL:'postgresql://db/staging'}])assert.throws(()=>validateConfig({...env,...change}));
 assert.ok(validateConfig({...env,TEAM_SESSION_DATABASE_URL:'postgresql://test:synthetic@/staging?host=/cloudsql/project:region:instance'}));
 assert.throws(()=>validateConfig({...env,TEAM_SESSION_DATABASE_URL:'postgresql://test:synthetic@localhost/staging?host=/cloudsql/project:region:instance'}));
});
test('encryption is randomized and binds ciphertext to session ID',()=>{
 const key=randomBytes(32),payload={idToken:'private-token'};
 const a=seal(key,payload,'session:abc'),b=seal(key,payload,'session:abc');
 assert.notEqual(a,b);assert.ok(!a.includes('private-token'));assert.deepEqual(unseal(key,a,'session:abc'),payload);
 assert.throws(()=>unseal(key,a,'session:other'));assert.throws(()=>unseal(randomBytes(32),a,'session:abc'));
});
test('sign-in uses state nonce PKCE and minimal scopes',async()=>{
 const h=harness(),{start,url}=await h.begin();
 assert.equal(url.origin,'https://accounts.google.com');assert.equal(url.searchParams.get('scope'),'openid email');
 assert.equal(url.searchParams.get('code_challenge_method'),'S256');assert.equal(url.searchParams.get('redirect_uri'),ORIGIN+'/api/team/auth/callback');
 for(const key of ['nonce','state','code_challenge'])assert.equal(url.searchParams.get(key).length,43);
 const cookie=start.headers.getSetCookie()[0];for(const option of ['HttpOnly','Secure','SameSite=Lax','Path=/'])assert.match(cookie,new RegExp(option));assert.doesNotMatch(cookie,/Domain=/);
 assert.equal(h.requests.length,0);
});
test('cross-site sign-in start is denied',async()=>{
 const h=harness();assert.equal((await h.request('/api/team/auth/start',{headers:{'Sec-Fetch-Site':'cross-site'}})).status,403);assert.equal(h.store.logins.size,0);
});
test('successful code exchange checks membership and rotates opaque session',async()=>{
 const h=harness(),{callback,sessionCookie,data}=await h.login();assert.equal(callback.status,303);assert.equal(callback.headers.get('location'),'/team');
 assert.ok(data.csrf);assert.equal(data.member.role,'recruiter');assert.ok(!JSON.stringify(data).includes('synthetic.google.token'));assert.ok(!sessionCookie.includes('token'));
 const {url,options}=h.requests[0];assert.equal(url,'https://oauth2.googleapis.com/token');assert.equal(options.redirect,'error');assert.equal(options.body.get('grant_type'),'authorization_code');assert.equal(options.body.get('code_verifier').length,43);
 assert.equal(h.store.logins.size,0);assert.equal(h.store.sessions.size,1);assert.ok(!JSON.stringify([...h.store.sessions]).includes('synthetic.google.token'));
});
test('missing cookie or mismatched state prevents code exchange',async()=>{
 for(const bad of ['missing','wrong']){const h=harness(),{url,loginCookie}=await h.begin();const response=await h.request('/api/team/auth/callback?state='+(bad==='wrong'?'a'.repeat(43):url.searchParams.get('state'))+'&code=some',{headers:{Cookie:bad==='missing'?'':loginCookie}});assert.equal(response.headers.get('location'),'/team?error=login');assert.equal(h.requests.length,0);}
});
test('duplicate callback state parameters are rejected',async()=>{const h=harness(),{url,loginCookie}=await h.begin();await h.request('/api/team/auth/callback?state='+url.searchParams.get('state')+'&state='+url.searchParams.get('state')+'&code=x',{headers:{Cookie:loginCookie}});assert.equal(h.requests.length,0);});
test('login expires after ten minutes',async()=>{const h=harness(),{url,loginCookie}=await h.begin();h.setNow(h.getNow()+601);await h.request('/api/team/auth/callback?state='+url.searchParams.get('state')+'&code=x',{headers:{Cookie:loginCookie}});assert.equal(h.requests.length,0);});
test('login callback is single-use, including concurrent attempts',async()=>{const h=harness(),{url,loginCookie}=await h.begin();const path='/api/team/auth/callback?state='+url.searchParams.get('state')+'&code=x';const results=await Promise.all([h.request(path,{headers:{Cookie:loginCookie}}),h.request(path,{headers:{Cookie:loginCookie}})]);assert.deepEqual(results.map(r=>r.headers.get('location')).sort(),['/team','/team?error=login']);assert.equal(h.requests.length,1);});
test('provider cancellation consumes state without token exchange',async()=>{const h=harness(),{url,loginCookie}=await h.begin();await h.request('/api/team/auth/callback?state='+url.searchParams.get('state')+'&error=access_denied',{headers:{Cookie:loginCookie}});assert.equal(h.store.logins.size,0);assert.equal(h.requests.length,0);});
test('invalid identity or nonce fails closed',async()=>{const h=harness({verifyIdToken:async()=>{throw new Error('sensitive token')}});const {callback}=await h.login();assert.equal(callback.headers.get('location'),'/team?error=login');assert.equal(h.store.sessions.size,0);assert.equal(h.apiCalls.length,0);});
test('unprovisioned account cannot create a session',async()=>{const h=harness({api:async()=>new Response('sensitive account',{status:403})});const {callback}=await h.login();assert.equal(callback.headers.get('location'),'/team?error=access');assert.equal(h.store.sessions.size,0);});
test('provider failure body and secrets are not exposed',async()=>{const h=harness({fetcher:async()=>new Response('private-token-and-client-secret',{status:500})});const {callback}=await h.login();assert.equal(callback.headers.get('location'),'/team?error=login');assert.equal(await callback.text(),'');});
test('anonymous and duplicate session cookies cannot access data',async()=>{
 const h=harness();assert.equal((await h.request('/api/team/cases')).status,401);const {sessionCookie}=await h.login();assert.equal((await h.request('/api/team/cases',{headers:{Cookie:sessionCookie+'; '+sessionCookie}})).status,401);
});
test('session absolute expiry never outlives Google token',async()=>{const h=harness({verifyIdToken:async()=>({sub:'synthetic',exp:Math.floor(Date.now()/1000)+120})});const {sessionCookie,data}=await h.login();assert.ok(data.expires<=h.getNow()+90);h.setNow(h.getNow()+91);assert.equal((await h.request('/api/team/session',{headers:{Cookie:sessionCookie}})).status,401);});
test('idle session expires without background keepalive',async()=>{const h=harness(),{sessionCookie}=await h.login();h.setNow(h.getNow()+1801);assert.equal((await h.request('/api/team/cases',{headers:{Cookie:sessionCookie}})).status,401);});
test('revoked membership ends a previously valid session',async()=>{let allowed=true;const h=harness({api:async()=>allowed?Response.json({id:'one',role:'recruiter'}):new Response(null,{status:403})});const {sessionCookie}=await h.login();allowed=false;assert.equal((await h.request('/api/team/session',{headers:{Cookie:sessionCookie}})).status,401);assert.equal(h.store.sessions.size,0);});
test('mutations require same-origin and matching CSRF token',async()=>{const h=harness(),{sessionCookie,data}=await h.login();for(const change of [{Origin:'https://attacker.example'},{'X-CSRF-Token':'bad'},{'Sec-Fetch-Site':'cross-site'}]){const req=mutation(sessionCookie,data.csrf,{body:'Synthetic'});Object.assign(req.headers,change);assert.equal((await h.request('/api/team/cases/'+CASE+'/notes',req)).status,403);}assert.equal(h.apiCalls.filter(c=>c.options.method==='POST').length,0);});
test('mutation forwards only authenticated server tokens and required key',async()=>{const h=harness(),{sessionCookie,data}=await h.login();const req=mutation(sessionCookie,data.csrf,{body:'Synthetic note'});req.headers.Authorization='Bearer attacker';req.headers['X-Serverless-Authorization']='Bearer attacker';assert.equal((await h.request('/api/team/cases/'+CASE+'/notes',req)).status,200);const last=h.apiCalls.at(-1);assert.equal(last.token,'synthetic.google.token');assert.equal(last.options.key,req.headers['Idempotency-Key']);assert.ok(!JSON.stringify(last.options).includes('attacker'));});
test('missing idempotency key and wrong content type rejected',async()=>{const h=harness(),{sessionCookie,data}=await h.login();let req=mutation(sessionCookie,data.csrf,{body:'Synthetic'});delete req.headers['Idempotency-Key'];assert.equal((await h.request('/api/team/cases/'+CASE+'/notes',req)).status,400);req=mutation(sessionCookie,data.csrf,{});req.headers['Content-Type']='text/plain';assert.equal((await h.request('/api/team/cases/'+CASE+'/notes',req)).status,415);});
test('oversized or non-object request body rejected',async()=>{const h=harness(),{sessionCookie,data}=await h.login();for(const [body,code] of [[[],400],[null,400],[{body:'x'.repeat(18000)},413]])assert.equal((await h.request('/api/team/cases/'+CASE+'/notes',mutation(sessionCookie,data.csrf,body))).status,code);});
test('proxy refuses unknown paths and arbitrary upstream endpoints',async()=>{const h=harness(),{sessionCookie}=await h.login();for(const path of ['/api/team/https://evil.example','/api/team/candidate-search','/api/team/cases/'+CASE+'/send','/api/team/cases/'+CASE+'%2fnotes'])assert.equal((await h.request(path,{headers:{Cookie:sessionCookie}})).status,404);});
test('manager overview is an allowlisted authenticated read endpoint',async()=>{const h=harness(),{sessionCookie}=await h.login();const r=await h.request('/api/team/manager/overview',{headers:{Cookie:sessionCookie}});assert.equal(r.status,200);assert.equal(h.apiCalls.at(-1).options.method,'GET');assert.equal(h.apiCalls.at(-1).path,'/manager/overview');});
test('jobs list and detail are allowlisted authenticated read endpoints',async()=>{const h=harness(),{sessionCookie}=await h.login();assert.equal((await h.request('/api/team/jobs?limit=50',{headers:{Cookie:sessionCookie}})).status,200);assert.equal(h.apiCalls.at(-1).path,'/jobs?limit=50');assert.equal((await h.request('/api/team/jobs/'+CASE,{headers:{Cookie:sessionCookie}})).status,200);assert.equal(h.apiCalls.at(-1).path,'/jobs/'+CASE);});
test('candidates list and detail are allowlisted authenticated read endpoints',async()=>{const h=harness(),{sessionCookie}=await h.login();assert.equal((await h.request('/api/team/candidates?limit=50',{headers:{Cookie:sessionCookie}})).status,200);assert.equal(h.apiCalls.at(-1).path,'/candidates?limit=50');assert.equal((await h.request('/api/team/candidates/'+CASE,{headers:{Cookie:sessionCookie}})).status,200);assert.equal(h.apiCalls.at(-1).path,'/candidates/'+CASE);});
test('pagination query is allowlisted bounded and single-valued',async()=>{const h=harness(),{sessionCookie}=await h.login();for(const q of ['limit=999','url=https://evil.example','limit=10&limit=20','after=bad'])assert.equal((await h.request('/api/team/cases?'+q,{headers:{Cookie:sessionCookie}})).status,400);assert.equal((await h.request('/api/team/cases?limit=50',{headers:{Cookie:sessionCookie}})).status,200);});
test('backend sensitive error body is not returned',async()=>{let bad=false;const h=harness({api:async()=>bad?new Response('candidate report secret',{status:500}):Response.json({id:'one',role:'recruiter'})});const {sessionCookie}=await h.login();bad=true;const r=await h.request('/api/team/cases',{headers:{Cookie:sessionCookie}});assert.equal(r.status,503);assert.doesNotMatch(await r.text(),/candidate report/);});
test('stale version error remains actionable without exposing backend body',async()=>{let bad=false;const h=harness({api:async()=>bad?new Response('private query',{status:409}):Response.json({id:'one',role:'manager'})});const {sessionCookie,data}=await h.login();bad=true;const r=await h.request('/api/team/cases/'+CASE+'/reassign',mutation(sessionCookie,data.csrf,{expected_version:1}));assert.equal(r.status,409);assert.match(await r.text(),/Reload/);});
test('logout requires CSRF and destroys the server session',async()=>{const h=harness(),{sessionCookie,data}=await h.login();assert.equal((await h.request('/api/team/auth/logout',mutation(sessionCookie,'bad',{}))).status,403);const r=await h.request('/api/team/auth/logout',mutation(sessionCookie,data.csrf,{}));assert.equal(r.status,200);assert.match(r.headers.get('set-cookie'),/Max-Age=0/);assert.equal((await h.request('/api/team/cases',{headers:{Cookie:sessionCookie}})).status,401);});
test('a second login revokes the old cookie',async()=>{const h=harness(),first=await h.login();const {url,loginCookie}=await h.begin();await h.request('/api/team/auth/callback?state='+url.searchParams.get('state')+'&code=new',{headers:{Cookie:loginCookie+'; '+first.sessionCookie}});assert.equal(h.store.sessions.size,1);assert.equal((await h.request('/api/team/cases',{headers:{Cookie:first.sessionCookie}})).status,401);});
test('server-side session can be used by a second gateway instance',async()=>{const store=new MemoryStore(),h=harness({store}),{sessionCookie}=await h.login();const second=harness({store,config:{encryptionKey:h.config.encryptionKey}});assert.equal((await second.request('/api/team/session',{headers:{Cookie:sessionCookie}})).status,200);});
test('responses do not allow caching or cross-origin reads',async()=>{const h=harness(),{sessionCookie}=await h.login();const r=await h.request('/api/team/session',{headers:{Cookie:sessionCookie}});assert.match(r.headers.get('cache-control'),/no-store/);assert.equal(r.headers.get('access-control-allow-origin'),null);assert.equal(r.headers.get('referrer-policy'),'no-referrer');});
test('private transport separates Google user token and service identity',async()=>{const requests=[],origin='https://private-test.run.app',now=1000;const service='e30.'+Buffer.from(JSON.stringify({aud:origin,exp:4000})).toString('base64url')+'.sig';const api=createPrivateApi(origin,{clock:()=>now,fetcher:async(url,options)=>{requests.push({url:String(url),options});return String(url).startsWith('http://metadata.')?new Response(service):Response.json({});}});await api('synthetic-user-token','/me');await api('synthetic-user-token','/cases');assert.equal(requests.length,3);assert.equal(new URL(requests[0].url).searchParams.get('audience'),origin);assert.equal(requests[1].options.headers.Authorization,'Bearer synthetic-user-token');assert.equal(requests[1].options.headers['X-Serverless-Authorization'],'Bearer '+service);assert.equal(requests[1].options.redirect,'error');});
test('metadata failure does not fall back to anonymous API call',async()=>{let calls=0;const api=createPrivateApi('https://private.run.app',{fetcher:async()=>{calls++;return new Response(null,{status:403});}});await assert.rejects(()=>api('user','/me'));assert.equal(calls,1);});
test('team page uses hash-based CSP and no client token or impersonation selector',async()=>{const r=renderTeam(true),html=await r.text();assert.match(r.headers.get('content-security-policy'),/script-src 'sha256-/);assert.match(r.headers.get('content-security-policy'),/frame-ancestors 'none'/);assert.doesNotMatch(html,/localStorage|sessionStorage|id_token|demo-manager/);assert.match(html,/Continue with Google/);assert.equal(r.headers.get('cache-control'),'no-store, max-age=0');});


test('daily priorities is an allowlisted authenticated read endpoint',async()=>{
 const h=harness(),{sessionCookie}=await h.login();
 const r=await h.request('/api/team/daily-priorities?limit=12',{headers:{Cookie:sessionCookie}});
 assert.equal(r.status,200);
 assert.equal(h.apiCalls.at(-1).options.method,'GET');
 assert.equal(h.apiCalls.at(-1).path,'/daily-priorities?limit=12');
});


test('recruiter dashboard is an allowlisted authenticated read endpoint',async()=>{
 const h=harness(),{sessionCookie}=await h.login();
 const r=await h.request('/api/team/recruiter/dashboard?week_start=2026-10-05',{headers:{Cookie:sessionCookie}});
 assert.equal(r.status,200);
 assert.equal(h.apiCalls.at(-1).path,'/recruiter/dashboard?week_start=2026-10-05');
});

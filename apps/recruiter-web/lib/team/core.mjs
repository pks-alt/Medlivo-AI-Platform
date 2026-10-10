/** Server-side browser gateway. All external dependencies are injected for testing.
 * Production wiring is in runtime.ts. No runtime impersonation/test-login switch exists.
 */
import { randomBytes, createHash, createCipheriv, createDecipheriv, timingSafeEqual } from 'node:crypto';

export const SESSION_COOKIE = '__Host-medlivo-team';
export const LOGIN_COOKIE = '__Host-medlivo-login';
export const AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth';
export const TOKEN_URL = 'https://oauth2.googleapis.com/token';
export const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
export const randomSecret = () => randomBytes(32).toString('base64url');
export const hash = value => createHash('sha256').update(value).digest('hex');
export class SafeError extends Error {
  constructor(status, message) { super(message); this.status = status; }
}
export function same(a, b) {
  if (typeof a !== 'string' || typeof b !== 'string') return false;
  const left=Buffer.from(a), right=Buffer.from(b);
  return left.length === right.length && timingSafeEqual(left,right);
}
export function cookie(request, name) {
  const matches = (request.headers.get('cookie') || '').split(';').map(x => x.trim()).filter(x => x.startsWith(name + '='));
  if (matches.length !== 1) return null;
  const value = matches[0].slice(name.length + 1);
  return /^[A-Za-z0-9_-]{43}$/.test(value) ? value : null;
}
export function cookieHeader(name, value, age) {
  return `${name}=${value}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${Math.max(0, Math.floor(age))}`;
}
export function seal(key, value, context) {
  const iv = randomBytes(12), cipher = createCipheriv('aes-256-gcm', key, iv);
  cipher.setAAD(Buffer.from(context));
  const data = Buffer.concat([cipher.update(JSON.stringify(value), 'utf8'), cipher.final()]);
  return Buffer.concat([iv, cipher.getAuthTag(), data]).toString('base64url');
}
export function unseal(key, encoded, context) {
  try {
    const data = Buffer.from(encoded, 'base64url');
    if (data.length < 29 || data.length > 20000) throw new Error();
    const decipher = createDecipheriv('aes-256-gcm', key, data.subarray(0, 12));
    decipher.setAAD(Buffer.from(context)); decipher.setAuthTag(data.subarray(12, 28));
    return JSON.parse(Buffer.concat([decipher.update(data.subarray(28)), decipher.final()]).toString('utf8'));
  } catch { throw new SafeError(401, 'Your session has ended. Please sign in again.'); }
}
export function securityHeaders(extra = {}) {
  return { 'Cache-Control': 'no-store, max-age=0', 'Pragma': 'no-cache',
    'Referrer-Policy': 'no-referrer', 'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY', 'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
    ...extra };
}
function json(data, status = 200) {
  return new Response(JSON.stringify(data), {status, headers: securityHeaders({'Content-Type':'application/json; charset=utf-8'})});
}
function redirect(location, cookies = []) {
  const headers = new Headers(securityHeaders({Location: location}));
  for (const value of cookies) headers.append('Set-Cookie', value);
  return new Response(null, {status:303, headers});
}
export async function boundedBytes(response, limit = 104857600) {
  if (!response.body) return Buffer.alloc(0);
  const reader=response.body.getReader(); const chunks=[]; let size=0;
  try {
    for (;;) {
      const {done,value}=await reader.read(); if(done)break;
      size+=value.length;
      if(size>limit){await reader.cancel();throw new SafeError(502,'The service response was too large.');}
      chunks.push(Buffer.from(value));
    }
    return Buffer.concat(chunks);
  } finally { reader.releaseLock(); }
}
export async function boundedText(response, limit = 1048576) {
  if (!response.body) return '';
  const reader = response.body.getReader(); const chunks = []; let size = 0;
  try {
    for (;;) {
      const {done, value} = await reader.read(); if (done) break;
      size += value.length;
      if (size > limit) { await reader.cancel(); throw new SafeError(502, 'The service response was too large.'); }
      chunks.push(Buffer.from(value));
    }
    return Buffer.concat(chunks).toString('utf8');
  } finally { reader.releaseLock(); }
}
export function validateConfig(env) {
  if (env.TEAM_WORKSPACE_ENABLED !== 'true') return null;
  const fail = () => { throw new SafeError(503, 'Team sign-in is not configured. Please contact your administrator.'); };
  const origin = env.TEAM_APP_ORIGIN, apiUrl = env.TEAM_API_URL;
  try {
    for (const value of [origin, apiUrl]) {
      const u = new URL(value);
      if (u.protocol !== 'https:' || u.origin !== value || u.username || u.password || u.port) fail();
    }
    if (!new URL(apiUrl).hostname.endsWith('.run.app')) fail();
  } catch { fail(); }
  const clientId = env.TEAM_GOOGLE_CLIENT_ID, clientSecret = env.TEAM_GOOGLE_CLIENT_SECRET;
  const domain = env.TEAM_GOOGLE_HOSTED_DOMAIN || 'medlivo.com';
  const encryptionKey = Buffer.from(env.TEAM_SESSION_KEY || '', 'base64');
  if (!clientId?.endsWith('.apps.googleusercontent.com') || !clientSecret ||
      !/^[a-z0-9]+([a-z0-9.-]*[a-z0-9])?$/.test(domain) || encryptionKey.length !== 32 ||
      encryptionKey.toString('base64') !== env.TEAM_SESSION_KEY ||
      !env.TEAM_SESSION_DATABASE_URL?.startsWith('postgresql://')) fail();
  // TLS or Cloud SQL Unix socket are required for the session database in production.
  // WHATWG URL rejects PostgreSQL socket URLs with an intentionally empty network host
  // (postgresql://user:pass@/db?host=/cloudsql/...), so validate that supported form
  // using a localhost placeholder only for parsing. The original URL is passed to pg.
  const databaseUrl = env.TEAM_SESSION_DATABASE_URL;
  const socketForm = /^postgresql:\/\/[^/?#@]+:[^/?#@]+@\//.test(databaseUrl);
  let db;
  try {
    db = new URL(socketForm ? databaseUrl.replace('@/', '@localhost/') : databaseUrl);
  } catch { fail(); }
  const host = db.searchParams.get('host');
  const cloudSqlSocket = socketForm && host?.startsWith('/cloudsql/');
  const verifiedTls = !socketForm && db.protocol === 'postgresql:' && db.hostname &&
    db.searchParams.get('sslmode') === 'verify-full';
  if (!(cloudSqlSocket || verifiedTls)) fail();
  return {origin, apiUrl, clientId, clientSecret, domain, encryptionKey,
    databaseUrl:env.TEAM_SESSION_DATABASE_URL, sessionSeconds:3300, idleSeconds:1800};
}
function endpoint(path, method, query) {
  const id = '[0-9a-fA-F-]{36}', root = `/cases/${id}`;
  const read = [
    '/me', '/cases', '/jobs', `/jobs/${id}`, `/jobs/${id}/operational`,
    '/candidates', `/candidates/${id}`, `/candidates/${id}/best-jobs`,
    '/manager/overview', '/manager/weekly-review', '/manager/match-quality', '/manager/operational-audit',
    '/recruiter/dashboard', '/recruiter/follow-ups', '/daily-priorities', '/work-queue',
    '/admin/users', '/admin/teams', '/admin/audit', '/admin/operations',
    '/job-intake/batches', `/job-intake/batches/${id}/items`, '/job-intake/mappings',
    `/recruiters/${id}/weekly-goals`, '/job-publications', `/job-publications/${id}`,
    '/economic-config/assumptions', '/economic-config/customers', '/economic-config/customer-rules',
    `/economic-config/customers/${id}`,
    `/margin/snapshots/${id}`, '/margin/history', '/margin/management-summary',
    '/margin/negative-gm-exceptions',
    '/submission-studio/templates', '/submission-studio/packages', `/submission-studio/packages/${id}`,
    `/submission-studio/packages/${id}/download`,
    '/funnel', `/funnel/${id}/${id}`,
    root, `${root}/(?:notes|tasks|audit|eligible-owners)`
  ];
  const post = [
    '/admin/users', `/matches/${id}/feedback`, '/job-intake/upload', '/job-intake/batches',
    `/job-intake/batches/${id}/rows`, '/job-publications', `/job-publications/${id}/decision`,
    '/economic-config/bootstrap-assumptions', '/economic-config/assumptions', '/economic-config/customers',
    '/margin/locums-pay-package-snapshots', '/margin/w2-pay-package-snapshots', '/margin/snapshots',
    `/margin/snapshots/${id}/discussions`, `/margin/snapshots/${id}/finalize`,
    `/margin/negative-gm-exceptions/${id}/decision`,
    '/submission-studio/templates', '/submission-studio/bootstrap-templates',
    `/submission-studio/jobs/${id}/candidates/${id}/prepare`,
    `/submission-studio/packages/${id}/compose-ai`,
    `/submission-studio/packages/${id}/items/${id}/review`,
    `/submission-studio/packages/${id}/finalize`,
    `${root}/(?:notes|tasks|reassign)`
  ];
  const put = [
    '/job-intake/mappings', `/recruiters/${id}/weekly-goals`,
    `/jobs/${id}/operational`, `/jobs/${id}/assignment`,
    `/job-intake/batches/${id}/items/${id}/decision`,
    `/funnel/${id}/${id}/start-readiness`,
    `/funnel/${id}/${id}/start-readiness/items`
  ];
  const patch = [`/admin/users/${id}`, `${root}/tasks/${id}`];
  const patterns = method === 'GET' ? read : method === 'POST' ? post :
    method === 'PUT' ? put : method === 'PATCH' ? patch : [];
  if (!patterns.some(p => new RegExp('^' + p + '$').test(path))) throw new SafeError(404, 'This action is not available.');
  for (const segment of path.split('/')) if (segment.includes('-') && segment.length === 36 && !UUID.test(segment)) throw new SafeError(400, 'Invalid work item.');

  const params = new URLSearchParams();
  for (const key of new Set(query.keys())) {
    const value = query.get(key);
    if (method !== 'GET' || query.getAll(key).length !== 1) throw new SafeError(400, 'Invalid request parameters.');
    if (key === 'after' && UUID.test(value)) params.set(key, value);
    else if (key === 'limit' && /^(?:[1-9][0-9]{0,2}|500)$/.test(value) && Number(value) <= 500) params.set(key, value);
    else if (key === 'matches_per_job' && /^(?:[1-9]|10)$/.test(value)) params.set(key, value);
    else if (key === 'team_id' && UUID.test(value)) params.set(key, value);
    else if (key === 'week_start' && /^20[0-9]{2}-[01][0-9]-[0-3][0-9]$/.test(value)) params.set(key, value);
    else if (key === 'status' && ['open','done','all','pending','approved','rejected'].includes(value)) params.set(key, value);
    else if (key === 'division' && ['Rehabilitation','Nursing & Allied','Locum Tenens'].includes(value)) params.set(key, value);
    else if (['job_id','candidate_id','object_id'].includes(key) && UUID.test(value)) params.set(key, value);
    else if (key === 'profile' && /^[a-z0-9_]{1,80}$/.test(value)) params.set(key, value);
    else if (key === 'object_type' && /^[a-z0-9_]{1,80}$/.test(value)) params.set(key, value);
    else throw new SafeError(400, 'Invalid request parameters.');
  }
  return path + (params.size ? '?' + params : '');
}
export function createGateway({config, store, verifyIdToken, api, fetcher = fetch, clock = () => Math.floor(Date.now()/1000)}) {
  const tokenCookie = value => cookieHeader(SESSION_COOKIE, value, config.sessionSeconds);
  const clearLogin = cookieHeader(LOGIN_COOKIE, '', 0), clearSession = cookieHeader(SESSION_COOKIE, '', 0);
  const callbackUri = config.origin + '/api/team/auth/callback';
  async function session(request) {
    const raw = cookie(request, SESSION_COOKIE);
    if (!raw) throw new SafeError(401, 'Please sign in to your team workspace.');
    const id = hash(raw), record = await store.getSession(id, clock(), config.idleSeconds);
    if (!record) throw new SafeError(401, 'Your session has ended. Please sign in again.');
    const data = unseal(config.encryptionKey, record.ciphertext, 'session:' + id);
    if (!data.idToken || !data.csrf || data.expires <= clock()) throw new SafeError(401, 'Your session has ended. Please sign in again.');
    return {...data, id};
  }
  function originCheck(request) {
    if (request.headers.get('origin') !== config.origin || request.headers.get('sec-fetch-site') === 'cross-site')
      throw new SafeError(403, 'Please perform this action from your team workspace.');
  }
  function csrfCheck(request, data) {
    originCheck(request);
    if (!same(request.headers.get('x-csrf-token'), data.csrf)) throw new SafeError(403, 'Please reload the page before saving.');
  }
  async function start(request) {
    if (request.headers.get('sec-fetch-site') === 'cross-site') throw new SafeError(403, 'Open the sign-in page first.');
    const old = cookie(request, LOGIN_COOKIE);
    if (old) await store.removeLogin(hash(old));
    const oldSession = cookie(request, SESSION_COOKIE);
    if (oldSession) await store.removeSession(hash(oldSession));
    const binding = randomSecret(), state = randomSecret(), nonce = randomSecret(), verifier = randomSecret();
    const id = hash(binding), now = clock();
    await store.saveLogin(id, hash(state), seal(config.encryptionKey, {nonce,verifier}, 'login:' + id), now+600, now);
    const url = new URL(AUTH_URL);
    url.search = new URLSearchParams({client_id:config.clientId, redirect_uri:callbackUri, response_type:'code',
      scope:'openid email', state, nonce, hd:config.domain, prompt:'select_account',
      code_challenge:createHash('sha256').update(verifier).digest('base64url'), code_challenge_method:'S256'}).toString();
    return redirect(url.href, [cookieHeader(LOGIN_COOKIE, binding, 600),clearSession]);
  }
  async function callback(request, url) {
    const binding = cookie(request, LOGIN_COOKIE), state = url.searchParams.get('state');
    if (!binding || !/^[A-Za-z0-9_-]{43}$/.test(state || '') || url.searchParams.getAll('state').length !== 1)
      return redirect('/team?error=login', [clearLogin]);
    const id = hash(binding), record = await store.consumeLogin(id, hash(state), clock());
    if (!record) return redirect('/team?error=login', [clearLogin]);
    try {
      const {nonce,verifier} = unseal(config.encryptionKey, record.ciphertext, 'login:' + id);
      const code = url.searchParams.get('code');
      if (url.searchParams.has('error') || !code || code.length > 4096 || url.searchParams.getAll('code').length !== 1) throw new Error();
      const response = await fetcher(TOKEN_URL, {method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded', Accept:'application/json'},
        body:new URLSearchParams({client_id:config.clientId,client_secret:config.clientSecret,code,code_verifier:verifier,redirect_uri:callbackUri,grant_type:'authorization_code'}),
        redirect:'error', cache:'no-store', signal:AbortSignal.timeout(10000)});
      if (!response.ok) throw new Error();
      const tokens = JSON.parse(await boundedText(response, 24000));
      if (typeof tokens.id_token !== 'string' || tokens.id_token.length > 8192) throw new Error();
      const claims = await verifyIdToken(tokens.id_token, nonce);
      const expiry = Math.min(claims.exp - 30, clock()+config.sessionSeconds);
      if (!claims.sub || !Number.isFinite(expiry) || expiry <= clock()) throw new Error();
      // Membership, active status and roles must come from the PRIVATE API/database.
      const member = await api(tokens.id_token, '/me', {method:'GET'});
      if (member.status === 403) return redirect('/team?error=access', [clearLogin]);
      if (member.status !== 200) throw new Error();
      const old = cookie(request, SESSION_COOKIE); if (old) await store.removeSession(hash(old));
      const raw = randomSecret(), sid = hash(raw), csrf = randomSecret();
      await store.saveSession(sid, seal(config.encryptionKey, {idToken:tokens.id_token,csrf,sub:claims.sub,expires:expiry}, 'session:'+sid), expiry, Math.min(expiry,clock()+config.idleSeconds));
      return redirect('/team', [clearLogin, cookieHeader(SESSION_COOKIE, raw, expiry-clock())]);
    } catch { return redirect('/team?error=login', [clearLogin]); }
  }
  async function proxy(request, url, data) {
    const method = request.method, resource = endpoint(url.pathname.slice('/api/team'.length), method, url.searchParams);
    let body, key, contentType;
    if (method !== 'GET') {
      csrfCheck(request,data);
      key = request.headers.get('idempotency-key');
      if (!UUID.test(key || '')) throw new SafeError(400, 'A request identifier is required. Reload and try again.');
      contentType = request.headers.get('content-type') || '';
      const isXlsxUpload = resource === '/job-intake/upload' && method === 'POST';
      if (isXlsxUpload) {
        if (!contentType.toLowerCase().startsWith('multipart/form-data;')) throw new SafeError(415,'An Excel upload is required.');
        const declared = Number(request.headers.get('content-length') || '0');
        if (Number.isFinite(declared) && declared > 5 * 1024 * 1024) throw new SafeError(413,'The spreadsheet is too large.');
        const bytes = await request.arrayBuffer();
        if (bytes.byteLength > 5 * 1024 * 1024) throw new SafeError(413,'The spreadsheet is too large.');
        body = bytes;
      } else {
        if (contentType.split(';')[0].trim() !== 'application/json') throw new SafeError(415,'A JSON request is required.');
        try { body = await boundedText(request, resource.includes('/job-intake/') ? 1048576 : 16384); }
        catch (error) { if (error instanceof SafeError) throw new SafeError(413,'The request body is too large.'); throw error; }
        try { const value=JSON.parse(body); if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error(); }
        catch { throw new SafeError(400, 'Invalid request body.'); }
      }
    }
    const response = await api(data.idToken, resource, {method,body,key,contentType});
    if (response.status === 401) { await store.removeSession(data.id); throw new SafeError(401, 'Your session has ended. Please sign in again.'); }
    if (!response.ok) {
      const message = {403:'You do not have permission for this action.',404:'Work item not found.',
        409:'This item changed or the request was already used. Reload before saving.',422:'Check the fields and select an eligible team member.'}[response.status];
      throw new SafeError(message ? response.status : 503, message || 'The team service is unavailable. Please try again.');
    }
    if (resource.endsWith('/download')) {
      const media=(response.headers.get('content-type')||'').split(';')[0].trim().toLowerCase();
      if(media!=='application/zip')throw new SafeError(503,'The submission package download is unavailable.');
      const disposition=response.headers.get('content-disposition')||'';
      const match=/^attachment; filename="([A-Za-z0-9._ -]{1,180})"$/.exec(disposition);
      if(!match)throw new SafeError(503,'The submission package download is unavailable.');
      const bytes=await boundedBytes(response,100*1024*1024);
      return new Response(bytes,{status:response.status,headers:securityHeaders({
        'Content-Type':'application/zip',
        'Content-Disposition':`attachment; filename="${match[1]}"`
      })});
    }
    return json(JSON.parse(await boundedText(response)), response.status);
  }
  return async function handle(request) {
    const url = new URL(request.url);
    try {
      if (url.pathname === '/api/team/auth/start' && request.method === 'GET') return await start(request);
      if (url.pathname === '/api/team/auth/callback' && request.method === 'GET') return await callback(request,url);
      // Avoid cookie-authenticated endpoints being used cross-origin, even for reads.
      if (request.headers.get('sec-fetch-site') === 'cross-site') throw new SafeError(403, 'Open your team workspace directly.');
      const data = await session(request);
      if (url.pathname === '/api/team/auth/logout' && request.method === 'POST') {
        csrfCheck(request,data); await store.removeSession(data.id);
        const response = json({signedOut:true}); response.headers.append('Set-Cookie',clearSession); return response;
      }
      if (url.pathname === '/api/team/session' && request.method === 'GET') {
        const response = await api(data.idToken, '/me', {method:'GET'});
        if ([401,403].includes(response.status)) {
          await store.removeSession(data.id); throw new SafeError(401,'Your access ended. Please sign in again or contact your administrator.');
        }
        if (response.status !== 200) throw new SafeError(503,'The team service is unavailable. Please try again.');
        const member = JSON.parse(await boundedText(response, 16384));
        return json({member:{id:member.id,display_name:member.display_name,role:member.role},csrf:data.csrf,expires:data.expires});
      }
      return await proxy(request,url,data);
    } catch (error) {
      const safe = error instanceof SafeError ? error : new SafeError(503,'The team service is unavailable. Please try again.');
      const response = json({detail:safe.message}, safe.status);
      if (safe.status === 401) response.headers.append('Set-Cookie',clearSession);
      return response;
    }
  };
}

import 'server-only';
import { Pool } from 'pg';
import { createGateway, securityHeaders, validateConfig } from './core.mjs';
import { googleVerifier } from './google.mjs';
import { createPrivateApi } from './private-api.mjs';
import { PostgresSessionStore } from './session-store.mjs';
import { renderTeam } from './ui.mjs';

let gateway: ((request: Request) => Promise<Response>) | undefined;
let configFailed = false;
function initialize() {
  if (gateway || configFailed) return;
  try {
    const config = validateConfig(process.env);
    if (!config) return;
    // Cloud Run metadata credentials are required. No personal-token env fallback.
    if (!process.env.K_SERVICE) throw new Error('Cloud Run runtime required');
    const rawDatabaseUrl = config.databaseUrl;
    const socketForm = /^postgresql:\/\/([^:@/?#]+):([^@/?#]+)@\/([^?#]+)\?/.exec(rawDatabaseUrl);
    let poolConfig: ConstructorParameters<typeof Pool>[0];
    if (socketForm) {
      const parsed = new URL(rawDatabaseUrl.replace('@/', '@localhost/'));
      const host = parsed.searchParams.get('host');
      if (!host?.startsWith('/cloudsql/')) throw new Error('Cloud SQL socket required');
      poolConfig = {
        user: decodeURIComponent(socketForm[1]),
        password: decodeURIComponent(socketForm[2]),
        database: decodeURIComponent(socketForm[3]),
        host,
      };
    } else {
      poolConfig = {connectionString:rawDatabaseUrl};
    }
    const pool = new Pool({...poolConfig,max:5,connectionTimeoutMillis:5000,
      idleTimeoutMillis:30000,statement_timeout:10000,query_timeout:10000});
    // Pool errors must not print connection strings or parameters.
    pool.on('error', () => { /* request errors return a sanitized 503 */ });
    gateway = createGateway({config,store:new PostgresSessionStore(pool),
      verifyIdToken:googleVerifier(config.clientId,config.domain),api:createPrivateApi(config.apiUrl)});
  } catch { configFailed = true; }
}
export async function teamApi(request: Request): Promise<Response> {
  initialize();
  if (!gateway) return new Response(JSON.stringify({detail:'Team sign-in is not configured. Contact your administrator.'}),
    {status:503,headers:securityHeaders({'Content-Type':'application/json'})});
  return gateway(request);
}
export async function teamPage(): Promise<Response> {
  initialize();
  return renderTeam(Boolean(gateway));
}

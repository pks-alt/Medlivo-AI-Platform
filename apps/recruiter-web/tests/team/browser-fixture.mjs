/** TEST ONLY. HTTPS loopback harness around the production gateway and real private API.
 * Google is simulated on another loopback site. No production route imports this file.
 * Diagnostics contain route paths/statuses only, never token values or callback queries.
 */
import {createServer} from 'node:https';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash,generateKeyPairSync,sign,randomBytes,randomUUID} from 'node:crypto';
import {spawn} from 'node:child_process';
import {createGateway} from '../../lib/team/core.mjs';
import {renderTeam} from '../../lib/team/ui.mjs';
import {googleVerifier} from '../../lib/team/google.mjs';
import {PostgresSessionStore} from '../../lib/team/session-store.mjs';
import {Pool} from 'pg';
if(!process.env.TEAM_TEST_POSTGRES_URL || !process.env.TEAM_FIXTURE_DIR)throw new Error('Disposable test database and directory required');
const origin='https://localhost:9443',now=()=>Math.floor(Date.now()/1000);
const {privateKey,publicKey}=generateKeyPairSync('rsa',{modulusLength:2048}),codes=new Map();
const result=(value,status=200)=>Response.json(value,{status});
const schema='wb_browser_'+randomUUID().replaceAll('-','');
const control=new Pool({connectionString:process.env.TEAM_TEST_POSTGRES_URL});await control.query('CREATE SCHEMA '+schema);
const pool=new Pool({connectionString:process.env.TEAM_TEST_POSTGRES_URL,options:'-c search_path='+schema});
await pool.query(await readFile(new URL('../../../../services/team-workspace/migrations/002_browser_sessions.sql',import.meta.url),'utf8'));
const store=new PostgresSessionStore(pool);
const file=process.env.TEAM_FIXTURE_DIR+'/public.pem';await writeFile(file,publicKey.export({type:'spki',format:'pem'}));
const backend=spawn('python',['tests/team/backend_fixture.py'],{env:{...process.env,TEAM_FIXTURE_PUBLIC_KEY:file},stdio:['ignore','ignore','inherit']});
let ready=false;
for(let i=0;i<80;i++){try{if((await fetch('http://127.0.0.1:9409/health')).ok){ready=true;break;}}catch{}await new Promise(r=>setTimeout(r,250));}
if(!ready)throw new Error('Synthetic private API fixture did not start');
const verify=googleVerifier('test.apps.googleusercontent.com','example.test',publicKey);
const gateway=createGateway({config:{origin,apiUrl:'https://private-test.run.app',clientId:'test.apps.googleusercontent.com',clientSecret:'test-only-secret',domain:'example.test',encryptionKey:randomBytes(32),sessionSeconds:3300,idleSeconds:1800},store,
 api:async(token,path,options)=>{
  const r=await fetch('http://127.0.0.1:9409/api/v1/team'+path,{method:options.method,headers:{Authorization:'Bearer '+token,'Content-Type':'application/json',...(options.key?{'Idempotency-Key':options.key}:{})},body:options.body,redirect:'error'});
  console.log('TEST private API',path.split('?')[0],r.status);return r;
 },
 verifyIdToken:async(...args)=>{const r=await verify(...args);console.log('TEST ID token verified');return r;},
 fetcher:async(url,options)=>{
  if(String(url)!=='https://oauth2.googleapis.com/token')throw new Error('Unexpected test token endpoint');
  const code=options.body.get('code'),flow=codes.get(code);codes.delete(code);
  if(!flow||createHash('sha256').update(options.body.get('code_verifier')).digest('base64url')!==flow.challenge)return result({},400);
  console.log('TEST PKCE challenge matched');
  const claims={iss:'https://accounts.google.com',aud:'test.apps.googleusercontent.com',sub:flow.actor,email:flow.actor+'@example.test',hd:'example.test',email_verified:true,nonce:flow.nonce,iat:now(),exp:now()+3600};
  const prefix=Buffer.from(JSON.stringify({alg:'RS256',kid:'synthetic'})).toString('base64url')+'.'+Buffer.from(JSON.stringify(claims)).toString('base64url');
  return result({id_token:prefix+'.'+sign('RSA-SHA256',Buffer.from(prefix),privateKey).toString('base64url')});
 }});
const server=createServer({key:await readFile(process.env.TEAM_TEST_TLS_KEY),cert:await readFile(process.env.TEAM_TEST_TLS_CERT)},async(req,res)=>{
 try{
  const url=new URL(req.url,origin);let response;
  if(url.pathname==='/_test/ready')response=result({ready:true,realApi:true,postgres:true});
  else if(url.pathname==='/_test/identity-provider'){
   const code=randomUUID();codes.set(code,{actor:url.searchParams.get('actor'),nonce:url.searchParams.get('nonce'),challenge:url.searchParams.get('code_challenge')});
   const callback=new URL('/api/team/auth/callback',origin);callback.searchParams.set('state',url.searchParams.get('state'));callback.searchParams.set('code',code);
   response=new Response(null,{status:303,headers:{Location:callback.href}});
  }else if(url.pathname==='/team')response=renderTeam(true);
  else if(url.pathname.startsWith('/api/team')){
   const parts=[];for await(const chunk of req)parts.push(chunk);
   response=await gateway(new Request(url,{method:req.method,headers:req.headers,...(parts.length?{body:Buffer.concat(parts)}:{})}));
  }else response=new Response(null,{status:404});
  // Rewrite ONLY this test server's Google redirect to a loopback provider on
  // another site (127.0.0.1 vs localhost), exercising SameSite=Lax callbacks.
  // Production core/runtime have no provider override or actor-cookie switch.
  if(url.pathname==='/api/team/auth/start'&&response.status===303){
   const target=new URL(response.headers.get('location'));
   if(target.origin!=='https://accounts.google.com')throw new Error('Unexpected authorization target');
   const simulated=new URL('https://127.0.0.1:9443/_test/identity-provider');simulated.search=target.search;
   const actor=(req.headers.cookie||'').split(';').map(x=>x.trim()).find(x=>x.startsWith('medlivo_test_actor='))?.split('=')[1];
   simulated.searchParams.set('actor',actor||'unprovisioned');response.headers.set('Location',simulated.href);
  }
  console.log('TEST browser HTTP',url.pathname,response.status,'cookies present',Boolean(req.headers.cookie),'location',response.headers.has('location')?new URL(response.headers.get('location'),origin).pathname:'none');
  res.statusCode=response.status;for(const [k,v]of response.headers)if(k!=='set-cookie')res.setHeader(k,v);
  if(response.headers.getSetCookie().length)res.setHeader('Set-Cookie',response.headers.getSetCookie());
  res.end(Buffer.from(await response.arrayBuffer()));
 }catch(e){console.log('TEST fixture exception type',e?.constructor?.name);res.statusCode=500;res.end('Fixture error');}
});
server.listen(9443,'127.0.0.1',()=>console.log('TEST fixture ready'));
async function close(){server.close();backend.kill();await pool.end();await control.query('DROP SCHEMA '+schema+' CASCADE');await control.end();process.exit(0);}
process.on('SIGTERM',close);process.on('SIGINT',close);

/** Integration-only HTTPS server: Google is simulated, production gateway and UI are reused.
 * Binds ONLY loopback; never imported by production routes. No production env bypass.
 */
import {createServer} from 'node:https';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash,generateKeyPairSync,sign,verify,randomBytes,randomUUID} from 'node:crypto';
import {spawn} from 'node:child_process';
import {createGateway} from '../../lib/team/core.mjs';
import {renderTeam} from '../../lib/team/ui.mjs';
import {MemoryStore,CASE,USER,OTHER,MANAGER} from './helpers.mjs';
import {PostgresSessionStore} from '../../lib/team/session-store.mjs';
const origin='https://localhost:9443',now=()=>Math.floor(Date.now()/1000);
const {privateKey,publicKey}=generateKeyPairSync('rsa',{modulusLength:2048});
const codes=new Map(),tokens=new Map(),receipts=new Map();
const people={'recruiter-a':{id:USER,display_name:'Alex Chen',role:'recruiter'},'recruiter-b':{id:OTHER,display_name:'Taylor Morgan',role:'recruiter'},'manager-a':{id:MANAGER,display_name:'Jordan Lee',role:'manager'}};
const item={id:CASE,title:'TEST · Physical Therapist · Dallas',owner_user_id:USER,version:1},notes=[],tasks=[],audit=[];
const result=(value,status=200)=>Response.json(value,{status});
let backendProcess,pgPool,pgControl,pgSchema;
let store=new MemoryStore();
if(process.env.TEAM_TEST_POSTGRES_URL){
 const {Pool}=await import('pg');pgSchema='wb_browser_'+randomUUID().replaceAll('-','');pgControl=new Pool({connectionString:process.env.TEAM_TEST_POSTGRES_URL});await pgControl.query('CREATE SCHEMA '+pgSchema);
 pgPool=new Pool({connectionString:process.env.TEAM_TEST_POSTGRES_URL,options:'-c search_path='+pgSchema});
 await pgPool.query(await readFile(new URL('../../../../services/team-workspace/migrations/002_browser_sessions.sql',import.meta.url),'utf8'));
 store=new PostgresSessionStore(pgPool);
}
let realApi=false;
if(process.env.TEAM_E2E_REAL_API==='1'){
 const file=process.env.TEAM_FIXTURE_DIR+'/public.pem';await writeFile(file,publicKey.export({type:'spki',format:'pem'}));
 backendProcess=spawn('python',['tests/team/backend_fixture.py'],{env:{...process.env,TEAM_FIXTURE_PUBLIC_KEY:file},stdio:['ignore','ignore','inherit']});
 for(let i=0;i<80;i++){try{if((await fetch('http://127.0.0.1:9409/health')).ok){realApi=true;break;}}catch{}await new Promise(r=>setTimeout(r,250));}
 if(!realApi)throw new Error('Synthetic private API fixture did not start');
}
async function mockApi(token,path,options){
 const claims=tokens.get(token),member=people[claims?.sub];if(!member)return result({},403);
 if(path==='/me')return result(member);
 const permitted=member.role==='manager'||item.owner_user_id===member.id;
 if(path.startsWith('/cases?')||path==='/cases')return result({items:permitted?[item]:[],next_cursor:null});
 if(!path.startsWith('/cases/'+CASE)||!permitted)return result({},404);
 if(path==='/cases/'+CASE)return result(item);
 const type=path.split('/')[3]?.split('?')[0],body=options.body?JSON.parse(options.body):null;
 if(options.method==='GET')return result(type==='eligible-owners'?{items:member.role==='manager'?Object.values(people).filter(p=>p.role==='recruiter'):[],truncated:false}:{items:({notes,tasks,audit})[type]||[],next_cursor:null});
 const key=member.id+':'+options.key;if(receipts.has(key))return result(receipts.get(key),201);
 let value;
 if(type==='notes'){value={id:randomUUID(),body:body.body,actor_user_id:member.id,created_at:new Date().toISOString()};notes.push(value);}
 if(type==='tasks'&&options.method==='POST'){value={id:randomUUID(),title:body.title,due_at:body.due_at,status:'open',version:1};tasks.push(value);}
 if(type==='tasks'&&options.method==='PATCH'){value=tasks.find(t=>t.id===path.split('/')[4]);if(!value)return result({},404);if(value.version!==body.expected_version)return result({},409);value.status=body.status;value.version++;}
 if(type==='reassign'){if(member.role!=='manager')return result({},403);if(item.version!==body.expected_version)return result({},409);item.owner_user_id=body.owner_user_id;item.version++;value=item;}
 audit.push({id:randomUUID(),action:type==='notes'?'note.created':type==='reassign'?'case.reassigned':'task.updated',actor_user_id:member.id,created_at:new Date().toISOString(),details:{reason:body.reason}});
 receipts.set(key,value);return result(value,options.method==='POST'&&type!=='reassign'?201:200);
}
const api=realApi?async(token,path,options)=>fetch('http://127.0.0.1:9409/api/v1/team'+path,{method:options.method,headers:{Authorization:'Bearer '+token,'Content-Type':'application/json',...(options.key?{'Idempotency-Key':options.key}:{})},body:options.body,redirect:'error'}):mockApi;
let verifier=async(token,nonce)=>{const claims=tokens.get(token);if(!claims||claims.nonce!==nonce||claims.exp<=now())throw new Error('invalid test token');const parts=token.split('.');if(!verify('RSA-SHA256',Buffer.from(parts[0]+'.'+parts[1]),publicKey,Buffer.from(parts[2],'base64url')))throw new Error();return {sub:claims.sub,exp:claims.exp};};
try{const {googleVerifier}=await import('../../lib/team/google.mjs');verifier=googleVerifier('test.apps.googleusercontent.com','example.test',publicKey);}
catch(e){if(process.env.GITHUB_ACTIONS)throw e;}
const gateway=createGateway({config:{origin,apiUrl:'https://private-test.run.app',clientId:'test.apps.googleusercontent.com',clientSecret:'test-only-secret',domain:'example.test',encryptionKey:randomBytes(32),sessionSeconds:3300,idleSeconds:1800},store,api,verifyIdToken:verifier,
 fetcher:async(url,options)=>{
  const code=options.body.get('code'),flow=codes.get(code);codes.delete(code);
  if(!flow||createHash('sha256').update(options.body.get('code_verifier')).digest('base64url')!==flow.challenge)return result({},400);
  const claims={iss:'https://accounts.google.com',aud:'test.apps.googleusercontent.com',sub:flow.actor,hd:'example.test',email_verified:true,nonce:flow.nonce,iat:now(),exp:now()+3600};
  const prefix=Buffer.from(JSON.stringify({alg:'RS256',kid:'synthetic'})).toString('base64url')+'.'+Buffer.from(JSON.stringify(claims)).toString('base64url');
  const token=prefix+'.'+sign('RSA-SHA256',Buffer.from(prefix),privateKey).toString('base64url');tokens.set(token,claims);return result({id_token:token});
 }});
const server=createServer({key:await readFile(process.env.TEAM_TEST_TLS_KEY),cert:await readFile(process.env.TEAM_TEST_TLS_CERT)},async(req,res)=>{
 try{
  const url=new URL(req.url,origin);let response;
  if(url.pathname==='/_test/ready')response=result({ready:true,realApi,postgres:Boolean(pgPool)});
  else if(url.pathname==='/_test/authorize'){
   const code=randomUUID();codes.set(code,{actor:url.searchParams.get('actor'),nonce:url.searchParams.get('nonce'),challenge:url.searchParams.get('challenge')});response=result({code});
  }else if(url.pathname==='/team')response=renderTeam(true);
  else if(url.pathname.startsWith('/api/team')){
   const parts=[];for await(const chunk of req)parts.push(chunk);
   response=await gateway(new Request(url,{method:req.method,headers:req.headers,...(parts.length?{body:Buffer.concat(parts)}:{})}));
  }else response=new Response(null,{status:404});
  res.statusCode=response.status;for(const [k,v]of response.headers)if(k!=='set-cookie')res.setHeader(k,v);if(response.headers.getSetCookie().length)res.setHeader('Set-Cookie',response.headers.getSetCookie());res.end(Buffer.from(await response.arrayBuffer()));
 }catch{res.statusCode=500;res.end('Fixture error');}
});
server.listen(9443,'127.0.0.1',()=>console.log('TEST fixture ready'));
async function close(){server.close();backendProcess?.kill();if(pgPool)await pgPool.end();if(pgControl){await pgControl.query('DROP SCHEMA '+pgSchema+' CASCADE');await pgControl.end();}process.exit(0);}
process.on('SIGTERM',close);process.on('SIGINT',close);

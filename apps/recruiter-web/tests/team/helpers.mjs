/** Synthetic test dependencies. Never imported by app/ or lib/. */
import {randomBytes,randomUUID} from 'node:crypto';
import {createGateway,hash,SESSION_COOKIE,LOGIN_COOKIE,SafeError} from '../../lib/team/core.mjs';
export const ORIGIN='https://workspace.example.test';
export const CASE='00000000-0000-0000-0000-000000000100';
export const USER='00000000-0000-0000-0000-000000000010';
export const OTHER='00000000-0000-0000-0000-000000000011';
export const MANAGER='00000000-0000-0000-0000-000000000012';
export class MemoryStore {
 constructor(){this.logins=new Map();this.sessions=new Map();}
 async saveLogin(id,state,ciphertext,expires,now){this.logins.set(id,{state,ciphertext,expires,now});}
 async consumeLogin(id,state,now){const row=this.logins.get(id);if(!row||row.state!==state||row.expires<=now)return null;this.logins.delete(id);return row;}
 async removeLogin(id){this.logins.delete(id);}
 async saveSession(id,ciphertext,expires,idle){this.sessions.set(id,{ciphertext,expires,idle});}
 async getSession(id,now,idle){const row=this.sessions.get(id);if(!row||row.expires<=now||row.idle<=now)return null;row.idle=Math.min(row.expires,now+idle);return row;}
 async removeSession(id){this.sessions.delete(id);}
}
export function harness(overrides={}){
 let now=Math.floor(Date.now()/1000); const store=overrides.store||new MemoryStore();
 const requests=[],apiCalls=[];let currentNonce='';
 const config={origin:ORIGIN,apiUrl:'https://private-test.run.app',clientId:'test.apps.googleusercontent.com',clientSecret:'synthetic-oauth-secret',domain:'example.test',encryptionKey:randomBytes(32),sessionSeconds:3300,idleSeconds:1800,...overrides.config};
 const mockApi=async(token,path,options)=>{apiCalls.push({token,path,options});return Response.json(path==='/me'?{id:USER,display_name:'Alex Chen',role:'recruiter'}:{items:[],next_cursor:null});};
 const mockFetcher=async(url,options)=>{requests.push({url:String(url),options});return Response.json({id_token:'synthetic.google.token',access_token:'never-expose-this'});};
 const gateway=createGateway({config,store,clock:()=>now,api:overrides.api||mockApi,fetcher:overrides.fetcher||mockFetcher,
  verifyIdToken:overrides.verifyIdToken||(async(token,nonce)=>{if(nonce!==currentNonce)throw new Error('bad nonce');return {sub:'synthetic-sub',email:'synthetic@example.test',exp:now+3600};})});
 const request=(path,opts={})=>gateway(new Request(ORIGIN+path,opts));
 async function begin(){const start=await request('/api/team/auth/start',{headers:{'Sec-Fetch-Site':'same-origin'}});const url=new URL(start.headers.get('location'));currentNonce=url.searchParams.get('nonce');return {start,url,loginCookie:start.headers.getSetCookie().find(x=>x.startsWith(LOGIN_COOKIE+'=')).split(';')[0]};}
 async function login(){const {url,loginCookie}=await begin();const callback=await request('/api/team/auth/callback?state='+url.searchParams.get('state')+'&code=test-code',{headers:{Cookie:loginCookie}});const line=callback.headers.getSetCookie().find(x=>x.startsWith(SESSION_COOKIE+'='));const sessionCookie=line?.split(';')[0];const response=await request('/api/team/session',{headers:{Cookie:sessionCookie||''}});return {callback,sessionCookie,data:await response.json(),response};}
 return {config,store,requests,apiCalls,gateway,request,begin,login,setNow:v=>{now=v},getNow:()=>now};
}
export function mutation(sessionCookie,csrf,body,key=randomUUID()){
 return {method:'POST',headers:{Cookie:sessionCookie,Origin:ORIGIN,'Content-Type':'application/json','X-CSRF-Token':csrf,'Idempotency-Key':key},body:JSON.stringify(body)};
}

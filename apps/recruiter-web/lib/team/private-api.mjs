import { SafeError, boundedText } from './core.mjs';
/** Use only this configured Cloud Run origin, never a URL supplied by a browser. */
export function createPrivateApi(apiUrl, {fetcher=fetch, clock=()=>Math.floor(Date.now()/1000)}={}) {
  const origin=new URL(apiUrl);
  if(origin.protocol!=='https:' || origin.origin!==apiUrl || !origin.hostname.endsWith('.run.app') || origin.port)
    throw new SafeError(503,'Invalid private team service configuration.');
  let cached=null, pending=null;
  async function serviceToken() {
    if(cached && cached.expires>clock()+60) return cached.value;
    if(pending) return pending;
    pending=(async()=>{
      const url=new URL('http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity');
      url.searchParams.set('audience',apiUrl);
      const response=await fetcher(url,{headers:{'Metadata-Flavor':'Google'},redirect:'error',cache:'no-store',signal:AbortSignal.timeout(5000)});
      if(!response.ok) throw new SafeError(503,'The team service identity is unavailable.');
      const value=(await boundedText(response,16384)).trim();
      if(!/^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$/.test(value)) throw new SafeError(503,'The team service identity is unavailable.');
      // Source is the fixed metadata endpoint, not user input. Expiry used ONLY for cache.
      let claims; try {claims=JSON.parse(Buffer.from(value.split('.')[1],'base64url').toString());} catch {throw new SafeError(503,'The team service identity is unavailable.');}
      if(!Number.isFinite(claims.exp) || claims.exp<=clock()+60 || claims.aud!==apiUrl) throw new SafeError(503,'The team service identity is unavailable.');
      cached={value,expires:Math.min(claims.exp,clock()+300)};
      return value;
    })();
    try {return await pending;} finally {pending=null;}
  }
  return async function call(userToken,path,{method='GET',body,key}={}) {
    if(!path.startsWith('/') || path.includes('..') || path.includes('%') || path.includes('//') ||
        !['GET','POST','PUT','PATCH'].includes(method)) throw new SafeError(404,'This action is not available.');
    const headers={Accept:'application/json',Authorization:`Bearer ${userToken}`,
      'X-Serverless-Authorization':`Bearer ${await serviceToken()}`};
    if(body!==undefined) headers['Content-Type']='application/json';
    if(key) headers['Idempotency-Key']=key;
    // No automatic mutation retry: preserve the caller's idempotency key for explicit retry.
    return fetcher(apiUrl+'/api/v1/team'+path,{method,headers,body,redirect:'error',cache:'no-store',signal:AbortSignal.timeout(15000)});
  };
}

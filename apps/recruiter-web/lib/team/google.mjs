import { createRemoteJWKSet, jwtVerify } from 'jose';
import { SafeError, same } from './core.mjs';
/** JWKS origin is fixed; token-supplied jku/x5u headers cannot select another server. */
export function googleVerifier(clientId, domain, keySet) {
  const keys=keySet || createRemoteJWKSet(new URL('https://www.googleapis.com/oauth2/v3/certs'),
    {timeoutDuration:5000,cooldownDuration:30000,cacheMaxAge:300000});
  return async function verify(token,nonce) {
    try {
      const {payload,protectedHeader}=await jwtVerify(token,keys,{algorithms:['RS256'],audience:clientId,
        issuer:['https://accounts.google.com','accounts.google.com'],clockTolerance:0,maxTokenAge:'1h',
        requiredClaims:['exp','iat','iss','aud','sub','email','email_verified','hd','nonce']});
      if(protectedHeader.alg!=='RS256' || payload.aud!==clientId || payload.hd!==domain ||
          payload.email_verified!==true || (payload.azp!==undefined && payload.azp!==clientId) ||
          !same(payload.nonce,nonce) || typeof payload.sub!=='string' || !payload.sub || payload.sub.length>255 ||
          typeof payload.email!=='string' || payload.email.toLowerCase().endsWith('@'+domain)===false)
        throw new Error();
      return {sub:payload.sub,email:payload.email.toLowerCase(),exp:payload.exp};
    } catch { throw new SafeError(401,'Google sign-in could not be verified. Please try again.'); }
  };
}

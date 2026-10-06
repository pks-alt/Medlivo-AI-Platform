import test from 'node:test';
import assert from 'node:assert/strict';
let jose, googleVerifier;
try{jose=await import('jose');({googleVerifier}=await import('../../lib/team/google.mjs'));}
catch(error){if(process.env.GITHUB_ACTIONS)throw error;}
const options={skip:!jose?'JOSE is not installed locally; mandatory in GitHub CI':false};
test('Google verifier validates a signed ID token and rejects invalid claims',options,async()=>{
 const {privateKey,publicKey}=await jose.generateKeyPair('RS256'),jwk=await jose.exportJWK(publicKey);jwk.kid='test';jwk.alg='RS256';
 const resolve=jose.createLocalJWKSet({keys:[jwk]}),verify=googleVerifier('test.apps.googleusercontent.com','example.test',resolve),now=Math.floor(Date.now()/1000);
 const base={iss:'https://accounts.google.com',aud:'test.apps.googleusercontent.com',sub:'user-1',email:'user-1@example.test',iat:now,exp:now+3600,hd:'example.test',email_verified:true,nonce:'correct-nonce'};
 const sign=claims=>new jose.SignJWT(claims).setProtectedHeader({alg:'RS256',kid:'test'}).sign(privateKey);
 assert.equal((await verify(await sign(base),'correct-nonce')).sub,'user-1');
 for(const fields of [{aud:'wrong'},{aud:[base.aud,'wrong']},{iss:'https://evil.example'},{hd:'evil.example'},{email:'user@evil.example'},{email_verified:false},{email_verified:'true'},{nonce:'wrong'},{exp:now-1},{iat:now+300},{azp:'wrong'},{sub:''}])await assert.rejects(()=>sign({...base,...fields}).then(t=>verify(t,'correct-nonce')));
});
test('Google verifier rejects a token signed by an untrusted key',options,async()=>{
 const trusted=await jose.generateKeyPair('RS256'),attacker=await jose.generateKeyPair('RS256'),jwk=await jose.exportJWK(trusted.publicKey);jwk.kid='test';
 const verify=googleVerifier('test.apps.googleusercontent.com','example.test',jose.createLocalJWKSet({keys:[jwk]}));
 const token=await new jose.SignJWT({iss:'https://accounts.google.com',aud:'test.apps.googleusercontent.com',sub:'x',email:'x@example.test',hd:'example.test',nonce:'x',email_verified:true}).setIssuedAt().setExpirationTime('1h').setProtectedHeader({alg:'RS256',kid:'test'}).sign(attacker.privateKey);
 await assert.rejects(()=>verify(token,'x'));
});

import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {randomUUID} from 'node:crypto';
import {PostgresSessionStore} from '../../lib/team/session-store.mjs';
const options={skip:!process.env.TEAM_TEST_POSTGRES_URL?'Requires disposable PostgreSQL; run in CI':false};
test('PostgreSQL sessions support atomic consumption shared reads revocation and expiry',options,async()=>{
 const {Pool}=await import('pg'),schema='wb_test_'+randomUUID().replaceAll('-','');
 const control=new Pool({connectionString:process.env.TEAM_TEST_POSTGRES_URL});await control.query('CREATE SCHEMA '+schema);
 const pool=new Pool({connectionString:process.env.TEAM_TEST_POSTGRES_URL,options:'-c search_path='+schema}),pool2=new Pool({connectionString:process.env.TEAM_TEST_POSTGRES_URL,options:'-c search_path='+schema});
 try{
 const migration=await readFile(new URL('../../../../services/team-workspace/migrations/002_browser_sessions.sql',import.meta.url),'utf8').catch(()=>readFile(new URL('../../../../../services/team-workspace/migrations/002_browser_sessions.sql',import.meta.url),'utf8'));
 await pool.query(migration);await pool.query(migration);const store=new PostgresSessionStore(pool),other=new PostgresSessionStore(pool2);
 await store.saveLogin('a'.repeat(64),'b'.repeat(64),'encrypted-only',2000,1000);
 assert.equal(await other.consumeLogin('a'.repeat(64),'c'.repeat(64),1001),null);
 const both=await Promise.all([store.consumeLogin('a'.repeat(64),'b'.repeat(64),1001),other.consumeLogin('a'.repeat(64),'b'.repeat(64),1001)]);assert.equal(both.filter(Boolean).length,1);
 await store.saveSession('s'.repeat(64),'encrypted-only',3000,1600);assert.equal((await other.getSession('s'.repeat(64),1200,600)).ciphertext,'encrypted-only');
 await store.removeSession('s'.repeat(64));assert.equal(await other.getSession('s'.repeat(64),1201,600),null);
 await store.saveSession('s'.repeat(64),'encrypted-only',3000,1600);assert.equal(await other.getSession('s'.repeat(64),1601,600),null);
 await store.removeSession('s'.repeat(64));await store.saveSession('s'.repeat(64),'encrypted-only',3000,2900);assert.equal(await other.getSession('s'.repeat(64),3001,600),null);
 }finally{await pool.end();await pool2.end();await control.query('DROP SCHEMA '+schema+' CASCADE');await control.end();}
});

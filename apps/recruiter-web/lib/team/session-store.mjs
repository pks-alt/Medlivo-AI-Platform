/** PostgreSQL-backed opaque sessions. Parameterized SQL; no schema creation at runtime. */
import { SafeError } from './core.mjs';
export class PostgresSessionStore {
  constructor(pool) { this.pool=pool; }
  async saveLogin(id,state,ciphertext,expires,now) {
    const conn=await this.pool.connect();
    try {
      await conn.query('BEGIN');
      // Distributed safety ceiling for anonymous login starts, across all instances.
      await conn.query('SELECT pg_advisory_xact_lock(731601003)');
      await conn.query('DELETE FROM wb_login WHERE expires_at <= $1',[now]);
      const count=await conn.query('SELECT count(*)::integer AS n FROM wb_login WHERE created_at > $1',[now-60]);
      if(count.rows[0].n>=120) throw new SafeError(429,'Too many sign-in attempts. Please try again shortly.');
      await conn.query('INSERT INTO wb_login (id_hash,state_hash,ciphertext,expires_at,created_at) VALUES ($1,$2,$3,$4,$5)',[id,state,ciphertext,expires,now]);
      await conn.query('DELETE FROM wb_session WHERE expires_at <= $1 OR idle_expires_at <= $1',[now]);
      await conn.query('COMMIT');
    } catch(e) { await conn.query('ROLLBACK'); throw e; }
    finally { conn.release(); }
  }
  async consumeLogin(id,state,now) {
    // Exactly one callback can consume this browser-bound, state-bound login.
    const result=await this.pool.query('DELETE FROM wb_login WHERE id_hash=$1 AND state_hash=$2 AND expires_at>$3 RETURNING ciphertext',[id,state,now]);
    return result.rows[0] || null;
  }
  async removeLogin(id) { await this.pool.query('DELETE FROM wb_login WHERE id_hash=$1',[id]); }
  async saveSession(id,ciphertext,expires,idle) {
    await this.pool.query('INSERT INTO wb_session (id_hash,ciphertext,expires_at,idle_expires_at) VALUES ($1,$2,$3,$4)',[id,ciphertext,expires,idle]);
  }
  async getSession(id,now,idleSeconds) {
    const result=await this.pool.query('UPDATE wb_session SET idle_expires_at=LEAST(expires_at,$2::bigint+$3::bigint) WHERE id_hash=$1 AND expires_at>$2 AND idle_expires_at>$2 RETURNING ciphertext',[id,now,idleSeconds]);
    return result.rows[0] || null;
  }
  async removeSession(id) { await this.pool.query('DELETE FROM wb_session WHERE id_hash=$1',[id]); }
}

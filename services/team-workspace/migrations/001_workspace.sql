-- Reviewed migration only. Apply to a disposable/staging copy first.
-- Requires the canonical Medlivo schema at apps/api/app/db/schema.sql.
-- Run with psql --single-transaction -v ON_ERROR_STOP=1 -f migrations/001_workspace.sql
-- This script does not create users, bind identities, seed cases or grant access.
CREATE UNIQUE INDEX IF NOT EXISTS uq_ws_app_user_tenant_id ON app_user (tenant_id, id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_ws_team_tenant_id ON team (tenant_id, id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_ws_job_tenant_id ON job (tenant_id, id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_ws_candidate_tenant_id ON candidate (tenant_id, id);

CREATE TABLE IF NOT EXISTS ws_case (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	team_id UUID NOT NULL, 
	owner_user_id UUID NOT NULL, 
	job_id UUID, 
	candidate_id UUID, 
	title VARCHAR NOT NULL, 
	version INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (tenant_id, id), 
	CHECK (version > 0), 
	FOREIGN KEY(tenant_id, team_id) REFERENCES team (tenant_id, id), 
	FOREIGN KEY(tenant_id, owner_user_id) REFERENCES app_user (tenant_id, id), 
	FOREIGN KEY(tenant_id, job_id) REFERENCES job (tenant_id, id), 
	FOREIGN KEY(tenant_id, candidate_id) REFERENCES candidate (tenant_id, id)
)

;
CREATE INDEX IF NOT EXISTS idx_ws_case_owner ON ws_case (tenant_id, owner_user_id, id);
CREATE INDEX IF NOT EXISTS idx_ws_case_team ON ws_case (tenant_id, team_id, id);

CREATE TABLE IF NOT EXISTS ws_identity (
	provider VARCHAR NOT NULL, 
	subject VARCHAR NOT NULL, 
	tenant_id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	PRIMARY KEY (provider, subject), 
	FOREIGN KEY(tenant_id, user_id) REFERENCES app_user (tenant_id, id), 
	UNIQUE (tenant_id, user_id, provider)
)

;

CREATE TABLE IF NOT EXISTS ws_operation (
	tenant_id UUID NOT NULL, 
	actor_user_id UUID NOT NULL, 
	idempotency_key UUID NOT NULL, 
	fingerprint VARCHAR NOT NULL, 
	result JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (tenant_id, actor_user_id, idempotency_key), 
	FOREIGN KEY(tenant_id, actor_user_id) REFERENCES app_user (tenant_id, id)
)

;

CREATE TABLE IF NOT EXISTS ws_audit (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	case_id UUID NOT NULL, 
	actor_user_id UUID NOT NULL, 
	action VARCHAR NOT NULL, 
	entity_id UUID NOT NULL, 
	details JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id, case_id) REFERENCES ws_case (tenant_id, id), 
	FOREIGN KEY(tenant_id, actor_user_id) REFERENCES app_user (tenant_id, id)
)

;
CREATE INDEX IF NOT EXISTS idx_ws_audit_case ON ws_audit (tenant_id, case_id, created_at);

CREATE TABLE IF NOT EXISTS ws_note (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	case_id UUID NOT NULL, 
	actor_user_id UUID NOT NULL, 
	body VARCHAR NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id, case_id) REFERENCES ws_case (tenant_id, id), 
	FOREIGN KEY(tenant_id, actor_user_id) REFERENCES app_user (tenant_id, id)
)

;
CREATE INDEX IF NOT EXISTS idx_ws_note_case ON ws_note (tenant_id, case_id, created_at);

CREATE TABLE IF NOT EXISTS ws_task (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	case_id UUID NOT NULL, 
	created_by UUID NOT NULL, 
	title VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	due_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	version INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (status IN ('open','done')), 
	CHECK (version > 0), 
	FOREIGN KEY(tenant_id, case_id) REFERENCES ws_case (tenant_id, id), 
	FOREIGN KEY(tenant_id, created_by) REFERENCES app_user (tenant_id, id)
)

;
CREATE INDEX IF NOT EXISTS idx_ws_task_case ON ws_task (tenant_id, case_id, created_at);

-- Runtime access should already be INSERT/SELECT-only on audit records.
-- This trigger also prevents accidental updates or deletes by broader app roles.
CREATE OR REPLACE FUNCTION ws_reject_audit_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$ BEGIN
  RAISE EXCEPTION 'Workspace audit records are append-only';
END $$;
DROP TRIGGER IF EXISTS ws_audit_append_only ON ws_audit;
CREATE TRIGGER ws_audit_append_only BEFORE UPDATE OR DELETE ON ws_audit
FOR EACH ROW EXECUTE FUNCTION ws_reject_audit_mutation();

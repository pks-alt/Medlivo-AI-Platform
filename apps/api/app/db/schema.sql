CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS tenant (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slug text NOT NULL UNIQUE,
  name text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app_user (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenant(id),
  email text NOT NULL,
  display_name text,
  role text NOT NULL CHECK (role IN ('admin','manager','recruiter','operations')),
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, email)
);

CREATE TABLE IF NOT EXISTS team (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenant(id),
  name text NOT NULL,
  division text NOT NULL CHECK (division IN ('Nursing & Allied','Rehabilitation','Locum Tenens')),
  manager_user_id uuid REFERENCES app_user(id),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS recruiter_profile (
  user_id uuid PRIMARY KEY REFERENCES app_user(id),
  tenant_id uuid NOT NULL REFERENCES tenant(id),
  team_id uuid REFERENCES team(id),
  timezone text,
  specialties jsonb NOT NULL DEFAULT '[]'::jsonb,
  geographies jsonb NOT NULL DEFAULT '[]'::jsonb,
  workload_capacity integer,
  permissions jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS customer (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenant(id),
  name text NOT NULL,
  status text NOT NULL DEFAULT 'active',
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS customer_assignment (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenant(id),
  customer_id uuid NOT NULL REFERENCES customer(id),
  primary_recruiter_user_id uuid REFERENCES app_user(id),
  team_id uuid REFERENCES team(id),
  active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS job (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenant(id),
  customer_id uuid REFERENCES customer(id),
  title text NOT NULL,
  profession text,
  specialty text,
  division text CHECK (division IN ('Nursing & Allied','Rehabilitation','Locum Tenens')),
  city text,
  state text,
  country_code text DEFAULT 'US',
  start_date date,
  status text NOT NULL DEFAULT 'new',
  priority integer NOT NULL DEFAULT 0,
  owner_user_id uuid REFERENCES app_user(id),
  normalized_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS job_source_record (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenant(id),
  job_id uuid REFERENCES job(id),
  source_system text NOT NULL,
  source_id text NOT NULL,
  source_status text,
  source_updated_at timestamptz,
  raw_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, source_system, source_id)
);

CREATE TABLE IF NOT EXISTS job_requirement (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenant(id),
  job_id uuid NOT NULL REFERENCES job(id) ON DELETE CASCADE,
  requirement_type text NOT NULL,
  canonical_key text NOT NULL,
  value jsonb NOT NULL,
  is_hard_gate boolean NOT NULL DEFAULT false,
  weight numeric(8,4),
  source_evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
  rules_version text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS candidate (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenant(id),
  canonical_name text,
  primary_email text,
  primary_phone text,
  profession text,
  specialty text,
  city text,
  state text,
  country_code text DEFAULT 'US',
  lifecycle_status text NOT NULL DEFAULT 'inactive',
  profile_freshness numeric(5,2),
  canonical_profile jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS candidate_source_record (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenant(id),
  candidate_id uuid REFERENCES candidate(id),
  source_system text NOT NULL,
  source_id text NOT NULL,
  source_updated_at timestamptz,
  raw_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, source_system, source_id)
);

CREATE TABLE IF NOT EXISTS resume_version (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenant(id),
  candidate_id uuid NOT NULL REFERENCES candidate(id) ON DELETE CASCADE,
  source_record_id uuid REFERENCES candidate_source_record(id),
  source_resume_id text,
  storage_uri text,
  text_content text,
  parsed_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  is_primary boolean NOT NULL DEFAULT false,
  resume_date timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS candidate_availability (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenant(id),
  candidate_id uuid NOT NULL REFERENCES candidate(id) ON DELETE CASCADE,
  available_from date,
  available_until date,
  status text,
  confirmed_at timestamptz,
  source_type text,
  source_reference text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS candidate_preference (
  candidate_id uuid PRIMARY KEY REFERENCES candidate(id) ON DELETE CASCADE,
  tenant_id uuid NOT NULL REFERENCES tenant(id),
  travel_local text,
  preferred_locations jsonb NOT NULL DEFAULT '[]'::jsonb,
  shift_preferences jsonb NOT NULL DEFAULT '[]'::jsonb,
  compensation_expectations jsonb NOT NULL DEFAULT '{}'::jsonb,
  best_contact_windows jsonb NOT NULL DEFAULT '[]'::jsonb,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS candidate_license (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenant(id),
  candidate_id uuid NOT NULL REFERENCES candidate(id) ON DELETE CASCADE,
  license_type text NOT NULL,
  state text,
  license_number text,
  status text,
  issued_at date,
  expires_at date,
  verification_status text NOT NULL DEFAULT 'unverified',
  verified_at timestamptz,
  verification_source text,
  raw_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS candidate_certification (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenant(id),
  candidate_id uuid NOT NULL REFERENCES candidate(id) ON DELETE CASCADE,
  certification_key text NOT NULL,
  certification_name text NOT NULL,
  status text,
  expires_at date,
  verification_status text NOT NULL DEFAULT 'unverified',
  verified_at timestamptz,
  verification_source text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS candidate_evidence (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenant(id),
  candidate_id uuid NOT NULL REFERENCES candidate(id) ON DELETE CASCADE,
  fact_key text NOT NULL,
  fact_value jsonb NOT NULL,
  source_type text NOT NULL,
  source_reference text,
  confidence numeric(5,2),
  is_verified boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS match (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenant(id),
  job_id uuid NOT NULL REFERENCES job(id) ON DELETE CASCADE,
  candidate_id uuid NOT NULL REFERENCES candidate(id) ON DELETE CASCADE,
  overall_score numeric(5,2) NOT NULL,
  status text NOT NULL DEFAULT 'shortlisted',
  rules_version text,
  explanation jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, job_id, candidate_id)
);

CREATE TABLE IF NOT EXISTS match_score_component (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenant(id),
  match_id uuid NOT NULL REFERENCES match(id) ON DELETE CASCADE,
  component_key text NOT NULL,
  score numeric(5,2),
  weight numeric(8,4),
  evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS match_exclusion (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenant(id),
  job_id uuid NOT NULL REFERENCES job(id) ON DELETE CASCADE,
  candidate_id uuid NOT NULL REFERENCES candidate(id) ON DELETE CASCADE,
  reason_code text NOT NULL,
  reason_detail text,
  overridden boolean NOT NULL DEFAULT false,
  overridden_by uuid REFERENCES app_user(id),
  overridden_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS match_feedback (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenant(id),
  match_id uuid NOT NULL REFERENCES match(id) ON DELETE CASCADE,
  recruiter_user_id uuid NOT NULL REFERENCES app_user(id),
  feedback_code text NOT NULL,
  notes text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS conversation (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenant(id),
  candidate_id uuid NOT NULL REFERENCES candidate(id),
  job_id uuid REFERENCES job(id),
  owner_user_id uuid REFERENCES app_user(id),
  status text NOT NULL DEFAULT 'open',
  ai_mode text NOT NULL DEFAULT 'approved_assist',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS message (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenant(id),
  conversation_id uuid NOT NULL REFERENCES conversation(id) ON DELETE CASCADE,
  channel text NOT NULL CHECK (channel IN ('sms','email','voice','portal')),
  direction text NOT NULL CHECK (direction IN ('inbound','outbound','system')),
  actor_type text NOT NULL,
  actor_id text,
  content text NOT NULL,
  provider_message_id text,
  sent_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS qualification (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenant(id),
  candidate_id uuid NOT NULL REFERENCES candidate(id),
  job_id uuid REFERENCES job(id),
  conversation_id uuid REFERENCES conversation(id),
  status text NOT NULL DEFAULT 'in_progress',
  summary text,
  completed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS qualification_answer (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenant(id),
  qualification_id uuid NOT NULL REFERENCES qualification(id) ON DELETE CASCADE,
  question_key text NOT NULL,
  answer jsonb NOT NULL,
  source_message_id uuid REFERENCES message(id),
  confirmed boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS submission (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenant(id),
  candidate_id uuid NOT NULL REFERENCES candidate(id),
  job_id uuid NOT NULL REFERENCES job(id),
  recruiter_user_id uuid REFERENCES app_user(id),
  status text NOT NULL DEFAULT 'draft',
  readiness_status text NOT NULL DEFAULT 'near_ready',
  summary text,
  source_system_submission_id text,
  approved_at timestamptz,
  submitted_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS submission_requirement (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenant(id),
  submission_id uuid NOT NULL REFERENCES submission(id) ON DELETE CASCADE,
  requirement_key text NOT NULL,
  status text NOT NULL,
  evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
  completed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS assignment (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenant(id),
  candidate_id uuid NOT NULL REFERENCES candidate(id),
  job_id uuid REFERENCES job(id),
  customer_id uuid REFERENCES customer(id),
  start_date date,
  end_date date,
  status text,
  source_system text,
  source_id text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS consent_profile (
  candidate_id uuid PRIMARY KEY REFERENCES candidate(id) ON DELETE CASCADE,
  tenant_id uuid NOT NULL REFERENCES tenant(id),
  sms_status text,
  email_status text,
  voice_status text,
  preferred_channel text,
  quiet_hours jsonb NOT NULL DEFAULT '{}'::jsonb,
  source_of_consent text,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_event (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenant(id),
  actor_type text NOT NULL,
  actor_id text,
  action text NOT NULL,
  entity_type text NOT NULL,
  entity_id uuid,
  before_state jsonb,
  after_state jsonb,
  context jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS integration_cursor (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenant(id),
  integration text NOT NULL,
  entity_type text NOT NULL,
  cursor_value text,
  last_success_at timestamptz,
  last_error_at timestamptz,
  last_error text,
  UNIQUE (tenant_id, integration, entity_type)
);

CREATE INDEX IF NOT EXISTS idx_job_tenant_status ON job(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_job_owner ON job(tenant_id, owner_user_id);
CREATE INDEX IF NOT EXISTS idx_candidate_tenant_status ON candidate(tenant_id, lifecycle_status);
CREATE INDEX IF NOT EXISTS idx_candidate_profession_specialty ON candidate(tenant_id, profession, specialty);
CREATE INDEX IF NOT EXISTS idx_candidate_location ON candidate(tenant_id, state, city);
CREATE INDEX IF NOT EXISTS idx_candidate_license_lookup ON candidate_license(tenant_id, candidate_id, state, status);
CREATE INDEX IF NOT EXISTS idx_match_job_score ON match(tenant_id, job_id, overall_score DESC);
CREATE INDEX IF NOT EXISTS idx_match_candidate ON match(tenant_id, candidate_id);
CREATE INDEX IF NOT EXISTS idx_conversation_candidate ON conversation(tenant_id, candidate_id, status);
CREATE INDEX IF NOT EXISTS idx_submission_job_status ON submission(tenant_id, job_id, status);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_event(tenant_id, entity_type, entity_id, created_at DESC);

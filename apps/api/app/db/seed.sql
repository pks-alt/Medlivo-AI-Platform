INSERT INTO tenant (id, slug, name)
VALUES ('00000000-0000-0000-0000-000000000001', 'medlivo', 'Medlivo Inc.')
ON CONFLICT (slug) DO NOTHING;

INSERT INTO app_user (id, tenant_id, email, display_name, role)
VALUES ('00000000-0000-0000-0000-000000000011','00000000-0000-0000-0000-000000000001','recruiter@example.invalid','Rey Rivera','recruiter')
ON CONFLICT DO NOTHING;

INSERT INTO customer (id, tenant_id, name)
VALUES ('00000000-0000-0000-0000-000000000021','00000000-0000-0000-0000-000000000001','Regional Health')
ON CONFLICT DO NOTHING;

INSERT INTO job (id, tenant_id, customer_id, title, profession, specialty, division, city, state, start_date, status, priority, owner_user_id)
VALUES ('00000000-0000-0000-0000-000000000101','00000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000021','Urologist','Physician','Urology','Locum Tenens','Kearney','NE','2026-10-19','matching',100,'00000000-0000-0000-0000-000000000011')
ON CONFLICT DO NOTHING;

INSERT INTO job_source_record (tenant_id, job_id, source_system, source_id)
VALUES ('00000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000101','prototype','26-37123')
ON CONFLICT DO NOTHING;

INSERT INTO job_requirement (tenant_id, job_id, requirement_type, canonical_key, value, is_hard_gate, weight)
VALUES
('00000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000101','clinical','profession','{"display":"Physician"}',true,1),
('00000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000101','clinical','specialty','{"display":"Urology"}',true,1),
('00000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000101','license','license_readiness','{"display":"NE active or ready before start"}',true,1);

INSERT INTO candidate (id, tenant_id, canonical_name, profession, specialty, city, state, lifecycle_status, profile_freshness)
VALUES ('00000000-0000-0000-0000-000000000201','00000000-0000-0000-0000-000000000001','Dr. Dana Patel','Physician','Urology','Omaha','NE','qualified',95)
ON CONFLICT DO NOTHING;

INSERT INTO candidate_preference (candidate_id, tenant_id, travel_local, preferred_locations)
VALUES ('00000000-0000-0000-0000-000000000201','00000000-0000-0000-0000-000000000001','Travel','["Nebraska"]')
ON CONFLICT (candidate_id) DO NOTHING;

INSERT INTO candidate_availability (tenant_id, candidate_id, available_from, status, confirmed_at, source_type)
VALUES ('00000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000201','2026-10-19','confirmed',now(),'prototype');

INSERT INTO candidate_license (tenant_id, candidate_id, license_type, state, status, verification_status, verified_at, verification_source)
VALUES ('00000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000201','Medical License','NE','active','verified',now(),'prototype');

INSERT INTO candidate_evidence (tenant_id, candidate_id, fact_key, fact_value, source_type, confidence, is_verified)
VALUES
('00000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000201','clinical_fit','{"display":"Recent urology experience aligns closely"}','resume',0.98,false),
('00000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000201','availability','{"display":"Available Oct 19"}','candidate_confirmation',1.0,true),
('00000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000201','license_readiness','{"display":"Nebraska license verified"}','license_registry',1.0,true);

INSERT INTO match (id, tenant_id, job_id, candidate_id, overall_score, status, explanation)
VALUES ('00000000-0000-0000-0000-000000000301','00000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000101','00000000-0000-0000-0000-000000000201',94,'near_ready','{"summary":"Strong specialty alignment, Nebraska location, confirmed availability, and no current hard blocker."}')
ON CONFLICT DO NOTHING;

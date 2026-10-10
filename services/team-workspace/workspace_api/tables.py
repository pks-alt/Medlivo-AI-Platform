"""Map existing canonical tables; only new ws_* tables are migrated in production.

metadata.create_all is used only by isolated tests, never by service startup.
"""
from sqlalchemy import (
    MetaData, Table, Column, String, Boolean, Integer, DateTime, Uuid, JSON,
    ForeignKeyConstraint, UniqueConstraint, CheckConstraint, Index, Date, Numeric,
)

metadata = MetaData()
U = lambda name, **kw: Column(name, Uuid(as_uuid=False), **kw)
S = lambda name, **kw: Column(name, String, **kw)
D = lambda name, **kw: Column(name, DateTime(timezone=True), **kw)

# Relevant column subsets of the existing Medlivo canonical schema.
tenant = Table("tenant", metadata, U("id", primary_key=True), S("slug", nullable=False, unique=True), S("name", nullable=False))
users = Table("app_user", metadata, U("id", primary_key=True), U("tenant_id", nullable=False),
              S("email", nullable=False), S("display_name"), S("role", nullable=False),
              Column("is_active", Boolean, nullable=False), UniqueConstraint("tenant_id", "id"),
              UniqueConstraint("tenant_id", "email"),
              ForeignKeyConstraint(["tenant_id"], ["tenant.id"]))
teams = Table("team", metadata, U("id", primary_key=True), U("tenant_id", nullable=False),
              S("name", nullable=False), S("division", nullable=False), U("manager_user_id"),
              UniqueConstraint("tenant_id", "id"), ForeignKeyConstraint(["tenant_id"], ["tenant.id"]))
access_profiles = Table(
    "ws_access_profile", metadata,
    U("user_id", primary_key=True), U("tenant_id", nullable=False),
    S("business_role", nullable=False), Column("system_admin", Boolean, nullable=False),
    D("created_at", nullable=False), D("updated_at", nullable=False),
    UniqueConstraint("tenant_id", "user_id"),
    ForeignKeyConstraint(["tenant_id", "user_id"], ["app_user.tenant_id", "app_user.id"]),
)


profiles = Table("recruiter_profile", metadata, U("user_id", primary_key=True), U("tenant_id", nullable=False), U("team_id"))
jobs = Table(
    "job", metadata,
    U("id", primary_key=True), U("tenant_id", nullable=False), U("customer_id"),
    S("title", nullable=False), S("profession"), S("specialty"), S("division"),
    S("city"), S("state"), Column("start_date", Date), S("status", nullable=False, default="new"),
    Column("priority", Integer, nullable=False, default=0), U("owner_user_id"),
    Column("normalized_payload", JSON, nullable=False, default=dict), D("created_at"), D("updated_at"),
    UniqueConstraint("tenant_id", "id"),
)
candidates = Table(
    "candidate", metadata,
    U("id", primary_key=True), U("tenant_id", nullable=False), S("canonical_name"),
    S("primary_email"), S("primary_phone"), S("profession"), S("specialty"),
    S("city"), S("state"), S("lifecycle_status"),
    Column("profile_freshness", Numeric(5, 2)), Column("canonical_profile", JSON, nullable=False, default=dict),
    D("created_at"), D("updated_at"),
    UniqueConstraint("tenant_id", "id"),
)

customers = Table(
    "customer", metadata,
    U("id", primary_key=True), U("tenant_id", nullable=False), S("name", nullable=False),
    S("status"), Column("metadata", JSON, nullable=False, default=dict), D("created_at"), D("updated_at"),
    UniqueConstraint("tenant_id", "id"),
)
job_requirements = Table(
    "job_requirement", metadata,
    U("id", primary_key=True), U("tenant_id", nullable=False), U("job_id", nullable=False),
    S("requirement_type", nullable=False), S("canonical_key", nullable=False),
    Column("value", JSON, nullable=False), Column("is_hard_gate", Boolean, nullable=False, default=False),
    Column("weight", Numeric(8, 4)), Column("source_evidence", JSON, nullable=False, default=dict),
    S("rules_version"), D("created_at"),
)
resume_versions = Table(
    "resume_version", metadata,
    U("id", primary_key=True), U("tenant_id", nullable=False), U("candidate_id", nullable=False),
    U("source_record_id"), S("source_resume_id"), S("storage_uri"), S("text_content"),
    Column("parsed_payload", JSON, nullable=False, default=dict), Column("is_primary", Boolean, nullable=False, default=False),
    D("resume_date"), D("created_at"), D("updated_at"),
)
candidate_availability = Table(
    "candidate_availability", metadata,
    U("id", primary_key=True), U("tenant_id", nullable=False), U("candidate_id", nullable=False),
    Column("available_from", Date), Column("available_until", Date), S("status"), D("confirmed_at"),
    S("source_type"), S("source_reference"), D("created_at"),
)
candidate_preferences = Table(
    "candidate_preference", metadata,
    U("candidate_id", primary_key=True), U("tenant_id", nullable=False), S("travel_local"),
    Column("preferred_locations", JSON, nullable=False, default=list),
    Column("shift_preferences", JSON, nullable=False, default=list),
    Column("compensation_expectations", JSON, nullable=False, default=dict),
    Column("best_contact_windows", JSON, nullable=False, default=list), D("updated_at"),
)
candidate_licenses = Table(
    "candidate_license", metadata,
    U("id", primary_key=True), U("tenant_id", nullable=False), U("candidate_id", nullable=False),
    S("license_type", nullable=False), S("state"), S("license_number"), S("status"),
    Column("issued_at", Date), Column("expires_at", Date), S("verification_status"), D("verified_at"),
    S("verification_source"), S("source_system"), S("source_reference"),
    Column("raw_payload", JSON, nullable=False, default=dict), D("created_at"), D("updated_at"),
)
candidate_certifications = Table(
    "candidate_certification", metadata,
    U("id", primary_key=True), U("tenant_id", nullable=False), U("candidate_id", nullable=False),
    S("certification_key", nullable=False), S("certification_name", nullable=False), S("status"),
    Column("expires_at", Date), S("verification_status"), D("verified_at"),
    S("verification_source"), S("source_system"), S("source_reference"),
    Column("raw_payload", JSON, nullable=False, default=dict), D("created_at"), D("updated_at"),
)
candidate_evidence = Table(
    "candidate_evidence", metadata,
    U("id", primary_key=True), U("tenant_id", nullable=False), U("candidate_id", nullable=False),
    S("fact_key", nullable=False), Column("fact_value", JSON, nullable=False), S("source_type", nullable=False),
    S("source_reference"), Column("confidence", Numeric(5, 2)), Column("is_verified", Boolean, nullable=False, default=False),
    D("created_at"), D("updated_at"),
)
match_exclusions = Table(
    "match_exclusion", metadata,
    U("id", primary_key=True), U("tenant_id", nullable=False), U("job_id", nullable=False),
    U("candidate_id", nullable=False), S("reason_code", nullable=False), S("reason_detail"),
    Column("overridden", Boolean, nullable=False, default=False), U("overridden_by"), D("overridden_at"), D("created_at"),
)
qualifications = Table(
    "qualification", metadata,
    U("id", primary_key=True), U("tenant_id", nullable=False), U("candidate_id", nullable=False),
    U("job_id"), U("conversation_id"), S("status", nullable=False), S("summary"), D("completed_at"), D("created_at"),
)
qualification_answers = Table(
    "qualification_answer", metadata,
    U("id", primary_key=True), U("tenant_id", nullable=False), U("qualification_id", nullable=False),
    S("question_key", nullable=False), Column("answer", JSON, nullable=False), U("source_message_id"),
    Column("confirmed", Boolean, nullable=False, default=False), D("created_at"),
)
job_source_records = Table(
    "job_source_record", metadata,
    U("id", primary_key=True), U("tenant_id", nullable=False), U("job_id"),
    S("source_system", nullable=False), S("source_id", nullable=False), S("source_status"),
    D("source_updated_at"), Column("raw_payload", JSON, nullable=False),
    D("promoted_at"), S("promotion_version"), D("enriched_at"), S("enrichment_version"),
    S("enrichment_error_code"), D("created_at"), D("updated_at"),
)
candidate_source_records = Table(
    "candidate_source_record", metadata,
    U("id", primary_key=True), U("tenant_id", nullable=False), U("candidate_id"),
    S("source_system", nullable=False), S("source_id", nullable=False), D("source_updated_at"),
    Column("raw_payload", JSON, nullable=False), D("promoted_at"), S("promotion_version"),
    D("enriched_at"), S("enrichment_version"), S("enrichment_error_code"),
    D("created_at"), D("updated_at"),
)
matches = Table(
    "match", metadata,
    U("id", primary_key=True), U("tenant_id", nullable=False), U("job_id", nullable=False),
    U("candidate_id", nullable=False), Column("overall_score", Numeric(5, 2), nullable=False),
    S("status", nullable=False), S("rules_version"), Column("explanation", JSON, nullable=False),
    D("created_at"), D("updated_at"),
    UniqueConstraint("tenant_id", "job_id", "candidate_id"),
)
match_feedback = Table(
    "match_feedback", metadata,
    U("id", primary_key=True), U("tenant_id", nullable=False), U("match_id", nullable=False),
    U("recruiter_user_id", nullable=False), S("feedback_code", nullable=False), S("reason_code"), S("notes"),
    D("created_at", nullable=False),
)
conversations = Table(
    "conversation", metadata,
    U("id", primary_key=True), U("tenant_id", nullable=False), U("candidate_id", nullable=False),
    U("job_id"), U("owner_user_id"), S("status", nullable=False), S("ai_mode", nullable=False),
    D("created_at"), D("updated_at"),
)
submissions = Table(
    "submission", metadata,
    U("id", primary_key=True), U("tenant_id", nullable=False), U("candidate_id", nullable=False),
    U("job_id", nullable=False), U("recruiter_user_id"), S("status", nullable=False),
    S("readiness_status", nullable=False), S("summary"), S("source_system_submission_id"),
    D("approved_at"), D("submitted_at"), D("created_at"), D("updated_at"),
)


submission_projections = Table(
    "ws_submission_projection", metadata,
    U("id", primary_key=True), U("tenant_id", nullable=False), U("job_id", nullable=False),
    U("candidate_id", nullable=False), U("recruiter_user_id"),
    S("source_system", nullable=False), S("source_submission_id", nullable=False),
    S("source_status", nullable=False), D("submitted_at"), D("client_response_at"),
    D("source_updated_at"), Column("raw_payload", JSON, nullable=False, default=dict),
    D("synced_at", nullable=False),
    UniqueConstraint("tenant_id", "source_system", "source_submission_id"),
    ForeignKeyConstraint(["tenant_id", "job_id"], ["job.tenant_id", "job.id"]),
    ForeignKeyConstraint(["tenant_id", "candidate_id"], ["candidate.tenant_id", "candidate.id"]),
    ForeignKeyConstraint(["tenant_id", "recruiter_user_id"], ["app_user.tenant_id", "app_user.id"]),
)

interview_projections = Table(
    "ws_interview_projection", metadata,
    U("id", primary_key=True), U("tenant_id", nullable=False), U("job_id", nullable=False),
    U("candidate_id", nullable=False), U("submission_projection_id"),
    S("source_system", nullable=False), S("source_interview_id", nullable=False),
    S("source_status", nullable=False), S("interview_type"), D("scheduled_at"), D("completed_at"),
    S("outcome"), D("outcome_at"), D("source_updated_at"),
    Column("raw_payload", JSON, nullable=False, default=dict), D("synced_at", nullable=False),
    UniqueConstraint("tenant_id", "source_system", "source_interview_id"),
    ForeignKeyConstraint(["tenant_id", "job_id"], ["job.tenant_id", "job.id"]),
    ForeignKeyConstraint(["tenant_id", "candidate_id"], ["candidate.tenant_id", "candidate.id"]),
    ForeignKeyConstraint(["submission_projection_id"], ["ws_submission_projection.id"]),
)

offer_projections = Table(
    "ws_offer_projection", metadata,
    U("id", primary_key=True), U("tenant_id", nullable=False), U("job_id", nullable=False),
    U("candidate_id", nullable=False), U("submission_projection_id"),
    S("source_system", nullable=False), S("source_offer_id", nullable=False),
    S("source_status", nullable=False), D("offered_at"), D("accepted_at"), D("declined_at"),
    S("decline_reason"), D("source_updated_at"), Column("raw_payload", JSON, nullable=False, default=dict),
    D("synced_at", nullable=False),
    UniqueConstraint("tenant_id", "source_system", "source_offer_id"),
    ForeignKeyConstraint(["tenant_id", "job_id"], ["job.tenant_id", "job.id"]),
    ForeignKeyConstraint(["tenant_id", "candidate_id"], ["candidate.tenant_id", "candidate.id"]),
    ForeignKeyConstraint(["submission_projection_id"], ["ws_submission_projection.id"]),
)

placement_projections = Table(
    "ws_placement_projection", metadata,
    U("id", primary_key=True), U("tenant_id", nullable=False), U("job_id", nullable=False),
    U("candidate_id", nullable=False), S("source_system", nullable=False),
    S("source_placement_id", nullable=False), S("source_status", nullable=False),
    S("placement_status"), Column("planned_start_date", Date), Column("actual_start_date", Date),
    Column("planned_end_date", Date), Column("actual_end_date", Date), D("source_updated_at"),
    Column("raw_payload", JSON, nullable=False, default=dict), D("synced_at", nullable=False),
    UniqueConstraint("tenant_id", "source_system", "source_placement_id"),
    ForeignKeyConstraint(["tenant_id", "job_id"], ["job.tenant_id", "job.id"]),
    ForeignKeyConstraint(["tenant_id", "candidate_id"], ["candidate.tenant_id", "candidate.id"]),
)

start_readiness = Table(
    "ws_start_readiness", metadata,
    U("id", primary_key=True), U("tenant_id", nullable=False), U("job_id", nullable=False),
    U("candidate_id", nullable=False), U("placement_projection_id"),
    S("status", nullable=False), S("risk_level", nullable=False), S("risk_reason"),
    S("next_action"), U("owner_user_id"), D("due_at"), Column("version", Integer, nullable=False),
    U("updated_by", nullable=False), D("created_at", nullable=False), D("updated_at", nullable=False),
    UniqueConstraint("tenant_id", "job_id", "candidate_id"),
    CheckConstraint("status IN ('not_started','in_progress','ready','blocked','started')"),
    CheckConstraint("risk_level IN ('unknown','low','medium','high','critical')"),
    CheckConstraint("version > 0"),
    ForeignKeyConstraint(["tenant_id", "job_id"], ["job.tenant_id", "job.id"]),
    ForeignKeyConstraint(["tenant_id", "candidate_id"], ["candidate.tenant_id", "candidate.id"]),
    ForeignKeyConstraint(["placement_projection_id"], ["ws_placement_projection.id"]),
    ForeignKeyConstraint(["tenant_id", "owner_user_id"], ["app_user.tenant_id", "app_user.id"]),
    ForeignKeyConstraint(["tenant_id", "updated_by"], ["app_user.tenant_id", "app_user.id"]),
)

start_readiness_items = Table(
    "ws_start_readiness_item", metadata,
    U("id", primary_key=True), U("tenant_id", nullable=False), U("readiness_id", nullable=False),
    S("item_key", nullable=False), S("label", nullable=False), S("category", nullable=False),
    S("status", nullable=False), Column("required", Boolean, nullable=False), S("source_type"),
    S("source_reference"), D("due_at"), S("notes"), U("updated_by", nullable=False),
    D("created_at", nullable=False), D("updated_at", nullable=False),
    UniqueConstraint("readiness_id", "item_key"),
    CheckConstraint("status IN ('missing','pending','complete','waived','not_applicable')"),
    ForeignKeyConstraint(["readiness_id"], ["ws_start_readiness.id"]),
    ForeignKeyConstraint(["tenant_id", "updated_by"], ["app_user.tenant_id", "app_user.id"]),
)

Index("idx_ws_submission_projection_pair", submission_projections.c.tenant_id,
      submission_projections.c.job_id, submission_projections.c.candidate_id,
      submission_projections.c.submitted_at)
Index("idx_ws_interview_projection_pair", interview_projections.c.tenant_id,
      interview_projections.c.job_id, interview_projections.c.candidate_id,
      interview_projections.c.scheduled_at)
Index("idx_ws_offer_projection_pair", offer_projections.c.tenant_id,
      offer_projections.c.job_id, offer_projections.c.candidate_id,
      offer_projections.c.offered_at)
Index("idx_ws_placement_projection_start", placement_projections.c.tenant_id,
      placement_projections.c.planned_start_date, placement_projections.c.source_status)
Index("idx_ws_start_readiness_risk", start_readiness.c.tenant_id,
      start_readiness.c.risk_level, start_readiness.c.status, start_readiness.c.due_at)
Index("idx_ws_start_readiness_item_status", start_readiness_items.c.tenant_id,
      start_readiness_items.c.readiness_id, start_readiness_items.c.status,
      start_readiness_items.c.due_at)

identities = Table("ws_identity", metadata, S("provider", primary_key=True), S("subject", primary_key=True),
                   U("tenant_id", nullable=False), U("user_id", nullable=False),
                   ForeignKeyConstraint(["tenant_id", "user_id"], ["app_user.tenant_id", "app_user.id"]),
                   UniqueConstraint("tenant_id", "user_id", "provider"))
cases = Table("ws_case", metadata, U("id", primary_key=True), U("tenant_id", nullable=False),
              U("team_id", nullable=False), U("owner_user_id", nullable=False), U("job_id"), U("candidate_id"),
              S("title", nullable=False), Column("version", Integer, nullable=False, default=1),
              D("created_at", nullable=False), D("updated_at", nullable=False),
              UniqueConstraint("tenant_id", "id"), CheckConstraint("version > 0"),
              ForeignKeyConstraint(["tenant_id", "team_id"], ["team.tenant_id", "team.id"]),
              ForeignKeyConstraint(["tenant_id", "owner_user_id"], ["app_user.tenant_id", "app_user.id"]),
              ForeignKeyConstraint(["tenant_id", "job_id"], ["job.tenant_id", "job.id"]),
              ForeignKeyConstraint(["tenant_id", "candidate_id"], ["candidate.tenant_id", "candidate.id"]))
notes = Table("ws_note", metadata, U("id", primary_key=True), U("tenant_id", nullable=False),
              U("case_id", nullable=False), U("actor_user_id", nullable=False), S("body", nullable=False), D("created_at", nullable=False),
              ForeignKeyConstraint(["tenant_id", "case_id"], ["ws_case.tenant_id", "ws_case.id"]),
              ForeignKeyConstraint(["tenant_id", "actor_user_id"], ["app_user.tenant_id", "app_user.id"]))
tasks = Table("ws_task", metadata, U("id", primary_key=True), U("tenant_id", nullable=False),
              U("case_id", nullable=False), U("created_by", nullable=False), S("title", nullable=False),
              S("status", nullable=False), D("due_at", nullable=False), Column("version", Integer, nullable=False),
              D("created_at", nullable=False), D("updated_at", nullable=False),
              CheckConstraint("status IN ('open','done')"), CheckConstraint("version > 0"),
              ForeignKeyConstraint(["tenant_id", "case_id"], ["ws_case.tenant_id", "ws_case.id"]),
              ForeignKeyConstraint(["tenant_id", "created_by"], ["app_user.tenant_id", "app_user.id"]))
audit = Table("ws_audit", metadata, U("id", primary_key=True), U("tenant_id", nullable=False), U("case_id", nullable=False),
              U("actor_user_id", nullable=False), S("action", nullable=False), U("entity_id", nullable=False),
              Column("details", JSON, nullable=False), D("created_at", nullable=False),
              ForeignKeyConstraint(["tenant_id", "case_id"], ["ws_case.tenant_id", "ws_case.id"]),
              ForeignKeyConstraint(["tenant_id", "actor_user_id"], ["app_user.tenant_id", "app_user.id"]))
admin_audit = Table("ws_admin_audit", metadata, U("id", primary_key=True), U("tenant_id", nullable=False),
                    U("actor_user_id", nullable=False), U("target_user_id", nullable=False),
                    S("action", nullable=False), Column("before_state", JSON, nullable=False),
                    Column("after_state", JSON, nullable=False), D("created_at", nullable=False),
                    ForeignKeyConstraint(["tenant_id", "actor_user_id"], ["app_user.tenant_id", "app_user.id"]),
                    ForeignKeyConstraint(["tenant_id", "target_user_id"], ["app_user.tenant_id", "app_user.id"]))
operations = Table("ws_operation", metadata, U("tenant_id", primary_key=True), U("actor_user_id", primary_key=True),
                   U("idempotency_key", primary_key=True), S("fingerprint", nullable=False),
                   Column("result", JSON, nullable=False), D("created_at", nullable=False),
                   ForeignKeyConstraint(["tenant_id", "actor_user_id"], ["app_user.tenant_id", "app_user.id"]))
Index("idx_ws_case_owner", cases.c.tenant_id, cases.c.owner_user_id, cases.c.id)
Index("idx_ws_case_team", cases.c.tenant_id, cases.c.team_id, cases.c.id)
for table in (notes, tasks, audit):
    Index("idx_" + table.name + "_case", table.c.tenant_id, table.c.case_id, table.c.created_at)


job_intake_batches = Table(
    "ws_job_intake_batch", metadata,
    U("id", primary_key=True), U("tenant_id", nullable=False), U("team_id"),
    U("uploaded_by", nullable=False), S("customer_name", nullable=False),
    S("division", nullable=False), S("source_filename", nullable=False),
    S("status", nullable=False), Column("mapping", JSON, nullable=False),
    S("source_file_hash"), S("ai_processing_status", nullable=False, default="not_started"),
    U("review_owner_user_id"), U("approved_by"), D("approved_at"), U("correlation_id"),
    Column("row_count", Integer, nullable=False), Column("ready_count", Integer, nullable=False),
    Column("review_count", Integer, nullable=False), Column("duplicate_count", Integer, nullable=False),
    D("created_at", nullable=False), D("updated_at", nullable=False),
    UniqueConstraint("tenant_id", "id"),
    ForeignKeyConstraint(["tenant_id", "team_id"], ["team.tenant_id", "team.id"]),
    ForeignKeyConstraint(["tenant_id", "uploaded_by"], ["app_user.tenant_id", "app_user.id"]),
)

job_intake_items = Table(
    "ws_job_intake_item", metadata,
    U("id", primary_key=True), U("tenant_id", nullable=False), U("batch_id", nullable=False),
    Column("row_number", Integer, nullable=False), Column("source_row", JSON, nullable=False),
    Column("normalized_job", JSON, nullable=False), Column("validation_errors", JSON, nullable=False),
    Column("extracted_values", JSON, nullable=False, default=dict), Column("ai_suggestions", JSON, nullable=False, default=list),
    Column("conflicts", JSON, nullable=False, default=list), Column("missing_fields", JSON, nullable=False, default=list),
    Column("final_approved_values", JSON), Column("standardized_internal_jd", JSON, nullable=False, default=dict), S("bill_rate_state", nullable=False, default="unknown"),
    S("recruiting_readiness", nullable=False, default="review"), S("commercial_readiness", nullable=False, default="review"),
    U("reviewed_by"), D("reviewed_at"), U("duplicate_job_id"), S("status", nullable=False), U("created_job_id"),
    D("created_at", nullable=False), D("updated_at", nullable=False),
    UniqueConstraint("tenant_id", "id"), UniqueConstraint("tenant_id", "batch_id", "row_number"),
    ForeignKeyConstraint(["tenant_id", "batch_id"], ["ws_job_intake_batch.tenant_id", "ws_job_intake_batch.id"]),
    ForeignKeyConstraint(["tenant_id", "duplicate_job_id"], ["job.tenant_id", "job.id"]),
    ForeignKeyConstraint(["tenant_id", "created_job_id"], ["job.tenant_id", "job.id"]),
)

customer_job_mappings = Table(
    "ws_customer_job_mapping", metadata,
    U("id", primary_key=True), U("tenant_id", nullable=False),
    S("customer_name", nullable=False), S("division", nullable=False),
    Column("mapping", JSON, nullable=False), Column("mapping_version", Integer, nullable=False, default=1),
    U("approved_by"), D("effective_from"), Column("is_active", Boolean, nullable=False, default=True),
    U("updated_by", nullable=False), D("created_at", nullable=False), D("updated_at", nullable=False),
    UniqueConstraint("tenant_id", "id"), UniqueConstraint("tenant_id", "customer_name", "division"),
    ForeignKeyConstraint(["tenant_id", "updated_by"], ["app_user.tenant_id", "app_user.id"]),
)

weekly_goals = Table(
    "ws_weekly_recruiter_goal", metadata,
    U("id", primary_key=True), U("tenant_id", nullable=False), U("team_id", nullable=False),
    U("recruiter_user_id", nullable=False), Column("week_start", Date, nullable=False),
    Column("submissions_target", Integer, nullable=False), Column("interviews_target", Integer, nullable=False),
    Column("closures_target", Integer, nullable=False), Column("priority_jobs_target", Integer, nullable=False),
    S("notes"), U("created_by", nullable=False), D("created_at", nullable=False), D("updated_at", nullable=False),
    UniqueConstraint("tenant_id", "id"), UniqueConstraint("tenant_id", "recruiter_user_id", "week_start"),
    ForeignKeyConstraint(["tenant_id", "team_id"], ["team.tenant_id", "team.id"]),
    ForeignKeyConstraint(["tenant_id", "recruiter_user_id"], ["app_user.tenant_id", "app_user.id"]),
    ForeignKeyConstraint(["tenant_id", "created_by"], ["app_user.tenant_id", "app_user.id"]),
)

weekly_snapshots = Table(
    "ws_weekly_recruiter_snapshot", metadata,
    U("id", primary_key=True), U("tenant_id", nullable=False), U("team_id", nullable=False),
    U("recruiter_user_id", nullable=False), Column("week_start", Date, nullable=False),
    Column("submissions_actual", Integer, nullable=False), Column("interviews_actual", Integer, nullable=False),
    Column("closures_actual", Integer, nullable=False), Column("offers_actual", Integer, nullable=False),
    Column("starts_actual", Integer, nullable=False), Column("qualified_actual", Integer, nullable=False),
    Column("responses_actual", Integer, nullable=False), Column("source_breakdown", JSON, nullable=False),
    D("generated_at", nullable=False),
    UniqueConstraint("tenant_id", "id"), UniqueConstraint("tenant_id", "recruiter_user_id", "week_start"),
    ForeignKeyConstraint(["tenant_id", "team_id"], ["team.tenant_id", "team.id"]),
    ForeignKeyConstraint(["tenant_id", "recruiter_user_id"], ["app_user.tenant_id", "app_user.id"]),
)

Index("idx_ws_job_intake_batch_team_created", job_intake_batches.c.tenant_id, job_intake_batches.c.team_id, job_intake_batches.c.created_at)
Index("idx_ws_job_intake_item_batch_status", job_intake_items.c.tenant_id, job_intake_items.c.batch_id, job_intake_items.c.status, job_intake_items.c.row_number)
Index("idx_ws_weekly_goal_team_week", weekly_goals.c.tenant_id, weekly_goals.c.team_id, weekly_goals.c.week_start)
Index("idx_ws_weekly_snapshot_team_week", weekly_snapshots.c.tenant_id, weekly_snapshots.c.team_id, weekly_snapshots.c.week_start)


job_operational_overlays = Table(
    "ws_job_operational_overlay", metadata,
    U("job_id", primary_key=True), U("tenant_id", nullable=False), U("team_id"),
    U("recruiter_user_id"), S("client_priority", nullable=False), S("job_priority", nullable=False),
    S("priority_reason"), S("manager_note"), S("next_action"), D("due_at"),
    S("operational_status", nullable=False), Column("version", Integer, nullable=False),
    U("assigned_by"), D("assigned_at"), U("updated_by", nullable=False),
    D("created_at", nullable=False), D("updated_at", nullable=False),
    UniqueConstraint("tenant_id", "job_id"),
    CheckConstraint("client_priority IN ('high','normal','low')"),
    CheckConstraint("job_priority IN ('hot','priority','standard','hold')"),
    CheckConstraint("operational_status IN ('active','hold','closed')"),
    CheckConstraint("version > 0"),
    ForeignKeyConstraint(["tenant_id", "job_id"], ["job.tenant_id", "job.id"]),
    ForeignKeyConstraint(["tenant_id", "team_id"], ["team.tenant_id", "team.id"]),
    ForeignKeyConstraint(["tenant_id", "recruiter_user_id"], ["app_user.tenant_id", "app_user.id"]),
    ForeignKeyConstraint(["tenant_id", "assigned_by"], ["app_user.tenant_id", "app_user.id"]),
    ForeignKeyConstraint(["tenant_id", "updated_by"], ["app_user.tenant_id", "app_user.id"]),
)

job_ownership_history = Table(
    "ws_job_ownership_history", metadata,
    U("id", primary_key=True), U("tenant_id", nullable=False), U("job_id", nullable=False),
    U("previous_owner_user_id"), U("new_owner_user_id"), U("changed_by", nullable=False),
    S("reason", nullable=False), D("created_at", nullable=False),
    ForeignKeyConstraint(["tenant_id", "job_id"], ["job.tenant_id", "job.id"]),
    ForeignKeyConstraint(["tenant_id", "previous_owner_user_id"], ["app_user.tenant_id", "app_user.id"]),
    ForeignKeyConstraint(["tenant_id", "new_owner_user_id"], ["app_user.tenant_id", "app_user.id"]),
    ForeignKeyConstraint(["tenant_id", "changed_by"], ["app_user.tenant_id", "app_user.id"]),
)

approval_requests = Table(
    "ws_approval_request", metadata,
    U("id", primary_key=True), U("tenant_id", nullable=False), S("approval_type", nullable=False),
    S("object_type", nullable=False), U("object_id", nullable=False), U("requested_by", nullable=False),
    S("required_authority", nullable=False), S("status", nullable=False), S("reason"),
    S("decision_notes"), U("decided_by"), D("decided_at"), D("created_at", nullable=False),
    D("updated_at", nullable=False),
    CheckConstraint("required_authority IN ('delivery_manager','executive','system_admin')"),
    CheckConstraint("status IN ('pending','approved','rejected','cancelled')"),
    ForeignKeyConstraint(["tenant_id", "requested_by"], ["app_user.tenant_id", "app_user.id"]),
    ForeignKeyConstraint(["tenant_id", "decided_by"], ["app_user.tenant_id", "app_user.id"]),
)

provenance_records = Table(
    "ws_provenance", metadata,
    U("id", primary_key=True), U("tenant_id", nullable=False), S("object_type", nullable=False),
    U("object_id", nullable=False), S("field_path", nullable=False), S("source_type", nullable=False),
    S("source_reference"), Column("confidence", Numeric(5,4)), Column("value_payload", JSON),
    D("created_at", nullable=False),
)

ai_suggestions = Table(
    "ws_ai_suggestion", metadata,
    U("id", primary_key=True), U("tenant_id", nullable=False), S("object_type", nullable=False),
    U("object_id", nullable=False), S("field_path", nullable=False), Column("suggested_value", JSON, nullable=False),
    Column("source_basis", JSON, nullable=False), Column("confidence", Numeric(5,4)),
    S("model_provider"), S("model_version"), S("policy_version"), S("status", nullable=False),
    U("reviewed_by"), D("reviewed_at"), D("created_at", nullable=False),
    CheckConstraint("status IN ('proposed','accepted','modified','rejected','expired')"),
    ForeignKeyConstraint(["tenant_id", "reviewed_by"], ["app_user.tenant_id", "app_user.id"]),
)

operational_audit = Table(
    "ws_operational_audit", metadata,
    U("id", primary_key=True), U("tenant_id", nullable=False), U("actor_user_id", nullable=False),
    S("action", nullable=False), S("object_type", nullable=False), U("object_id", nullable=False),
    Column("before_state", JSON, nullable=False), Column("after_state", JSON, nullable=False),
    S("reason"), U("correlation_id"), D("created_at", nullable=False),
    ForeignKeyConstraint(["tenant_id", "actor_user_id"], ["app_user.tenant_id", "app_user.id"]),
)

Index("idx_ws_job_overlay_team_priority", job_operational_overlays.c.tenant_id,
      job_operational_overlays.c.team_id, job_operational_overlays.c.job_priority,
      job_operational_overlays.c.updated_at)
Index("idx_ws_job_overlay_recruiter", job_operational_overlays.c.tenant_id,
      job_operational_overlays.c.recruiter_user_id, job_operational_overlays.c.updated_at)
Index("idx_ws_job_ownership_history_job_created", job_ownership_history.c.tenant_id,
      job_ownership_history.c.job_id, job_ownership_history.c.created_at)
Index("idx_ws_approval_request_status", approval_requests.c.tenant_id,
      approval_requests.c.status, approval_requests.c.required_authority, approval_requests.c.created_at)
Index("idx_ws_provenance_object", provenance_records.c.tenant_id, provenance_records.c.object_type,
      provenance_records.c.object_id, provenance_records.c.field_path)
Index("idx_ws_ai_suggestion_object_status", ai_suggestions.c.tenant_id, ai_suggestions.c.object_type,
      ai_suggestions.c.object_id, ai_suggestions.c.status, ai_suggestions.c.created_at)
Index("idx_ws_operational_audit_object_created", operational_audit.c.tenant_id,
      operational_audit.c.object_type, operational_audit.c.object_id, operational_audit.c.created_at)


cost_assumption_sets = Table(
    "ws_cost_assumption_set", metadata,
    U("id", primary_key=True), U("tenant_id", nullable=False), S("profile", nullable=False),
    S("version", nullable=False), Column("assumption_payload", JSON, nullable=False),
    S("status", nullable=False), D("effective_from", nullable=False), D("effective_to"),
    U("created_by", nullable=False), D("created_at", nullable=False),
    UniqueConstraint("tenant_id", "profile", "version"),
    ForeignKeyConstraint(["tenant_id", "created_by"], ["app_user.tenant_id", "app_user.id"]),
)

customer_economic_rules = Table(
    "ws_customer_economic_rule", metadata,
    U("id", primary_key=True), U("tenant_id", nullable=False), U("customer_id", nullable=False),
    S("calculation_profile", nullable=False), S("version", nullable=False),
    Column("rule_payload", JSON, nullable=False), S("status", nullable=False),
    D("effective_from", nullable=False), D("effective_to"), U("created_by", nullable=False),
    D("created_at", nullable=False),
    UniqueConstraint("tenant_id", "customer_id", "calculation_profile", "version"),
    ForeignKeyConstraint(["tenant_id", "customer_id"], ["customer.tenant_id", "customer.id"]),
    ForeignKeyConstraint(["tenant_id", "created_by"], ["app_user.tenant_id", "app_user.id"]),
)

margin_snapshots = Table(
    "ws_margin_snapshot", metadata,
    U("id", primary_key=True), U("tenant_id", nullable=False), U("job_id", nullable=False),
    U("candidate_id", nullable=False), U("recruiter_user_id", nullable=False),
    S("calculation_profile", nullable=False), U("assumption_set_id", nullable=False),
    S("assumption_version", nullable=False), Column("version", Integer, nullable=False),
    Column("input_payload", JSON, nullable=False), Column("result_payload", JSON, nullable=False),
    S("guideline_status", nullable=False), S("lifecycle_status", nullable=False),
    U("customer_rule_id"), S("customer_rule_version"),
    U("created_by", nullable=False), D("created_at", nullable=False),
    U("finalized_by"), D("finalized_at"),
    UniqueConstraint("tenant_id", "job_id", "candidate_id", "version"),
    ForeignKeyConstraint(["tenant_id", "job_id"], ["job.tenant_id", "job.id"]),
    ForeignKeyConstraint(["tenant_id", "candidate_id"], ["candidate.tenant_id", "candidate.id"]),
    ForeignKeyConstraint(["tenant_id", "recruiter_user_id"], ["app_user.tenant_id", "app_user.id"]),
    ForeignKeyConstraint(["tenant_id", "created_by"], ["app_user.tenant_id", "app_user.id"]),
    ForeignKeyConstraint(["tenant_id", "finalized_by"], ["app_user.tenant_id", "app_user.id"]),
    ForeignKeyConstraint(["assumption_set_id"], ["ws_cost_assumption_set.id"]),
    ForeignKeyConstraint(["customer_rule_id"], ["ws_customer_economic_rule.id"]),
)

margin_cost_components = Table(
    "ws_margin_cost_component", metadata,
    U("id", primary_key=True), U("tenant_id", nullable=False), U("snapshot_id", nullable=False),
    S("component_key", nullable=False), S("label", nullable=False), S("category", nullable=False),
    Column("per_week", Numeric(18,6), nullable=False),
    Column("assignment_total", Numeric(18,6), nullable=False), D("created_at", nullable=False),
    UniqueConstraint("snapshot_id", "component_key"),
    ForeignKeyConstraint(["snapshot_id"], ["ws_margin_snapshot.id"]),
)

margin_discussions = Table(
    "ws_margin_discussion", metadata,
    U("id", primary_key=True), U("tenant_id", nullable=False), U("snapshot_id", nullable=False),
    U("recorded_by", nullable=False), U("participant_user_id"), S("participant_role", nullable=False),
    S("discussion_type", nullable=False), S("notes", nullable=False), D("created_at", nullable=False),
    ForeignKeyConstraint(["snapshot_id"], ["ws_margin_snapshot.id"]),
    ForeignKeyConstraint(["tenant_id", "recorded_by"], ["app_user.tenant_id", "app_user.id"]),
    ForeignKeyConstraint(["tenant_id", "participant_user_id"], ["app_user.tenant_id", "app_user.id"]),
)

commission_projections = Table(
    "ws_commission_projection", metadata,
    U("id", primary_key=True), U("tenant_id", nullable=False), U("snapshot_id", nullable=False),
    U("recruiter_user_id", nullable=False),
    Column("commissionable_net_profit", Numeric(18,6), nullable=False),
    Column("commission_rate", Numeric(12,10), nullable=False),
    Column("projected_amount", Numeric(18,6), nullable=False), S("status", nullable=False),
    D("created_at", nullable=False), UniqueConstraint("snapshot_id"),
    ForeignKeyConstraint(["snapshot_id"], ["ws_margin_snapshot.id"]),
    ForeignKeyConstraint(["tenant_id", "recruiter_user_id"], ["app_user.tenant_id", "app_user.id"]),
)

Index("idx_ws_customer_economic_rule_effective", customer_economic_rules.c.tenant_id,
      customer_economic_rules.c.customer_id, customer_economic_rules.c.calculation_profile,
      customer_economic_rules.c.effective_from)
Index("idx_ws_margin_snapshot_job_candidate", margin_snapshots.c.tenant_id,
      margin_snapshots.c.job_id, margin_snapshots.c.candidate_id, margin_snapshots.c.version)
Index("idx_ws_margin_discussion_snapshot", margin_discussions.c.tenant_id,
      margin_discussions.c.snapshot_id, margin_discussions.c.created_at)


job_publications = Table(
    "ws_job_publication", metadata,
    U("id", primary_key=True), U("tenant_id", nullable=False), U("team_id"),
    U("job_id"), U("intake_item_id"), Column("source_snapshot", JSON, nullable=False),
    Column("enhanced_snapshot", JSON, nullable=False), Column("quality_score", JSON, nullable=False),
    S("readiness", nullable=False), S("recruiting_status", nullable=False), S("website_status", nullable=False),
    U("recruiting_approved_by"), D("recruiting_approved_at"),
    U("website_approved_by"), D("website_approved_at"),
    Column("version", Integer, nullable=False), U("created_by", nullable=False),
    D("created_at", nullable=False), D("updated_at", nullable=False),
    UniqueConstraint("tenant_id", "id"),
    ForeignKeyConstraint(["tenant_id", "team_id"], ["team.tenant_id", "team.id"]),
    ForeignKeyConstraint(["tenant_id", "job_id"], ["job.tenant_id", "job.id"]),
    ForeignKeyConstraint(["tenant_id", "intake_item_id"], ["ws_job_intake_item.tenant_id", "ws_job_intake_item.id"]),
    ForeignKeyConstraint(["tenant_id", "created_by"], ["app_user.tenant_id", "app_user.id"]),
    ForeignKeyConstraint(["tenant_id", "recruiting_approved_by"], ["app_user.tenant_id", "app_user.id"]),
    ForeignKeyConstraint(["tenant_id", "website_approved_by"], ["app_user.tenant_id", "app_user.id"]),
)

job_publication_audit = Table(
    "ws_job_publication_audit", metadata,
    U("id", primary_key=True), U("tenant_id", nullable=False), U("publication_id", nullable=False),
    U("actor_user_id", nullable=False), S("action", nullable=False), Column("details", JSON, nullable=False),
    D("created_at", nullable=False),
    ForeignKeyConstraint(["tenant_id", "publication_id"], ["ws_job_publication.tenant_id", "ws_job_publication.id"]),
    ForeignKeyConstraint(["tenant_id", "actor_user_id"], ["app_user.tenant_id", "app_user.id"]),
)

Index("idx_ws_job_publication_team_status", job_publications.c.tenant_id, job_publications.c.team_id, job_publications.c.recruiting_status, job_publications.c.website_status, job_publications.c.updated_at)
Index("idx_ws_job_publication_audit_pub_created", job_publication_audit.c.tenant_id, job_publication_audit.c.publication_id, job_publication_audit.c.created_at)

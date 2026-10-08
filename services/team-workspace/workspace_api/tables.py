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
job_source_records = Table(
    "job_source_record", metadata,
    U("id", primary_key=True), U("tenant_id", nullable=False), U("job_id"),
    S("source_system", nullable=False), S("source_id", nullable=False), S("source_status"),
    D("source_updated_at"), Column("raw_payload", JSON, nullable=False),
)
candidate_source_records = Table(
    "candidate_source_record", metadata,
    U("id", primary_key=True), U("tenant_id", nullable=False), U("candidate_id"),
    S("source_system", nullable=False), S("source_id", nullable=False), D("source_updated_at"),
    Column("raw_payload", JSON, nullable=False),
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
    U("recruiter_user_id", nullable=False), S("feedback_code", nullable=False), S("notes"),
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
    U("duplicate_job_id"), S("status", nullable=False), U("created_job_id"),
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
    Column("mapping", JSON, nullable=False), U("updated_by", nullable=False),
    D("created_at", nullable=False), D("updated_at", nullable=False),
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

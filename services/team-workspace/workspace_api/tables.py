"""Map existing canonical tables; only new ws_* tables are migrated in production.

metadata.create_all is used only by isolated tests, never by service startup.
"""
from sqlalchemy import (
    MetaData, Table, Column, String, Boolean, Integer, DateTime, Uuid, JSON,
    ForeignKeyConstraint, UniqueConstraint, CheckConstraint, Index,
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
              ForeignKeyConstraint(["tenant_id"], ["tenant.id"]))
teams = Table("team", metadata, U("id", primary_key=True), U("tenant_id", nullable=False),
              S("name", nullable=False), S("division", nullable=False), U("manager_user_id"),
              UniqueConstraint("tenant_id", "id"), ForeignKeyConstraint(["tenant_id"], ["tenant.id"]))
profiles = Table("recruiter_profile", metadata, U("user_id", primary_key=True), U("tenant_id", nullable=False), U("team_id"))
jobs = Table("job", metadata, U("id", primary_key=True), U("tenant_id", nullable=False), S("title", nullable=False),
             UniqueConstraint("tenant_id", "id"))
candidates = Table("candidate", metadata, U("id", primary_key=True), U("tenant_id", nullable=False), S("canonical_name"),
                   UniqueConstraint("tenant_id", "id"))

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
operations = Table("ws_operation", metadata, U("tenant_id", primary_key=True), U("actor_user_id", primary_key=True),
                   U("idempotency_key", primary_key=True), S("fingerprint", nullable=False),
                   Column("result", JSON, nullable=False), D("created_at", nullable=False),
                   ForeignKeyConstraint(["tenant_id", "actor_user_id"], ["app_user.tenant_id", "app_user.id"]))
Index("idx_ws_case_owner", cases.c.tenant_id, cases.c.owner_user_id, cases.c.id)
Index("idx_ws_case_team", cases.c.tenant_id, cases.c.team_id, cases.c.id)
for table in (notes, tasks, audit):
    Index("idx_" + table.name + "_case", table.c.tenant_id, table.c.case_id, table.c.created_at)

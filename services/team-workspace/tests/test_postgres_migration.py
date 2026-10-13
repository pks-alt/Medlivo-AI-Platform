from pathlib import Path
import pytest
from sqlalchemy import inspect, text, insert, select
from sqlalchemy.exc import DBAPIError
from workspace_api import tables as t
from workspace_api.store import now, uid
from conftest import idn


def test_postgres_migration_is_repeatable_and_audit_is_append_only(seeded):
    if seeded.dialect.name != "postgresql":
        pytest.skip("Requires PostgreSQL migration execution")
    sql = (Path(__file__).parents[1]/"migrations/001_workspace.sql").read_text()
    with seeded.begin() as conn:
        conn.exec_driver_sql(sql)
        conn.exec_driver_sql(sql)
        row_id=uid()
        conn.execute(insert(t.audit).values(id=row_id,tenant_id=idn(1),case_id=idn(100),actor_user_id=idn(10),
            action="synthetic.probe",entity_id=idn(100),details={},created_at=now()))
    for verb in ("UPDATE ws_audit SET action='tampered'", "DELETE FROM ws_audit"):
        with pytest.raises(DBAPIError), seeded.begin() as conn:
            conn.exec_driver_sql(verb)
    with seeded.begin() as conn:
        assert conn.scalar(select(t.audit.c.action).where(t.audit.c.id==row_id)) == "synthetic.probe"


def test_postgres_migration_builds_tables_from_canonical_only(engine):
    if engine.dialect.name != "postgresql":
        pytest.skip("Requires PostgreSQL migration execution")
    sql = (Path(__file__).parents[1]/"migrations/001_workspace.sql").read_text()
    with engine.begin() as conn:
        for table in reversed(t.metadata.sorted_tables):
            if table.name.startswith("ws_"):
                table.drop(conn)
        conn.exec_driver_sql(sql)
        assert {"ws_case","ws_note","ws_task","ws_identity","ws_audit","ws_operation"} <= set(inspect(conn).get_table_names())


def test_admin_user_management_migration_is_audited_and_guarded(seeded):
    if seeded.dialect.name != "postgresql":
        pytest.skip("Requires PostgreSQL administrator functions")
    root = Path(__file__).parents[1] / "migrations"
    with seeded.begin() as conn:
        # Production canonical tables live in public. CI isolates every test in
        # a temporary search_path schema, so qualify this migration to that
        # disposable schema without weakening production schema qualification.
        test_schema = conn.scalar(text("SELECT current_schema()"))
        conn.exec_driver_sql((root/"001_workspace.sql").read_text())
        conn.exec_driver_sql((root/"003_identity_admin.sql").read_text())
        sql = (root/"004_admin_user_management.sql").read_text().replace(
            "public.", '"' + test_schema + '".')
        conn.exec_driver_sql(sql)
        conn.exec_driver_sql(sql)

        provisioned = conn.execute(text(
            "SELECT * FROM workspace_admin.provision_user("
            ":actor,:email,:name,:role,:team,:active)"
        ), {"actor":idn(13),"email":"phase2@medlivo.com","name":"Phase Two Recruiter",
            "role":"recruiter","team":idn(30),"active":True}).mappings().one()
        target = str(provisioned["user_id"])

        updated = conn.execute(text(
            "SELECT * FROM workspace_admin.update_user("
            ":actor,:target,:name,:role,:team,:active)"
        ), {"actor":idn(13),"target":target,"name":"Phase Two Manager",
            "role":"manager","team":idn(30),"active":False}).mappings().one()
        assert updated["role"] == "manager"
        assert updated["is_active"] is False

        audit = conn.execute(text(
            "SELECT action,before_state,after_state FROM ws_admin_audit "
            "WHERE target_user_id=:target ORDER BY created_at"
        ), {"target":target}).mappings().all()
        assert [row["action"] for row in audit] == ["user.provisioned","user.updated"]
        assert audit[-1]["after_state"]["is_active"] is False
        assert audit[-1]["after_state"]["role"] == "manager"

        # An administrator cannot change their own access through this function.
        self_change = conn.execute(text(
            "SELECT * FROM workspace_admin.update_user("
            ":actor,:target,:name,:role,:team,:active)"
        ), {"actor":idn(13),"target":idn(13),"name":"Locked Out",
            "role":"recruiter","team":idn(30),"active":False}).mappings().first()
        assert self_change is None

    for verb in ("UPDATE ws_admin_audit SET action='user.updated'",
                 "DELETE FROM ws_admin_audit"):
        with pytest.raises(DBAPIError), seeded.begin() as conn:
            conn.exec_driver_sql(verb)


def test_recruiter_execution_and_outreach_migrations_are_repeatable(engine):
    if engine.dialect.name != "postgresql":
        pytest.skip("Requires PostgreSQL migration execution")
    root = Path(__file__).parents[1] / "migrations"
    with engine.begin() as conn:
        test_schema = conn.scalar(text("SELECT current_schema()"))
        for name in (
            "015_recruiter_execution_controls.sql",
            "016_outreach_drafts.sql",
        ):
            sql = (root / name).read_text().replace(
                "public.", '"' + test_schema + '".'
            )
            conn.exec_driver_sql(sql)
            conn.exec_driver_sql(sql)
        names = set(inspect(conn).get_table_names())
        assert {
            "ws_business_calendar_exception",
            "ws_protected_action_window",
            "ws_candidate_relationship",
            "ws_candidate_engagement_event",
            "ws_outreach_draft",
        } <= names


def test_staging_workflow_applies_explicit_reviewed_migrations():
    workflow = (
        Path(__file__).parents[3] / ".github" / "workflows" / "deploy-team-staging.yml"
    ).read_text()
    assert "014_job_content_standards.sql" in workflow
    assert "015_recruiter_execution_controls.sql" in workflow
    assert "016_outreach_drafts.sql" in workflow
    assert "for MIGRATION in" in workflow
    assert "find " not in workflow


def test_reviewed_migration_runner_has_replay_safe_ledger_and_legacy_sentinels():
    runner = (Path(__file__).parents[1] / "workspace_api" / "migrate.py").read_text()
    assert "ws_schema_migration" in runner
    assert "checksum_sha256" in runner
    assert "Reviewed migration checksum changed after recording" in runner
    for name in (
        "014_job_content_standards.sql",
        "015_recruiter_execution_controls.sql",
        "016_outreach_drafts.sql",
        "017_outreach_execution.sql",
        "018_gmail_provider_pilot.sql",
        "019_gmail_reply_sync.sql",
        "020_followup_sequences.sql",
        "021_scheduled_followup_execution.sql",
        "022_repair_recruiter_execution_controls.sql",
    ):
        assert name in runner
    assert "Baselined existing reviewed migration" in runner
    assert "Migration already recorded" in runner
    assert "MIGRATION_FAILED" in runner
    assert "sqlstate=" in runner
    assert "error_class=" in runner


def test_recruiter_execution_repair_migration_is_guarded_and_non_destructive():
    sql = (
        Path(__file__).parents[1] / "migrations" /
        "022_repair_recruiter_execution_controls.sql"
    ).read_text()
    assert "DROP TABLE" not in sql
    assert "TRUNCATE" not in sql
    assert "DELETE FROM" not in sql
    assert "ADD COLUMN IF NOT EXISTS assignment_version" in sql
    assert "ADD COLUMN IF NOT EXISTS meaningful_action_by" in sql
    assert "GRANT SELECT, INSERT, UPDATE ON public.ws_protected_action_window" in sql
    assert "administrator-reviewed data repair" in sql

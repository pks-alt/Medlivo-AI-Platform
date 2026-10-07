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
        conn.exec_driver_sql((root/"001_workspace.sql").read_text())
        conn.exec_driver_sql((root/"003_identity_admin.sql").read_text())
        sql = (root/"004_admin_user_management.sql").read_text()
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

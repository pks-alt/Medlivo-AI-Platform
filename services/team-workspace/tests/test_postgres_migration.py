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

import time
from uuid import uuid4
import jwt
import pytest
from sqlalchemy import select, insert, update, func
from sqlalchemy.exc import IntegrityError
from workspace_api import tables as t
from workspace_api.auth import AuthenticationError, GoogleIdentityVerifier, Identity
from workspace_api.app import create_app, build_app
from workspace_api.config import Settings
from workspace_api.store import WorkspaceStore
from fastapi.testclient import TestClient
from conftest import idn, AUDIENCE, DOMAIN

ROOT = "/api/v1/team"
CASE = ROOT + "/cases/" + idn(100)

@pytest.mark.parametrize("claims", [
    {"aud": "another-client.apps.googleusercontent.com"}, {"aud": [AUDIENCE, "second-client"]},
    {"iss": "https://attacker.example"}, {"exp": 1}, {"iat": 9999999999},
    {"hd": "another.example"}, {"hd": ""}, {"email_verified": False},
    {"email_verified": "true"}, {"email": "other@wrong.example"}, {"email": ""}, {"sub": ""}, {"azp": "another-client"},
])
def test_invalid_claims_are_rejected(verifier, token, claims):
    with pytest.raises(AuthenticationError):
        verifier.verify(token(**claims))


def test_valid_signature_and_identity(verifier, token):
    assert verifier.verify(token()) == Identity("google", "recruiter-a", "recruiter-a@example.test")
    assert verifier.verify(token(iss="accounts.google.com")) == Identity("google", "recruiter-a", "recruiter-a@example.test")


def test_wrong_signature_rejected(verifier, token):
    from cryptography.hazmat.primitives.asymmetric import rsa
    claims = jwt.decode(token(), options={"verify_signature": False})
    fake = jwt.encode(claims, rsa.generate_private_key(public_exponent=65537, key_size=2048), algorithm="RS256", headers={"kid": "other"})
    with pytest.raises(AuthenticationError): verifier.verify(fake)


def test_none_algorithm_and_malformed_tokens_rejected(verifier):
    for value in ["not-a-token", "a" * 9000, jwt.encode({"sub": "recruiter-a"}, "", algorithm="none")]:
        with pytest.raises(AuthenticationError): verifier.verify(value)


def test_missing_required_claim_rejected(verifier, token, keys):
    claims = jwt.decode(token(), options={"verify_signature": False}); claims.pop("exp")
    signed = jwt.encode(claims, keys[0], algorithm="RS256", headers={"kid": "synthetic"})
    with pytest.raises(AuthenticationError): verifier.verify(signed)


def test_key_failure_is_sanitized(token):
    def fail(value): raise OSError("PRIVATE_TOKEN=" + value)
    verifier = GoogleIdentityVerifier(AUDIENCE, DOMAIN, key_resolver=fail)
    with pytest.raises(AuthenticationError) as error: verifier.verify(token())
    assert str(error.value) == "Authentication required"


def test_disabled_default_exposes_no_workspace_routes(monkeypatch):
    monkeypatch.setenv("WORKSPACE_ENABLED", "false")
    app = TestClient(create_app())
    assert app.get("/health").json()["workspace_enabled"] is False
    assert app.get(ROOT + "/me").status_code == 404


def test_enabled_config_requires_secure_values():
    with pytest.raises(ValueError): Settings(enabled=True, database_url="sqlite:///public.db", google_client_id=AUDIENCE)
    with pytest.raises(ValueError): Settings(enabled=True, database_url="postgresql+psycopg://invalid", google_client_id="bad")


def test_secrets_are_not_in_settings_repr():
    assert "password-secret" not in repr(Settings(database_url="postgresql+psycopg://user:password-secret@host/db"))


@pytest.mark.parametrize("path", ["/me", "/cases", "/cases/" + idn(100), "/cases/" + idn(100) + "/notes"])
def test_unauthenticated_api_denied(client, path):
    response = client.get(ROOT + path)
    assert response.status_code == 401
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("subject", ["unknown-subject", "disabled", "operations"])
def test_only_provisioned_active_supported_roles(client, headers, subject):
    assert client.get(ROOT + "/me", headers=headers(subject)).status_code == 403


def test_claimed_role_and_email_do_not_grant_access(client, token):
    head = {"Authorization": "Bearer " + token(role="admin", email="admin-a@example.test", tenant_id=idn(2))}
    response = client.get(ROOT + "/cases", headers=head)
    assert [r["id"] for r in response.json()["items"]] == [idn(100)]
    assert client.get(ROOT + "/me", headers=head).json()["role"] == "recruiter"


@pytest.mark.parametrize("subject, expected", [
    ("recruiter-a", [100]), ("recruiter-b", [101]), ("manager-a", [100,101]),
    ("manager-other", [102]), ("admin-a", [100,101,102]), ("admin-foreign", [103]),
])
def test_cases_scoped_by_database_tenant_team_owner(client, headers, subject, expected):
    response = client.get(ROOT + "/cases", headers=headers(subject))
    assert response.status_code == 200
    assert [r["id"] for r in response.json()["items"]] == [idn(n) for n in expected]


def test_hidden_and_nonexistent_return_same_result(client, headers):
    results = [client.get(ROOT + "/cases/" + idn(case), headers=headers()).json() for case in (101,103,999)]
    assert results == [{"detail": "Work item not found"}] * 3


def test_cross_tenant_admin_cannot_read_notes(client, headers):
    assert client.get(CASE + "/notes", headers=headers("admin-foreign")).status_code == 404


def test_admin_routes_require_administrator_role(client, headers):
    for path in ("/admin/users", "/admin/teams", "/admin/audit"):
        assert client.get(ROOT + path, headers=headers()).status_code == 403
    response = client.patch(ROOT + "/admin/users/" + idn(11),
        json={"display_name":"Synthetic","role":"recruiter","team_id":idn(30),"is_active":True},
        headers=headers())
    assert response.status_code == 403


def test_activity_includes_actor_display_name(client, headers):
    client.post(CASE + "/notes", json={"body": "Synthetic named activity"}, headers=headers())
    rows = client.get(CASE + "/audit", headers=headers("manager-a")).json()["items"]
    assert rows[0]["actor_user_id"] == idn(10)
    assert rows[0]["actor_display_name"] == "Synthetic recruiter-a"


def test_pagination_is_bounded_and_scoped(client, headers):
    first = client.get(ROOT + "/cases?limit=1", headers=headers("manager-a")).json()
    second = client.get(ROOT + "/cases?limit=1&after=" + first["next_cursor"], headers=headers("manager-a")).json()
    assert [r["id"] for r in first["items"] + second["items"]] == [idn(100),idn(101)]
    assert second["next_cursor"] is None
    assert client.get(ROOT + "/cases?limit=10000", headers=headers()).status_code == 422


def test_deactivation_takes_effect_with_existing_valid_token(client, headers, seeded):
    head = headers()
    assert client.get(ROOT + "/me", headers=head).status_code == 200
    with seeded.begin() as conn: conn.execute(update(t.users).where(t.users.c.id == idn(10)).values(is_active=False))
    assert client.get(ROOT + "/me", headers=head).status_code == 403


def test_note_is_shared_persistent_and_actor_is_server_assigned(client, headers, seeded, verifier):
    result = client.post(CASE + "/notes", json={"body": "Synthetic availability follow-up"}, headers=headers())
    assert result.status_code == 201
    assert result.json()["actor_user_id"] == idn(10)
    another_app = TestClient(build_app(WorkspaceStore(seeded), verifier))
    notes = another_app.get(CASE + "/notes", headers=headers("manager-a")).json()["items"]
    assert notes[0]["body"] == "Synthetic availability follow-up"
    with seeded.begin() as conn:
        record = conn.execute(select(t.audit)).mappings().one()
        assert record["action"] == "note.created"
        assert "body" not in record["details"]


def test_note_retry_is_exactly_once(client, headers, seeded):
    head = headers()
    a = client.post(CASE + "/notes", json={"body": "Synthetic test"}, headers=head)
    b = client.post(CASE + "/notes", json={"body": "Synthetic test"}, headers=head)
    assert a.json() == b.json()
    with seeded.begin() as conn:
        assert conn.scalar(select(func.count()).select_from(t.notes)) == 1
        assert conn.scalar(select(func.count()).select_from(t.audit)) == 1


def test_idempotency_key_different_content_is_conflict(client, headers):
    head = headers()
    assert client.post(CASE + "/notes", json={"body": "One"}, headers=head).status_code == 201
    assert client.post(CASE + "/notes", json={"body": "Two"}, headers=head).status_code == 409


def test_duplicate_key_separate_actors_allowed(client, headers):
    key = str(uuid4())
    for subject in ("recruiter-a", "manager-a"):
        assert client.post(CASE + "/notes", json={"body": "Synthetic"}, headers=headers(subject,key)).status_code == 201


def test_write_without_idempotency_key_is_rejected(client, token):
    assert client.post(CASE + "/notes", json={"body": "Synthetic"}, headers={"Authorization": "Bearer " + token()}).status_code == 422


@pytest.mark.parametrize("payload", [
    {"body": ""}, {"body": "   "}, {"body": "x" * 4001}, {"body": "Synthetic", "tenant_id": idn(2)},
    {"body": "Synthetic", "actor_user_id": idn(13)},
])
def test_invalid_note_or_identity_spoofing_rejected(client, headers, payload):
    assert client.post(CASE + "/notes", json=payload, headers=headers()).status_code == 422


def test_oversized_and_nonjson_body_rejected(client, headers):
    assert client.post(CASE + "/notes", content=b'x' * 17000, headers={**headers(),"Content-Type":"application/json"}).status_code == 413
    assert client.post(CASE + "/notes", data={"body": "text"}, headers=headers()).status_code == 415


def test_validation_response_does_not_echo_sensitive_input(client, headers):
    response = client.post(CASE + "/notes", json={"body": "Secret-not-for-errors", "role": "admin"}, headers=headers())
    assert response.status_code == 422
    assert "Secret-not-for-errors" not in response.text


def test_inaccessible_case_cannot_be_modified(client, headers, seeded):
    response = client.post(ROOT + "/cases/"+idn(103)+"/notes", json={"body":"Synthetic"}, headers=headers())
    assert response.status_code == 404
    with seeded.begin() as conn: assert conn.scalar(select(func.count()).select_from(t.notes)) == 0


def test_audit_failure_rolls_back_note_and_receipt(client, headers, seeded, monkeypatch):
    def fail(*args):
        raise IntegrityError("SQL containing sensitive note", {}, Exception("constraint"))
    monkeypatch.setattr(WorkspaceStore, "_audit", fail)
    response = client.post(CASE + "/notes", json={"body":"Synthetic"}, headers=headers())
    assert response.status_code == 409
    with seeded.begin() as conn:
        assert conn.scalar(select(func.count()).select_from(t.notes)) == 0
        assert conn.scalar(select(func.count()).select_from(t.operations)) == 0


def test_task_version_conflict_and_retry(client, headers):
    response = client.post(CASE + "/tasks", json={"title":"Synthetic follow-up", "due_at":"2026-10-12T16:00:00Z"}, headers=headers())
    assert response.status_code == 201
    url = CASE + "/tasks/" + response.json()["id"]
    head = headers()
    first = client.patch(url, json={"status":"done", "expected_version":1}, headers=head)
    assert first.status_code == 200 and first.json()["version"] == 2
    assert client.patch(url, json={"status":"done", "expected_version":1}, headers=head).json() == first.json()
    assert client.patch(url, json={"status":"open", "expected_version":1}, headers=headers()).status_code == 409
    assert client.patch(url, json={"status":"open", "expected_version":2}, headers=headers()).status_code == 200


def test_task_requires_timezone_and_cannot_send(client, headers):
    for due in ["2026-10-12T16:00:00", "not-a-date"]:
        assert client.post(CASE + "/tasks", json={"title":"Synthetic", "due_at":due}, headers=headers()).status_code == 422
    response = client.post(CASE + "/tasks", json={"title":"Synthetic", "due_at":"2026-10-12T16:00:00Z"}, headers=headers())
    url = CASE + "/tasks/" + response.json()["id"]
    assert client.patch(url, json={"status":"sent", "expected_version":1}, headers=headers()).status_code == 422


def test_task_cannot_be_referenced_through_another_case(client, headers):
    result = client.post(CASE + "/tasks", json={"title":"Synthetic", "due_at":"2026-10-12T16:00:00Z"}, headers=headers()).json()
    url = ROOT + "/cases/"+idn(101)+"/tasks/"+result["id"]
    assert client.patch(url, json={"status":"done", "expected_version":1}, headers=headers("manager-a")).status_code == 404


def test_recruiter_cannot_reassign(client, headers):
    response = client.post(CASE + "/reassign", json={"owner_user_id":idn(11),"reason":"Synthetic coverage change","expected_version":1}, headers=headers())
    assert response.status_code == 403


def test_manager_reassignment_transfers_scope_and_preserves_history(client, headers):
    note_head = headers()
    client.post(CASE + "/notes", json={"body":"Synthetic handoff"}, headers=note_head)
    action = {"owner_user_id":idn(11),"reason":"Synthetic coverage change","expected_version":1}
    head = headers("manager-a")
    response = client.post(CASE + "/reassign", json=action, headers=head)
    assert response.status_code == 200 and response.json()["version"] == 2
    assert client.post(CASE + "/reassign", json=action, headers=head).json() == response.json()
    assert client.get(CASE, headers=headers()).status_code == 404
    assert client.get(CASE, headers=headers("recruiter-b")).status_code == 200
    # Replaying an old successful save does not bypass current access.
    assert client.post(CASE + "/notes", json={"body":"Synthetic handoff"}, headers=note_head).status_code == 404
    rows = client.get(CASE + "/audit", headers=headers("recruiter-b")).json()["items"]
    assert {r["action"] for r in rows} == {"note.created", "case.reassigned"}


@pytest.mark.parametrize("target", [15,16,20,999])
def test_reassignment_rejects_wrong_team_inactive_foreign_unknown(client, headers, target):
    response = client.post(CASE + "/reassign", json={"owner_user_id":idn(target),"reason":"Synthetic coverage change","expected_version":1}, headers=headers("manager-a"))
    assert response.status_code == 422


def test_other_team_manager_cannot_reassign(client, headers):
    assert client.post(CASE + "/reassign", json={"owner_user_id":idn(11),"reason":"Synthetic change","expected_version":1}, headers=headers("manager-other")).status_code == 404


def test_reassignment_requires_reason_and_current_version(client, headers):
    for payload, code in [
        ({"owner_user_id":idn(11),"reason":"","expected_version":1},422),
        ({"owner_user_id":idn(11),"reason":"Synthetic change","expected_version":2},409),
    ]:
        assert client.post(CASE + "/reassign", json=payload, headers=headers("manager-a")).status_code == code


def test_audit_has_no_update_delete_routes(client, headers):
    assert client.delete(CASE + "/audit", headers=headers("admin-a")).status_code == 405
    assert client.delete(CASE + "/notes", headers=headers("admin-a")).status_code == 405


def test_foreign_keys_reject_cross_tenant_identity(seeded):
    with pytest.raises(IntegrityError), seeded.begin() as conn:
        conn.execute(insert(t.identities).values(provider="google",subject="wrong",tenant_id=idn(1),user_id=idn(20)))


def test_foreign_keys_reject_cross_tenant_note(seeded):
    from workspace_api.store import now
    with pytest.raises(IntegrityError), seeded.begin() as conn:
        conn.execute(insert(t.notes).values(id=str(uuid4()),tenant_id=idn(2),case_id=idn(100),actor_user_id=idn(20),body="Synthetic",created_at=now()))


def test_database_error_is_sanitized(client, headers, monkeypatch):
    from sqlalchemy.exc import OperationalError
    def fail(*args): raise OperationalError("SELECT secret", {}, Exception("postgresql://password@host"))
    monkeypatch.setattr(WorkspaceStore,"me",fail)
    response = client.get(ROOT + "/me", headers=headers())
    assert response.status_code == 503
    assert response.json() == {"detail":"Workspace storage is unavailable"}


def test_no_browser_cross_origin_permission(client, headers):
    response = client.get(ROOT + "/me", headers={**headers(), "Origin":"https://attacker.example"})
    assert "access-control-allow-origin" not in response.headers


def test_eligible_owners_only_lists_active_same_team_recruiters(client, headers):
    response = client.get(CASE + "/eligible-owners", headers=headers("manager-a"))
    assert response.status_code == 200
    assert [r["id"] for r in response.json()["items"]] == [idn(10),idn(11)]
    assert all(set(r) == {"id","display_name"} for r in response.json()["items"])
    assert client.get(CASE + "/eligible-owners", headers=headers()).status_code == 403
    assert client.get(CASE + "/eligible-owners", headers=headers("admin-foreign")).status_code == 404


def test_cross_tenant_case_link_is_rejected(seeded):
    from workspace_api.store import now
    with seeded.begin() as conn:
        conn.execute(insert(t.candidates).values(id=idn(800),tenant_id=idn(2),canonical_name="Synthetic foreign candidate"))
    with pytest.raises(IntegrityError), seeded.begin() as conn:
        conn.execute(insert(t.cases).values(id=idn(900),tenant_id=idn(1),team_id=idn(30),owner_user_id=idn(10),
            candidate_id=idn(800),title="Synthetic case",version=1,created_at=now(),updated_at=now()))


def test_storage_survives_new_engine_and_process_layer(seeded, headers, verifier, client):
    # A second SQLAlchemy engine simulates a fresh service process, not localStorage.
    from sqlalchemy import create_engine
    if seeded.dialect.name != "sqlite":
        pytest.skip("SQLite file-reopen persistence probe; PostgreSQL sharing covered by API and transaction tests")
    client.post(CASE + "/notes", json={"body":"Synthetic persistent note"}, headers=headers())
    new_engine = create_engine(seeded.url, connect_args={"check_same_thread":False})
    try:
        app = TestClient(build_app(WorkspaceStore(new_engine),verifier))
        rows = app.get(CASE + "/notes",headers=headers("manager-a")).json()["items"]
        assert rows[0]["body"] == "Synthetic persistent note"
    finally:
        new_engine.dispose()


def test_postgres_concurrent_note_retries_commit_once(client, headers, seeded):
    if seeded.dialect.name != "postgresql":
        pytest.skip("Requires real PostgreSQL row locking")
    from concurrent.futures import ThreadPoolExecutor
    head = headers()
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _:client.post(CASE + "/notes",json={"body":"Concurrent synthetic"},headers=head),range(2)))
    assert [r.status_code for r in results] == [201,201]
    assert results[0].json() == results[1].json()
    with seeded.begin() as conn: assert conn.scalar(select(func.count()).select_from(t.notes)) == 1


def test_postgres_concurrent_task_edits_prevent_lost_update(client, headers, seeded):
    if seeded.dialect.name != "postgresql":
        pytest.skip("Requires real PostgreSQL row locking")
    from concurrent.futures import ThreadPoolExecutor
    task = client.post(CASE+"/tasks",json={"title":"Concurrent synthetic task","due_at":"2026-10-12T16:00:00Z"},headers=headers()).json()
    url = CASE + "/tasks/" + task["id"]
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: client.patch(url,json={"status":"done","expected_version":1},headers=headers()),range(2)))
    assert sorted(r.status_code for r in results) == [200,409]

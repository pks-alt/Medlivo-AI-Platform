import os
import time
from uuid import uuid4
import pytest
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, insert, text
from workspace_api import tables as t
from workspace_api.auth import GoogleIdentityVerifier
from workspace_api.app import build_app
from workspace_api.store import WorkspaceStore, now

AUDIENCE = "synthetic-client.apps.googleusercontent.com"
DOMAIN = "example.test"

def idn(n):
    return f"00000000-0000-0000-0000-{n:012d}"


@pytest.fixture(scope="session")
def keys():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key, key.public_key()


@pytest.fixture
def token(keys):
    def issue(subject="recruiter-a", **overrides):
        timestamp = int(time.time())
        values = {"iss": "https://accounts.google.com", "aud": AUDIENCE, "sub": subject,
                  "email": subject + "@" + DOMAIN, "iat": timestamp - 5, "exp": timestamp + 3600,
                  "email_verified": True, "hd": DOMAIN}
        values.update(overrides)
        return jwt.encode(values, keys[0], algorithm="RS256", headers={"kid": "synthetic-test-key"})
    return issue


@pytest.fixture
def verifier(keys):
    return GoogleIdentityVerifier(AUDIENCE, DOMAIN, key_resolver=lambda token: keys[1])


@pytest.fixture
def engine(tmp_path):
    postgres = os.getenv("WORKSPACE_TEST_DATABASE_URL")
    schema = "ws_test_" + uuid4().hex
    if postgres:
        control = create_engine(postgres)
        with control.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        result = create_engine(postgres, connect_args={"options": f"-csearch_path={schema}"}, hide_parameters=True)
    else:
        result = create_engine("sqlite:///" + str(tmp_path / "workspace.sqlite"), connect_args={"check_same_thread": False}, hide_parameters=True)
        @event.listens_for(result, "connect")
        def foreign_keys(connection, record):
            connection.execute("PRAGMA foreign_keys=ON")
    t.metadata.create_all(result)
    yield result
    result.dispose()
    if postgres:
        with control.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        control.dispose()


@pytest.fixture
def seeded(engine):
    with engine.begin() as conn:
        conn.execute(insert(t.tenant), [{"id": idn(1), "slug": "test-a", "name": "Synthetic A"},
                                        {"id": idn(2), "slug": "test-b", "name": "Synthetic B"}])
        entries = [
            (10, 1, "recruiter-a", "recruiter", True), (11, 1, "recruiter-b", "recruiter", True),
            (12, 1, "manager-a", "manager", True), (13, 1, "admin-a", "admin", True),
            (14, 1, "manager-other", "manager", True), (15, 1, "recruiter-other", "recruiter", True),
            (16, 1, "disabled", "recruiter", False), (17, 1, "operations", "operations", True),
            (20, 2, "recruiter-foreign", "recruiter", True), (21, 2, "admin-foreign", "admin", True),
        ]
        for user, tenant, subject, role, active in entries:
            conn.execute(insert(t.users).values(id=idn(user), tenant_id=idn(tenant), email=subject+"@example.test",
                display_name="Synthetic " + subject, role=role, is_active=active))
            conn.execute(insert(t.identities).values(provider="google", subject=subject, tenant_id=idn(tenant), user_id=idn(user)))
        conn.execute(insert(t.teams), [
            {"id": idn(30), "tenant_id": idn(1), "name": "Synthetic rehab", "division": "Rehabilitation", "manager_user_id": idn(12)},
            {"id": idn(31), "tenant_id": idn(1), "name": "Synthetic nursing", "division": "Nursing & Allied", "manager_user_id": idn(14)},
            {"id": idn(32), "tenant_id": idn(2), "name": "Synthetic foreign", "division": "Locum Tenens", "manager_user_id": idn(21)},
        ])
        for user, tenant, team in [(10,1,30),(11,1,30),(15,1,31),(16,1,30),(20,2,32)]:
            conn.execute(insert(t.profiles).values(user_id=idn(user), tenant_id=idn(tenant), team_id=idn(team)))
        for case, tenant, team, owner in [(100,1,30,10),(101,1,30,11),(102,1,31,15),(103,2,32,20)]:
            conn.execute(insert(t.cases).values(id=idn(case), tenant_id=idn(tenant), team_id=idn(team), owner_user_id=idn(owner),
                title=f"Synthetic work item {case}", version=1, created_at=now(), updated_at=now()))
    return engine


@pytest.fixture
def client(seeded, verifier):
    return TestClient(build_app(WorkspaceStore(seeded), verifier))


@pytest.fixture
def headers(token):
    def make(subject="recruiter-a", key=None):
        return {"Authorization": "Bearer " + token(subject), "Idempotency-Key": key or str(uuid4())}
    return make

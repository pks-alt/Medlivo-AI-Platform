"""Loopback-only synthetic private API for the browser integration test. NOT deployed."""
import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, update, event
from cryptography.hazmat.primitives import serialization
import uvicorn
ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT/'services/team-workspace'),str(ROOT/'services/team-workspace/tests')]
from conftest import seeded, idn
from workspace_api import tables as t
from workspace_api.app import build_app
from workspace_api.auth import GoogleIdentityVerifier
from workspace_api.store import WorkspaceStore
engine=create_engine('sqlite:///'+str(Path(os.environ['TEAM_FIXTURE_DIR'])/'api.sqlite'),connect_args={'check_same_thread':False})
@event.listens_for(engine,'connect')
def fk(conn,record): conn.execute('PRAGMA foreign_keys=ON')
t.metadata.create_all(engine)
seeded.__wrapped__(engine)
with engine.begin() as conn:
    for n,name in [(10,'Alex Chen'),(11,'Taylor Morgan'),(12,'Jordan Lee')]:
        conn.execute(update(t.users).where(t.users.c.id==idn(n)).values(display_name=name))
    for n,title in [(100,'TEST · Physical Therapist · Dallas'),(101,'TEST · Occupational Therapist · Austin')]:
        conn.execute(update(t.cases).where(t.cases.c.id==idn(n)).values(title=title))
key=serialization.load_pem_public_key(Path(os.environ['TEAM_FIXTURE_PUBLIC_KEY']).read_bytes())
verifier=GoogleIdentityVerifier('test.apps.googleusercontent.com','example.test',key_resolver=lambda token:key)
uvicorn.run(build_app(WorkspaceStore(engine),verifier),host='127.0.0.1',port=9409,access_log=False,log_level='warning')

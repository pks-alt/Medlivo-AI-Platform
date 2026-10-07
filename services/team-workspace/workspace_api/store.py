from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from uuid import UUID, uuid4
from sqlalchemy import select, insert, update, and_, true, text
from sqlalchemy.exc import IntegrityError
from . import tables as t
from .auth import Identity


class AccessError(Exception):
    def __init__(self, status: int, message: str):
        self.status, self.message = status, message
        super().__init__(message)


def now():
    return datetime.now(timezone.utc)


def uid():
    return str(uuid4())


def json_value(value):
    """JSON-compatible output for receipts, without serializing arbitrary objects."""
    if isinstance(value, datetime):
        return value.replace(tzinfo=timezone.utc).isoformat() if value.tzinfo is None else value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    raise TypeError("Unsupported response value")


def clean(row):
    return json.loads(json.dumps(dict(row), default=json_value))


class WorkspaceStore:
    def __init__(self, engine):
        self.engine = engine

    def _principal(self, conn, identity: Identity):
        def lookup():
            return conn.execute(select(t.users).join(t.identities, and_(
                t.users.c.id == t.identities.c.user_id, t.users.c.tenant_id == t.identities.c.tenant_id
            )).where(t.identities.c.provider == identity.provider, t.identities.c.subject == identity.subject,
                     t.users.c.is_active.is_(True))).mappings().first()
        row = lookup()
        # Automatic first-login binding is deliberately limited to the same
        # Medlivo email namespace enforced by the guarded database function.
        # Other verified domains remain ordinary unprovisioned access denials.
        if (row is None and conn.dialect.name == "postgresql"
                and identity.email.lower().endswith("@medlivo.com")):
            conn.execute(text("SELECT * FROM workspace_admin.bind_google_identity(:provider,:subject,:email)"),
                         {"provider": identity.provider, "subject": identity.subject, "email": identity.email}).all()
            row = lookup()
        if row is None or row["role"] not in {"admin", "manager", "recruiter"}:
            raise AccessError(403, "Workspace access is not enabled for this account")
        return row

    def _scope(self, principal):
        if principal["role"] == "admin":
            return true()
        if principal["role"] == "manager":
            return t.cases.c.team_id.in_(select(t.teams.c.id).where(
                t.teams.c.tenant_id == principal["tenant_id"], t.teams.c.manager_user_id == principal["id"]))
        return t.cases.c.owner_user_id == principal["id"]

    def _case(self, conn, principal, case_id, lock=False):
        statement = select(t.cases).where(t.cases.c.id == case_id,
            t.cases.c.tenant_id == principal["tenant_id"], self._scope(principal))
        if lock:
            statement = statement.with_for_update()
        row = conn.execute(statement).mappings().first()
        if row is None:
            # Same response for nonexistent, another tenant, or unassigned records.
            raise AccessError(404, "Work item not found")
        return row

    def me(self, identity):
        with self.engine.begin() as conn:
            principal = self._principal(conn, identity)
            return {key: principal[key] for key in ("id", "display_name", "role")}

    def admin_teams(self, identity):
        with self.engine.begin() as conn:
            principal = self._principal(conn, identity)
            if principal["role"] != "admin":
                raise AccessError(403, "Administrator access required")
            rows = conn.execute(
                select(t.teams.c.id, t.teams.c.name, t.teams.c.division, t.teams.c.manager_user_id)
                .where(t.teams.c.tenant_id == principal["tenant_id"])
                .order_by(t.teams.c.name)
                .limit(201)
            ).mappings().all()
            return {"items": [dict(row) for row in rows[:200]], "truncated": len(rows) > 200}

    def admin_users(self, identity):
        with self.engine.begin() as conn:
            principal = self._principal(conn, identity)
            if principal["role"] != "admin":
                raise AccessError(403, "Administrator access required")
            rows = conn.execute(
                select(t.users.c.id, t.users.c.email, t.users.c.display_name, t.users.c.role, t.users.c.is_active,
                       t.profiles.c.team_id)
                .outerjoin(t.profiles, and_(t.profiles.c.user_id == t.users.c.id,
                                            t.profiles.c.tenant_id == t.users.c.tenant_id))
                .where(t.users.c.tenant_id == principal["tenant_id"])
                .order_by(t.users.c.email)
                .limit(501)
            ).mappings().all()
            return {"items": [dict(row) for row in rows[:500]], "truncated": len(rows) > 500}

    def _admin_mutate(self, identity, key, action, payload, callback):
        fingerprint = hashlib.sha256(json.dumps({"action": action, "payload": payload},
            sort_keys=True, separators=(",", ":"), default=json_value).encode()).hexdigest()
        try:
            with self.engine.begin() as conn:
                principal = self._principal(conn, identity)
                if principal["role"] != "admin":
                    raise AccessError(403, "Administrator access required")
                replay = self._receipt(conn, principal, key, fingerprint)
                if replay is not None:
                    return replay
                result = clean(callback(conn, principal))
                conn.execute(insert(t.operations).values(
                    tenant_id=principal["tenant_id"], actor_user_id=principal["id"],
                    idempotency_key=key, fingerprint=fingerprint, result=result, created_at=now()))
                return result
        except IntegrityError:
            with self.engine.begin() as conn:
                principal = self._principal(conn, identity)
                if principal["role"] != "admin":
                    raise AccessError(403, "Administrator access required")
                replay = self._receipt(conn, principal, key, fingerprint)
                if replay is not None:
                    return replay
            raise AccessError(409, "Conflicting administrator change; reload before retrying") from None

    def admin_provision_user(self, identity, key, value):
        payload = {"email": value.email, "display_name": value.display_name, "role": value.role,
                   "team_id": str(value.team_id) if value.team_id else None, "is_active": value.is_active}
        def apply(conn, principal):
            row = conn.execute(text(
                "SELECT * FROM workspace_admin.provision_user("
                ":actor_user_id,:email,:display_name,:role,:team_id,:is_active)"
            ), {"actor_user_id": principal["id"], **payload}).mappings().first()
            if row is None:
                raise AccessError(422, "User could not be provisioned with those settings")
            return dict(row)
        return self._admin_mutate(identity, key, "admin.user.provision", payload, apply)

    def admin_update_user(self, identity, user_id, key, value):
        payload = {"user_id": user_id, "display_name": value.display_name, "role": value.role,
                   "team_id": str(value.team_id) if value.team_id else None, "is_active": value.is_active}
        def apply(conn, principal):
            row = conn.execute(text(
                "SELECT * FROM workspace_admin.update_user("
                ":actor_user_id,:target_user_id,:display_name,:role,:team_id,:is_active)"
            ), {"actor_user_id": principal["id"], "target_user_id": user_id,
                "display_name": value.display_name, "role": value.role,
                "team_id": str(value.team_id) if value.team_id else None,
                "is_active": value.is_active}).mappings().first()
            if row is None:
                raise AccessError(422, "User could not be updated. Check the role, team, status, and self-lockout rules.")
            return dict(row)
        return self._admin_mutate(identity, key, "admin.user.update", payload, apply)

    def admin_audit(self, identity, *, limit=50):
        with self.engine.begin() as conn:
            principal = self._principal(conn, identity)
            if principal["role"] != "admin":
                raise AccessError(403, "Administrator access required")
            actor = t.users.alias("admin_actor")
            target = t.users.alias("admin_target")
            rows = conn.execute(
                select(t.admin_audit,
                       actor.c.display_name.label("actor_display_name"),
                       target.c.display_name.label("target_display_name"),
                       target.c.email.label("target_email"))
                .join(actor, and_(actor.c.id == t.admin_audit.c.actor_user_id,
                                  actor.c.tenant_id == t.admin_audit.c.tenant_id))
                .join(target, and_(target.c.id == t.admin_audit.c.target_user_id,
                                   target.c.tenant_id == t.admin_audit.c.tenant_id))
                .where(t.admin_audit.c.tenant_id == principal["tenant_id"])
                .order_by(t.admin_audit.c.created_at.desc(), t.admin_audit.c.id.desc())
                .limit(limit)
            ).mappings().all()
            return {"items": [clean(row) for row in rows]}

    def list_cases(self, identity, *, after=None, limit=50):
        with self.engine.begin() as conn:
            principal = self._principal(conn, identity)
            statement = select(t.cases).where(t.cases.c.tenant_id == principal["tenant_id"], self._scope(principal))
            if after:
                statement = statement.where(t.cases.c.id > after)
            rows = conn.execute(statement.order_by(t.cases.c.id).limit(limit + 1)).mappings().all()
            return self._page(rows, limit)

    def get_case(self, identity, case_id):
        with self.engine.begin() as conn:
            return clean(self._case(conn, self._principal(conn, identity), case_id))

    def eligible_owners(self, identity, case_id):
        with self.engine.begin() as conn:
            principal = self._principal(conn, identity)
            case = self._case(conn, principal, case_id)
            if principal["role"] not in {"manager", "admin"}:
                raise AccessError(403, "Manager access required")
            rows = conn.execute(select(t.users.c.id, t.users.c.display_name).join(t.profiles, and_(
                t.profiles.c.user_id == t.users.c.id, t.profiles.c.tenant_id == t.users.c.tenant_id
            )).where(t.users.c.tenant_id == principal["tenant_id"], t.profiles.c.team_id == case["team_id"],
                     t.users.c.is_active.is_(True), t.users.c.role == "recruiter").order_by(t.users.c.id).limit(101)).mappings().all()
            return {"items": [dict(row) for row in rows[:100]], "truncated": len(rows) > 100}

    @staticmethod
    def _page(rows, limit):
        more = len(rows) > limit
        items = [clean(row) for row in rows[:limit]]
        return {"items": items, "next_cursor": items[-1]["id"] if more else None}

    def records(self, identity, case_id, kind, *, after=None, limit=50):
        table = {"notes": t.notes, "tasks": t.tasks, "audit": t.audit}[kind]
        with self.engine.begin() as conn:
            principal = self._principal(conn, identity)
            self._case(conn, principal, case_id)
            if kind == "audit":
                statement = (
                    select(t.audit, t.users.c.display_name.label("actor_display_name"))
                    .join(t.users, and_(
                        t.users.c.id == t.audit.c.actor_user_id,
                        t.users.c.tenant_id == t.audit.c.tenant_id,
                    ))
                    .where(
                        t.audit.c.tenant_id == principal["tenant_id"],
                        t.audit.c.case_id == case_id,
                    )
                )
            elif kind == "notes":
                statement = (
                    select(table, t.users.c.display_name.label("actor_display_name"))
                    .join(t.users, and_(
                        t.users.c.id == table.c.actor_user_id,
                        t.users.c.tenant_id == table.c.tenant_id,
                    ))
                    .where(
                        table.c.tenant_id == principal["tenant_id"],
                        table.c.case_id == case_id,
                    )
                )
            else:
                statement = (
                    select(table, table.c.created_by.label("actor_user_id"),
                           t.users.c.display_name.label("actor_display_name"))
                    .join(t.users, and_(
                        t.users.c.id == table.c.created_by,
                        t.users.c.tenant_id == table.c.tenant_id,
                    ))
                    .where(
                        table.c.tenant_id == principal["tenant_id"],
                        table.c.case_id == case_id,
                    )
                )
            if after:
                statement = statement.where(table.c.id > after)
            return self._page(conn.execute(statement.order_by(table.c.id).limit(limit + 1)).mappings().all(), limit)

    def _receipt(self, conn, principal, key, fingerprint):
        row = conn.execute(select(t.operations).where(t.operations.c.tenant_id == principal["tenant_id"],
            t.operations.c.actor_user_id == principal["id"], t.operations.c.idempotency_key == key)).mappings().first()
        if row is None:
            return None
        if row["fingerprint"] != fingerprint:
            raise AccessError(409, "Idempotency key was already used for a different request")
        return row["result"]

    def _audit(self, conn, principal, case_id, action, entity_id, details):
        conn.execute(insert(t.audit).values(id=uid(), tenant_id=principal["tenant_id"], case_id=case_id,
            actor_user_id=principal["id"], action=action, entity_id=entity_id, details=details, created_at=now()))

    def _mutate(self, identity, case_id, key, action, payload, callback):
        fingerprint = hashlib.sha256(json.dumps({"action": action, "case_id": case_id, "payload": payload},
            sort_keys=True, separators=(",", ":"), default=json_value).encode()).hexdigest()
        try:
            with self.engine.begin() as conn:
                principal = self._principal(conn, identity)
                case = self._case(conn, principal, case_id, lock=True)
                replay = self._receipt(conn, principal, key, fingerprint)
                if replay is not None:
                    return replay
                result = clean(callback(conn, principal, case))
                conn.execute(insert(t.operations).values(tenant_id=principal["tenant_id"], actor_user_id=principal["id"],
                    idempotency_key=key, fingerprint=fingerprint, result=result, created_at=now()))
                return result
        except IntegrityError:
            # Roll back the entire transaction, including the note/task and audit.
            # A racing identical request may already have committed the receipt.
            with self.engine.begin() as conn:
                principal = self._principal(conn, identity)
                self._case(conn, principal, case_id)
                replay = self._receipt(conn, principal, key, fingerprint)
                if replay is not None:
                    return replay
            raise AccessError(409, "Conflicting change; reload the work item before retrying") from None

    def add_note(self, identity, case_id, key, body):
        def apply(conn, principal, case):
            row = dict(id=uid(), tenant_id=principal["tenant_id"], case_id=case_id,
                       actor_user_id=principal["id"], body=body, created_at=now())
            conn.execute(insert(t.notes).values(**row))
            self._audit(conn, principal, case_id, "note.created", row["id"], {"characters": len(body)})
            return row
        return self._mutate(identity, case_id, key, "note.created", {"body": body}, apply)

    def add_task(self, identity, case_id, key, title, due_at):
        def apply(conn, principal, case):
            row = dict(id=uid(), tenant_id=principal["tenant_id"], case_id=case_id, created_by=principal["id"],
                title=title, due_at=due_at, status="open", version=1, created_at=now(), updated_at=now())
            conn.execute(insert(t.tasks).values(**row))
            self._audit(conn, principal, case_id, "task.created", row["id"], {"status": "open"})
            return row
        return self._mutate(identity, case_id, key, "task.created", {"title": title, "due_at": due_at}, apply)

    def update_task(self, identity, case_id, task_id, key, status, expected_version):
        def apply(conn, principal, case):
            where = and_(t.tasks.c.id == task_id, t.tasks.c.case_id == case_id, t.tasks.c.tenant_id == principal["tenant_id"])
            old = conn.execute(select(t.tasks).where(where)).mappings().first()
            if old is None:
                raise AccessError(404, "Task not found")
            if old["version"] != expected_version:
                raise AccessError(409, "This task changed; reload it before saving")
            timestamp = now()
            updated = conn.execute(update(t.tasks).where(where, t.tasks.c.version == expected_version)
                .values(status=status, version=expected_version + 1, updated_at=timestamp))
            if updated.rowcount != 1:
                raise AccessError(409, "This task changed; reload it before saving")
            self._audit(conn, principal, case_id, "task.updated", task_id,
                        {"from": old["status"], "to": status, "version": expected_version + 1})
            return dict(old, status=status, version=expected_version + 1, updated_at=timestamp)
        return self._mutate(identity, case_id, key, "task.updated", {"task_id": task_id, "status": status,
                             "expected_version": expected_version}, apply)

    def reassign(self, identity, case_id, key, owner_user_id, reason, expected_version):
        def apply(conn, principal, case):
            if principal["role"] not in {"manager", "admin"}:
                raise AccessError(403, "Only an authorized manager or administrator can reassign work")
            target = conn.execute(select(t.users.c.id).join(t.profiles, and_(
                t.profiles.c.user_id == t.users.c.id, t.profiles.c.tenant_id == t.users.c.tenant_id
            )).where(t.users.c.id == owner_user_id, t.users.c.tenant_id == principal["tenant_id"],
                     t.users.c.is_active.is_(True), t.users.c.role == "recruiter", t.profiles.c.team_id == case["team_id"])).first()
            if target is None:
                raise AccessError(422, "Select an active recruiter in this work item's team")
            if case["version"] != expected_version:
                raise AccessError(409, "Ownership changed; reload the work item before saving")
            if case["owner_user_id"] == owner_user_id:
                raise AccessError(422, "The selected recruiter already owns this work item")
            timestamp = now()
            result = conn.execute(update(t.cases).where(t.cases.c.id == case_id, t.cases.c.tenant_id == principal["tenant_id"],
                    t.cases.c.version == expected_version).values(owner_user_id=owner_user_id,
                        version=expected_version + 1, updated_at=timestamp))
            if result.rowcount != 1:
                raise AccessError(409, "Ownership changed; reload the work item before saving")
            self._audit(conn, principal, case_id, "case.reassigned", case_id,
                {"from_user_id": case["owner_user_id"], "to_user_id": owner_user_id, "reason": reason,
                 "version": expected_version + 1})
            return dict(case, owner_user_id=owner_user_id, version=expected_version + 1, updated_at=timestamp)
        return self._mutate(identity, case_id, key, "case.reassigned", {"owner_user_id": owner_user_id,
                             "reason": reason, "expected_version": expected_version}, apply)

from __future__ import annotations
from datetime import datetime, date, timezone
import hashlib
import json
from uuid import UUID, uuid4
from sqlalchemy import select, insert, update, and_, true, text
from sqlalchemy.exc import IntegrityError
from . import tables as t
from .auth import Identity
from .job_intake import process_rows, parse_xlsx, suggest_mapping


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
    if isinstance(value, date):
        return value.isoformat()
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
            google_identity = t.identities.alias("google_identity")
            rows = conn.execute(
                select(t.users.c.id, t.users.c.email, t.users.c.display_name, t.users.c.role, t.users.c.is_active,
                       t.profiles.c.team_id, google_identity.c.user_id.label("google_identity_user_id"))
                .outerjoin(t.profiles, and_(t.profiles.c.user_id == t.users.c.id,
                                            t.profiles.c.tenant_id == t.users.c.tenant_id))
                .outerjoin(google_identity, and_(
                    google_identity.c.user_id == t.users.c.id,
                    google_identity.c.tenant_id == t.users.c.tenant_id,
                    google_identity.c.provider == "google"))
                .where(t.users.c.tenant_id == principal["tenant_id"])
                .order_by(t.users.c.email)
                .limit(501)
            ).mappings().all()
            items = []
            for row in rows[:500]:
                item = dict(row)
                item["identity_bound"] = bool(item.pop("google_identity_user_id"))
                items.append(item)
            return {"items": items, "truncated": len(rows) > 500}

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

    def manager_overview(self, identity):
        with self.engine.begin() as conn:
            principal = self._principal(conn, identity)
            if principal["role"] not in {"manager", "admin"}:
                raise AccessError(403, "Manager access required")

            if principal["role"] == "manager":
                team_rows = conn.execute(
                    select(t.teams.c.id, t.teams.c.name, t.teams.c.division)
                    .where(
                        t.teams.c.tenant_id == principal["tenant_id"],
                        t.teams.c.manager_user_id == principal["id"],
                    )
                    .order_by(t.teams.c.name)
                ).mappings().all()
            else:
                team_rows = conn.execute(
                    select(t.teams.c.id, t.teams.c.name, t.teams.c.division)
                    .where(t.teams.c.tenant_id == principal["tenant_id"])
                    .order_by(t.teams.c.name)
                ).mappings().all()

            team_ids = [row["id"] for row in team_rows]
            if not team_ids:
                return {
                    "teams": [],
                    "totals": {"work_items": 0, "active_recruiters": 0, "open_followups": 0, "overdue_followups": 0},
                    "recruiters": [],
                }

            case_rows = conn.execute(
                select(t.cases.c.id, t.cases.c.team_id, t.cases.c.owner_user_id)
                .where(
                    t.cases.c.tenant_id == principal["tenant_id"],
                    t.cases.c.team_id.in_(team_ids),
                )
            ).mappings().all()
            case_ids = [row["id"] for row in case_rows]

            recruiter_rows = conn.execute(
                select(t.users.c.id, t.users.c.display_name, t.users.c.email, t.profiles.c.team_id)
                .join(t.profiles, and_(
                    t.profiles.c.user_id == t.users.c.id,
                    t.profiles.c.tenant_id == t.users.c.tenant_id,
                ))
                .where(
                    t.users.c.tenant_id == principal["tenant_id"],
                    t.profiles.c.team_id.in_(team_ids),
                    t.users.c.role == "recruiter",
                    t.users.c.is_active.is_(True),
                )
                .order_by(t.users.c.display_name, t.users.c.email)
            ).mappings().all()

            open_tasks = []
            if case_ids:
                open_tasks = conn.execute(
                    select(t.tasks.c.id, t.tasks.c.case_id, t.tasks.c.due_at)
                    .where(
                        t.tasks.c.tenant_id == principal["tenant_id"],
                        t.tasks.c.case_id.in_(case_ids),
                        t.tasks.c.status == "open",
                    )
                ).mappings().all()

            owner_counts = {}
            for row in case_rows:
                owner_counts[row["owner_user_id"]] = owner_counts.get(row["owner_user_id"], 0) + 1

            owner_by_case = {row["id"]: row["owner_user_id"] for row in case_rows}
            task_counts = {}
            overdue_counts = {}
            timestamp = now()
            for task in open_tasks:
                owner_id = owner_by_case.get(task["case_id"])
                if owner_id is None:
                    continue
                task_counts[owner_id] = task_counts.get(owner_id, 0) + 1
                due_at = task["due_at"]
                if due_at is not None:
                    if due_at.tzinfo is None:
                        due_at = due_at.replace(tzinfo=timezone.utc)
                    if due_at < timestamp:
                        overdue_counts[owner_id] = overdue_counts.get(owner_id, 0) + 1

            recruiters = [{
                "id": row["id"],
                "display_name": row["display_name"],
                "email": row["email"],
                "team_id": row["team_id"],
                "work_items": owner_counts.get(row["id"], 0),
                "open_followups": task_counts.get(row["id"], 0),
                "overdue_followups": overdue_counts.get(row["id"], 0),
            } for row in recruiter_rows]

            return {
                "teams": [dict(row) for row in team_rows],
                "totals": {
                    "work_items": len(case_rows),
                    "active_recruiters": len(recruiter_rows),
                    "open_followups": len(open_tasks),
                    "overdue_followups": sum(overdue_counts.values()),
                },
                "recruiters": recruiters,
            }

    def list_candidates(self, identity, *, after=None, limit=50):
        with self.engine.begin() as conn:
            principal = self._principal(conn, identity)
            statement = select(t.candidates.c.id, t.candidates.c.canonical_name).where(
                t.candidates.c.tenant_id == principal["tenant_id"]
            )
            if after:
                statement = statement.where(t.candidates.c.id > after)
            rows = conn.execute(statement.order_by(t.candidates.c.id).limit(limit + 1)).mappings().all()
            return self._page(rows, limit)

    def get_candidate(self, identity, candidate_id):
        with self.engine.begin() as conn:
            principal = self._principal(conn, identity)
            row = conn.execute(
                select(t.candidates.c.id, t.candidates.c.canonical_name).where(
                    t.candidates.c.id == candidate_id,
                    t.candidates.c.tenant_id == principal["tenant_id"],
                )
            ).mappings().first()
            if row is None:
                raise AccessError(404, "Candidate not found")
            return clean(row)

    def list_jobs(self, identity, *, after=None, limit=50):
        with self.engine.begin() as conn:
            principal = self._principal(conn, identity)
            statement = select(t.jobs.c.id, t.jobs.c.title).where(
                t.jobs.c.tenant_id == principal["tenant_id"]
            )
            if after:
                statement = statement.where(t.jobs.c.id > after)
            rows = conn.execute(statement.order_by(t.jobs.c.id).limit(limit + 1)).mappings().all()
            return self._page(rows, limit)

    def get_job(self, identity, job_id):
        with self.engine.begin() as conn:
            principal = self._principal(conn, identity)
            row = conn.execute(
                select(t.jobs.c.id, t.jobs.c.title).where(
                    t.jobs.c.id == job_id,
                    t.jobs.c.tenant_id == principal["tenant_id"],
                )
            ).mappings().first()
            if row is None:
                raise AccessError(404, "Job not found")
            return clean(row)

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


    def _global_mutate(self, identity, key, action, payload, callback):
        fingerprint = hashlib.sha256(json.dumps({"action": action, "payload": payload},
            sort_keys=True, separators=(",", ":"), default=json_value).encode()).hexdigest()
        try:
            with self.engine.begin() as conn:
                principal = self._principal(conn, identity)
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
                replay = self._receipt(conn, principal, key, fingerprint)
                if replay is not None:
                    return replay
            raise AccessError(409, "Conflicting change; reload before retrying") from None

    def _team_allowed(self, conn, principal, team_id):
        if principal["role"] == "admin":
            return conn.execute(select(t.teams.c.id).where(
                t.teams.c.id == team_id, t.teams.c.tenant_id == principal["tenant_id"]
            )).first() is not None
        if principal["role"] == "manager":
            return conn.execute(select(t.teams.c.id).where(
                t.teams.c.id == team_id, t.teams.c.tenant_id == principal["tenant_id"],
                t.teams.c.manager_user_id == principal["id"]
            )).first() is not None
        return False

    def create_job_intake_batch(self, identity, key, value):
        payload = {
            "customer_name": value.customer_name, "division": value.division,
            "source_filename": value.source_filename,
            "team_id": str(value.team_id) if value.team_id else None,
            "mapping": value.mapping,
        }
        def apply(conn, principal):
            if principal["role"] not in {"manager", "admin"}:
                raise AccessError(403, "Manager access required")
            team_id = str(value.team_id) if value.team_id else None
            if principal["role"] == "manager":
                managed = conn.execute(select(t.teams.c.id).where(
                    t.teams.c.tenant_id == principal["tenant_id"],
                    t.teams.c.manager_user_id == principal["id"],
                    t.teams.c.division == value.division,
                ).order_by(t.teams.c.id).limit(2)).scalars().all()
                if team_id is None:
                    if len(managed) != 1:
                        raise AccessError(422, "Select the team for this intake batch")
                    team_id = managed[0]
            if team_id is not None and not self._team_allowed(conn, principal, team_id):
                raise AccessError(422, "Select a team you are authorized to manage")
            timestamp = now()
            row = dict(
                id=uid(), tenant_id=principal["tenant_id"], team_id=team_id,
                uploaded_by=principal["id"], customer_name=value.customer_name,
                division=value.division, source_filename=value.source_filename,
                status="draft", mapping=value.mapping, row_count=0, ready_count=0,
                review_count=0, duplicate_count=0, created_at=timestamp, updated_at=timestamp,
            )
            conn.execute(insert(t.job_intake_batches).values(**row))
            return row
        return self._global_mutate(identity, key, "job_intake.batch.created", payload, apply)

    def list_job_intake_batches(self, identity, *, limit=50):
        with self.engine.begin() as conn:
            principal = self._principal(conn, identity)
            statement = select(t.job_intake_batches).where(
                t.job_intake_batches.c.tenant_id == principal["tenant_id"]
            )
            if principal["role"] == "manager":
                managed_teams = select(t.teams.c.id).where(
                    t.teams.c.tenant_id == principal["tenant_id"],
                    t.teams.c.manager_user_id == principal["id"],
                )
                statement = statement.where(t.job_intake_batches.c.team_id.in_(managed_teams))
            elif principal["role"] != "admin":
                raise AccessError(403, "Manager access required")
            rows = conn.execute(statement.order_by(
                t.job_intake_batches.c.created_at.desc(), t.job_intake_batches.c.id.desc()
            ).limit(limit)).mappings().all()
            return {"items": [clean(row) for row in rows]}

    def upsert_customer_job_mapping(self, identity, key, value):
        payload = {"customer_name": value.customer_name, "division": value.division, "mapping": value.mapping}
        def apply(conn, principal):
            if principal["role"] not in {"manager", "admin"}:
                raise AccessError(403, "Manager access required")
            if principal["role"] == "manager":
                allowed_division = conn.execute(select(t.teams.c.id).where(
                    t.teams.c.tenant_id == principal["tenant_id"],
                    t.teams.c.manager_user_id == principal["id"],
                    t.teams.c.division == value.division,
                )).first()
                if allowed_division is None:
                    raise AccessError(403, "Division is outside your scope")
            where = and_(
                t.customer_job_mappings.c.tenant_id == principal["tenant_id"],
                t.customer_job_mappings.c.customer_name == value.customer_name,
                t.customer_job_mappings.c.division == value.division,
            )
            old = conn.execute(select(t.customer_job_mappings).where(where)).mappings().first()
            timestamp = now()
            if old:
                conn.execute(update(t.customer_job_mappings).where(where).values(
                    mapping=value.mapping, updated_by=principal["id"], updated_at=timestamp
                ))
                return dict(old, mapping=value.mapping, updated_by=principal["id"], updated_at=timestamp)
            row = dict(
                id=uid(), tenant_id=principal["tenant_id"], customer_name=value.customer_name,
                division=value.division, mapping=value.mapping, updated_by=principal["id"],
                created_at=timestamp, updated_at=timestamp,
            )
            conn.execute(insert(t.customer_job_mappings).values(**row))
            return row
        return self._global_mutate(identity, key, "job_intake.mapping.upserted", payload, apply)

    def list_customer_job_mappings(self, identity, *, division=None):
        with self.engine.begin() as conn:
            principal = self._principal(conn, identity)
            if principal["role"] not in {"manager", "admin"}:
                raise AccessError(403, "Manager access required")
            statement = select(t.customer_job_mappings).where(
                t.customer_job_mappings.c.tenant_id == principal["tenant_id"]
            )
            if principal["role"] == "manager":
                managed_divisions = select(t.teams.c.division).where(
                    t.teams.c.tenant_id == principal["tenant_id"],
                    t.teams.c.manager_user_id == principal["id"],
                )
                statement = statement.where(t.customer_job_mappings.c.division.in_(managed_divisions))
            if division:
                statement = statement.where(t.customer_job_mappings.c.division == division)
            rows = conn.execute(statement.order_by(
                t.customer_job_mappings.c.customer_name, t.customer_job_mappings.c.division
            ).limit(500)).mappings().all()
            return {"items": [clean(row) for row in rows]}

    def set_weekly_goal(self, identity, recruiter_user_id, key, value):
        payload = {
            "recruiter_user_id": recruiter_user_id, "week_start": value.week_start.isoformat(),
            "submissions_target": value.submissions_target, "interviews_target": value.interviews_target,
            "closures_target": value.closures_target, "priority_jobs_target": value.priority_jobs_target,
            "notes": value.notes,
        }
        def apply(conn, principal):
            recruiter = conn.execute(
                select(t.users.c.id, t.profiles.c.team_id)
                .join(t.profiles, and_(
                    t.profiles.c.user_id == t.users.c.id,
                    t.profiles.c.tenant_id == t.users.c.tenant_id,
                ))
                .where(
                    t.users.c.id == recruiter_user_id,
                    t.users.c.tenant_id == principal["tenant_id"],
                    t.users.c.role == "recruiter",
                    t.users.c.is_active.is_(True),
                )
            ).mappings().first()
            if recruiter is None:
                raise AccessError(404, "Recruiter not found")
            if principal["role"] == "recruiter":
                if principal["id"] != recruiter_user_id:
                    raise AccessError(403, "Recruiters can set only their own goals")
            elif principal["role"] in {"manager", "admin"}:
                if principal["role"] == "manager" and not self._team_allowed(conn, principal, recruiter["team_id"]):
                    raise AccessError(403, "Recruiter is outside your team")
            else:
                raise AccessError(403, "Workspace access required")
            where = and_(
                t.weekly_goals.c.tenant_id == principal["tenant_id"],
                t.weekly_goals.c.recruiter_user_id == recruiter_user_id,
                t.weekly_goals.c.week_start == value.week_start,
            )
            timestamp = now()
            existing = conn.execute(select(t.weekly_goals).where(where)).mappings().first()
            values = dict(
                team_id=recruiter["team_id"],
                submissions_target=value.submissions_target,
                interviews_target=value.interviews_target,
                closures_target=value.closures_target,
                priority_jobs_target=value.priority_jobs_target,
                notes=value.notes, updated_at=timestamp,
            )
            if existing:
                conn.execute(update(t.weekly_goals).where(where).values(**values))
                return dict(existing, **values)
            row = dict(
                id=uid(), tenant_id=principal["tenant_id"], recruiter_user_id=recruiter_user_id,
                created_by=principal["id"], created_at=timestamp, week_start=value.week_start, **values
            )
            conn.execute(insert(t.weekly_goals).values(**row))
            return row
        return self._global_mutate(identity, key, "weekly_goal.set", payload, apply)

    def weekly_review(self, identity, week_start, *, team_id=None):
        with self.engine.begin() as conn:
            principal = self._principal(conn, identity)
            if principal["role"] not in {"manager", "admin"}:
                raise AccessError(403, "Manager access required")
            if team_id is not None and not self._team_allowed(conn, principal, team_id):
                raise AccessError(403, "Team is outside your scope")
            teams_stmt = select(t.teams.c.id, t.teams.c.name, t.teams.c.division).where(
                t.teams.c.tenant_id == principal["tenant_id"]
            )
            if principal["role"] == "manager":
                teams_stmt = teams_stmt.where(t.teams.c.manager_user_id == principal["id"])
            if team_id is not None:
                teams_stmt = teams_stmt.where(t.teams.c.id == team_id)
            team_rows = conn.execute(teams_stmt).mappings().all()
            team_ids = [r["id"] for r in team_rows]
            if not team_ids:
                return {"week_start": week_start.isoformat(), "teams": [], "recruiters": []}
            recruiters = conn.execute(
                select(t.users.c.id, t.users.c.display_name, t.users.c.email, t.profiles.c.team_id)
                .join(t.profiles, and_(
                    t.profiles.c.user_id == t.users.c.id,
                    t.profiles.c.tenant_id == t.users.c.tenant_id,
                ))
                .where(
                    t.users.c.tenant_id == principal["tenant_id"],
                    t.users.c.role == "recruiter", t.users.c.is_active.is_(True),
                    t.profiles.c.team_id.in_(team_ids),
                )
                .order_by(t.users.c.display_name, t.users.c.email)
            ).mappings().all()
            goals = conn.execute(select(t.weekly_goals).where(
                t.weekly_goals.c.tenant_id == principal["tenant_id"],
                t.weekly_goals.c.team_id.in_(team_ids),
                t.weekly_goals.c.week_start == week_start,
            )).mappings().all()
            snapshots = conn.execute(select(t.weekly_snapshots).where(
                t.weekly_snapshots.c.tenant_id == principal["tenant_id"],
                t.weekly_snapshots.c.team_id.in_(team_ids),
                t.weekly_snapshots.c.week_start == week_start,
            )).mappings().all()
            goal_by_user = {r["recruiter_user_id"]: r for r in goals}
            snap_by_user = {r["recruiter_user_id"]: r for r in snapshots}
            items = []
            for recruiter in recruiters:
                goal = goal_by_user.get(recruiter["id"])
                actual = snap_by_user.get(recruiter["id"])
                targets = {
                    "submissions": goal["submissions_target"] if goal else 0,
                    "interviews": goal["interviews_target"] if goal else 0,
                    "closures": goal["closures_target"] if goal else 0,
                    "priority_jobs": goal["priority_jobs_target"] if goal else 0,
                }
                actuals = {
                    "submissions": actual["submissions_actual"] if actual else 0,
                    "interviews": actual["interviews_actual"] if actual else 0,
                    "closures": actual["closures_actual"] if actual else 0,
                    "offers": actual["offers_actual"] if actual else 0,
                    "starts": actual["starts_actual"] if actual else 0,
                    "qualified": actual["qualified_actual"] if actual else 0,
                    "responses": actual["responses_actual"] if actual else 0,
                }
                items.append({
                    **dict(recruiter), "targets": targets, "actuals": actuals,
                    "notes": goal["notes"] if goal else None,
                    "actuals_generated_at": actual["generated_at"] if actual else None,
                })
            return {
                "week_start": week_start.isoformat(),
                "teams": [dict(r) for r in team_rows],
                "recruiters": clean(items),
            }


    def ingest_job_intake_rows(self, identity, batch_id, key, value):
        payload = {"batch_id": batch_id, "rows": value.rows, "mapping": value.mapping}
        def apply(conn, principal):
            if principal["role"] not in {"manager", "admin"}:
                raise AccessError(403, "Manager access required")
            batch = conn.execute(select(t.job_intake_batches).where(
                t.job_intake_batches.c.id == batch_id,
                t.job_intake_batches.c.tenant_id == principal["tenant_id"],
            ).with_for_update()).mappings().first()
            if batch is None:
                raise AccessError(404, "Job intake batch not found")
            if batch["team_id"] is not None and not self._team_allowed(conn, principal, batch["team_id"]):
                raise AccessError(403, "Job intake batch is outside your scope")
            if batch["status"] not in {"draft", "review"}:
                raise AccessError(409, "Only draft or review batches can be reprocessed")

            mapping = value.mapping if value.mapping is not None else batch["mapping"]
            if not mapping:
                raise AccessError(422, "Map the spreadsheet columns before processing rows")

            processed = process_rows(value.rows, mapping, batch["division"])
            conn.execute(t.job_intake_items.delete().where(
                t.job_intake_items.c.tenant_id == principal["tenant_id"],
                t.job_intake_items.c.batch_id == batch_id,
            ))
            timestamp = now()
            for item in processed:
                conn.execute(insert(t.job_intake_items).values(
                    id=uid(), tenant_id=principal["tenant_id"], batch_id=batch_id,
                    duplicate_job_id=None, created_job_id=None, created_at=timestamp,
                    updated_at=timestamp, **item,
                ))
            ready_count = sum(1 for item in processed if item["status"] == "ready")
            review_count = sum(1 for item in processed if item["status"] == "review")
            duplicate_count = sum(1 for item in processed if item["status"] == "duplicate")
            conn.execute(update(t.job_intake_batches).where(
                t.job_intake_batches.c.id == batch_id,
                t.job_intake_batches.c.tenant_id == principal["tenant_id"],
            ).values(
                mapping=mapping, status="review", row_count=len(processed),
                ready_count=ready_count, review_count=review_count,
                duplicate_count=duplicate_count, updated_at=timestamp,
            ))
            return {
                "batch_id": batch_id,
                "status": "review",
                "row_count": len(processed),
                "ready_count": ready_count,
                "review_count": review_count,
                "duplicate_count": duplicate_count,
            }
        return self._global_mutate(identity, key, "job_intake.rows.processed", payload, apply)

    def list_job_intake_items(self, identity, batch_id, *, limit=200):
        with self.engine.begin() as conn:
            principal = self._principal(conn, identity)
            if principal["role"] not in {"manager", "admin"}:
                raise AccessError(403, "Manager access required")
            batch = conn.execute(select(t.job_intake_batches).where(
                t.job_intake_batches.c.id == batch_id,
                t.job_intake_batches.c.tenant_id == principal["tenant_id"],
            )).mappings().first()
            if batch is None:
                raise AccessError(404, "Job intake batch not found")
            if batch["team_id"] is not None and not self._team_allowed(conn, principal, batch["team_id"]):
                raise AccessError(403, "Job intake batch is outside your scope")
            rows = conn.execute(select(t.job_intake_items).where(
                t.job_intake_items.c.tenant_id == principal["tenant_id"],
                t.job_intake_items.c.batch_id == batch_id,
            ).order_by(t.job_intake_items.c.row_number).limit(limit)).mappings().all()
            return {"batch": clean(batch), "items": [clean(row) for row in rows]}


    def upload_job_intake_xlsx(self, identity, key, *, customer_name, division, source_filename, team_id, content):
        payload = {
            "customer_name": customer_name,
            "division": division,
            "source_filename": source_filename,
            "team_id": team_id,
            "content_sha256": hashlib.sha256(content).hexdigest(),
        }
        def apply(conn, principal):
            if principal["role"] not in {"manager", "admin"}:
                raise AccessError(403, "Manager access required")
            resolved_team_id = team_id
            if principal["role"] == "manager":
                managed = conn.execute(select(t.teams.c.id).where(
                    t.teams.c.tenant_id == principal["tenant_id"],
                    t.teams.c.manager_user_id == principal["id"],
                    t.teams.c.division == division,
                ).order_by(t.teams.c.id).limit(2)).scalars().all()
                if resolved_team_id is None:
                    if len(managed) != 1:
                        raise AccessError(422, "Select the team for this intake batch")
                    resolved_team_id = managed[0]
            if resolved_team_id is not None and not self._team_allowed(conn, principal, resolved_team_id):
                raise AccessError(422, "Select a team you are authorized to manage")

            try:
                headers, rows = parse_xlsx(content)
            except ValueError as error:
                raise AccessError(422, str(error)) from None

            saved = conn.execute(select(t.customer_job_mappings.c.mapping).where(
                t.customer_job_mappings.c.tenant_id == principal["tenant_id"],
                t.customer_job_mappings.c.customer_name == customer_name,
                t.customer_job_mappings.c.division == division,
            )).scalar_one_or_none()
            mapping = saved or suggest_mapping(headers)
            processed = process_rows(rows, mapping, division)
            timestamp = now()
            batch_id = uid()
            ready_count = sum(1 for item in processed if item["status"] == "ready")
            review_count = sum(1 for item in processed if item["status"] == "review")
            duplicate_count = sum(1 for item in processed if item["status"] == "duplicate")
            batch = dict(
                id=batch_id, tenant_id=principal["tenant_id"], team_id=resolved_team_id,
                uploaded_by=principal["id"], customer_name=customer_name,
                division=division, source_filename=source_filename,
                status="review", mapping=mapping, row_count=len(processed),
                ready_count=ready_count, review_count=review_count,
                duplicate_count=duplicate_count, created_at=timestamp, updated_at=timestamp,
            )
            conn.execute(insert(t.job_intake_batches).values(**batch))
            for item in processed:
                conn.execute(insert(t.job_intake_items).values(
                    id=uid(), tenant_id=principal["tenant_id"], batch_id=batch_id,
                    duplicate_job_id=None, created_job_id=None,
                    created_at=timestamp, updated_at=timestamp, **item,
                ))
            return {
                **batch,
                "headers": headers,
                "mapping_source": "saved" if saved else "suggested",
                "recognized_columns": len(mapping),
            }
        return self._global_mutate(identity, key, "job_intake.xlsx.uploaded", payload, apply)

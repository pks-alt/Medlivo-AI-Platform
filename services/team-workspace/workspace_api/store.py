from __future__ import annotations
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal
import hashlib
import json
from uuid import UUID, uuid4
from sqlalchemy import select, insert, update, and_, true, text, func, or_
from sqlalchemy.exc import IntegrityError
from . import tables as t
from .auth import Identity
from .job_intake import process_rows, parse_xlsx, suggest_mapping
from .intake_intelligence import analyze_intake_job


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
    if isinstance(value, Decimal):
        return float(value)
    raise TypeError("Unsupported response value")


def clean(row):
    if isinstance(row, list):
        value = row
    elif isinstance(row, tuple):
        value = list(row)
    else:
        value = dict(row)
    return json.loads(json.dumps(value, default=json_value))


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


    def admin_operations_summary(self, identity):
        """Administrator-only operational view over canonical JobDiva-backed data."""
        with self.engine.begin() as conn:
            principal = self._principal(conn, identity)
            if principal["role"] != "admin":
                raise AccessError(403, "Administrator access required")
            tenant_id = principal["tenant_id"]

            def scalar(sql, **params):
                row = conn.execute(text(sql), {"tenant_id": tenant_id, **params}).first()
                return int(row[0] or 0) if row else 0

            checkpoints = conn.execute(text("""
                SELECT stream, watermark, last_success_at, last_error_code, updated_at
                FROM integration_sync_checkpoint
                WHERE tenant_id=:tenant_id AND source_system='jobdiva'
                ORDER BY stream
            """), {"tenant_id": tenant_id}).mappings().all()

            latest_runs = conn.execute(text("""
                SELECT DISTINCT ON (stream)
                    stream, status, window_start, window_end, pages_processed,
                    records_seen, records_upserted, error_code, started_at, finished_at
                FROM integration_sync_run
                WHERE tenant_id=:tenant_id AND source_system='jobdiva'
                ORDER BY stream, started_at DESC
            """), {"tenant_id": tenant_id}).mappings().all() if conn.dialect.name == "postgresql" else []

            source_counts = {
                "jobs": scalar("""
                    SELECT count(*) FROM job_source_record
                    WHERE tenant_id=:tenant_id AND source_system='jobdiva'
                """),
                "candidates": scalar("""
                    SELECT count(*) FROM candidate_source_record
                    WHERE tenant_id=:tenant_id AND source_system='jobdiva'
                """),
                "jobs_enriched": scalar("""
                    SELECT count(*) FROM job_source_record
                    WHERE tenant_id=:tenant_id AND source_system='jobdiva'
                      AND enriched_at IS NOT NULL
                """),
                "candidates_enriched": scalar("""
                    SELECT count(*) FROM candidate_source_record
                    WHERE tenant_id=:tenant_id AND source_system='jobdiva'
                      AND enriched_at IS NOT NULL
                """),
                "job_enrichment_errors": scalar("""
                    SELECT count(*) FROM job_source_record
                    WHERE tenant_id=:tenant_id AND source_system='jobdiva'
                      AND enrichment_error_code IS NOT NULL
                """),
                "candidate_enrichment_errors": scalar("""
                    SELECT count(*) FROM candidate_source_record
                    WHERE tenant_id=:tenant_id AND source_system='jobdiva'
                      AND enrichment_error_code IS NOT NULL
                """),
            }

            canonical = {
                "jobs": scalar("SELECT count(*) FROM job WHERE tenant_id=:tenant_id"),
                "open_jobs": scalar("""
                    SELECT count(*) FROM job
                    WHERE tenant_id=:tenant_id AND status IN ('open','active')
                """),
                "candidates": scalar("SELECT count(*) FROM candidate WHERE tenant_id=:tenant_id"),
                "matches": scalar("SELECT count(*) FROM match WHERE tenant_id=:tenant_id"),
                "strong_matches": scalar("""
                    SELECT count(*) FROM match
                    WHERE tenant_id=:tenant_id AND overall_score >= 9
                """),
                "good_matches": scalar("""
                    SELECT count(*) FROM match
                    WHERE tenant_id=:tenant_id AND overall_score >= 8 AND overall_score < 9
                """),
                "excluded_matches": scalar("""
                    SELECT count(*) FROM match
                    WHERE tenant_id=:tenant_id AND status='excluded'
                """),
            }

            division_rows = conn.execute(text("""
                SELECT COALESCE(NULLIF(division,''),'Unclassified') AS division,
                       count(*) AS jobs,
                       count(*) FILTER (WHERE status IN ('open','active')) AS open_jobs
                FROM job
                WHERE tenant_id=:tenant_id
                GROUP BY COALESCE(NULLIF(division,''),'Unclassified')
                ORDER BY division
            """), {"tenant_id": tenant_id}).mappings().all() if conn.dialect.name == "postgresql" else []

            recent_failures = conn.execute(text("""
                SELECT stream, status, error_code, started_at, finished_at
                FROM integration_sync_run
                WHERE tenant_id=:tenant_id AND source_system='jobdiva'
                  AND status='failed'
                ORDER BY started_at DESC
                LIMIT 10
            """), {"tenant_id": tenant_id}).mappings().all()

            return clean({
                "source_system": "jobdiva",
                "read_only": True,
                "generated_at": now(),
                "checkpoints": checkpoints,
                "latest_runs": latest_runs,
                "source_counts": source_counts,
                "canonical": canonical,
                "divisions": division_rows,
                "recent_failures": recent_failures,
            })

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
            source = t.candidate_source_records.alias("candidate_source")
            statement = (
                select(
                    t.candidates.c.id, t.candidates.c.canonical_name,
                    t.candidates.c.profession, t.candidates.c.specialty,
                    t.candidates.c.city, t.candidates.c.state,
                    t.candidates.c.lifecycle_status, t.candidates.c.profile_freshness,
                    source.c.source_id.label("jobdiva_candidate_id"),
                    source.c.enriched_at,
                )
                .outerjoin(source, and_(
                    source.c.candidate_id == t.candidates.c.id,
                    source.c.tenant_id == t.candidates.c.tenant_id,
                    source.c.source_system == "jobdiva",
                ))
                .where(t.candidates.c.tenant_id == principal["tenant_id"])
            )
            if after:
                statement = statement.where(t.candidates.c.id > after)
            rows = conn.execute(statement.order_by(t.candidates.c.id).limit(limit + 1)).mappings().all()
            return self._page(rows, limit)

    def get_candidate(self, identity, candidate_id):
        with self.engine.begin() as conn:
            principal = self._principal(conn, identity)
            candidate = conn.execute(
                select(t.candidates).where(
                    t.candidates.c.id == candidate_id,
                    t.candidates.c.tenant_id == principal["tenant_id"],
                )
            ).mappings().first()
            if candidate is None:
                raise AccessError(404, "Candidate not found")

            source = conn.execute(
                select(t.candidate_source_records.c.source_id,
                       t.candidate_source_records.c.source_updated_at,
                       t.candidate_source_records.c.enriched_at,
                       t.candidate_source_records.c.enrichment_version,
                       t.candidate_source_records.c.enrichment_error_code)
                .where(
                    t.candidate_source_records.c.tenant_id == principal["tenant_id"],
                    t.candidate_source_records.c.candidate_id == candidate_id,
                    t.candidate_source_records.c.source_system == "jobdiva",
                )
                .order_by(t.candidate_source_records.c.source_updated_at.desc())
                .limit(1)
            ).mappings().first()

            licenses = conn.execute(
                select(t.candidate_licenses).where(
                    t.candidate_licenses.c.tenant_id == principal["tenant_id"],
                    t.candidate_licenses.c.candidate_id == candidate_id,
                ).order_by(t.candidate_licenses.c.state, t.candidate_licenses.c.license_type)
            ).mappings().all()
            certifications = conn.execute(
                select(t.candidate_certifications).where(
                    t.candidate_certifications.c.tenant_id == principal["tenant_id"],
                    t.candidate_certifications.c.candidate_id == candidate_id,
                ).order_by(t.candidate_certifications.c.certification_name)
            ).mappings().all()
            evidence = conn.execute(
                select(t.candidate_evidence).where(
                    t.candidate_evidence.c.tenant_id == principal["tenant_id"],
                    t.candidate_evidence.c.candidate_id == candidate_id,
                ).order_by(t.candidate_evidence.c.created_at.desc()).limit(100)
            ).mappings().all()
            resumes = conn.execute(
                select(
                    t.resume_versions.c.id, t.resume_versions.c.source_resume_id,
                    t.resume_versions.c.is_primary, t.resume_versions.c.resume_date,
                    t.resume_versions.c.parsed_payload, t.resume_versions.c.updated_at,
                ).where(
                    t.resume_versions.c.tenant_id == principal["tenant_id"],
                    t.resume_versions.c.candidate_id == candidate_id,
                ).order_by(t.resume_versions.c.is_primary.desc(), t.resume_versions.c.resume_date.desc())
            ).mappings().all()
            availability = conn.execute(
                select(t.candidate_availability).where(
                    t.candidate_availability.c.tenant_id == principal["tenant_id"],
                    t.candidate_availability.c.candidate_id == candidate_id,
                ).order_by(t.candidate_availability.c.created_at.desc()).limit(10)
            ).mappings().all()
            preference = conn.execute(
                select(t.candidate_preferences).where(
                    t.candidate_preferences.c.tenant_id == principal["tenant_id"],
                    t.candidate_preferences.c.candidate_id == candidate_id,
                )
            ).mappings().first()
            qualification = conn.execute(
                select(t.qualifications).where(
                    t.qualifications.c.tenant_id == principal["tenant_id"],
                    t.qualifications.c.candidate_id == candidate_id,
                ).order_by(t.qualifications.c.created_at.desc()).limit(1)
            ).mappings().first()
            answers = []
            if qualification is not None:
                answers = conn.execute(
                    select(t.qualification_answers).where(
                        t.qualification_answers.c.tenant_id == principal["tenant_id"],
                        t.qualification_answers.c.qualification_id == qualification["id"],
                    ).order_by(t.qualification_answers.c.created_at)
                ).mappings().all()

            best_jobs = conn.execute(
                select(
                    t.matches.c.id.label("match_id"), t.matches.c.overall_score,
                    t.matches.c.status.label("match_status"), t.matches.c.explanation,
                    t.jobs.c.id.label("job_id"), t.jobs.c.title, t.jobs.c.division,
                    t.jobs.c.city, t.jobs.c.state, t.jobs.c.start_date,
                    t.job_source_records.c.source_id.label("jobdiva_job_id"),
                )
                .join(t.jobs, and_(
                    t.jobs.c.id == t.matches.c.job_id,
                    t.jobs.c.tenant_id == t.matches.c.tenant_id,
                ))
                .outerjoin(t.job_source_records, and_(
                    t.job_source_records.c.job_id == t.jobs.c.id,
                    t.job_source_records.c.tenant_id == t.jobs.c.tenant_id,
                    t.job_source_records.c.source_system == "jobdiva",
                ))
                .where(
                    t.matches.c.tenant_id == principal["tenant_id"],
                    t.matches.c.candidate_id == candidate_id,
                )
                .order_by(t.matches.c.overall_score.desc(), t.matches.c.updated_at.desc())
                .limit(20)
            ).mappings().all()

            payload = dict(candidate)
            payload.update({
                "source": dict(source) if source else None,
                "licenses": [dict(x) for x in licenses],
                "certifications": [dict(x) for x in certifications],
                "evidence": [dict(x) for x in evidence],
                "resumes": [dict(x) for x in resumes],
                "availability": [dict(x) for x in availability],
                "preference": dict(preference) if preference else None,
                "validation": {
                    "status": qualification["status"] if qualification else "not_screened",
                    "summary": qualification["summary"] if qualification else None,
                    "job_id": qualification["job_id"] if qualification else None,
                    "completed_at": qualification["completed_at"] if qualification else None,
                    "answers": [dict(x) for x in answers],
                },
                "best_jobs": [dict(x) for x in best_jobs],
            })
            return clean(payload)

    def list_jobs(self, identity, *, after=None, limit=50):
        with self.engine.begin() as conn:
            principal = self._principal(conn, identity)
            source = t.job_source_records.alias("job_source")
            customer = t.customers.alias("job_customer")
            statement = (
                select(
                    t.jobs.c.id, t.jobs.c.title, t.jobs.c.profession, t.jobs.c.specialty,
                    t.jobs.c.division, t.jobs.c.city, t.jobs.c.state, t.jobs.c.start_date,
                    t.jobs.c.status, t.jobs.c.priority, t.jobs.c.owner_user_id,
                    source.c.source_id.label("jobdiva_job_id"), source.c.enriched_at,
                    customer.c.name.label("customer_name"),
                )
                .outerjoin(source, and_(
                    source.c.job_id == t.jobs.c.id,
                    source.c.tenant_id == t.jobs.c.tenant_id,
                    source.c.source_system == "jobdiva",
                ))
                .outerjoin(customer, and_(
                    customer.c.id == t.jobs.c.customer_id,
                    customer.c.tenant_id == t.jobs.c.tenant_id,
                ))
                .where(t.jobs.c.tenant_id == principal["tenant_id"])
            )
            if after:
                statement = statement.where(t.jobs.c.id > after)
            rows = conn.execute(statement.order_by(t.jobs.c.id).limit(limit + 1)).mappings().all()
            return self._page(rows, limit)

    def get_job(self, identity, job_id):
        with self.engine.begin() as conn:
            principal = self._principal(conn, identity)
            customer = t.customers.alias("job_customer")
            job = conn.execute(
                select(t.jobs, customer.c.name.label("customer_name"))
                .outerjoin(customer, and_(
                    customer.c.id == t.jobs.c.customer_id,
                    customer.c.tenant_id == t.jobs.c.tenant_id,
                ))
                .where(
                    t.jobs.c.id == job_id,
                    t.jobs.c.tenant_id == principal["tenant_id"],
                )
            ).mappings().first()
            if job is None:
                raise AccessError(404, "Job not found")

            source = conn.execute(
                select(t.job_source_records.c.source_id, t.job_source_records.c.source_status,
                       t.job_source_records.c.source_updated_at, t.job_source_records.c.enriched_at,
                       t.job_source_records.c.enrichment_version, t.job_source_records.c.enrichment_error_code)
                .where(
                    t.job_source_records.c.tenant_id == principal["tenant_id"],
                    t.job_source_records.c.job_id == job_id,
                    t.job_source_records.c.source_system == "jobdiva",
                )
                .order_by(t.job_source_records.c.source_updated_at.desc()).limit(1)
            ).mappings().first()
            requirements = conn.execute(
                select(t.job_requirements).where(
                    t.job_requirements.c.tenant_id == principal["tenant_id"],
                    t.job_requirements.c.job_id == job_id,
                ).order_by(t.job_requirements.c.is_hard_gate.desc(), t.job_requirements.c.canonical_key)
            ).mappings().all()
            matches = conn.execute(
                select(
                    t.matches.c.id.label("match_id"), t.matches.c.overall_score,
                    t.matches.c.status.label("match_status"), t.matches.c.explanation,
                    t.candidates.c.id.label("candidate_id"), t.candidates.c.canonical_name,
                    t.candidates.c.profession, t.candidates.c.specialty,
                    t.candidates.c.city, t.candidates.c.state,
                    t.candidate_source_records.c.source_id.label("jobdiva_candidate_id"),
                )
                .join(t.candidates, and_(
                    t.candidates.c.id == t.matches.c.candidate_id,
                    t.candidates.c.tenant_id == t.matches.c.tenant_id,
                ))
                .outerjoin(t.candidate_source_records, and_(
                    t.candidate_source_records.c.candidate_id == t.candidates.c.id,
                    t.candidate_source_records.c.tenant_id == t.candidates.c.tenant_id,
                    t.candidate_source_records.c.source_system == "jobdiva",
                ))
                .where(t.matches.c.tenant_id == principal["tenant_id"], t.matches.c.job_id == job_id)
                .order_by(t.matches.c.overall_score.desc(), t.matches.c.updated_at.desc()).limit(50)
            ).mappings().all()
            exclusions = conn.execute(
                select(
                    t.match_exclusions.c.candidate_id, t.match_exclusions.c.reason_code,
                    t.match_exclusions.c.reason_detail, t.match_exclusions.c.overridden,
                    t.candidates.c.canonical_name,
                )
                .join(t.candidates, and_(
                    t.candidates.c.id == t.match_exclusions.c.candidate_id,
                    t.candidates.c.tenant_id == t.match_exclusions.c.tenant_id,
                ))
                .where(
                    t.match_exclusions.c.tenant_id == principal["tenant_id"],
                    t.match_exclusions.c.job_id == job_id,
                ).order_by(t.match_exclusions.c.created_at.desc()).limit(50)
            ).mappings().all()

            payload = dict(job)
            payload.update({
                "source": dict(source) if source else None,
                "requirements": [dict(x) for x in requirements],
                "hard_gates": [dict(x) for x in requirements if x["is_hard_gate"]],
                "preferences": [dict(x) for x in requirements if not x["is_hard_gate"]],
                "best_candidates": [dict(x) for x in matches],
                "exclusions": [dict(x) for x in exclusions],
            })
            return clean(payload)

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


    def _persist_intake_items(self, conn, principal, *, batch_id, division,
                              customer_name, processed, timestamp):
        statuses = []
        for item in processed:
            item_id = uid()
            source_id = str(
                item["normalized_job"].get("requisition_id")
                or f"{batch_id}:{item['row_number']}"
            )
            intelligence = analyze_intake_job(
                item["normalized_job"],
                division=division,
                source_id=source_id,
                customer_name=customer_name,
            )
            conflicts = intelligence["conflicts"]
            missing_fields = intelligence["missing_fields"]

            status = item["status"]
            if status != "duplicate" and (conflicts or missing_fields):
                status = "review"
            statuses.append(status)

            conn.execute(insert(t.job_intake_items).values(
                id=item_id,
                tenant_id=principal["tenant_id"],
                batch_id=batch_id,
                duplicate_job_id=None,
                created_job_id=None,
                created_at=timestamp,
                updated_at=timestamp,
                row_number=item["row_number"],
                source_row=item["source_row"],
                normalized_job=item["normalized_job"],
                validation_errors=item["validation_errors"],
                status=status,
                extracted_values=intelligence["extracted_values"],
                ai_suggestions=intelligence["ai_suggestions"],
                conflicts=conflicts,
                missing_fields=missing_fields,
                final_approved_values=None,
                standardized_internal_jd=intelligence["standardized_internal_jd"],
                bill_rate_state=intelligence["bill_rate_state"],
                recruiting_readiness=intelligence["recruiting_readiness"],
                commercial_readiness=intelligence["commercial_readiness"],
                reviewed_by=None,
                reviewed_at=None,
            ))
            for provenance in intelligence["provenance"]:
                conn.execute(insert(t.provenance_records).values(
                    id=uid(),
                    tenant_id=principal["tenant_id"],
                    object_type="job_intake_item",
                    object_id=item_id,
                    field_path=provenance["field"],
                    source_type=provenance["source_type"],
                    source_reference=provenance["source_reference"],
                    confidence=provenance["confidence"],
                    value_payload={
                        "value": item["normalized_job"].get(provenance["field"])
                    },
                    created_at=timestamp,
                ))

        return {
            "ready_count": sum(1 for status in statuses if status == "ready"),
            "review_count": sum(1 for status in statuses if status == "review"),
            "duplicate_count": sum(1 for status in statuses if status == "duplicate"),
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
            counts = self._persist_intake_items(
                conn,
                principal,
                batch_id=batch_id,
                division=batch["division"],
                customer_name=batch["customer_name"],
                processed=processed,
                timestamp=timestamp,
            )
            ready_count = counts["ready_count"]
            review_count = counts["review_count"]
            duplicate_count = counts["duplicate_count"]
            conn.execute(update(t.job_intake_batches).where(
                t.job_intake_batches.c.id == batch_id,
                t.job_intake_batches.c.tenant_id == principal["tenant_id"],
            ).values(
                mapping=mapping, status="review", ai_processing_status="rules_analyzed", row_count=len(processed),
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


    def recruiter_weekly_progress(self, identity, recruiter_user_id, week_start):
        with self.engine.begin() as conn:
            principal = self._principal(conn, identity)
            recruiter = conn.execute(
                select(t.users.c.id, t.users.c.display_name, t.users.c.email, t.profiles.c.team_id)
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
                    raise AccessError(403, "Recruiter progress is private to the recruiter and authorized managers")
            elif principal["role"] == "manager":
                if not self._team_allowed(conn, principal, recruiter["team_id"]):
                    raise AccessError(403, "Recruiter is outside your team")
            elif principal["role"] != "admin":
                raise AccessError(403, "Workspace access required")

            goal = conn.execute(select(t.weekly_goals).where(
                t.weekly_goals.c.tenant_id == principal["tenant_id"],
                t.weekly_goals.c.recruiter_user_id == recruiter_user_id,
                t.weekly_goals.c.week_start == week_start,
            )).mappings().first()
            actual = conn.execute(select(t.weekly_snapshots).where(
                t.weekly_snapshots.c.tenant_id == principal["tenant_id"],
                t.weekly_snapshots.c.recruiter_user_id == recruiter_user_id,
                t.weekly_snapshots.c.week_start == week_start,
            )).mappings().first()
            return clean({
                "recruiter": dict(recruiter),
                "week_start": week_start,
                "targets": {
                    "submissions": goal["submissions_target"] if goal else 0,
                    "interviews": goal["interviews_target"] if goal else 0,
                    "closures": goal["closures_target"] if goal else 0,
                    "priority_jobs": goal["priority_jobs_target"] if goal else 0,
                },
                "actuals": {
                    "submissions": actual["submissions_actual"] if actual else 0,
                    "interviews": actual["interviews_actual"] if actual else 0,
                    "closures": actual["closures_actual"] if actual else 0,
                    "offers": actual["offers_actual"] if actual else 0,
                    "starts": actual["starts_actual"] if actual else 0,
                    "qualified": actual["qualified_actual"] if actual else 0,
                    "responses": actual["responses_actual"] if actual else 0,
                },
                "notes": goal["notes"] if goal else None,
                "actuals_generated_at": actual["generated_at"] if actual else None,
            })


    def create_job_publication(self, identity, key, value):
        payload = {
            "team_id": str(value.team_id) if value.team_id else None,
            "job_id": str(value.job_id) if value.job_id else None,
            "intake_item_id": str(value.intake_item_id) if value.intake_item_id else None,
            "source_snapshot": value.source_snapshot,
            "enhanced_snapshot": value.enhanced_snapshot,
            "quality_score": value.quality_score,
            "readiness": value.readiness,
        }
        def apply(conn, principal):
            if principal["role"] not in {"manager", "admin"}:
                raise AccessError(403, "Manager access required")
            team_id = str(value.team_id) if value.team_id else None

            if value.intake_item_id:
                intake = conn.execute(
                    select(t.job_intake_items.c.id, t.job_intake_batches.c.team_id)
                    .join(t.job_intake_batches, and_(
                        t.job_intake_batches.c.id == t.job_intake_items.c.batch_id,
                        t.job_intake_batches.c.tenant_id == t.job_intake_items.c.tenant_id,
                    ))
                    .where(
                        t.job_intake_items.c.id == str(value.intake_item_id),
                        t.job_intake_items.c.tenant_id == principal["tenant_id"],
                    )
                ).mappings().first()
                if intake is None:
                    raise AccessError(404, "Job intake row not found")
                if team_id is None:
                    team_id = intake["team_id"]
            elif value.job_id:
                exists = conn.execute(select(t.jobs.c.id).where(
                    t.jobs.c.id == str(value.job_id),
                    t.jobs.c.tenant_id == principal["tenant_id"],
                )).first()
                if exists is None:
                    raise AccessError(404, "Job not found")

            if principal["role"] == "manager":
                if team_id is None or not self._team_allowed(conn, principal, team_id):
                    raise AccessError(403, "Job is outside your team")
            elif team_id is not None and not self._team_allowed(conn, principal, team_id):
                raise AccessError(422, "Select a valid team")

            timestamp = now()
            row = dict(
                id=uid(), tenant_id=principal["tenant_id"], team_id=team_id,
                job_id=str(value.job_id) if value.job_id else None,
                intake_item_id=str(value.intake_item_id) if value.intake_item_id else None,
                source_snapshot=value.source_snapshot,
                enhanced_snapshot=value.enhanced_snapshot,
                quality_score=value.quality_score,
                readiness=value.readiness,
                recruiting_status="pending", website_status="pending",
                recruiting_approved_by=None, recruiting_approved_at=None,
                website_approved_by=None, website_approved_at=None,
                version=1, created_by=principal["id"], created_at=timestamp, updated_at=timestamp,
            )
            conn.execute(insert(t.job_publications).values(**row))
            conn.execute(insert(t.job_publication_audit).values(
                id=uid(), tenant_id=principal["tenant_id"], publication_id=row["id"],
                actor_user_id=principal["id"], action="draft.created",
                details={"readiness": value.readiness}, created_at=timestamp,
            ))
            return row
        return self._global_mutate(identity, key, "job_publication.created", payload, apply)

    def list_job_publications(self, identity, *, limit=100):
        with self.engine.begin() as conn:
            principal = self._principal(conn, identity)
            if principal["role"] not in {"manager", "admin"}:
                raise AccessError(403, "Manager access required")
            statement = select(t.job_publications).where(
                t.job_publications.c.tenant_id == principal["tenant_id"]
            )
            if principal["role"] == "manager":
                managed_teams = select(t.teams.c.id).where(
                    t.teams.c.tenant_id == principal["tenant_id"],
                    t.teams.c.manager_user_id == principal["id"],
                )
                statement = statement.where(t.job_publications.c.team_id.in_(managed_teams))
            rows = conn.execute(statement.order_by(
                t.job_publications.c.updated_at.desc(), t.job_publications.c.id.desc()
            ).limit(limit)).mappings().all()
            return {"items": [clean(row) for row in rows]}

    def get_job_publication(self, identity, publication_id):
        with self.engine.begin() as conn:
            principal = self._principal(conn, identity)
            if principal["role"] not in {"manager", "admin"}:
                raise AccessError(403, "Manager access required")
            row = conn.execute(select(t.job_publications).where(
                t.job_publications.c.id == publication_id,
                t.job_publications.c.tenant_id == principal["tenant_id"],
            )).mappings().first()
            if row is None:
                raise AccessError(404, "Job publication draft not found")
            if principal["role"] == "manager" and (
                row["team_id"] is None or not self._team_allowed(conn, principal, row["team_id"])
            ):
                raise AccessError(404, "Job publication draft not found")
            history = conn.execute(select(t.job_publication_audit).where(
                t.job_publication_audit.c.tenant_id == principal["tenant_id"],
                t.job_publication_audit.c.publication_id == publication_id,
            ).order_by(t.job_publication_audit.c.created_at, t.job_publication_audit.c.id)).mappings().all()
            return {"publication": clean(row), "history": [clean(item) for item in history]}

    def decide_job_publication(self, identity, publication_id, key, value):
        payload = {
            "publication_id": publication_id, "target": value.target,
            "decision": value.decision, "reason": value.reason,
            "expected_version": value.expected_version,
        }
        def apply(conn, principal):
            if principal["role"] not in {"manager", "admin"}:
                raise AccessError(403, "Manager access required")
            row = conn.execute(select(t.job_publications).where(
                t.job_publications.c.id == publication_id,
                t.job_publications.c.tenant_id == principal["tenant_id"],
            ).with_for_update()).mappings().first()
            if row is None:
                raise AccessError(404, "Job publication draft not found")
            if principal["role"] == "manager" and (
                row["team_id"] is None or not self._team_allowed(conn, principal, row["team_id"])
            ):
                raise AccessError(404, "Job publication draft not found")
            if row["version"] != value.expected_version:
                raise AccessError(409, "This job draft changed; reload it before approving")

            if value.target == "website" and value.decision == "approved":
                if row["recruiting_status"] != "approved":
                    raise AccessError(422, "Approve the job for recruiting before website publication")
                if row["readiness"] != "ready_to_publish":
                    raise AccessError(422, "Resolve all website readiness items before approval")

            timestamp = now()
            version = value.expected_version + 1
            updates = {"version": version, "updated_at": timestamp}
            if value.target == "recruiting":
                updates["recruiting_status"] = value.decision
                updates["recruiting_approved_by"] = principal["id"] if value.decision == "approved" else None
                updates["recruiting_approved_at"] = timestamp if value.decision == "approved" else None
            else:
                updates["website_status"] = value.decision
                updates["website_approved_by"] = principal["id"] if value.decision == "approved" else None
                updates["website_approved_at"] = timestamp if value.decision == "approved" else None

            result = conn.execute(update(t.job_publications).where(
                t.job_publications.c.id == publication_id,
                t.job_publications.c.tenant_id == principal["tenant_id"],
                t.job_publications.c.version == value.expected_version,
            ).values(**updates))
            if result.rowcount != 1:
                raise AccessError(409, "This job draft changed; reload it before approving")

            action = f"{value.target}.{value.decision}"
            conn.execute(insert(t.job_publication_audit).values(
                id=uid(), tenant_id=principal["tenant_id"], publication_id=publication_id,
                actor_user_id=principal["id"], action=action,
                details={"reason": value.reason, "version": version}, created_at=timestamp,
            ))
            return clean(dict(row, **updates))
        return self._global_mutate(identity, key, "job_publication.decision", payload, apply)


    def recruiter_followups(self, identity, *, status="open", limit=100):
        """Recruiter-wide follow-up queue across assigned work items."""
        with self.engine.begin() as conn:
            principal = self._principal(conn, identity)
            if principal["role"] != "recruiter":
                raise AccessError(403, "Recruiter access required")
            if status not in {"open", "done", "all"}:
                raise AccessError(422, "Unsupported follow-up status")

            statement = (
                select(
                    t.tasks.c.id,
                    t.tasks.c.case_id,
                    t.tasks.c.title,
                    t.tasks.c.status,
                    t.tasks.c.due_at,
                    t.tasks.c.version,
                    t.tasks.c.created_at,
                    t.tasks.c.updated_at,
                    t.cases.c.title.label("case_title"),
                    t.cases.c.job_id,
                    t.cases.c.candidate_id,
                )
                .join(t.cases, and_(
                    t.cases.c.id == t.tasks.c.case_id,
                    t.cases.c.tenant_id == t.tasks.c.tenant_id,
                ))
                .where(
                    t.tasks.c.tenant_id == principal["tenant_id"],
                    t.cases.c.owner_user_id == principal["id"],
                )
            )
            if status != "all":
                statement = statement.where(t.tasks.c.status == status)

            rows = conn.execute(
                statement.order_by(
                    t.tasks.c.status.asc(),
                    t.tasks.c.due_at.asc(),
                    t.tasks.c.updated_at.desc(),
                    t.tasks.c.id,
                ).limit(limit)
            ).mappings().all()

            timestamp = now()
            items = []
            for row in rows:
                due_at = row["due_at"]
                if due_at is not None and due_at.tzinfo is None:
                    due_at = due_at.replace(tzinfo=timezone.utc)
                items.append({
                    **dict(row),
                    "is_overdue": bool(row["status"] == "open" and due_at and due_at < timestamp),
                })
            return clean({"items": items, "status": status, "read_only": False})

    def recruiter_dashboard(self, identity, week_start):
        """Recruiter-only read-only productivity scorecard."""
        with self.engine.begin() as conn:
            principal = self._principal(conn, identity)
            if principal["role"] != "recruiter":
                raise AccessError(403, "Recruiter access required")

            goal = conn.execute(select(t.weekly_goals).where(
                t.weekly_goals.c.tenant_id == principal["tenant_id"],
                t.weekly_goals.c.recruiter_user_id == principal["id"],
                t.weekly_goals.c.week_start == week_start,
            )).mappings().first()
            actual = conn.execute(select(t.weekly_snapshots).where(
                t.weekly_snapshots.c.tenant_id == principal["tenant_id"],
                t.weekly_snapshots.c.recruiter_user_id == principal["id"],
                t.weekly_snapshots.c.week_start == week_start,
            )).mappings().first()

            owned_cases = conn.execute(
                select(func.count()).select_from(t.cases).where(
                    t.cases.c.tenant_id == principal["tenant_id"],
                    t.cases.c.owner_user_id == principal["id"],
                )
            ).scalar_one()

            open_followups = conn.execute(
                select(func.count()).select_from(t.tasks)
                .join(t.cases, and_(
                    t.cases.c.id == t.tasks.c.case_id,
                    t.cases.c.tenant_id == t.tasks.c.tenant_id,
                ))
                .where(
                    t.tasks.c.tenant_id == principal["tenant_id"],
                    t.cases.c.owner_user_id == principal["id"],
                    t.tasks.c.status == "open",
                )
            ).scalar_one()

            overdue_followups = conn.execute(
                select(func.count()).select_from(t.tasks)
                .join(t.cases, and_(
                    t.cases.c.id == t.tasks.c.case_id,
                    t.cases.c.tenant_id == t.tasks.c.tenant_id,
                ))
                .where(
                    t.tasks.c.tenant_id == principal["tenant_id"],
                    t.cases.c.owner_user_id == principal["id"],
                    t.tasks.c.status == "open",
                    t.tasks.c.due_at < now(),
                )
            ).scalar_one()

            active_priority_jobs = conn.execute(
                select(func.count()).select_from(t.jobs).where(
                    t.jobs.c.tenant_id == principal["tenant_id"],
                    t.jobs.c.owner_user_id == principal["id"],
                    t.jobs.c.status.not_in(["closed", "cancelled", "canceled"]),
                    t.jobs.c.priority >= 8,
                )
            ).scalar_one()

            reviewed = select(t.match_feedback.c.match_id).where(
                t.match_feedback.c.tenant_id == principal["tenant_id"],
                t.match_feedback.c.recruiter_user_id == principal["id"],
            )
            unreviewed_matches = conn.execute(
                select(func.count()).select_from(t.matches)
                .join(t.jobs, and_(
                    t.jobs.c.id == t.matches.c.job_id,
                    t.jobs.c.tenant_id == t.matches.c.tenant_id,
                ))
                .where(
                    t.matches.c.tenant_id == principal["tenant_id"],
                    t.jobs.c.owner_user_id == principal["id"],
                    t.jobs.c.status.not_in(["closed", "cancelled", "canceled"]),
                    t.matches.c.status != "excluded",
                    t.matches.c.overall_score >= 8,
                    t.matches.c.id.not_in(reviewed),
                )
            ).scalar_one()

            return clean({
                "week_start": week_start,
                "targets": {
                    "submissions": goal["submissions_target"] if goal else 0,
                    "interviews": goal["interviews_target"] if goal else 0,
                    "closures": goal["closures_target"] if goal else 0,
                    "priority_jobs": goal["priority_jobs_target"] if goal else 0,
                },
                "actuals": {
                    "submissions": actual["submissions_actual"] if actual else 0,
                    "interviews": actual["interviews_actual"] if actual else 0,
                    "closures": actual["closures_actual"] if actual else 0,
                    "offers": actual["offers_actual"] if actual else 0,
                    "starts": actual["starts_actual"] if actual else 0,
                    "qualified": actual["qualified_actual"] if actual else 0,
                    "responses": actual["responses_actual"] if actual else 0,
                },
                "workload": {
                    "owned_work_items": owned_cases,
                    "open_followups": open_followups,
                    "overdue_followups": overdue_followups,
                    "active_priority_jobs": active_priority_jobs,
                    "unreviewed_matches": unreviewed_matches,
                },
                "actuals_generated_at": actual["generated_at"] if actual else None,
                "read_only": True,
                "source_of_record": "jobdiva",
            })


    def daily_priorities(self, identity, *, limit=20):
        """Recruiter-only, read-only start-of-day priorities.

        Uses existing shared follow-ups plus strong unreviewed persisted matches.
        No outreach, submission, ownership or JobDiva mutation occurs here.
        """
        with self.engine.begin() as conn:
            principal = self._principal(conn, identity)
            if principal["role"] != "recruiter":
                raise AccessError(403, "Recruiter access required")

            timestamp = now()
            due_soon = timestamp + timedelta(hours=24)

            task_rows = conn.execute(
                select(
                    t.tasks.c.id,
                    t.tasks.c.case_id,
                    t.tasks.c.title,
                    t.tasks.c.due_at,
                    t.tasks.c.version,
                    t.cases.c.title.label("case_title"),
                    t.cases.c.job_id,
                    t.cases.c.candidate_id,
                )
                .join(t.cases, and_(
                    t.cases.c.id == t.tasks.c.case_id,
                    t.cases.c.tenant_id == t.tasks.c.tenant_id,
                ))
                .where(
                    t.tasks.c.tenant_id == principal["tenant_id"],
                    t.cases.c.owner_user_id == principal["id"],
                    t.tasks.c.status == "open",
                    t.tasks.c.due_at <= due_soon,
                )
                .order_by(t.tasks.c.due_at.asc(), t.tasks.c.id)
                .limit(limit)
            ).mappings().all()

            items = []
            overdue_count = 0
            due_soon_count = 0
            for row in task_rows:
                due_at = row["due_at"]
                if due_at.tzinfo is None:
                    due_at = due_at.replace(tzinfo=timezone.utc)
                overdue = due_at < timestamp
                overdue_count += 1 if overdue else 0
                due_soon_count += 0 if overdue else 1
                items.append({
                    "type": "follow_up",
                    "urgency": "overdue" if overdue else "due_soon",
                    "title": row["title"],
                    "detail": row["case_title"],
                    "due_at": due_at,
                    "case_id": row["case_id"],
                    "job_id": row["job_id"],
                    "candidate_id": row["candidate_id"],
                    "task_id": row["id"],
                    "version": row["version"],
                    "recommended_next_action": "Complete overdue follow-up" if overdue else "Complete upcoming follow-up",
                })

            remaining = max(0, limit - len(items))
            strong_match_count = 0
            if remaining:
                reviewed = (
                    select(t.match_feedback.c.match_id)
                    .where(
                        t.match_feedback.c.tenant_id == principal["tenant_id"],
                        t.match_feedback.c.recruiter_user_id == principal["id"],
                    )
                )
                match_rows = conn.execute(
                    select(
                        t.matches.c.id.label("match_id"),
                        t.matches.c.job_id,
                        t.matches.c.candidate_id,
                        t.matches.c.overall_score,
                        t.jobs.c.title.label("job_title"),
                        t.jobs.c.priority,
                        t.jobs.c.start_date,
                        t.candidates.c.canonical_name.label("candidate_name"),
                        t.candidates.c.profession,
                        t.candidates.c.specialty,
                    )
                    .join(t.jobs, and_(
                        t.jobs.c.id == t.matches.c.job_id,
                        t.jobs.c.tenant_id == t.matches.c.tenant_id,
                    ))
                    .join(t.candidates, and_(
                        t.candidates.c.id == t.matches.c.candidate_id,
                        t.candidates.c.tenant_id == t.matches.c.tenant_id,
                    ))
                    .where(
                        t.matches.c.tenant_id == principal["tenant_id"],
                        t.jobs.c.owner_user_id == principal["id"],
                        t.jobs.c.status.not_in(["closed", "cancelled", "canceled"]),
                        t.matches.c.status != "excluded",
                        t.matches.c.overall_score >= 8,
                        t.matches.c.id.not_in(reviewed),
                    )
                    .order_by(
                        t.jobs.c.priority.desc(),
                        t.matches.c.overall_score.desc(),
                        t.jobs.c.start_date.asc().nulls_last(),
                        t.matches.c.updated_at.desc(),
                    )
                    .limit(remaining)
                ).mappings().all()

                for row in match_rows:
                    strong_match_count += 1
                    score = float(row["overall_score"])
                    items.append({
                        "type": "match_review",
                        "urgency": "strong_match" if score >= 9 else "good_match",
                        "title": row["candidate_name"] or "Unnamed candidate",
                        "detail": row["job_title"],
                        "job_id": row["job_id"],
                        "candidate_id": row["candidate_id"],
                        "match_id": row["match_id"],
                        "score": score,
                        "profession": row["profession"],
                        "specialty": row["specialty"],
                        "start_date": row["start_date"],
                        "recommended_next_action": "Review strong match" if score >= 9 else "Review match",
                    })

            return clean({
                "items": items,
                "totals": {
                    "overdue_followups": overdue_count,
                    "due_soon_followups": due_soon_count,
                    "match_reviews": strong_match_count,
                },
                "read_only": True,
                "window_hours": 24,
                "source_of_record": "jobdiva",
            })


    def match_work_queue(self, identity, *, limit=25, matches_per_job=5):
        """Read-only recruiter priority queue from canonical jobs + stored match results.

        JobDiva remains the ATS. This endpoint only presents synchronized
        canonical data and Medlivo intelligence; it performs no outreach,
        submission, ownership change, or ATS mutation.
        """
        with self.engine.begin() as conn:
            principal = self._principal(conn, identity)

            job_stmt = select(t.jobs).where(
                t.jobs.c.tenant_id == principal["tenant_id"],
                t.jobs.c.status.not_in(["closed", "cancelled", "canceled"]),
            )
            if principal["role"] == "recruiter":
                job_stmt = job_stmt.where(t.jobs.c.owner_user_id == principal["id"])
            elif principal["role"] == "manager":
                managed_recruiters = (
                    select(t.profiles.c.user_id)
                    .join(t.teams, and_(
                        t.teams.c.id == t.profiles.c.team_id,
                        t.teams.c.tenant_id == t.profiles.c.tenant_id,
                    ))
                    .where(
                        t.profiles.c.tenant_id == principal["tenant_id"],
                        t.teams.c.manager_user_id == principal["id"],
                    )
                )
                job_stmt = job_stmt.where(t.jobs.c.owner_user_id.in_(managed_recruiters))
            elif principal["role"] != "admin":
                raise AccessError(403, "Workspace access required")

            job_rows = conn.execute(
                job_stmt.order_by(
                    t.jobs.c.priority.desc(),
                    t.jobs.c.start_date.asc().nulls_last(),
                    t.jobs.c.updated_at.desc(),
                    t.jobs.c.id,
                ).limit(limit)
            ).mappings().all()

            items = []
            for job in job_rows:
                jobdiva_id = conn.execute(
                    select(t.job_source_records.c.source_id)
                    .where(
                        t.job_source_records.c.tenant_id == principal["tenant_id"],
                        t.job_source_records.c.job_id == job["id"],
                        t.job_source_records.c.source_system == "jobdiva",
                    )
                    .order_by(t.job_source_records.c.source_updated_at.desc().nulls_last())
                    .limit(1)
                ).scalar_one_or_none()

                match_rows = conn.execute(
                    select(t.matches, t.candidates)
                    .join(t.candidates, and_(
                        t.candidates.c.id == t.matches.c.candidate_id,
                        t.candidates.c.tenant_id == t.matches.c.tenant_id,
                    ))
                    .where(
                        t.matches.c.tenant_id == principal["tenant_id"],
                        t.matches.c.job_id == job["id"],
                        t.matches.c.status != "excluded",
                    )
                    .order_by(t.matches.c.overall_score.desc(), t.matches.c.updated_at.desc())
                    .limit(matches_per_job)
                ).mappings().all()

                match_items = []
                for row in match_rows:
                    candidate_id = row["candidate_id"]
                    jobdiva_candidate_id = conn.execute(
                        select(t.candidate_source_records.c.source_id)
                        .where(
                            t.candidate_source_records.c.tenant_id == principal["tenant_id"],
                            t.candidate_source_records.c.candidate_id == candidate_id,
                            t.candidate_source_records.c.source_system == "jobdiva",
                        )
                        .order_by(t.candidate_source_records.c.source_updated_at.desc().nulls_last())
                        .limit(1)
                    ).scalar_one_or_none()

                    owner = conn.execute(
                        select(t.cases.c.owner_user_id, t.users.c.display_name)
                        .join(t.users, and_(
                            t.users.c.id == t.cases.c.owner_user_id,
                            t.users.c.tenant_id == t.cases.c.tenant_id,
                        ))
                        .where(
                            t.cases.c.tenant_id == principal["tenant_id"],
                            t.cases.c.candidate_id == candidate_id,
                        )
                        .order_by(t.cases.c.updated_at.desc())
                        .limit(1)
                    ).mappings().first()

                    last_contact = conn.execute(
                        select(t.conversations.c.updated_at)
                        .where(
                            t.conversations.c.tenant_id == principal["tenant_id"],
                            t.conversations.c.candidate_id == candidate_id,
                            t.conversations.c.job_id == job["id"],
                        )
                        .order_by(t.conversations.c.updated_at.desc())
                        .limit(1)
                    ).scalar_one_or_none()

                    submission = conn.execute(
                        select(t.submissions.c.status, t.submissions.c.readiness_status)
                        .where(
                            t.submissions.c.tenant_id == principal["tenant_id"],
                            t.submissions.c.candidate_id == candidate_id,
                            t.submissions.c.job_id == job["id"],
                        )
                        .order_by(t.submissions.c.updated_at.desc())
                        .limit(1)
                    ).mappings().first()

                    feedback = None
                    if principal["role"] == "recruiter":
                        feedback = conn.execute(
                            select(t.match_feedback.c.feedback_code, t.match_feedback.c.reason_code)
                            .where(
                                t.match_feedback.c.tenant_id == principal["tenant_id"],
                                t.match_feedback.c.match_id == row["id"],
                                t.match_feedback.c.recruiter_user_id == principal["id"],
                            )
                            .order_by(t.match_feedback.c.created_at.desc())
                            .limit(1)
                        ).mappings().first()

                    explanation = row["explanation"] or {}
                    strengths = explanation.get("strengths") if isinstance(explanation, dict) else []
                    gaps = explanation.get("gaps") if isinstance(explanation, dict) else []
                    next_action = "Review match"
                    if submission:
                        next_action = "Review submission status"
                    elif owner and owner["owner_user_id"] != principal["id"]:
                        next_action = "Coordinate with candidate owner"
                    elif not last_contact:
                        next_action = "Review before first outreach"
                    else:
                        next_action = "Review latest candidate activity"

                    match_items.append({
                        "match_id": row["id"],
                        "candidate_id": candidate_id,
                        "jobdiva_candidate_id": jobdiva_candidate_id,
                        "candidate_name": row["canonical_name"] or "Unnamed candidate",
                        "profession": row["profession"],
                        "specialty": row["specialty"],
                        "city": row["city"],
                        "state": row["state"],
                        "profile_freshness": row["profile_freshness"],
                        "score": row["overall_score"],
                        "rules_version": row["rules_version"],
                        "strengths": strengths or [],
                        "gaps": gaps or [],
                        "owner_user_id": owner["owner_user_id"] if owner else None,
                        "owner_name": owner["display_name"] if owner else None,
                        "last_contact_at": last_contact,
                        "submission_status": submission["status"] if submission else None,
                        "submission_readiness": submission["readiness_status"] if submission else None,
                        "recommended_next_action": next_action,
                        "my_feedback_code": feedback["feedback_code"] if feedback else None,
                        "my_feedback_reason": feedback["reason_code"] if feedback else None,
                    })

                items.append({
                    "job_id": job["id"],
                    "jobdiva_job_id": jobdiva_id,
                    "title": job["title"],
                    "profession": job["profession"],
                    "specialty": job["specialty"],
                    "division": job["division"],
                    "city": job["city"],
                    "state": job["state"],
                    "start_date": job["start_date"],
                    "status": job["status"],
                    "priority": job["priority"],
                    "owner_user_id": job["owner_user_id"],
                    "matches": match_items,
                })

            return {
                "items": clean(items),
                "read_only": True,
                "source_of_record": "jobdiva",
            }


    def candidate_best_jobs(self, identity, candidate_id, *, limit=20):
        """Read-only ranked jobs for one canonical candidate from persisted matches."""
        with self.engine.begin() as conn:
            principal = self._principal(conn, identity)

            candidate = conn.execute(
                select(t.candidates).where(
                    t.candidates.c.id == candidate_id,
                    t.candidates.c.tenant_id == principal["tenant_id"],
                )
            ).mappings().first()
            if candidate is None:
                raise AccessError(404, "Candidate not found")

            # Recruiters may inspect candidates they own through an active case;
            # managers may inspect candidates owned by their managed teams;
            # admins may inspect all tenant candidates.
            owner_case = conn.execute(
                select(t.cases.c.owner_user_id, t.cases.c.team_id)
                .where(
                    t.cases.c.tenant_id == principal["tenant_id"],
                    t.cases.c.candidate_id == candidate_id,
                )
                .order_by(t.cases.c.updated_at.desc())
                .limit(1)
            ).mappings().first()
            if principal["role"] == "recruiter":
                if owner_case is not None and owner_case["owner_user_id"] != principal["id"]:
                    raise AccessError(403, "Candidate is owned by another recruiter")
            elif principal["role"] == "manager":
                if owner_case is not None and not self._team_allowed(conn, principal, owner_case["team_id"]):
                    raise AccessError(403, "Candidate is outside your managed team")
            elif principal["role"] != "admin":
                raise AccessError(403, "Workspace access required")

            excluded_count = conn.execute(
                select(func.count()).select_from(t.matches).where(
                    t.matches.c.tenant_id == principal["tenant_id"],
                    t.matches.c.candidate_id == candidate_id,
                    t.matches.c.status == "excluded",
                )
            ).scalar_one()

            rows = conn.execute(
                select(t.matches, t.jobs)
                .join(t.jobs, and_(
                    t.jobs.c.id == t.matches.c.job_id,
                    t.jobs.c.tenant_id == t.matches.c.tenant_id,
                ))
                .where(
                    t.matches.c.tenant_id == principal["tenant_id"],
                    t.matches.c.candidate_id == candidate_id,
                    t.matches.c.status != "excluded",
                    t.jobs.c.status.not_in(["closed", "cancelled", "canceled"]),
                )
                .order_by(
                    t.matches.c.overall_score.desc(),
                    t.jobs.c.priority.desc(),
                    t.jobs.c.start_date.asc().nulls_last(),
                    t.matches.c.updated_at.desc(),
                )
                .limit(limit)
            ).mappings().all()

            items = []
            for row in rows:
                explanation = row["explanation"] or {}
                jobdiva_id = conn.execute(
                    select(t.job_source_records.c.source_id)
                    .where(
                        t.job_source_records.c.tenant_id == principal["tenant_id"],
                        t.job_source_records.c.job_id == row["job_id"],
                        t.job_source_records.c.source_system == "jobdiva",
                    )
                    .order_by(t.job_source_records.c.source_updated_at.desc().nulls_last())
                    .limit(1)
                ).scalar_one_or_none()

                submission = conn.execute(
                    select(t.submissions.c.status, t.submissions.c.readiness_status)
                    .where(
                        t.submissions.c.tenant_id == principal["tenant_id"],
                        t.submissions.c.candidate_id == candidate_id,
                        t.submissions.c.job_id == row["job_id"],
                    )
                    .order_by(t.submissions.c.updated_at.desc())
                    .limit(1)
                ).mappings().first()

                next_action = "Review job match"
                if submission:
                    next_action = "Review submission status"
                elif row["overall_score"] >= 9:
                    next_action = "Prioritize for recruiter review"

                items.append({
                    "match_id": row["id"],
                    "job_id": row["job_id"],
                    "jobdiva_job_id": jobdiva_id,
                    "title": row["title"],
                    "division": row["division"],
                    "profession": row["profession"],
                    "specialty": row["specialty"],
                    "city": row["city"],
                    "state": row["state"],
                    "start_date": row["start_date"],
                    "priority": row["priority"],
                    "score": row["overall_score"],
                    "rules_version": row["rules_version"],
                    "gates": explanation.get("gates", []) if isinstance(explanation, dict) else [],
                    "strengths": explanation.get("strengths", []) if isinstance(explanation, dict) else [],
                    "gaps": explanation.get("gaps", []) if isinstance(explanation, dict) else [],
                    "submission_status": submission["status"] if submission else None,
                    "submission_readiness": submission["readiness_status"] if submission else None,
                    "recommended_next_action": next_action,
                })

            return clean({
                "candidate": {
                    "id": candidate["id"],
                    "canonical_name": candidate["canonical_name"],
                    "profession": candidate["profession"],
                    "specialty": candidate["specialty"],
                    "city": candidate["city"],
                    "state": candidate["state"],
                    "profile_freshness": candidate["profile_freshness"],
                },
                "items": items,
                "excluded_count": excluded_count,
                "read_only": True,
                "source_of_record": "jobdiva",
            })


    def save_match_feedback(self, identity, match_id, key, value):
        payload = {
            "match_id": match_id,
            "feedback_code": value.feedback_code,
            "reason_code": value.reason_code,
            "notes": value.notes,
        }
        def apply(conn, principal):
            match = conn.execute(
                select(t.matches.c.id, t.matches.c.job_id, t.matches.c.candidate_id)
                .where(
                    t.matches.c.id == match_id,
                    t.matches.c.tenant_id == principal["tenant_id"],
                )
            ).mappings().first()
            if match is None:
                raise AccessError(404, "Match not found")

            candidate_case = conn.execute(
                select(t.cases.c.owner_user_id, t.cases.c.team_id)
                .where(
                    t.cases.c.tenant_id == principal["tenant_id"],
                    t.cases.c.candidate_id == match["candidate_id"],
                )
                .order_by(t.cases.c.updated_at.desc())
                .limit(1)
            ).mappings().first()

            if principal["role"] == "recruiter":
                if candidate_case is not None and candidate_case["owner_user_id"] != principal["id"]:
                    raise AccessError(403, "Match belongs to another recruiter")
            elif principal["role"] == "manager":
                if candidate_case is not None and not self._team_allowed(conn, principal, candidate_case["team_id"]):
                    raise AccessError(403, "Match is outside your managed team")
            elif principal["role"] != "admin":
                raise AccessError(403, "Workspace access required")

            timestamp = now()
            existing = conn.execute(
                select(t.match_feedback)
                .where(
                    t.match_feedback.c.tenant_id == principal["tenant_id"],
                    t.match_feedback.c.match_id == match_id,
                    t.match_feedback.c.recruiter_user_id == principal["id"],
                )
                .order_by(t.match_feedback.c.created_at.desc())
                .limit(1)
            ).mappings().first()

            if existing:
                conn.execute(
                    update(t.match_feedback)
                    .where(
                        t.match_feedback.c.id == existing["id"],
                        t.match_feedback.c.tenant_id == principal["tenant_id"],
                    )
                    .values(
                        feedback_code=value.feedback_code,
                        reason_code=value.reason_code,
                        notes=value.notes,
                        created_at=timestamp,
                    )
                )
                return clean(dict(existing, feedback_code=value.feedback_code, reason_code=value.reason_code, notes=value.notes, created_at=timestamp))

            row = {
                "id": uid(),
                "tenant_id": principal["tenant_id"],
                "match_id": match_id,
                "recruiter_user_id": principal["id"],
                "feedback_code": value.feedback_code,
                "reason_code": value.reason_code,
                "notes": value.notes,
                "created_at": timestamp,
            }
            conn.execute(insert(t.match_feedback).values(**row))
            return clean(row)

        return self._global_mutate(identity, key, "match.feedback.saved", payload, apply)


    def match_quality_summary(self, identity):
        with self.engine.begin() as conn:
            principal = self._principal(conn, identity)
            if principal["role"] not in {"manager", "admin"}:
                raise AccessError(403, "Manager access required")

            statement = (
                select(
                    t.match_feedback.c.feedback_code,
                    t.match_feedback.c.reason_code,
                    t.matches.c.overall_score,
                    t.jobs.c.division,
                )
                .join(t.matches, and_(
                    t.matches.c.id == t.match_feedback.c.match_id,
                    t.matches.c.tenant_id == t.match_feedback.c.tenant_id,
                ))
                .join(t.jobs, and_(
                    t.jobs.c.id == t.matches.c.job_id,
                    t.jobs.c.tenant_id == t.matches.c.tenant_id,
                ))
                .where(t.match_feedback.c.tenant_id == principal["tenant_id"])
            )

            if principal["role"] == "manager":
                managed_recruiters = (
                    select(t.profiles.c.user_id)
                    .join(t.teams, and_(
                        t.teams.c.id == t.profiles.c.team_id,
                        t.teams.c.tenant_id == t.profiles.c.tenant_id,
                    ))
                    .where(
                        t.profiles.c.tenant_id == principal["tenant_id"],
                        t.teams.c.manager_user_id == principal["id"],
                    )
                )
                statement = statement.where(
                    or_(
                        t.jobs.c.owner_user_id.in_(managed_recruiters),
                        t.match_feedback.c.recruiter_user_id.in_(managed_recruiters),
                    )
                )

            rows = conn.execute(statement).mappings().all()

            def band(score):
                score = float(score)
                if score >= 9:
                    return "9.0+"
                if score >= 8:
                    return "8.0-8.9"
                return "<8.0"

            summary = {}
            divisions = {}
            negative_reasons = {}
            positive = {"strong_match", "good_match"}
            for row in rows:
                b = band(row["overall_score"])
                bucket = summary.setdefault(b, {"total": 0, "positive": 0, "strong": 0, "good": 0, "weak": 0, "not_a_match": 0})
                bucket["total"] += 1
                code = row["feedback_code"]
                if code in positive:
                    bucket["positive"] += 1
                if code == "strong_match":
                    bucket["strong"] += 1
                elif code == "good_match":
                    bucket["good"] += 1
                elif code == "weak_match":
                    bucket["weak"] += 1
                elif code == "not_a_match":
                    bucket["not_a_match"] += 1

                if code in {"weak_match", "not_a_match"}:
                    reason = row["reason_code"] or "other"
                    negative_reasons[reason] = negative_reasons.get(reason, 0) + 1

                division = row["division"] or "Unclassified"
                d = divisions.setdefault(division, {"total": 0, "positive": 0})
                d["total"] += 1
                if code in positive:
                    d["positive"] += 1

            def add_rates(mapping):
                result = []
                for key, value in mapping.items():
                    total = value["total"]
                    result.append({
                        "key": key,
                        **value,
                        "agreement_rate": round(100 * value["positive"] / total, 1) if total else None,
                    })
                return result

            return {
                "feedback_count": len(rows),
                "score_bands": add_rates(summary),
                "divisions": add_rates(divisions),
                "negative_reasons": [
                    {"key": key, "count": count}
                    for key, count in sorted(negative_reasons.items(), key=lambda item: (-item[1], item[0]))
                ],
                "pilot_target": {
                    "minimum_feedback": 100,
                    "recommended_division_minimum": 25,
                    "nine_plus_agreement_goal": 80.0,
                },
            }


    def _job_for_manager(self, conn, principal, job_id):
        job = conn.execute(select(t.jobs).where(
            t.jobs.c.id == job_id,
            t.jobs.c.tenant_id == principal["tenant_id"],
        )).mappings().first()
        if job is None:
            raise AccessError(404, "Job not found")
        if principal["role"] == "manager":
            teams = conn.execute(select(t.teams.c.id).where(
                t.teams.c.tenant_id == principal["tenant_id"],
                t.teams.c.manager_user_id == principal["id"],
                t.teams.c.division == job["division"],
            ).order_by(t.teams.c.id).limit(2)).scalars().all()
            if len(teams) != 1:
                raise AccessError(403, "Job is outside your managed scope")
            return job, teams[0]
        if principal["role"] == "admin":
            return job, None
        raise AccessError(403, "Delivery Manager access required")

    def _operational_audit(self, conn, principal, action, object_type, object_id,
                           before_state, after_state, *, reason=None):
        conn.execute(insert(t.operational_audit).values(
            id=uid(),
            tenant_id=principal["tenant_id"],
            actor_user_id=principal["id"],
            action=action,
            object_type=object_type,
            object_id=object_id,
            before_state=clean(before_state or {}),
            after_state=clean(after_state or {}),
            reason=reason,
            correlation_id=None,
            created_at=now(),
        ))

    def get_job_operational_overlay(self, identity, job_id):
        with self.engine.begin() as conn:
            principal = self._principal(conn, identity)
            job = conn.execute(select(t.jobs).where(
                t.jobs.c.id == job_id,
                t.jobs.c.tenant_id == principal["tenant_id"],
            )).mappings().first()
            if job is None:
                raise AccessError(404, "Job not found")

            overlay = conn.execute(select(t.job_operational_overlays).where(
                t.job_operational_overlays.c.tenant_id == principal["tenant_id"],
                t.job_operational_overlays.c.job_id == job_id,
            )).mappings().first()

            if principal["role"] == "manager":
                if overlay and overlay["team_id"] is not None:
                    if not self._team_allowed(conn, principal, overlay["team_id"]):
                        raise AccessError(403, "Job is outside your managed scope")
                else:
                    self._job_for_manager(conn, principal, job_id)
            elif principal["role"] == "recruiter":
                if overlay and overlay["recruiter_user_id"] not in {None, principal["id"]}:
                    raise AccessError(403, "Job is assigned to another recruiter")
            elif principal["role"] != "admin":
                raise AccessError(403, "Workspace access required")

            return {
                "job_id": job_id,
                "source_status": job["status"],
                "overlay": clean(overlay) if overlay else {
                    "job_id": job_id,
                    "client_priority": "normal",
                    "job_priority": "standard",
                    "operational_status": "active",
                    "version": 0,
                },
            }

    def update_job_operational_overlay(self, identity, job_id, key, value):
        payload = {
            "job_id": job_id,
            "client_priority": value.client_priority,
            "job_priority": value.job_priority,
            "priority_reason": value.priority_reason,
            "manager_note": value.manager_note,
            "next_action": value.next_action,
            "due_at": value.due_at,
            "operational_status": value.operational_status,
            "expected_version": value.expected_version,
        }
        def apply(conn, principal):
            job, managed_team = self._job_for_manager(conn, principal, job_id)
            existing = conn.execute(select(t.job_operational_overlays).where(
                t.job_operational_overlays.c.tenant_id == principal["tenant_id"],
                t.job_operational_overlays.c.job_id == job_id,
            ).with_for_update()).mappings().first()

            current_version = existing["version"] if existing else 0
            if current_version != value.expected_version:
                raise AccessError(409, "Job priorities changed; reload before saving")

            team_id = existing["team_id"] if existing else managed_team
            if principal["role"] == "manager" and team_id is not None and not self._team_allowed(conn, principal, team_id):
                raise AccessError(403, "Job is outside your managed scope")

            timestamp = now()
            version = current_version + 1
            values = dict(
                client_priority=value.client_priority,
                job_priority=value.job_priority,
                priority_reason=value.priority_reason,
                manager_note=value.manager_note,
                next_action=value.next_action,
                due_at=value.due_at,
                operational_status=value.operational_status,
                version=version,
                updated_by=principal["id"],
                updated_at=timestamp,
            )
            if existing:
                result = conn.execute(update(t.job_operational_overlays).where(
                    t.job_operational_overlays.c.tenant_id == principal["tenant_id"],
                    t.job_operational_overlays.c.job_id == job_id,
                    t.job_operational_overlays.c.version == current_version,
                ).values(**values))
                if result.rowcount != 1:
                    raise AccessError(409, "Job priorities changed; reload before saving")
                row = dict(existing, **values)
            else:
                row = dict(
                    job_id=job_id,
                    tenant_id=principal["tenant_id"],
                    team_id=team_id,
                    recruiter_user_id=job["owner_user_id"],
                    assigned_by=None,
                    assigned_at=None,
                    created_at=timestamp,
                    **values,
                )
                conn.execute(insert(t.job_operational_overlays).values(**row))

            self._operational_audit(
                conn, principal, "job.operational.updated", "job", job_id,
                clean(existing) if existing else {},
                row,
                reason=value.priority_reason,
            )
            return row
        return self._global_mutate(identity, key, "job.operational.updated", payload, apply)

    def assign_job(self, identity, job_id, key, value):
        payload = {
            "job_id": job_id,
            "team_id": str(value.team_id),
            "recruiter_user_id": str(value.recruiter_user_id) if value.recruiter_user_id else None,
            "reason": value.reason,
            "expected_version": value.expected_version,
        }
        def apply(conn, principal):
            job, managed_team = self._job_for_manager(conn, principal, job_id)
            team_id = str(value.team_id)
            if principal["role"] == "manager":
                if managed_team != team_id or not self._team_allowed(conn, principal, team_id):
                    raise AccessError(403, "Select a team you are authorized to manage")
            else:
                if not self._team_allowed(conn, principal, team_id):
                    raise AccessError(422, "Select a valid team")

            recruiter_id = str(value.recruiter_user_id) if value.recruiter_user_id else None
            if recruiter_id is not None:
                target = conn.execute(
                    select(t.users.c.id)
                    .join(t.profiles, and_(
                        t.profiles.c.user_id == t.users.c.id,
                        t.profiles.c.tenant_id == t.users.c.tenant_id,
                    ))
                    .where(
                        t.users.c.id == recruiter_id,
                        t.users.c.tenant_id == principal["tenant_id"],
                        t.users.c.role == "recruiter",
                        t.users.c.is_active.is_(True),
                        t.profiles.c.team_id == team_id,
                    )
                ).first()
                if target is None:
                    raise AccessError(422, "Select an active recruiter in this team")

            existing = conn.execute(select(t.job_operational_overlays).where(
                t.job_operational_overlays.c.tenant_id == principal["tenant_id"],
                t.job_operational_overlays.c.job_id == job_id,
            ).with_for_update()).mappings().first()
            current_version = existing["version"] if existing else 0
            if current_version != value.expected_version:
                raise AccessError(409, "Job ownership changed; reload before saving")

            timestamp = now()
            version = current_version + 1
            previous_owner = existing["recruiter_user_id"] if existing else job["owner_user_id"]
            values = dict(
                team_id=team_id,
                recruiter_user_id=recruiter_id,
                assigned_by=principal["id"],
                assigned_at=timestamp,
                updated_by=principal["id"],
                updated_at=timestamp,
                version=version,
            )
            if existing:
                result = conn.execute(update(t.job_operational_overlays).where(
                    t.job_operational_overlays.c.tenant_id == principal["tenant_id"],
                    t.job_operational_overlays.c.job_id == job_id,
                    t.job_operational_overlays.c.version == current_version,
                ).values(**values))
                if result.rowcount != 1:
                    raise AccessError(409, "Job ownership changed; reload before saving")
                row = dict(existing, **values)
            else:
                row = dict(
                    job_id=job_id,
                    tenant_id=principal["tenant_id"],
                    client_priority="normal",
                    job_priority="standard",
                    priority_reason=None,
                    manager_note=None,
                    next_action=None,
                    due_at=None,
                    operational_status="active",
                    created_at=timestamp,
                    **values,
                )
                conn.execute(insert(t.job_operational_overlays).values(**row))

            if previous_owner != recruiter_id:
                conn.execute(insert(t.job_ownership_history).values(
                    id=uid(),
                    tenant_id=principal["tenant_id"],
                    job_id=job_id,
                    previous_owner_user_id=previous_owner,
                    new_owner_user_id=recruiter_id,
                    changed_by=principal["id"],
                    reason=value.reason,
                    created_at=timestamp,
                ))

            self._operational_audit(
                conn, principal, "job.assignment.changed", "job", job_id,
                {"recruiter_user_id": previous_owner, "team_id": existing["team_id"] if existing else None},
                {"recruiter_user_id": recruiter_id, "team_id": team_id, "version": version},
                reason=value.reason,
            )
            return row
        return self._global_mutate(identity, key, "job.assignment.changed", payload, apply)

    def decide_job_intake_item(self, identity, batch_id, item_id, key, value):
        payload = {
            "batch_id": batch_id,
            "item_id": item_id,
            "decision": value.decision,
            "final_approved_values": value.final_approved_values,
            "bill_rate_state": value.bill_rate_state,
            "recruiting_readiness": value.recruiting_readiness,
            "commercial_readiness": value.commercial_readiness,
            "reason": value.reason,
        }
        def apply(conn, principal):
            if principal["role"] not in {"manager", "admin"}:
                raise AccessError(403, "Delivery Manager access required")
            batch = conn.execute(select(t.job_intake_batches).where(
                t.job_intake_batches.c.tenant_id == principal["tenant_id"],
                t.job_intake_batches.c.id == batch_id,
            )).mappings().first()
            if batch is None:
                raise AccessError(404, "Job intake batch not found")
            if batch["team_id"] is not None and not self._team_allowed(conn, principal, batch["team_id"]):
                raise AccessError(403, "Job intake batch is outside your scope")

            item = conn.execute(select(t.job_intake_items).where(
                t.job_intake_items.c.tenant_id == principal["tenant_id"],
                t.job_intake_items.c.batch_id == batch_id,
                t.job_intake_items.c.id == item_id,
            ).with_for_update()).mappings().first()
            if item is None:
                raise AccessError(404, "Job intake item not found")
            if item["status"] in {"synced", "failed"}:
                raise AccessError(409, "This intake item can no longer be reviewed")

            final_values = value.final_approved_values
            if value.decision == "approved" and final_values is None:
                final_values = item["normalized_job"]

            if value.decision == "approved":
                source_id = str(final_values.get("requisition_id") or f"{batch_id}:{item['row_number']}")
                final_review = analyze_intake_job(
                    final_values,
                    division=batch["division"],
                    source_id=source_id,
                    customer_name=batch["customer_name"],
                )

                # A manager may confirm or correct missing source facts, but the
                # platform still re-runs canonical readiness rules before release.
                if value.recruiting_readiness == "ready" and final_review["recruiting_readiness"] != "ready":
                    raise AccessError(
                        422,
                        "Recruiting Ready requires all required job facts to be confirmed and conflict-free",
                    )

                if value.bill_rate_state == "confirmed" and not final_values.get("bill_rate"):
                    raise AccessError(422, "Confirmed bill rate requires an approved bill rate value")

                if value.commercial_readiness == "ready":
                    if value.bill_rate_state != "confirmed" or not final_values.get("bill_rate"):
                        raise AccessError(
                            422,
                            "Commercially Ready requires an approved confirmed bill rate",
                        )
                    if final_review["recruiting_readiness"] != "ready":
                        raise AccessError(
                            422,
                            "Commercially Ready requires the job to be Recruiting Ready first",
                        )

                standardized_internal_jd = final_review["standardized_internal_jd"]
                conflicts = final_review["conflicts"]
                missing_fields = final_review["missing_fields"]
            else:
                standardized_internal_jd = item["standardized_internal_jd"]
                conflicts = item["conflicts"]
                missing_fields = item["missing_fields"]

            timestamp = now()
            new_status = "approved" if value.decision == "approved" else "rejected"
            updates = dict(
                final_approved_values=final_values,
                standardized_internal_jd=standardized_internal_jd,
                conflicts=conflicts,
                missing_fields=missing_fields,
                bill_rate_state=value.bill_rate_state,
                recruiting_readiness=value.recruiting_readiness,
                commercial_readiness=value.commercial_readiness,
                reviewed_by=principal["id"],
                reviewed_at=timestamp,
                status=new_status,
                updated_at=timestamp,
            )
            conn.execute(update(t.job_intake_items).where(
                t.job_intake_items.c.tenant_id == principal["tenant_id"],
                t.job_intake_items.c.id == item_id,
            ).values(**updates))

            after = dict(item, **updates)
            self._operational_audit(
                conn, principal, "job_intake.item." + new_status, "job_intake_item", item_id,
                clean(item), after, reason=value.reason,
            )
            return after
        return self._global_mutate(identity, key, "job_intake.item.decision", payload, apply)

    def list_operational_audit(self, identity, *, object_type=None, object_id=None, limit=100):
        with self.engine.begin() as conn:
            principal = self._principal(conn, identity)
            if principal["role"] not in {"manager", "admin"}:
                raise AccessError(403, "Delivery Manager access required")
            statement = select(t.operational_audit).where(
                t.operational_audit.c.tenant_id == principal["tenant_id"]
            )
            if object_type:
                statement = statement.where(t.operational_audit.c.object_type == object_type)
            if object_id:
                statement = statement.where(t.operational_audit.c.object_id == object_id)
            rows = conn.execute(statement.order_by(
                t.operational_audit.c.created_at.desc(),
                t.operational_audit.c.id.desc(),
            ).limit(limit)).mappings().all()
            return {"items": [clean(row) for row in rows]}

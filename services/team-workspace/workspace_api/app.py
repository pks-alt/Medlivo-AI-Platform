"""Factory for a separate private service; existing recruiter API is untouched."""
from contextlib import asynccontextmanager
import logging
from uuid import UUID
from datetime import date
from fastapi import FastAPI, Depends, HTTPException, Header, Query, UploadFile, File, Form
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from .auth import AuthenticationError, GoogleIdentityVerifier
from .config import Settings
from .schemas import (
    NoteInput, TaskInput, TaskUpdate, Reassignment, AdminUserInput, AdminUserUpdate,
    JobIntakeBatchInput, CustomerJobMappingInput, WeeklyGoalInput, JobIntakeRowsInput,
    JobPublicationDraftInput, JobPublicationDecision, MatchFeedbackInput,
)
from .store import WorkspaceStore, AccessError


logger = logging.getLogger("medlivo.workspace")


class LimitsMiddleware:
    """Bound JSON request bodies without logging them or trusting Content-Length."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        async def secure_send(message):
            if message["type"] == "http.response.start":
                message["headers"] = [(k, v) for k, v in message.get("headers", []) if k.lower() != b"cache-control"] + [
                    (b"cache-control", b"no-store"), (b"x-content-type-options", b"nosniff"),
                    (b"referrer-policy", b"no-referrer")]
            await send(message)
        if scope["method"] in {"POST", "PUT", "PATCH"}:
            headers = dict(scope.get("headers", []))
            content_type = headers.get(b"content-type", b"")
            media_type = content_type.split(b";", 1)[0].strip().lower()
            path = scope.get("path", "")
            xlsx_upload = path.endswith("/job-intake/upload") and media_type == b"multipart/form-data"
            if media_type != b"application/json" and not xlsx_upload:
                return await JSONResponse({"detail": "JSON body required"}, 415)(scope, receive, secure_send)
            body = bytearray()
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                body.extend(message.get("body", b""))
                max_body = 5 * 1024 * 1024 if xlsx_upload else (1048576 if "/job-intake/" in path else 16384)
                if len(body) > max_body:
                    return await JSONResponse({"detail": "Request body is too large"}, 413)(scope, receive, secure_send)
                if not message.get("more_body", False):
                    break
            sent = False
            async def replay():
                nonlocal sent
                if not sent:
                    sent = True
                    return {"type": "http.request", "body": bytes(body), "more_body": False}
                return await receive()
            return await self.app(scope, replay, secure_send)
        await self.app(scope, receive, secure_send)


def build_app(store, verifier):
    """Dependency injection for isolated tests; not configurable via a bypass flag."""
    @asynccontextmanager
    async def lifespan(app):
        yield
        store.engine.dispose()
    app = FastAPI(title="Medlivo private team workspace", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.add_middleware(LimitsMiddleware)
    bearer = HTTPBearer(auto_error=False)

    def identity(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
        if credentials is None or credentials.scheme.lower() != "bearer":
            logger.warning("workspace_authentication_denied")
            raise HTTPException(401, "Authentication required", headers={"WWW-Authenticate": "Bearer"})
        try:
            return verifier.verify(credentials.credentials)
        except AuthenticationError:
            logger.warning("workspace_authentication_denied")
            raise HTTPException(401, "Authentication required", headers={"WWW-Authenticate": "Bearer"}) from None

    @app.exception_handler(AccessError)
    async def access_error(request, error):
        if error.status in {401, 403, 404}:
            logger.warning("workspace_authorization_denied", extra={"status_code": error.status})
        return JSONResponse({"detail": error.message}, status_code=error.status)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        logger.warning("workspace_validation_rejected")
        return JSONResponse({"detail": "Invalid request fields"}, status_code=422)

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request, error):
        # Event-only logging: never include exception text, SQL, parameters, credentials, or record data.
        logger.error("workspace_database_unavailable")
        return JSONResponse({"detail": "Workspace storage is unavailable"}, status_code=503)

    @app.get("/health")
    def health():
        return {"ok": True, "workspace_enabled": True, "database_checked": False}

    @app.get("/ready")
    def ready():
        try:
            with store.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except SQLAlchemyError:
            logger.error("workspace_readiness_database_unavailable")
            return JSONResponse(
                {"ok": False, "workspace_enabled": True, "database_checked": True, "database_reachable": False},
                status_code=503,
            )
        return {
            "ok": True,
            "workspace_enabled": True,
            "database_checked": True,
            "database_reachable": True,
        }

    prefix = "/api/v1/team"

    @app.get(prefix + "/me")
    def me(who=Depends(identity)):
        return store.me(who)

    @app.get(prefix + "/admin/teams")
    def admin_teams(who=Depends(identity)):
        return store.admin_teams(who)

    @app.get(prefix + "/admin/users")
    def admin_users(who=Depends(identity)):
        return store.admin_users(who)

    @app.post(prefix + "/admin/users", status_code=201)
    def admin_provision_user(value: AdminUserInput, idempotency_key: UUID = Header(), who=Depends(identity)):
        return store.admin_provision_user(who, str(idempotency_key), value)

    @app.patch(prefix + "/admin/users/{user_id}")
    def admin_update_user(user_id: UUID, value: AdminUserUpdate, idempotency_key: UUID = Header(), who=Depends(identity)):
        return store.admin_update_user(who, str(user_id), str(idempotency_key), value)

    @app.get(prefix + "/admin/audit")
    def admin_audit(limit: int = Query(default=50, ge=1, le=100), who=Depends(identity)):
        return store.admin_audit(who, limit=limit)

    @app.get(prefix + "/manager/overview")
    def manager_overview(who=Depends(identity)):
        return store.manager_overview(who)

    @app.get(prefix + "/job-intake/batches")
    def job_intake_batches(limit: int = Query(default=50, ge=1, le=100), who=Depends(identity)):
        return store.list_job_intake_batches(who, limit=limit)

    @app.post(prefix + "/job-intake/upload", status_code=201)
    async def upload_job_intake(
        customer_name: str = Form(min_length=1, max_length=200),
        division: str = Form(),
        source_file: UploadFile = File(),
        team_id: UUID | None = Form(default=None),
        idempotency_key: UUID = Header(),
        who=Depends(identity),
    ):
        if division not in {"Rehabilitation", "Nursing & Allied", "Locum Tenens"}:
            raise HTTPException(422, "Unsupported division")
        filename = (source_file.filename or "").strip()
        if not filename.lower().endswith(".xlsx"):
            raise HTTPException(422, "Upload an .xlsx workbook")
        content = await source_file.read()
        return store.upload_job_intake_xlsx(
            who, str(idempotency_key), customer_name=customer_name, division=division,
            source_filename=filename, team_id=str(team_id) if team_id is not None else None,
            content=content,
        )

    @app.post(prefix + "/job-intake/batches", status_code=201)
    def create_job_intake_batch(value: JobIntakeBatchInput, idempotency_key: UUID = Header(), who=Depends(identity)):
        return store.create_job_intake_batch(who, str(idempotency_key), value)

    @app.post(prefix + "/job-intake/batches/{batch_id}/rows")
    def process_job_intake_rows(batch_id: UUID, value: JobIntakeRowsInput,
                                idempotency_key: UUID = Header(), who=Depends(identity)):
        return store.ingest_job_intake_rows(who, str(batch_id), str(idempotency_key), value)

    @app.get(prefix + "/job-intake/batches/{batch_id}/items")
    def job_intake_items(batch_id: UUID, limit: int = Query(default=200, ge=1, le=500), who=Depends(identity)):
        return store.list_job_intake_items(who, str(batch_id), limit=limit)

    @app.get(prefix + "/job-intake/mappings")
    def job_intake_mappings(division: str | None = None, who=Depends(identity)):
        return store.list_customer_job_mappings(who, division=division)

    @app.put(prefix + "/job-intake/mappings")
    def save_job_intake_mapping(value: CustomerJobMappingInput, idempotency_key: UUID = Header(), who=Depends(identity)):
        return store.upsert_customer_job_mapping(who, str(idempotency_key), value)

    @app.put(prefix + "/recruiters/{recruiter_user_id}/weekly-goals")
    def set_weekly_goal(recruiter_user_id: UUID, value: WeeklyGoalInput,
                        idempotency_key: UUID = Header(), who=Depends(identity)):
        return store.set_weekly_goal(who, str(recruiter_user_id), str(idempotency_key), value)

    @app.get(prefix + "/recruiters/{recruiter_user_id}/weekly-goals")
    def recruiter_weekly_progress(recruiter_user_id: UUID, week_start: date, who=Depends(identity)):
        if week_start.weekday() != 0:
            raise HTTPException(422, "week_start must be a Monday")
        return store.recruiter_weekly_progress(who, str(recruiter_user_id), week_start)

    @app.get(prefix + "/manager/weekly-review")
    def weekly_review(week_start: date, team_id: UUID | None = None, who=Depends(identity)):
        if week_start.weekday() != 0:
            raise HTTPException(422, "week_start must be a Monday")
        return store.weekly_review(
            who, week_start, team_id=str(team_id) if team_id is not None else None
        )

    @app.get(prefix + "/job-publications")
    def job_publications(limit: int = Query(default=100, ge=1, le=200), who=Depends(identity)):
        return store.list_job_publications(who, limit=limit)

    @app.get(prefix + "/recruiter/follow-ups")
    def recruiter_followups(status: str = Query(default="open"), limit: int = Query(default=100, ge=1, le=200), who=Depends(identity)):
        return store.recruiter_followups(who, status=status, limit=limit)

    @app.get(prefix + "/recruiter/dashboard")
    def recruiter_dashboard(week_start: date, who=Depends(identity)):
        if week_start.weekday() != 0:
            raise HTTPException(422, "week_start must be a Monday")
        return store.recruiter_dashboard(who, week_start)

    @app.get(prefix + "/daily-priorities")
    def daily_priorities(limit: int = Query(default=20, ge=1, le=50), who=Depends(identity)):
        return store.daily_priorities(who, limit=limit)

    @app.get(prefix + "/work-queue")
    def work_queue(limit: int = Query(default=25, ge=1, le=50),
                   matches_per_job: int = Query(default=5, ge=1, le=10),
                   who=Depends(identity)):
        return store.match_work_queue(
            who, limit=limit, matches_per_job=matches_per_job
        )

    @app.get(prefix + "/manager/match-quality")
    def match_quality(who=Depends(identity)):
        return store.match_quality_summary(who)

    @app.post(prefix + "/matches/{match_id}/feedback")
    def match_feedback(match_id: UUID, value: MatchFeedbackInput,
                       idempotency_key: UUID = Header(), who=Depends(identity)):
        return store.save_match_feedback(
            who, str(match_id), str(idempotency_key), value
        )

    @app.post(prefix + "/job-publications", status_code=201)
    def create_job_publication(value: JobPublicationDraftInput,
                               idempotency_key: UUID = Header(), who=Depends(identity)):
        return store.create_job_publication(who, str(idempotency_key), value)

    @app.get(prefix + "/job-publications/{publication_id}")
    def job_publication(publication_id: UUID, who=Depends(identity)):
        return store.get_job_publication(who, str(publication_id))

    @app.post(prefix + "/job-publications/{publication_id}/decision")
    def decide_job_publication(publication_id: UUID, value: JobPublicationDecision,
                               idempotency_key: UUID = Header(), who=Depends(identity)):
        return store.decide_job_publication(
            who, str(publication_id), str(idempotency_key), value
        )

    @app.get(prefix + "/candidates")
    def candidates(after: UUID | None = None, limit: int = Query(default=50, ge=1, le=100), who=Depends(identity)):
        return store.list_candidates(who, after=str(after) if after else None, limit=limit)

    @app.get(prefix + "/candidates/{candidate_id}")
    def candidate(candidate_id: UUID, who=Depends(identity)):
        return store.get_candidate(who, str(candidate_id))

    @app.get(prefix + "/candidates/{candidate_id}/best-jobs")
    def candidate_best_jobs(candidate_id: UUID,
                            limit: int = Query(default=20, ge=1, le=50),
                            who=Depends(identity)):
        return store.candidate_best_jobs(who, str(candidate_id), limit=limit)

    @app.get(prefix + "/jobs")
    def jobs(after: UUID | None = None, limit: int = Query(default=50, ge=1, le=100), who=Depends(identity)):
        return store.list_jobs(who, after=str(after) if after else None, limit=limit)

    @app.get(prefix + "/jobs/{job_id}")
    def job(job_id: UUID, who=Depends(identity)):
        return store.get_job(who, str(job_id))

    @app.get(prefix + "/cases")
    def cases(after: UUID | None = None, limit: int = Query(default=50, ge=1, le=100), who=Depends(identity)):
        return store.list_cases(who, after=str(after) if after else None, limit=limit)

    @app.get(prefix + "/cases/{case_id}")
    def case(case_id: UUID, who=Depends(identity)):
        return store.get_case(who, str(case_id))

    @app.get(prefix + "/cases/{case_id}/eligible-owners")
    def owners(case_id: UUID, who=Depends(identity)):
        return store.eligible_owners(who, str(case_id))

    def records_endpoint(kind):
        def records(case_id: UUID, after: UUID | None = None, limit: int = Query(default=50, ge=1, le=100), who=Depends(identity)):
            return store.records(who, str(case_id), kind, after=str(after) if after else None, limit=limit)
        return records

    for kind in ("notes", "tasks", "audit"):
        app.add_api_route(prefix + "/cases/{case_id}/" + kind, records_endpoint(kind), methods=["GET"], name="list_" + kind)

    @app.post(prefix + "/cases/{case_id}/notes", status_code=201)
    def note(case_id: UUID, value: NoteInput, idempotency_key: UUID = Header(), who=Depends(identity)):
        return store.add_note(who, str(case_id), str(idempotency_key), value.body)

    @app.post(prefix + "/cases/{case_id}/tasks", status_code=201)
    def task(case_id: UUID, value: TaskInput, idempotency_key: UUID = Header(), who=Depends(identity)):
        return store.add_task(who, str(case_id), str(idempotency_key), value.title, value.due_at)

    @app.patch(prefix + "/cases/{case_id}/tasks/{task_id}")
    def update_task(case_id: UUID, task_id: UUID, value: TaskUpdate, idempotency_key: UUID = Header(), who=Depends(identity)):
        return store.update_task(who, str(case_id), str(task_id), str(idempotency_key), value.status, value.expected_version)

    @app.post(prefix + "/cases/{case_id}/reassign")
    def reassign(case_id: UUID, value: Reassignment, idempotency_key: UUID = Header(), who=Depends(identity)):
        return store.reassign(who, str(case_id), str(idempotency_key), str(value.owner_user_id), value.reason, value.expected_version)

    return app


def create_app():
    settings = Settings()
    if not settings.enabled:
        app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
        app.add_middleware(LimitsMiddleware)
        @app.get("/health")
        def disabled():
            return {"ok": True, "workspace_enabled": False, "database_checked": False}
        @app.get("/ready")
        def disabled_ready():
            return JSONResponse(
                {"ok": False, "workspace_enabled": False, "database_checked": False, "database_reachable": False},
                status_code=503,
            )
        return app
    engine = create_engine(settings.database_url.get_secret_value(), pool_pre_ping=True,
                           hide_parameters=True, echo=False, pool_size=5, max_overflow=5)
    # No DDL or account creation at startup. An administrator applies migrations.
    return build_app(WorkspaceStore(engine), GoogleIdentityVerifier(settings.google_client_id, settings.google_hosted_domain))

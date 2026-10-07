"""Factory for a separate private service; existing recruiter API is untouched."""
from contextlib import asynccontextmanager
from uuid import UUID
from fastapi import FastAPI, Depends, HTTPException, Header, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from .auth import AuthenticationError, GoogleIdentityVerifier
from .config import Settings
from .schemas import NoteInput, TaskInput, TaskUpdate, Reassignment, AdminUserInput, AdminUserUpdate
from .store import WorkspaceStore, AccessError


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
            if headers.get(b"content-type", b"").split(b";", 1)[0].strip().lower() != b"application/json":
                return await JSONResponse({"detail": "JSON body required"}, 415)(scope, receive, secure_send)
            body = bytearray()
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                body.extend(message.get("body", b""))
                if len(body) > 16384:
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
            raise HTTPException(401, "Authentication required", headers={"WWW-Authenticate": "Bearer"})
        try:
            return verifier.verify(credentials.credentials)
        except AuthenticationError:
            raise HTTPException(401, "Authentication required", headers={"WWW-Authenticate": "Bearer"}) from None

    @app.exception_handler(AccessError)
    async def access_error(request, error):
        return JSONResponse({"detail": error.message}, status_code=error.status)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        return JSONResponse({"detail": "Invalid request fields"}, status_code=422)

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request, error):
        # Database exceptions can include credentials/SQL/record values; never echo them.
        return JSONResponse({"detail": "Workspace storage is unavailable"}, status_code=503)

    @app.get("/health")
    def health():
        return {"ok": True, "workspace_enabled": True, "database_checked": False}

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
            return {"ok": True, "workspace_enabled": False}
        return app
    engine = create_engine(settings.database_url.get_secret_value(), pool_pre_ping=True,
                           hide_parameters=True, echo=False, pool_size=5, max_overflow=5)
    # No DDL or account creation at startup. An administrator applies migrations.
    return build_app(WorkspaceStore(engine), GoogleIdentityVerifier(settings.google_client_id, settings.google_hosted_domain))

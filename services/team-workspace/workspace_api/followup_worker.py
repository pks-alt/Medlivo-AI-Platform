"""Cloud Run Job entrypoint for automatic preparation of due recruiter follow-ups.

This worker creates review-ready drafts only. It never queues or sends email.
"""
import json
import os
from sqlalchemy import create_engine

from .outreach_ai import VertexGeminiOutreachAIComposer
from .store import WorkspaceStore


def main():
    database_url = os.environ.get("WORKSPACE_DATABASE_URL", "")
    project = os.environ.get("WORKSPACE_OUTREACH_AI_PROJECT", "")
    location = os.environ.get("WORKSPACE_OUTREACH_AI_LOCATION", "global")
    model = os.environ.get("WORKSPACE_OUTREACH_AI_MODEL", "")
    if not database_url.startswith("postgresql+psycopg://"):
        raise RuntimeError("Follow-up worker requires private PostgreSQL configuration")
    if not project or not model:
        raise RuntimeError("Follow-up worker requires approved outreach AI configuration")

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        hide_parameters=True,
        echo=False,
        pool_size=2,
        max_overflow=2,
    )
    composer = VertexGeminiOutreachAIComposer(
        project=project,
        location=location,
        model=model,
    )
    try:
        result = WorkspaceStore(
            engine,
            outreach_ai=composer,
        ).prepare_due_followups_system(limit_per_recruiter=20)
        # Counts only; never log draft or candidate content.
        print(json.dumps({
            "ok": True,
            "recruiters_checked": result["recruiters_checked"],
            "drafts_prepared": result["drafts_prepared"],
            "human_review_required": True,
            "automatic_send_enabled": False,
        }))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()

from __future__ import annotations

from uuid import UUID

from psycopg.rows import dict_row

from app.db.database import connection
from app.schemas.career import PublicJobDetail, PublicJobListItem, PublicJobPage, PublicJobSection


def _public_fields(snapshot: dict) -> dict:
    fields = snapshot.get("public_fields") or {}
    if not isinstance(fields, dict):
        return {}
    return fields


def _list_item(row: dict) -> PublicJobListItem:
    snapshot = row["enhanced_snapshot"] or {}
    fields = _public_fields(snapshot)
    return PublicJobListItem(
        id=row["id"],
        title=snapshot.get("public_title") or "Medlivo Opportunity",
        summary=snapshot.get("summary") or "",
        division=snapshot.get("division"),
        profession=snapshot.get("profession") or fields.get("profession"),
        specialty=snapshot.get("specialty") or fields.get("specialty"),
        city=fields.get("city"),
        state=fields.get("state"),
        care_setting=fields.get("care_setting"),
        shift=fields.get("shift"),
        start_date=str(fields.get("start_date")) if fields.get("start_date") is not None else None,
        end_date=str(fields.get("end_date")) if fields.get("end_date") is not None else None,
        duration_weeks=fields.get("duration_weeks"),
        openings=fields.get("openings"),
        rate_unit=fields.get("rate_unit"),
    )


class CareerRepository:
    async def list_jobs(
        self,
        *,
        division: str | None = None,
        profession: str | None = None,
        specialty: str | None = None,
        state: str | None = None,
        city: str | None = None,
        after: UUID | None = None,
        limit: int = 24,
    ) -> PublicJobPage:
        clauses = [
            "website_status = 'approved'",
            "readiness = 'ready_to_publish'",
        ]
        params: dict[str, object] = {"limit": limit + 1}
        filters = {
            "division": division,
            "profession": profession,
            "specialty": specialty,
            "state": state,
            "city": city,
        }
        for key, value in filters.items():
            if value:
                clauses.append(f"(enhanced_snapshot->>'{key}' = %({key})s OR enhanced_snapshot->'public_fields'->>'{key}' = %({key})s)")
                params[key] = value
        if after is not None:
            clauses.append("id > %(after)s")
            params["after"] = after

        sql = f"""
            SELECT id, enhanced_snapshot
            FROM ws_job_publication
            WHERE {" AND ".join(clauses)}
            ORDER BY id
            LIMIT %(limit)s
        """
        async with connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(sql, params)
                rows = await cursor.fetchall()

        has_more = len(rows) > limit
        selected = rows[:limit]
        items = [_list_item(row) for row in selected]
        return PublicJobPage(
            items=items,
            next_cursor=selected[-1]["id"] if has_more and selected else None,
        )

    async def get_job(self, job_id: UUID) -> PublicJobDetail:
        async with connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(
                    """
                    SELECT id, enhanced_snapshot
                    FROM ws_job_publication
                    WHERE id = %(id)s
                      AND website_status = 'approved'
                      AND readiness = 'ready_to_publish'
                    """,
                    {"id": job_id},
                )
                row = await cursor.fetchone()
        if row is None:
            raise KeyError(job_id)

        base = _list_item(row)
        snapshot = row["enhanced_snapshot"] or {}
        raw_sections = snapshot.get("sections") or []
        sections = [
            PublicJobSection(
                key=section.get("key", "section"),
                heading=section.get("heading", ""),
                content=section.get("content", ""),
            )
            for section in raw_sections
            if isinstance(section, dict) and section.get("heading") and section.get("content")
        ]
        return PublicJobDetail(
            **base.model_dump(),
            sections=sections,
            public_fields=_public_fields(snapshot),
        )

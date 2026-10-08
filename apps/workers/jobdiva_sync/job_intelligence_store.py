from __future__ import annotations

from uuid import uuid4

from job_intelligence import NormalizedJob
from psycopg import AsyncConnection
from psycopg.types.json import Jsonb


class JobIntelligenceStore:
    """Persist JobDiva Job Intelligence into canonical Medlivo tables."""

    def __init__(self, connection: AsyncConnection):
        self.connection = connection

    async def pending_sources(self, *, tenant_id: str, limit: int = 100) -> list[dict]:
        if limit < 1 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        async with self.connection.cursor() as cur:
            await cur.execute(
                """
                SELECT id, job_id, source_id, source_updated_at, updated_at
                FROM job_source_record
                WHERE tenant_id=%s
                  AND source_system='jobdiva'
                  AND job_id IS NOT NULL
                  AND (
                    enriched_at IS NULL
                    OR enriched_at < updated_at
                    OR enrichment_version IS DISTINCT FROM 'jobdiva-detail-v1'
                  )
                ORDER BY updated_at, id
                LIMIT %s
                """,
                (tenant_id, limit),
            )
            rows = await cur.fetchall()
        return [
            {
                "source_record_id": str(row[0]),
                "job_id": str(row[1]),
                "source_job_id": row[2],
                "source_updated_at": row[3],
                "source_record_updated_at": row[4],
            }
            for row in rows
        ]

    async def persist(
        self,
        *,
        tenant_id: str,
        source_record_id: str,
        job_id: str,
        intelligence: NormalizedJob,
        enrichment_version: str = "jobdiva-detail-v1",
    ) -> None:
        normalized_payload = {
            "source_system": intelligence.source.system,
            "source_id": intelligence.source.source_id,
            "description_text": intelligence.description_text,
            "care_setting": intelligence.care_setting,
            "shift": intelligence.shift,
            "schedule": intelligence.schedule,
            "end_date": intelligence.end_date.isoformat() if intelligence.end_date else None,
            "duration_weeks": intelligence.duration_weeks,
            "openings": intelligence.openings,
            "rate_unit": intelligence.rate_unit,
            "remote_allowed": intelligence.remote_allowed,
            "travel_required": intelligence.travel_required,
            "required_license_states": intelligence.required_license_states,
        }
        normalized_payload = {k: v for k, v in normalized_payload.items() if v is not None}

        async with self.connection.transaction():
            await self.connection.execute(
                """
                UPDATE job
                SET title=%s,
                    profession=COALESCE(%s, profession),
                    specialty=COALESCE(%s, specialty),
                    city=COALESCE(%s, city),
                    state=COALESCE(%s, state),
                    start_date=COALESCE(%s, start_date),
                    status=CASE WHEN %s <> 'unknown' THEN %s ELSE status END,
                    normalized_payload=normalized_payload || %s,
                    updated_at=now()
                WHERE id=%s AND tenant_id=%s
                """,
                (
                    intelligence.title,
                    intelligence.profession,
                    intelligence.specialty,
                    intelligence.city,
                    intelligence.state,
                    intelligence.start_date,
                    intelligence.status,
                    intelligence.status,
                    Jsonb(normalized_payload),
                    job_id,
                    tenant_id,
                ),
            )

            # Only JobDiva detail-derived requirements under this rules version
            # are replaced. Requirements from customer intake or manager review
            # remain untouched.
            await self.connection.execute(
                """
                DELETE FROM job_requirement
                WHERE tenant_id=%s
                  AND job_id=%s
                  AND rules_version='jobdiva-detail-v1'
                """,
                (tenant_id, job_id),
            )

            for requirement in intelligence.hard_requirements:
                canonical_key = (
                    "license_state" if requirement.kind == "license"
                    else "certification" if requirement.kind == "certification"
                    else requirement.kind
                )
                await self.connection.execute(
                    """
                    INSERT INTO job_requirement
                      (id, tenant_id, job_id, requirement_type, canonical_key,
                       value, is_hard_gate, source_evidence, rules_version, created_at)
                    VALUES (%s,%s,%s,%s,%s,%s,true,%s,'jobdiva-detail-v1',now())
                    """,
                    (
                        str(uuid4()),
                        tenant_id,
                        job_id,
                        requirement.kind,
                        canonical_key,
                        Jsonb({"value": requirement.value}),
                        Jsonb({
                            "source_system": "jobdiva",
                            "source_job_id": intelligence.source.source_id,
                            "source_field": requirement.source_field,
                        }),
                    ),
                )

            await self.connection.execute(
                """
                UPDATE job_source_record
                SET enriched_at=now(),
                    enrichment_version=%s,
                    enrichment_error_code=NULL
                WHERE id=%s AND tenant_id=%s AND job_id=%s
                """,
                (enrichment_version, source_record_id, tenant_id, job_id),
            )

    async def mark_error(self, *, tenant_id: str, source_record_id: str, error_code: str) -> None:
        await self.connection.execute(
            """
            UPDATE job_source_record
            SET enrichment_error_code=%s
            WHERE id=%s AND tenant_id=%s
            """,
            (error_code[:120], source_record_id, tenant_id),
        )

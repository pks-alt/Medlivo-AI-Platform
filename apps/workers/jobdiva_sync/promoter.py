from __future__ import annotations

from dataclasses import asdict
from typing import Any
from uuid import uuid4

from psycopg import AsyncConnection
from psycopg.types.json import Jsonb

from .models import SyncStream
from .promotion import promote_candidate_payload, promote_job_payload


class CanonicalPromoter:
    """Promote landed JobDiva source records into canonical Medlivo entities.

    Promotion is conservative and idempotent. Existing richer canonical values
    are never overwritten by missing fields from a JobDiva delta record.
    """

    def __init__(self, connection: AsyncConnection):
        self.connection = connection

    async def promote_unlinked(self, *, tenant_id: str, stream: SyncStream, limit: int = 500) -> dict[str, int | str]:
        if limit < 1 or limit > 5000:
            raise ValueError("limit must be between 1 and 5000")

        source_system = "jobdiva"
        entity_type = "job" if stream == SyncStream.JOBS else "candidate"
        source_table = "job_source_record" if stream == SyncStream.JOBS else "candidate_source_record"
        link_column = "job_id" if stream == SyncStream.JOBS else "candidate_id"
        run_id = str(uuid4())

        async with self.connection.transaction():
            await self.connection.execute(
                """
                INSERT INTO integration_promotion_run
                  (id, tenant_id, source_system, entity_type, status)
                VALUES (%s, %s, %s, %s, 'running')
                """,
                (run_id, tenant_id, source_system, entity_type),
            )

        promoted = skipped = failed = seen = 0
        try:
            async with self.connection.cursor() as cur:
                await cur.execute(
                    f"""
                    SELECT id, source_id, raw_payload
                    FROM {source_table}
                    WHERE tenant_id=%s AND source_system=%s AND {link_column} IS NULL
                    ORDER BY created_at, id
                    LIMIT %s
                    """,
                    (tenant_id, source_system, limit),
                )
                rows = await cur.fetchall()

            for source_record_id, source_id, payload in rows:
                seen += 1
                try:
                    if stream == SyncStream.JOBS:
                        value = promote_job_payload(payload or {})
                        await self._promote_job(
                            tenant_id=tenant_id,
                            source_record_id=str(source_record_id),
                            source_id=source_id,
                            value=value,
                        )
                    else:
                        value = promote_candidate_payload(payload or {})
                        await self._promote_candidate(
                            tenant_id=tenant_id,
                            source_record_id=str(source_record_id),
                            source_id=source_id,
                            value=value,
                        )
                    promoted += 1
                except ValueError:
                    skipped += 1
                except Exception:
                    failed += 1
                    raise

            async with self.connection.transaction():
                await self.connection.execute(
                    """
                    UPDATE integration_promotion_run
                    SET status='succeeded', source_records_seen=%s, promoted=%s,
                        skipped=%s, failed=%s, finished_at=now()
                    WHERE id=%s AND tenant_id=%s
                    """,
                    (seen, promoted, skipped, failed, run_id, tenant_id),
                )
            return {
                "run_id": run_id,
                "source_records_seen": seen,
                "promoted": promoted,
                "skipped": skipped,
                "failed": failed,
            }
        except Exception as exc:
            async with self.connection.transaction():
                await self.connection.execute(
                    """
                    UPDATE integration_promotion_run
                    SET status='failed', source_records_seen=%s, promoted=%s,
                        skipped=%s, failed=%s, error_code=%s, finished_at=now()
                    WHERE id=%s AND tenant_id=%s
                    """,
                    (seen, promoted, skipped, failed, type(exc).__name__[:120], run_id, tenant_id),
                )
            raise

    async def _promote_job(self, *, tenant_id: str, source_record_id: str, source_id: str, value) -> None:
        async with self.connection.transaction():
            async with self.connection.cursor() as cur:
                await cur.execute(
                    """
                    SELECT job_id FROM job_source_record
                    WHERE id=%s AND tenant_id=%s
                    FOR UPDATE
                    """,
                    (source_record_id, tenant_id),
                )
                row = await cur.fetchone()
                if row is None:
                    raise RuntimeError("Job source record disappeared during promotion")
                if row[0] is not None:
                    return

                await cur.execute(
                    """
                    INSERT INTO job
                      (tenant_id, title, profession, specialty, city, state, start_date,
                       status, normalized_payload, created_at, updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,now(),now())
                    RETURNING id
                    """,
                    (
                        tenant_id,
                        value.title,
                        value.profession,
                        value.specialty,
                        value.city,
                        value.state,
                        value.start_date,
                        value.status,
                        Jsonb(value.normalized_payload),
                    ),
                )
                job_id = (await cur.fetchone())[0]
                await cur.execute(
                    """
                    UPDATE job_source_record
                    SET job_id=%s, source_status=%s, updated_at=now()
                    WHERE id=%s AND tenant_id=%s AND job_id IS NULL
                    """,
                    (job_id, value.status, source_record_id, tenant_id),
                )

    async def _promote_candidate(self, *, tenant_id: str, source_record_id: str, source_id: str, value) -> None:
        async with self.connection.transaction():
            async with self.connection.cursor() as cur:
                await cur.execute(
                    """
                    SELECT candidate_id FROM candidate_source_record
                    WHERE id=%s AND tenant_id=%s
                    FOR UPDATE
                    """,
                    (source_record_id, tenant_id),
                )
                row = await cur.fetchone()
                if row is None:
                    raise RuntimeError("Candidate source record disappeared during promotion")
                if row[0] is not None:
                    return

                await cur.execute(
                    """
                    INSERT INTO candidate
                      (tenant_id, canonical_name, primary_email, primary_phone,
                       profession, specialty, city, state, lifecycle_status,
                       canonical_profile, created_at, updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'inactive',%s,now(),now())
                    RETURNING id
                    """,
                    (
                        tenant_id,
                        value.canonical_name,
                        value.primary_email,
                        value.primary_phone,
                        value.profession,
                        value.specialty,
                        value.city,
                        value.state,
                        Jsonb(value.canonical_profile),
                    ),
                )
                candidate_id = (await cur.fetchone())[0]
                await cur.execute(
                    """
                    UPDATE candidate_source_record
                    SET candidate_id=%s, updated_at=now()
                    WHERE id=%s AND tenant_id=%s AND candidate_id IS NULL
                    """,
                    (candidate_id, source_record_id, tenant_id),
                )

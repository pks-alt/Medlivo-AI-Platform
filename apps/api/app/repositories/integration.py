from __future__ import annotations

from datetime import datetime, timezone

from psycopg.rows import dict_row

from app.db.database import connection
from app.schemas.integration import JobDivaSyncHealth, SyncStreamHealth


class IntegrationRepository:
    async def jobdiva_sync_health(self, *, stale_after_minutes: int = 30) -> JobDivaSyncHealth:
        async with connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(
                    """
                    WITH streams(stream) AS (
                      VALUES ('jobs'::text), ('candidates'::text)
                    ),
                    tenant_streams AS (
                      SELECT t.id AS tenant_id, t.slug AS tenant_slug, s.stream
                      FROM tenant t CROSS JOIN streams s
                    ),
                    latest_run AS (
                      SELECT DISTINCT ON (tenant_id, stream)
                        tenant_id, stream, status, started_at, finished_at,
                        records_seen, records_upserted, error_code
                      FROM integration_sync_run
                      WHERE source_system='jobdiva' AND mode='delta'
                      ORDER BY tenant_id, stream, started_at DESC, id DESC
                    )
                    SELECT
                      ts.tenant_slug,
                      ts.stream,
                      c.watermark,
                      c.last_success_at,
                      c.last_error_code,
                      lr.status AS last_run_status,
                      lr.started_at AS last_run_started_at,
                      lr.finished_at AS last_run_finished_at,
                      lr.records_seen AS latest_records_seen,
                      lr.records_upserted AS latest_records_upserted
                    FROM tenant_streams ts
                    LEFT JOIN integration_sync_checkpoint c
                      ON c.tenant_id=ts.tenant_id
                     AND c.source_system='jobdiva'
                     AND c.stream=ts.stream
                    LEFT JOIN latest_run lr
                      ON lr.tenant_id=ts.tenant_id AND lr.stream=ts.stream
                    ORDER BY ts.tenant_slug, ts.stream
                    """
                )
                rows = await cursor.fetchall()

        now = datetime.now(timezone.utc)
        items: list[SyncStreamHealth] = []
        for row in rows:
            watermark = row["watermark"]
            freshness = None
            if watermark is not None:
                freshness = max(0, int((now - watermark).total_seconds() // 60))

            if row["last_error_code"] or row["last_run_status"] == "failed":
                status = "error"
            elif watermark is None:
                status = "never_synced"
            elif freshness is not None and freshness > stale_after_minutes:
                status = "stale"
            else:
                status = "healthy"

            items.append(SyncStreamHealth(
                tenant_slug=row["tenant_slug"],
                source_system="jobdiva",
                stream=row["stream"],
                status=status,
                watermark=watermark,
                last_success_at=row["last_success_at"],
                last_run_status=row["last_run_status"],
                last_run_started_at=row["last_run_started_at"],
                last_run_finished_at=row["last_run_finished_at"],
                last_error_code=row["last_error_code"],
                freshness_minutes=freshness,
                latest_records_seen=row["latest_records_seen"],
                latest_records_upserted=row["latest_records_upserted"],
            ))
        return JobDivaSyncHealth(generated_at=now, streams=items)

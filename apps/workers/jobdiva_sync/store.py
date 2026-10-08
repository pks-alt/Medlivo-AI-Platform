from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from psycopg import AsyncConnection
from psycopg.types.json import Jsonb

from .models import SyncStream
from .runner import source_id


class PostgresSyncStore:
    """Durable JobDiva landing/checkpoint store using the canonical database."""

    def __init__(self, connection: AsyncConnection):
        self.connection = connection

    async def checkpoint(self, tenant_id: str, source_system: str, stream: SyncStream) -> datetime | None:
        async with self.connection.cursor() as cur:
            await cur.execute(
                """
                SELECT watermark
                FROM integration_sync_checkpoint
                WHERE tenant_id = %s AND source_system = %s AND stream = %s
                """,
                (tenant_id, source_system, stream.value),
            )
            row = await cur.fetchone()
            return row[0] if row else None

    async def start_run(self, *, run_id: str, tenant_id: str, source_system: str, stream: SyncStream, window_start: datetime, window_end: datetime) -> None:
        async with self.connection.transaction():
            await self.connection.execute(
                """
                INSERT INTO integration_sync_run
                  (id, tenant_id, source_system, stream, status, window_start, window_end)
                VALUES (%s, %s, %s, %s, 'running', %s, %s)
                """,
                (run_id, tenant_id, source_system, stream.value, window_start, window_end),
            )

    async def upsert_page(self, *, tenant_id: str, source_system: str, stream: SyncStream, records: list[dict[str, Any]]) -> int:
        table = "job_source_record" if stream == SyncStream.JOBS else "candidate_source_record"
        rows: list[tuple[str, Jsonb]] = []
        deduped: dict[str, dict[str, Any]] = {}
        for record in records:
            deduped[source_id(stream, record)] = record
        rows = [(ident, Jsonb(payload)) for ident, payload in deduped.items()]

        if not rows:
            return 0

        query = f"""
            INSERT INTO {table}
              (tenant_id, source_system, source_id, raw_payload, created_at, updated_at)
            VALUES (%s, %s, %s, %s, now(), now())
            ON CONFLICT (tenant_id, source_system, source_id)
            DO UPDATE SET raw_payload = EXCLUDED.raw_payload, updated_at = now()
        """
        async with self.connection.transaction():
            async with self.connection.cursor() as cur:
                await cur.executemany(
                    query,
                    [(tenant_id, source_system, ident, payload) for ident, payload in rows],
                )
        return len(rows)

    async def succeed_run(self, *, run_id: str, tenant_id: str, source_system: str, stream: SyncStream, window_end: datetime, pages_processed: int, records_seen: int, records_upserted: int) -> None:
        async with self.connection.transaction():
            await self.connection.execute(
                """
                UPDATE integration_sync_run
                SET status='succeeded', pages_processed=%s, records_seen=%s,
                    records_upserted=%s, finished_at=now()
                WHERE id=%s AND tenant_id=%s
                """,
                (pages_processed, records_seen, records_upserted, run_id, tenant_id),
            )
            await self.connection.execute(
                """
                INSERT INTO integration_sync_checkpoint
                  (tenant_id, source_system, stream, watermark, last_success_at, last_run_id, last_error_code, updated_at)
                VALUES (%s, %s, %s, %s, now(), %s, NULL, now())
                ON CONFLICT (tenant_id, source_system, stream)
                DO UPDATE SET watermark=EXCLUDED.watermark, last_success_at=now(),
                    last_run_id=EXCLUDED.last_run_id, last_error_code=NULL, updated_at=now()
                """,
                (tenant_id, source_system, stream.value, window_end, run_id),
            )

    async def fail_run(self, *, run_id: str, tenant_id: str, source_system: str, stream: SyncStream, error_code: str, pages_processed: int, records_seen: int, records_upserted: int) -> None:
        async with self.connection.transaction():
            await self.connection.execute(
                """
                UPDATE integration_sync_run
                SET status='failed', pages_processed=%s, records_seen=%s,
                    records_upserted=%s, error_code=%s, finished_at=now()
                WHERE id=%s AND tenant_id=%s
                """,
                (pages_processed, records_seen, records_upserted, error_code, run_id, tenant_id),
            )
            await self.connection.execute(
                """
                INSERT INTO integration_sync_checkpoint
                  (tenant_id, source_system, stream, last_run_id, last_error_code, updated_at)
                VALUES (%s, %s, %s, %s, %s, now())
                ON CONFLICT (tenant_id, source_system, stream)
                DO UPDATE SET last_run_id=EXCLUDED.last_run_id,
                    last_error_code=EXCLUDED.last_error_code, updated_at=now()
                """,
                (tenant_id, source_system, stream.value, run_id, error_code),
            )

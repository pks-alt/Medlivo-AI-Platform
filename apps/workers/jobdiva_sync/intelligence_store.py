from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

from candidate_intelligence import CandidateIntelligence
from psycopg import AsyncConnection
from psycopg.types.json import Jsonb


def _cert_key(name: str) -> str:
    return " ".join(name.strip().lower().split()).replace(" ", "_")[:200]


class CandidateIntelligenceStore:
    """Persist normalized Candidate Intelligence into canonical Medlivo tables."""

    def __init__(self, connection: AsyncConnection):
        self.connection = connection

    async def pending_sources(self, *, tenant_id: str, limit: int = 100) -> list[dict]:
        if limit < 1 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        async with self.connection.cursor() as cur:
            await cur.execute(
                """
                SELECT id, candidate_id, source_id, source_updated_at, updated_at
                FROM candidate_source_record
                WHERE tenant_id=%s
                  AND source_system='jobdiva'
                  AND candidate_id IS NOT NULL
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
                "candidate_id": str(row[1]),
                "source_candidate_id": row[2],
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
        candidate_id: str,
        intelligence: CandidateIntelligence,
        enrichment_version: str = "jobdiva-detail-v1",
    ) -> None:
        async with self.connection.transaction():
            # Rich detail fields may fill gaps but never erase existing canonical
            # values with nulls from a partial JobDiva detail response.
            await self.connection.execute(
                """
                UPDATE candidate
                SET canonical_name=COALESCE(%s, canonical_name),
                    primary_email=COALESCE(%s, primary_email),
                    primary_phone=COALESCE(%s, primary_phone),
                    profession=COALESCE(%s, profession),
                    specialty=COALESCE(%s, specialty),
                    city=COALESCE(%s, city),
                    state=COALESCE(%s, state),
                    profile_freshness=%s,
                    canonical_profile=canonical_profile || %s,
                    updated_at=now()
                WHERE id=%s AND tenant_id=%s
                """,
                (
                    intelligence.full_name,
                    intelligence.email,
                    intelligence.phone,
                    intelligence.profession,
                    intelligence.specialty,
                    intelligence.city,
                    intelligence.state,
                    intelligence.matching_readiness.score,
                    Jsonb({
                        "source_system": intelligence.source_system,
                        "source_candidate_id": intelligence.source_candidate_id,
                        "primary_resume_id": intelligence.primary_resume_id,
                        "matching_readiness": intelligence.matching_readiness.model_dump(mode="json"),
                    }),
                    candidate_id,
                    tenant_id,
                ),
            )

            # JobDiva-sourced credential rows are replaced transactionally from
            # the latest authoritative detail response.
            await self.connection.execute(
                """
                DELETE FROM candidate_license
                WHERE tenant_id=%s AND candidate_id=%s AND source_system='jobdiva'
                """,
                (tenant_id, candidate_id),
            )
            for license_item in intelligence.licenses:
                await self.connection.execute(
                    """
                    INSERT INTO candidate_license
                      (id, tenant_id, candidate_id, license_type, state, license_number,
                       status, expires_at, verification_status, verification_source,
                       source_system, source_reference, raw_payload, created_at, updated_at)
                    VALUES
                      (%s,%s,%s,%s,%s,%s,%s,%s,'unverified','jobdiva',
                       'jobdiva',%s,%s,now(),now())
                    """,
                    (
                        str(uuid4()),
                        tenant_id,
                        candidate_id,
                        license_item.license_type,
                        license_item.state,
                        license_item.license_number,
                        license_item.status,
                        license_item.expires_at,
                        license_item.source_reference,
                        Jsonb(license_item.model_dump(mode="json")),
                    ),
                )

            await self.connection.execute(
                """
                DELETE FROM candidate_certification
                WHERE tenant_id=%s AND candidate_id=%s AND source_system='jobdiva'
                """,
                (tenant_id, candidate_id),
            )
            for cert in intelligence.certifications:
                await self.connection.execute(
                    """
                    INSERT INTO candidate_certification
                      (id, tenant_id, candidate_id, certification_key, certification_name,
                       status, expires_at, verification_status, verification_source,
                       source_system, source_reference, raw_payload, created_at, updated_at)
                    VALUES
                      (%s,%s,%s,%s,%s,%s,%s,'unverified','jobdiva',
                       'jobdiva',%s,%s,now(),now())
                    """,
                    (
                        str(uuid4()),
                        tenant_id,
                        candidate_id,
                        _cert_key(cert.name),
                        cert.name,
                        cert.status,
                        cert.expires_at,
                        cert.source_reference,
                        Jsonb(cert.model_dump(mode="json")),
                    ),
                )

            # Keep all known JobDiva resume versions, but only mark the current
            # primary resume as primary. Resume files remain in JobDiva.
            await self.connection.execute(
                """
                UPDATE resume_version
                SET is_primary=false, updated_at=now()
                WHERE tenant_id=%s AND candidate_id=%s
                """,
                (tenant_id, candidate_id),
            )
            for resume in intelligence.resumes:
                await self.connection.execute(
                    """
                    INSERT INTO resume_version
                      (id, tenant_id, candidate_id, source_record_id, source_resume_id,
                       text_content, parsed_payload, is_primary, resume_date, created_at, updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,now(),now())
                    ON CONFLICT (tenant_id, candidate_id, source_resume_id)
                    WHERE source_resume_id IS NOT NULL
                    DO UPDATE SET
                      source_record_id=EXCLUDED.source_record_id,
                      text_content=EXCLUDED.text_content,
                      parsed_payload=EXCLUDED.parsed_payload,
                      is_primary=EXCLUDED.is_primary,
                      resume_date=EXCLUDED.resume_date,
                      updated_at=now()
                    """,
                    (
                        str(uuid4()),
                        tenant_id,
                        candidate_id,
                        source_record_id,
                        resume.source_resume_id,
                        resume.text,
                        Jsonb({"source_reference": resume.source_reference}),
                        resume.source_resume_id == intelligence.primary_resume_id,
                        resume.resume_date,
                    ),
                )

            # Evidence is regenerated from the current JobDiva detail snapshot.
            await self.connection.execute(
                """
                DELETE FROM candidate_evidence
                WHERE tenant_id=%s AND candidate_id=%s
                  AND source_type IN (
                    'jobdiva_profile','jobdiva_license',
                    'jobdiva_certification','jobdiva_resume'
                  )
                """,
                (tenant_id, candidate_id),
            )
            for evidence in intelligence.evidence:
                await self.connection.execute(
                    """
                    INSERT INTO candidate_evidence
                      (id, tenant_id, candidate_id, fact_key, fact_value, source_type,
                       source_reference, confidence, is_verified, created_at, updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,false,now(),now())
                    """,
                    (
                        str(uuid4()),
                        tenant_id,
                        candidate_id,
                        evidence.fact_key,
                        Jsonb(evidence.value),
                        evidence.source_type,
                        evidence.source_reference,
                        evidence.confidence,
                    ),
                )

            await self.connection.execute(
                """
                UPDATE candidate_source_record
                SET enriched_at=now(),
                    enrichment_version=%s,
                    enrichment_error_code=NULL
                WHERE id=%s AND tenant_id=%s AND candidate_id=%s
                """,
                (enrichment_version, source_record_id, tenant_id, candidate_id),
            )

    async def mark_error(
        self,
        *,
        tenant_id: str,
        source_record_id: str,
        error_code: str,
    ) -> None:
        await self.connection.execute(
            """
            UPDATE candidate_source_record
            SET enrichment_error_code=%s
            WHERE id=%s AND tenant_id=%s
            """,
            (error_code[:120], source_record_id, tenant_id),
        )

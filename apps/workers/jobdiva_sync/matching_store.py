from __future__ import annotations

from datetime import date
from typing import Any
from uuid import uuid4

from matching_engine import MatchResult
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


RULES_VERSION = "deterministic-v1"


def _documented_experience_years(entries: list[dict[str, Any]]) -> int | None:
    intervals: list[tuple[int, int]] = []
    current_year = date.today().year
    for item in entries:
        if not isinstance(item, dict):
            continue
        start = item.get("start_year")
        end = current_year if item.get("is_current") else item.get("end_year")
        if not isinstance(start, int) or not isinstance(end, int) or end < start:
            continue
        intervals.append((start, end))
    if not intervals:
        return None
    intervals.sort()
    merged: list[list[int]] = []
    for start, end in intervals:
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return sum(end - start for start, end in merged)


class MatchingStore:
    """Read canonical intelligence and persist deterministic match results."""

    def __init__(self, connection: AsyncConnection):
        self.connection = connection

    async def pending_pairs(
        self,
        *,
        tenant_id: str,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        if limit < 1 or limit > 5000:
            raise ValueError("limit must be between 1 and 5000")

        async with self.connection.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT
                  j.id AS job_id,
                  c.id AS candidate_id
                FROM job j
                JOIN candidate c
                  ON c.tenant_id=j.tenant_id
                 AND j.profession IS NOT NULL
                 AND c.profession IS NOT NULL
                 AND lower(c.profession)=lower(j.profession)
                LEFT JOIN match m
                  ON m.tenant_id=j.tenant_id
                 AND m.job_id=j.id
                 AND m.candidate_id=c.id
                WHERE j.tenant_id=%s
                  AND j.status NOT IN ('closed','cancelled','canceled')
                  AND EXISTS (
                    SELECT 1 FROM job_source_record js
                    WHERE js.tenant_id=j.tenant_id
                      AND js.job_id=j.id
                      AND js.source_system='jobdiva'
                      AND js.enrichment_version='jobdiva-detail-v1'
                      AND js.enriched_at IS NOT NULL
                  )
                  AND EXISTS (
                    SELECT 1 FROM candidate_source_record cs
                    WHERE cs.tenant_id=c.tenant_id
                      AND cs.candidate_id=c.id
                      AND cs.source_system='jobdiva'
                      AND cs.enrichment_version='jobdiva-detail-v1'
                      AND cs.enriched_at IS NOT NULL
                  )
                  AND (
                    m.id IS NULL
                    OR m.rules_version IS DISTINCT FROM %s
                    OR m.updated_at < j.updated_at
                    OR m.updated_at < c.updated_at
                  )
                ORDER BY j.priority DESC, j.updated_at DESC, c.profile_freshness DESC NULLS LAST, c.id
                LIMIT %s
                """,
                (tenant_id, RULES_VERSION, limit),
            )
            return [dict(row) for row in await cur.fetchall()]

    async def load_job(self, *, tenant_id: str, job_id: str) -> tuple[dict, list[dict]]:
        async with self.connection.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT id, division, profession, specialty, city, state, start_date,
                       normalized_payload, updated_at
                FROM job
                WHERE tenant_id=%s AND id=%s
                """,
                (tenant_id, job_id),
            )
            job = await cur.fetchone()
            if job is None:
                raise KeyError(job_id)

            await cur.execute(
                """
                SELECT requirement_type, canonical_key, value, is_hard_gate,
                       source_evidence, rules_version
                FROM job_requirement
                WHERE tenant_id=%s AND job_id=%s
                """,
                (tenant_id, job_id),
            )
            requirements = [dict(row) for row in await cur.fetchall()]
        return dict(job), requirements

    async def load_candidate(self, *, tenant_id: str, candidate_id: str) -> tuple[dict, list[dict], list[dict], dict | None, bool]:
        async with self.connection.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT id, profession, specialty, city, state, profile_freshness,
                       canonical_profile, updated_at
                FROM candidate
                WHERE tenant_id=%s AND id=%s
                """,
                (tenant_id, candidate_id),
            )
            candidate = await cur.fetchone()
            if candidate is None:
                raise KeyError(candidate_id)

            await cur.execute(
                """
                SELECT license_type, state, status, expires_at
                FROM candidate_license
                WHERE tenant_id=%s AND candidate_id=%s
                """,
                (tenant_id, candidate_id),
            )
            licenses = [dict(row) for row in await cur.fetchall()]

            await cur.execute(
                """
                SELECT certification_name, status, expires_at
                FROM candidate_certification
                WHERE tenant_id=%s AND candidate_id=%s
                """,
                (tenant_id, candidate_id),
            )
            certifications = [dict(row) for row in await cur.fetchall()]

            await cur.execute(
                """
                SELECT available_from, status, confirmed_at
                FROM candidate_availability
                WHERE tenant_id=%s AND candidate_id=%s
                ORDER BY confirmed_at DESC NULLS LAST, created_at DESC
                LIMIT 1
                """,
                (tenant_id, candidate_id),
            )
            availability = await cur.fetchone()

            await cur.execute(
                """
                SELECT EXISTS(
                  SELECT 1
                  FROM resume_version
                  WHERE tenant_id=%s AND candidate_id=%s
                    AND text_content IS NOT NULL
                    AND length(trim(text_content)) > 0
                )
                """,
                (tenant_id, candidate_id),
            )
            resume_available = bool((await cur.fetchone())[0])

            await cur.execute(
                """
                SELECT parsed_payload
                FROM resume_version
                WHERE tenant_id=%s AND candidate_id=%s AND is_primary=true
                ORDER BY resume_date DESC NULLS LAST, updated_at DESC
                LIMIT 1
                """,
                (tenant_id, candidate_id),
            )
            resume_row = await cur.fetchone()

        candidate_dict = dict(candidate)
        parsed_payload = (resume_row or {}).get("parsed_payload") if resume_row else None
        if isinstance(parsed_payload, dict):
            candidate_dict["resume_care_settings"] = [
                str(item.get("key"))
                for item in parsed_payload.get("care_settings", [])
                if isinstance(item, dict) and item.get("key")
            ]
            candidate_dict["resume_specialties"] = [
                str(item.get("key"))
                for item in parsed_payload.get("specialties", [])
                if isinstance(item, dict) and item.get("key")
            ]
            candidate_dict["resume_clinical_skills"] = [
                str(item.get("key"))
                for item in parsed_payload.get("clinical_skills", [])
                if isinstance(item, dict) and item.get("key")
            ]
            candidate_dict["documented_experience_years"] = _documented_experience_years(
                parsed_payload.get("experience_entries", [])
                if isinstance(parsed_payload.get("experience_entries", []), list)
                else []
            )

        return (
            candidate_dict,
            licenses,
            certifications,
            dict(availability) if availability else None,
            resume_available,
        )

    async def persist_result(
        self,
        *,
        tenant_id: str,
        result: MatchResult,
        rules_version: str = RULES_VERSION,
    ) -> None:
        if result.eligible:
            summary = (
                "; ".join(result.strengths[:3])
                if result.strengths
                else "Eligible match; recruiter review recommended."
            )
        else:
            summary = (
                "Excluded: " + "; ".join(result.gaps[:3])
                if result.gaps
                else "Excluded by a required hard gate."
            )

        explanation = {
            "eligible": result.eligible,
            "summary": summary,
            "gates": [gate.model_dump(mode="json") for gate in result.gates],
            "strengths": result.strengths,
            "gaps": result.gaps,
        }
        status = "shortlisted" if result.eligible else "excluded"

        async with self.connection.transaction():
            async with self.connection.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO match
                      (id, tenant_id, job_id, candidate_id, overall_score, status,
                       rules_version, explanation, created_at, updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,now(),now())
                    ON CONFLICT (tenant_id, job_id, candidate_id)
                    DO UPDATE SET
                      overall_score=EXCLUDED.overall_score,
                      status=EXCLUDED.status,
                      rules_version=EXCLUDED.rules_version,
                      explanation=EXCLUDED.explanation,
                      updated_at=now()
                    RETURNING id
                    """,
                    (
                        str(uuid4()),
                        tenant_id,
                        result.job_id,
                        result.candidate_id,
                        result.score,
                        status,
                        rules_version,
                        Jsonb(explanation),
                    ),
                )
                match_id = (await cur.fetchone())[0]

                await cur.execute(
                    "DELETE FROM match_score_component WHERE tenant_id=%s AND match_id=%s",
                    (tenant_id, match_id),
                )
                for component in result.components:
                    await cur.execute(
                        """
                        INSERT INTO match_score_component
                          (id, tenant_id, match_id, component_key, score, weight, evidence, created_at)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,now())
                        """,
                        (
                            str(uuid4()),
                            tenant_id,
                            match_id,
                            component.key,
                            component.score,
                            component.weight,
                            Jsonb({"reason": component.reason}),
                        ),
                    )

                await cur.execute(
                    """
                    DELETE FROM match_exclusion
                    WHERE tenant_id=%s AND job_id=%s AND candidate_id=%s
                      AND overridden=false
                    """,
                    (tenant_id, result.job_id, result.candidate_id),
                )
                for gate in result.gates:
                    if not gate.passed:
                        await cur.execute(
                            """
                            INSERT INTO match_exclusion
                              (id, tenant_id, job_id, candidate_id, reason_code,
                               reason_detail, overridden, created_at)
                            VALUES (%s,%s,%s,%s,%s,%s,false,now())
                            """,
                            (
                                str(uuid4()),
                                tenant_id,
                                result.job_id,
                                result.candidate_id,
                                gate.key,
                                gate.reason,
                            ),
                        )

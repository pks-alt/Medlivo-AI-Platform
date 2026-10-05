from __future__ import annotations

from datetime import date
from typing import Any

from psycopg.rows import dict_row

from app.db.database import connection
from app.schemas.recruiting import (
    CandidateMatch,
    CandidateProfile,
    DashboardSummary,
    JobDetail,
    JobListItem,
    MatchSignal,
)


class RecruitingRepository:
    async def dashboard(self) -> DashboardSummary:
        async with connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    SELECT
                      COUNT(*) FILTER (WHERE readiness_status = 'submission_ready') AS submission_ready,
                      COUNT(*) FILTER (WHERE status = 'interested') AS interested_replies
                    FROM submission
                    """
                )
                submission_row = await cur.fetchone()

                await cur.execute(
                    """
                    SELECT
                      COUNT(*) FILTER (WHERE status = 'at_risk') AS jobs_at_risk,
                      COUNT(*) FILTER (WHERE status IN ('matching','qualifying','needs_outreach')) AS active_matching_jobs
                    FROM job
                    """
                )
                job_row = await cur.fetchone()

                await cur.execute(
                    """
                    SELECT COUNT(*) AS qualified_today
                    FROM qualification
                    WHERE completed_at::date = CURRENT_DATE
                    """
                )
                qual_row = await cur.fetchone()

        return DashboardSummary(
            submission_ready=int((submission_row or {}).get("submission_ready") or 0),
            interested_replies=int((submission_row or {}).get("interested_replies") or 0),
            jobs_at_risk=int((job_row or {}).get("jobs_at_risk") or 0),
            active_matching_jobs=int((job_row or {}).get("active_matching_jobs") or 0),
            qualified_today=int((qual_row or {}).get("qualified_today") or 0),
        )

    async def jobs(self) -> list[JobListItem]:
        async with connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    SELECT
                      j.id::text,
                      COALESCE(jsr.source_id, j.id::text) AS source_job_id,
                      j.title,
                      COALESCE(j.division, '') AS division,
                      COALESCE(c.name, '') AS customer,
                      CONCAT_WS(', ', j.city, j.state) AS location,
                      j.status,
                      COUNT(m.id) FILTER (WHERE m.overall_score >= 80) AS strong_matches,
                      COUNT(s.id) FILTER (WHERE s.readiness_status = 'submission_ready') AS submission_ready,
                      j.start_date
                    FROM job j
                    LEFT JOIN customer c ON c.id = j.customer_id
                    LEFT JOIN job_source_record jsr ON jsr.job_id = j.id
                    LEFT JOIN match m ON m.job_id = j.id
                    LEFT JOIN submission s ON s.job_id = j.id
                    GROUP BY j.id, jsr.source_id, c.name
                    ORDER BY j.priority DESC, j.updated_at DESC
                    LIMIT 100
                    """
                )
                rows = await cur.fetchall()

        return [
            JobListItem(
                id=row["id"],
                source_job_id=row["source_job_id"],
                title=row["title"],
                division=row["division"],
                customer=row["customer"],
                location=row["location"] or "",
                status=row["status"],
                strong_matches=int(row["strong_matches"] or 0),
                submission_ready=int(row["submission_ready"] or 0),
                start_date=row["start_date"],
            )
            for row in rows
        ]

    async def job_detail(self, job_id: str) -> JobDetail:
        async with connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    SELECT
                      j.id::text,
                      COALESCE(jsr.source_id, j.id::text) AS source_job_id,
                      j.title,
                      COALESCE(j.division, '') AS division,
                      COALESCE(c.name, '') AS customer,
                      CONCAT_WS(', ', j.city, j.state) AS location,
                      j.status,
                      COALESCE(j.start_date::text, 'TBD') AS start_timing,
                      COALESCE(u.display_name, 'Unassigned') AS recruiter_owner
                    FROM job j
                    LEFT JOIN customer c ON c.id = j.customer_id
                    LEFT JOIN job_source_record jsr ON jsr.job_id = j.id
                    LEFT JOIN app_user u ON u.id = j.owner_user_id
                    WHERE j.id = %s
                    LIMIT 1
                    """,
                    (job_id,),
                )
                row = await cur.fetchone()
                if row is None:
                    raise KeyError(job_id)

                await cur.execute(
                    """
                    SELECT requirement_type, canonical_key, value, is_hard_gate
                    FROM job_requirement
                    WHERE job_id = %s
                    ORDER BY is_hard_gate DESC, canonical_key
                    """,
                    (job_id,),
                )
                req_rows = await cur.fetchall()

                await cur.execute(
                    """
                    SELECT
                      m.id::text AS match_id,
                      ca.id::text AS candidate_id,
                      COALESCE(ca.canonical_name, 'Candidate') AS name,
                      COALESCE(ca.profession, '') AS profession,
                      COALESCE(ca.specialty, '') AS specialty,
                      CONCAT_WS(', ', ca.city, ca.state) AS location,
                      m.overall_score,
                      m.status AS readiness_status,
                      m.explanation
                    FROM match m
                    JOIN candidate ca ON ca.id = m.candidate_id
                    WHERE m.job_id = %s
                    ORDER BY m.overall_score DESC
                    LIMIT 50
                    """,
                    (job_id,),
                )
                match_rows = await cur.fetchall()

        requirements: dict[str, str] = {}
        hard_gates: list[str] = []
        for req in req_rows:
            raw_value: Any = req["value"]
            display_value = str(raw_value.get("display") if isinstance(raw_value, dict) else raw_value)
            requirements[req["canonical_key"]] = display_value
            if req["is_hard_gate"]:
                hard_gates.append(req["canonical_key"].replace("_", " ").title())

        matches = [
            CandidateMatch(
                id=r["candidate_id"],
                name=r["name"],
                profession=r["profession"],
                specialty=r["specialty"],
                location=r["location"] or "",
                overall_score=float(r["overall_score"]),
                readiness_status=r["readiness_status"],
                signals=[],
                why_matched=(r["explanation"] or {}).get("summary", "Strong candidate match."),
            )
            for r in match_rows
        ]

        return JobDetail(
            id=row["id"],
            source_job_id=row["source_job_id"],
            title=row["title"],
            division=row["division"],
            customer=row["customer"],
            location=row["location"] or "",
            status=row["status"],
            start_timing=row["start_timing"],
            recruiter_owner=row["recruiter_owner"],
            requirements=requirements,
            hard_gates=hard_gates,
            candidate_matches=matches,
        )

    async def candidate_profile(self, candidate_id: str) -> CandidateProfile:
        async with connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    SELECT
                      ca.id::text,
                      COALESCE(ca.canonical_name, 'Candidate') AS name,
                      COALESCE(ca.profession, '') AS profession,
                      COALESCE(ca.specialty, '') AS specialty,
                      CONCAT_WS(', ', ca.city, ca.state) AS location,
                      COALESCE(cp.travel_local, 'Unknown') AS travel_preference,
                      COALESCE(av.available_from::text, 'Unknown') AS availability,
                      CASE
                        WHEN EXISTS (
                          SELECT 1 FROM candidate_license cl
                          WHERE cl.candidate_id = ca.id
                            AND cl.verification_status = 'verified'
                            AND (cl.expires_at IS NULL OR cl.expires_at >= CURRENT_DATE)
                        ) THEN 'Ready'
                        ELSE 'Needs verification'
                      END AS license_readiness
                    FROM candidate ca
                    LEFT JOIN candidate_preference cp ON cp.candidate_id = ca.id
                    LEFT JOIN LATERAL (
                      SELECT available_from
                      FROM candidate_availability
                      WHERE candidate_id = ca.id
                      ORDER BY confirmed_at DESC NULLS LAST, created_at DESC
                      LIMIT 1
                    ) av ON true
                    WHERE ca.id = %s
                    LIMIT 1
                    """,
                    (candidate_id,),
                )
                row = await cur.fetchone()
                if row is None:
                    raise KeyError(candidate_id)

                await cur.execute(
                    """
                    SELECT overall_score
                    FROM match
                    WHERE candidate_id = %s
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """,
                    (candidate_id,),
                )
                match_row = await cur.fetchone()

                await cur.execute(
                    """
                    SELECT fact_key, fact_value, source_type
                    FROM candidate_evidence
                    WHERE candidate_id = %s
                    ORDER BY is_verified DESC, confidence DESC NULLS LAST
                    LIMIT 12
                    """,
                    (candidate_id,),
                )
                evidence_rows = await cur.fetchall()

        evidence = [
            {
                "type": e["fact_key"].replace("_", " ").title(),
                "value": str(e["fact_value"].get("display") if isinstance(e["fact_value"], dict) else e["fact_value"]),
                "source": e["source_type"],
            }
            for e in evidence_rows
        ]

        score = float((match_row or {}).get("overall_score") or 0)

        return CandidateProfile(
            id=row["id"],
            name=row["name"],
            profession=row["profession"],
            specialty=row["specialty"],
            location=row["location"] or "",
            travel_preference=row["travel_preference"],
            availability=row["availability"],
            license_readiness=row["license_readiness"],
            overall_match=score,
            clinical_fit=score,
            engagement="Unknown",
            owner="Unassigned",
            evidence=evidence,
            readiness_status="near_ready" if score >= 80 else "review",
        )

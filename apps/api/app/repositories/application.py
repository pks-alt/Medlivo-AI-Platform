from __future__ import annotations

from uuid import UUID, uuid4

from psycopg.rows import dict_row

from app.db.database import connection
from app.schemas.application import CareerApplicationInput, CareerApplicationReceipt


class CareerApplicationRepository:
    async def create(self, value: CareerApplicationInput) -> CareerApplicationReceipt:
        async with connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(
                    """
                    SELECT tenant_id
                    FROM ws_job_publication
                    WHERE id = %(publication_id)s
                      AND website_status = 'approved'
                      AND readiness = 'ready_to_publish'
                    """,
                    {"publication_id": value.job_id},
                )
                publication = await cursor.fetchone()
                if publication is None:
                    raise KeyError(value.job_id)
                tenant_id = publication["tenant_id"]

                await cursor.execute(
                    """
                    SELECT id
                    FROM candidate
                    WHERE tenant_id = %(tenant_id)s
                      AND lower(primary_email) = lower(%(email)s)
                    ORDER BY updated_at DESC
                    LIMIT 2
                    """,
                    {"tenant_id": tenant_id, "email": value.email},
                )
                candidates = await cursor.fetchall()

                candidate_id = candidates[0]["id"] if len(candidates) == 1 else None
                candidate_status = "matched_existing_candidate" if candidate_id else "needs_candidate_create"
                ownership_status = "pending_lookup"
                assigned_recruiter = None

                if len(candidates) > 1:
                    candidate_status = "matched_existing_candidate"
                    ownership_status = "conflict"
                elif candidate_id:
                    await cursor.execute(
                        """
                        SELECT DISTINCT owner_user_id
                        FROM ws_case
                        WHERE tenant_id = %(tenant_id)s
                          AND candidate_id = %(candidate_id)s
                        LIMIT 3
                        """,
                        {"tenant_id": tenant_id, "candidate_id": candidate_id},
                    )
                    owners = [row["owner_user_id"] for row in await cursor.fetchall()]
                    if len(owners) == 1:
                        ownership_status = "owned"
                        assigned_recruiter = owners[0]
                    elif len(owners) > 1:
                        ownership_status = "conflict"
                    else:
                        ownership_status = "unowned"
                else:
                    ownership_status = "unowned"

                application_id = uuid4()
                await cursor.execute(
                    """
                    INSERT INTO career_application(
                      id, tenant_id, publication_id, candidate_id,
                      applicant_name, email, phone, profession, specialty,
                      preferred_location, availability, resume_url,
                      consent_to_contact, source, status, ownership_status,
                      assigned_recruiter_user_id, created_at, updated_at
                    ) VALUES (
                      %(id)s, %(tenant_id)s, %(publication_id)s, %(candidate_id)s,
                      %(applicant_name)s, %(email)s, %(phone)s, %(profession)s, %(specialty)s,
                      %(preferred_location)s, %(availability)s, %(resume_url)s,
                      true, 'medlivo_website', %(status)s, %(ownership_status)s,
                      %(assigned_recruiter_user_id)s, now(), now()
                    )
                    """,
                    {
                        "id": application_id,
                        "tenant_id": tenant_id,
                        "publication_id": value.job_id,
                        "candidate_id": candidate_id,
                        "applicant_name": value.name,
                        "email": value.email,
                        "phone": value.phone,
                        "profession": value.profession,
                        "specialty": value.specialty,
                        "preferred_location": value.preferred_location,
                        "availability": value.availability,
                        "resume_url": value.resume_url,
                        "status": candidate_status,
                        "ownership_status": ownership_status,
                        "assigned_recruiter_user_id": assigned_recruiter,
                    },
                )
                await conn.commit()

        return CareerApplicationReceipt(
            application_id=application_id,
            job_id=value.job_id,
            status="received",
            candidate_status=candidate_status,
            ownership_status=ownership_status,
            recruiter_assigned=assigned_recruiter is not None,
        )

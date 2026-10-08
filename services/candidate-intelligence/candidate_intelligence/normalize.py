from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable

from .models import (
    CandidateEvidence,
    CandidateIntelligence,
    CertificationIntelligence,
    JobDivaCandidateBundle,
    LicenseIntelligence,
    MatchingReadiness,
    ResumeIntelligence,
)


def _first(payload: dict[str, Any], names: Iterable[str]):
    for name in names:
        value = payload.get(name)
        if value not in (None, ""):
            return value
    return None


def _text(value):
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _date(value):
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def _datetime(value):
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    for parser in (
        lambda: datetime.fromisoformat(text.replace("Z", "+00:00")),
        lambda: datetime.strptime(text, "%m/%d/%Y %H:%M:%S"),
        lambda: datetime.strptime(text, "%m/%d/%Y"),
    ):
        try:
            return parser()
        except ValueError:
            pass
    return None


def _profile(bundle: JobDivaCandidateBundle) -> dict[str, Any]:
    return dict(bundle.profile_records[0]) if bundle.profile_records else {}


def _name(profile):
    full = _text(_first(profile, ("fullName", "FULLNAME", "name", "NAME", "candidateName", "CANDIDATENAME")))
    if full:
        return full
    first = _text(_first(profile, ("firstName", "FIRSTNAME", "first_name")))
    last = _text(_first(profile, ("lastName", "LASTNAME", "last_name")))
    value = " ".join(part for part in (first, last) if part)
    return value or None


def _resume_text(records):
    for record in records:
        text = _text(_first(record, ("text", "TEXT", "resumeText", "RESUMETEXT", "content", "CONTENT")))
        if text:
            return text
    return None


def normalize_candidate(bundle: JobDivaCandidateBundle) -> CandidateIntelligence:
    """Build AI-ready candidate facts without replacing JobDiva as the ATS.

    Only explicit JobDiva values are normalized. Raw profile data is preserved
    as evidence; missing healthcare facts stay missing rather than being guessed.
    """
    profile = _profile(bundle)
    full_name = _name(profile)
    email = _text(_first(profile, ("email", "EMAIL", "emailAddress", "EMAILADDRESS")))
    phone = _text(_first(profile, ("phone", "PHONE", "mobilePhone", "MOBILEPHONE", "cellPhone", "CELLPHONE")))
    profession = _text(_first(profile, ("profession", "PROFESSION", "candidateType", "CANDIDATETYPE", "jobType", "JOBTYPE")))
    specialty = _text(_first(profile, ("specialty", "SPECIALTY", "primarySpecialty", "PRIMARYSPECIALTY")))
    city = _text(_first(profile, ("city", "CITY")))
    state = _text(_first(profile, ("state", "STATE")))

    evidence: list[CandidateEvidence] = []
    for key, value in (
        ("full_name", full_name), ("email", email), ("phone", phone),
        ("profession", profession), ("specialty", specialty),
        ("city", city), ("state", state),
    ):
        if value is not None:
            evidence.append(CandidateEvidence(
                fact_key=key,
                value=value,
                source_type="jobdiva_profile",
                source_reference=f"candidate:{bundle.candidate_id}",
            ))

    licenses: list[LicenseIntelligence] = []
    for row in bundle.license_records:
        license_type = _text(_first(row, ("licenseType", "LICENSETYPE", "type", "TYPE", "license", "LICENSE")))
        if not license_type:
            continue
        ref = _text(_first(row, ("licenseId", "LICENSEID", "id", "ID")))
        item = LicenseIntelligence(
            license_type=license_type,
            state=_text(_first(row, ("state", "STATE", "licenseState", "LICENSESTATE"))),
            license_number=_text(_first(row, ("licenseNumber", "LICENSENUMBER", "number", "NUMBER"))),
            status=_text(_first(row, ("status", "STATUS"))),
            expires_at=_date(_first(row, ("expirationDate", "EXPIRATIONDATE", "expiresAt", "EXPIRESAT"))),
            source_reference=f"license:{ref}" if ref else f"candidate:{bundle.candidate_id}",
        )
        licenses.append(item)
        evidence.append(CandidateEvidence(
            fact_key="license",
            value=item.model_dump(mode="json"),
            source_type="jobdiva_license",
            source_reference=item.source_reference,
        ))

    certifications: list[CertificationIntelligence] = []
    for row in bundle.certification_records:
        name = _text(_first(row, ("certificationName", "CERTIFICATIONNAME", "name", "NAME", "certification", "CERTIFICATION")))
        if not name:
            continue
        ref = _text(_first(row, ("certificationId", "CERTIFICATIONID", "id", "ID")))
        item = CertificationIntelligence(
            name=name,
            status=_text(_first(row, ("status", "STATUS"))),
            expires_at=_date(_first(row, ("expirationDate", "EXPIRATIONDATE", "expiresAt", "EXPIRESAT"))),
            source_reference=f"certification:{ref}" if ref else f"candidate:{bundle.candidate_id}",
        )
        certifications.append(item)
        evidence.append(CandidateEvidence(
            fact_key="certification",
            value=item.model_dump(mode="json"),
            source_type="jobdiva_certification",
            source_reference=item.source_reference,
        ))

    resumes: list[ResumeIntelligence] = []
    for row in bundle.resume_records:
        resume_id = _text(_first(row, ("resumeId", "RESUMEID", "id", "ID")))
        if not resume_id:
            continue
        texts = bundle.resume_text_records.get(resume_id, [])
        item = ResumeIntelligence(
            source_resume_id=resume_id,
            resume_date=_datetime(_first(row, ("resumeDate", "RESUMEDATE", "date", "DATE", "createdAt", "CREATEDAT"))),
            text=_resume_text(texts),
            source_reference=f"resume:{resume_id}",
        )
        resumes.append(item)
        evidence.append(CandidateEvidence(
            fact_key="resume",
            value={"source_resume_id": resume_id, "resume_date": item.resume_date.isoformat() if item.resume_date else None},
            source_type="jobdiva_resume",
            source_reference=item.source_reference,
        ))

    resumes.sort(key=lambda item: item.resume_date or datetime.min, reverse=True)
    primary_resume_id = resumes[0].source_resume_id if resumes else None

    missing: list[str] = []
    if not full_name:
        missing.append("full_name")
    if not (email or phone):
        missing.append("contact")
    if not profession:
        missing.append("profession")
    if not resumes:
        missing.append("resume")

    readiness_points = 0
    readiness_points += 20 if full_name else 0
    readiness_points += 20 if (email or phone) else 0
    readiness_points += 20 if profession else 0
    readiness_points += 20 if (licenses or certifications) else 0
    readiness_points += 20 if resumes and any(r.text for r in resumes) else 0

    readiness = MatchingReadiness(
        score=readiness_points,
        identity_complete=bool(full_name),
        contact_complete=bool(email or phone),
        profession_complete=bool(profession),
        credential_signal=bool(licenses or certifications),
        resume_available=bool(resumes and any(r.text for r in resumes)),
        missing_fields=missing,
    )

    return CandidateIntelligence(
        source_candidate_id=bundle.candidate_id,
        source_updated_at=bundle.source_updated_at,
        full_name=full_name,
        email=email,
        phone=phone,
        profession=profession,
        specialty=specialty,
        city=city,
        state=state,
        licenses=licenses,
        certifications=certifications,
        resumes=resumes,
        primary_resume_id=primary_resume_id,
        matching_readiness=readiness,
        evidence=evidence,
        source_profile=profile,
    )

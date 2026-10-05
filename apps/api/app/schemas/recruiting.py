from datetime import date
from pydantic import BaseModel


class DashboardSummary(BaseModel):
    submission_ready: int
    interested_replies: int
    jobs_at_risk: int
    active_matching_jobs: int
    qualified_today: int


class JobListItem(BaseModel):
    id: str
    source_job_id: str
    title: str
    division: str
    customer: str
    location: str
    status: str
    strong_matches: int
    submission_ready: int
    start_date: date | None = None


class MatchSignal(BaseModel):
    key: str
    label: str
    status: str
    value: str


class CandidateMatch(BaseModel):
    id: str
    name: str
    profession: str
    specialty: str
    location: str
    overall_score: float
    readiness_status: str
    signals: list[MatchSignal]
    why_matched: str


class JobDetail(BaseModel):
    id: str
    source_job_id: str
    title: str
    division: str
    customer: str
    location: str
    status: str
    start_timing: str
    recruiter_owner: str
    requirements: dict[str, str]
    hard_gates: list[str]
    candidate_matches: list[CandidateMatch]


class CandidateProfile(BaseModel):
    id: str
    name: str
    profession: str
    specialty: str
    location: str
    travel_preference: str
    availability: str
    license_readiness: str
    overall_match: float
    clinical_fit: float
    engagement: str
    owner: str
    evidence: list[dict[str, str]]
    readiness_status: str

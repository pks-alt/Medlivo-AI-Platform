from datetime import datetime, date
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, hide_input_in_errors=True)


class NoteInput(StrictInput):
    body: str = Field(min_length=1, max_length=4000)


class TaskInput(StrictInput):
    title: str = Field(min_length=1, max_length=250)
    due_at: datetime

    @field_validator("due_at")
    @classmethod
    def require_zone(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("A timezone-aware deadline is required")
        return value


class TaskUpdate(StrictInput):
    status: Literal["open", "done"]
    expected_version: int = Field(ge=1)


class Reassignment(StrictInput):
    owner_user_id: UUID
    reason: str = Field(min_length=5, max_length=500)
    expected_version: int = Field(ge=1)


class AdminUserInput(StrictInput):
    email: str = Field(min_length=6, max_length=320)
    display_name: str = Field(min_length=1, max_length=200)
    role: Literal["admin", "manager", "recruiter"]
    team_id: UUID | None = None
    is_active: bool = True

    @field_validator("email")
    @classmethod
    def require_medlivo_email(cls, value):
        value = value.lower()
        if not value.endswith("@medlivo.com") or any(ch.isspace() for ch in value):
            raise ValueError("Use an approved Medlivo email address")
        return value


class AdminUserUpdate(StrictInput):
    display_name: str = Field(min_length=1, max_length=200)
    role: Literal["admin", "manager", "recruiter"]
    team_id: UUID | None = None
    is_active: bool


class JobIntakeBatchInput(StrictInput):
    customer_name: str = Field(min_length=1, max_length=200)
    division: Literal["Rehabilitation", "Nursing & Allied", "Locum Tenens"]
    source_filename: str = Field(min_length=1, max_length=255)
    team_id: UUID | None = None
    mapping: dict[str, str] = Field(default_factory=dict)


class CustomerJobMappingInput(StrictInput):
    customer_name: str = Field(min_length=1, max_length=200)
    division: Literal["Rehabilitation", "Nursing & Allied", "Locum Tenens"]
    mapping: dict[str, str]


class WeeklyGoalInput(StrictInput):
    week_start: date
    submissions_target: int = Field(ge=0, le=1000)
    interviews_target: int = Field(ge=0, le=1000)
    closures_target: int = Field(ge=0, le=1000)
    priority_jobs_target: int = Field(default=0, ge=0, le=1000)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("week_start")
    @classmethod
    def require_monday(cls, value):
        if value.weekday() != 0:
            raise ValueError("week_start must be a Monday")
        return value


class JobIntakeRowsInput(StrictInput):
    rows: list[dict[str, str | int | float | bool | None]] = Field(min_length=1, max_length=500)
    mapping: dict[str, str] | None = None


class JobPublicationDraftInput(StrictInput):
    team_id: UUID | None = None
    job_id: UUID | None = None
    intake_item_id: UUID | None = None
    source_snapshot: dict
    enhanced_snapshot: dict
    quality_score: dict
    readiness: Literal["not_ready", "manager_review", "ready_for_recruiting", "ready_to_publish"]

    @field_validator("intake_item_id")
    @classmethod
    def require_one_source(cls, value, info):
        job_id = info.data.get("job_id")
        if (job_id is None) == (value is None):
            raise ValueError("Provide exactly one of job_id or intake_item_id")
        return value


class JobPublicationDecision(StrictInput):
    target: Literal["recruiting", "website"]
    decision: Literal["approved", "rejected"]
    reason: str | None = Field(default=None, max_length=1000)
    expected_version: int = Field(ge=1)

    @field_validator("reason")
    @classmethod
    def rejection_needs_reason(cls, value, info):
        if info.data.get("decision") == "rejected" and not value:
            raise ValueError("A rejection reason is required")
        return value


class MatchFeedbackInput(StrictInput):
    feedback_code: Literal["strong_match", "good_match", "weak_match", "not_a_match"]
    reason_code: Literal[
        "license", "certification", "specialty", "care_setting", "experience",
        "availability", "location", "compensation", "other"
    ] | None = None
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def negative_feedback_needs_reason(self):
        if self.feedback_code in {"weak_match", "not_a_match"} and self.reason_code is None:
            raise ValueError("A reason is required for weak or not-a-match feedback")
        return self


class JobOperationalUpdate(StrictInput):
    client_priority: Literal["high", "normal", "low"] = "normal"
    job_priority: Literal["hot", "priority", "standard", "hold"] = "standard"
    priority_reason: str | None = Field(default=None, max_length=1000)
    manager_note: str | None = Field(default=None, max_length=2000)
    next_action: str | None = Field(default=None, max_length=500)
    due_at: datetime | None = None
    operational_status: Literal["active", "hold", "closed"] = "active"
    expected_version: int = Field(ge=0)

    @field_validator("due_at")
    @classmethod
    def operational_due_requires_zone(cls, value):
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("A timezone-aware deadline is required")
        return value


class JobAssignmentInput(StrictInput):
    recruiter_user_id: UUID | None = None
    team_id: UUID
    reason: str = Field(min_length=5, max_length=1000)
    expected_version: int = Field(ge=0)


class JobIntakeItemDecision(StrictInput):
    decision: Literal["approved", "rejected"]
    final_approved_values: dict | None = None
    bill_rate_state: Literal["confirmed", "suggested", "unknown"] = "unknown"
    recruiting_readiness: Literal["not_ready", "review", "ready"] = "review"
    commercial_readiness: Literal["not_ready", "review", "ready"] = "review"
    reason: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def intake_rejection_requires_reason(self):
        if self.decision == "rejected" and not self.reason:
            raise ValueError("A rejection reason is required")
        return self


class ApprovalDecisionInput(StrictInput):
    decision: Literal["approved", "rejected", "cancelled"]
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def approval_rejection_requires_notes(self):
        if self.decision == "rejected" and not self.notes:
            raise ValueError("A rejection reason is required")
        return self


class MarginCalculationInput(StrictInput):
    job_id: UUID
    candidate_id: UUID
    recruiter_user_id: UUID
    profile: Literal[
        "nursing_allied_ca_w2",
        "nursing_allied_national_w2",
        "rehabilitation_ca_w2",
        "rehabilitation_national_w2",
        "locums_ca_w2",
        "locums_national_1099",
    ]
    division: Literal["nursing_allied", "rehabilitation", "locum_tenens"]
    customer_type: Literal["direct", "msp_vms"]
    contract_type: Literal["new_contract", "extension"] = "new_contract"
    candidate_source: Literal["internal_database", "vivian", "referral", "job_board", "other"] = "internal_database"
    assignment_weeks_equivalent: float = Field(gt=0)
    gross_client_billing_per_week: float = Field(ge=0)
    taxable_wages_per_week: float = Field(default=0, ge=0)
    contractor_compensation_per_week: float = Field(default=0, ge=0)
    recurring_non_taxable_cost_per_week: float = Field(default=0, ge=0)
    other_recurring_cost_per_week: float = Field(default=0, ge=0)
    other_one_time_cost_assignment: float = Field(default=0, ge=0)
    employee_benefits_enabled: bool = False
    actual_worked_hours_per_week: float | None = Field(default=None, gt=0)
    shifts_per_week: float | None = Field(default=None, gt=0)
    commissionable_net_profit_override: float | None = None


class MarginDiscussionInput(StrictInput):
    participant_user_id: UUID | None = None
    participant_role: Literal["delivery_manager", "executive", "designated_leadership"]
    discussion_type: Literal["rate_guidance", "commercial_exception", "leadership_exception"]
    notes: str = Field(min_length=3, max_length=2000)


class MarginFinalizeInput(StrictInput):
    expected_version: int = Field(ge=1)


class CostAssumptionSetInput(StrictInput):
    profile: Literal[
        "nursing_allied_ca_w2",
        "nursing_allied_national_w2",
        "rehabilitation_ca_w2",
        "rehabilitation_national_w2",
        "locums_ca_w2",
        "locums_national_1099",
    ]
    version: str = Field(min_length=1, max_length=80)
    assumption_payload: dict
    effective_from: datetime

    @field_validator("effective_from")
    @classmethod
    def assumption_effective_from_requires_zone(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("A timezone-aware effective date is required")
        return value


class CustomerEconomicRulePayload(StrictInput):
    msp_fee_rate: float | None = Field(default=None, ge=0, le=1)
    professional_liability_rate: float | None = Field(default=None, ge=0, le=1)
    factoring_rate: float | None = Field(default=None, ge=0, le=1)
    overhead_rate: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def at_least_one_customer_rule(self):
        if all(
            getattr(self, field) is None
            for field in (
                "msp_fee_rate",
                "professional_liability_rate",
                "factoring_rate",
                "overhead_rate",
            )
        ):
            raise ValueError("At least one customer economic override is required")
        return self


class CustomerEconomicRuleInput(StrictInput):
    customer_id: UUID
    calculation_profile: Literal[
        "nursing_allied_ca_w2",
        "nursing_allied_national_w2",
        "rehabilitation_ca_w2",
        "rehabilitation_national_w2",
        "locums_ca_w2",
        "locums_national_1099",
    ]
    version: str = Field(min_length=1, max_length=80)
    rule_payload: CustomerEconomicRulePayload
    effective_from: datetime

    @field_validator("effective_from")
    @classmethod
    def customer_rule_effective_from_requires_zone(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("A timezone-aware effective date is required")
        return value


class W2PayPackageSnapshotInput(StrictInput):
    job_id: UUID
    candidate_id: UUID
    recruiter_user_id: UUID
    customer_type: Literal["direct", "msp_vms"]
    contract_type: Literal["new_contract", "extension"] = "new_contract"
    candidate_source: Literal["internal_database", "vivian", "referral", "job_board", "other"] = "internal_database"

    contract_weeks: float = Field(gt=0)
    shift_length_hours: float = Field(gt=0)
    shifts_per_week: float = Field(gt=0)

    regular_client_bill_rate: float = Field(gt=0)
    ot_client_bill_rate: float | None = Field(default=None, ge=0)
    double_time_client_bill_rate: float | None = Field(default=None, ge=0)
    holiday_client_bill_rate: float | None = Field(default=None, ge=0)
    on_call_client_bill_rate: float | None = Field(default=None, ge=0)
    callback_client_bill_rate: float | None = Field(default=None, ge=0)

    taxable_base_hourly_pay: float = Field(gt=0)
    housing_stipend_per_hour: float = Field(default=0, ge=0)
    meals_incidentals_stipend_per_hour: float = Field(default=0, ge=0)
    clinician_holiday_pay_rate: float | None = Field(default=None, ge=0)
    clinician_on_call_pay_rate: float = Field(default=0, ge=0)
    callback_pay_rate: float | None = Field(default=None, ge=0)

    additional_expected_ot_hours: float = Field(default=0, ge=0)
    holiday_hours: float = Field(default=0, ge=0)
    on_call_hours: float = Field(default=0, ge=0)
    callback_hours: float = Field(default=0, ge=0)
    orientation_hours: float = Field(default=0, ge=0)
    national_double_time_hours: float = Field(default=0, ge=0)
    national_ot_rule: Literal["standard_ot", "48_regular_no_ot"] = "standard_ot"

    employee_benefits_enabled: bool = False

    assignment_stipend: float = Field(default=0, ge=0)
    sign_on_bonus: float = Field(default=0, ge=0)
    completion_bonus: float = Field(default=0, ge=0)
    travel_reimbursement: float = Field(default=0, ge=0)
    other_reimbursement: float = Field(default=0, ge=0)

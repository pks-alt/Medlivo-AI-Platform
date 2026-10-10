from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


Profile = Literal[
    "nursing_rehab_ca_w2",
    "nursing_rehab_national_w2",
    "locums_ca_w2",
    "locums_national_1099",
]

Division = Literal["nursing_allied", "rehabilitation", "locum_tenens"]
CustomerType = Literal["direct", "msp_vms"]
ContractType = Literal["new_contract", "extension"]
CandidateSource = Literal["internal_database", "vivian", "referral", "job_board", "other"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ApprovalBands(StrictModel):
    recruiter_min_margin: Decimal | None = Field(default=None, ge=Decimal("-1"), le=Decimal("1"))
    manager_min_margin: Decimal | None = Field(default=None, ge=Decimal("-1"), le=Decimal("1"))
    legacy_workbook_approval_floor: Decimal | None = Field(
        default=None, ge=Decimal("-1"), le=Decimal("1")
    )


class CostAssumptionSet(StrictModel):
    profile: Profile
    version: str = Field(min_length=1, max_length=80)

    payroll_tax_rate: Decimal = Field(default=Decimal("0"), ge=0, le=1)
    workers_comp_rate: Decimal = Field(default=Decimal("0"), ge=0, le=1)
    professional_liability_rate: Decimal = Field(default=Decimal("0"), ge=0, le=1)
    factoring_rate: Decimal = Field(default=Decimal("0"), ge=0, le=1)
    overhead_rate: Decimal = Field(default=Decimal("0"), ge=0, le=1)
    default_msp_fee_rate: Decimal = Field(default=Decimal("0"), ge=0, le=1)
    sick_leave_reserve_hours_per_hour: Decimal = Field(default=Decimal("0"), ge=0, le=1)

    medical_monthly_premium: Decimal = Field(default=Decimal("0"), ge=0)
    dental_monthly_premium: Decimal = Field(default=Decimal("0"), ge=0)
    vision_monthly_premium: Decimal = Field(default=Decimal("0"), ge=0)
    employer_benefit_contribution: Decimal = Field(default=Decimal("0"), ge=0, le=1)

    nursing_allied_onboarding_cost: Decimal = Field(default=Decimal("0"), ge=0)
    rehabilitation_onboarding_cost: Decimal = Field(default=Decimal("0"), ge=0)
    locums_onboarding_cost: Decimal = Field(default=Decimal("0"), ge=0)

    vivian_sourcing_cost: Decimal = Field(default=Decimal("0"), ge=0)
    referral_sourcing_cost: Decimal = Field(default=Decimal("0"), ge=0)

    commission_rate: Decimal = Field(default=Decimal("0.03"), ge=0, le=1)
    approval_bands: ApprovalBands = Field(default_factory=ApprovalBands)


class MarginInput(StrictModel):
    profile: Profile
    division: Division
    customer_type: CustomerType
    contract_type: ContractType = "new_contract"
    candidate_source: CandidateSource = "internal_database"

    assignment_weeks_equivalent: Decimal = Field(gt=0)
    gross_client_billing_per_week: Decimal = Field(ge=0)

    taxable_wages_per_week: Decimal = Field(default=Decimal("0"), ge=0)
    contractor_compensation_per_week: Decimal = Field(default=Decimal("0"), ge=0)
    recurring_non_taxable_cost_per_week: Decimal = Field(default=Decimal("0"), ge=0)
    other_recurring_cost_per_week: Decimal = Field(default=Decimal("0"), ge=0)
    other_one_time_cost_assignment: Decimal = Field(default=Decimal("0"), ge=0)

    employee_benefits_enabled: bool = False
    msp_fee_rate_override: Decimal | None = Field(default=None, ge=0, le=1)

    actual_worked_hours_per_week: Decimal | None = Field(default=None, gt=0)
    shifts_per_week: Decimal | None = Field(default=None, gt=0)
    commissionable_net_profit_override: Decimal | None = None

    @model_validator(mode="after")
    def validate_profile_alignment(self):
        if self.profile.startswith("nursing_rehab_") and self.division == "locum_tenens":
            raise ValueError("Nursing/Rehab profiles cannot be used for Locum Tenens")
        if self.profile.startswith("locums_") and self.division != "locum_tenens":
            raise ValueError("Locums profiles require the Locum Tenens division")
        if self.profile == "locums_national_1099":
            if self.taxable_wages_per_week != 0:
                raise ValueError("1099 profile cannot include W-2 taxable wages")
        else:
            if self.contractor_compensation_per_week != 0:
                raise ValueError("W-2 profiles cannot include 1099 contractor compensation")
        return self


class CostComponent(StrictModel):
    key: str
    label: str
    per_week: Decimal
    assignment_total: Decimal
    category: Literal["revenue_reduction", "recurring_cost", "one_time_cost"]


class MarginResult(StrictModel):
    profile: Profile
    assumption_version: str
    effective_msp_fee_rate: Decimal

    gross_client_billing_per_week: Decimal
    msp_vms_fee_per_week: Decimal
    net_client_billing_per_week: Decimal

    recurring_cost_per_week: Decimal
    one_time_cost_assignment: Decimal
    allocated_one_time_cost_per_week: Decimal
    total_cost_per_week: Decimal

    gross_margin_per_week: Decimal
    gross_margin_assignment: Decimal
    gross_margin_percent: Decimal

    gross_margin_per_actual_hour: Decimal | None = None
    gross_margin_per_shift: Decimal | None = None

    commissionable_net_profit: Decimal
    projected_recruiter_commission: Decimal
    approval_status: Literal[
        "healthy",
        "manager_approval_required",
        "executive_approval_required",
        "negative_gm",
        "policy_unconfigured",
    ]

    cost_components: list[CostComponent]

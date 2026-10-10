from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Literal

from pydantic import Field, model_validator

from .models import CostAssumptionSet, MarginInput, StrictModel


ZERO = Decimal("0")


def _q(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


class W2PayPackageInput(StrictModel):
    profile: Literal["nursing_rehab_ca_w2", "nursing_rehab_national_w2"]
    division: Literal["nursing_allied", "rehabilitation"]
    customer_type: Literal["direct", "msp_vms"]
    contract_type: Literal["new_contract", "extension"] = "new_contract"
    candidate_source: Literal["internal_database", "vivian", "referral", "job_board", "other"] = "internal_database"

    contract_weeks: Decimal = Field(gt=0)
    shift_length_hours: Decimal = Field(gt=0)
    shifts_per_week: Decimal = Field(gt=0)

    regular_client_bill_rate: Decimal = Field(gt=0)
    ot_client_bill_rate: Decimal | None = Field(default=None, ge=0)
    double_time_client_bill_rate: Decimal | None = Field(default=None, ge=0)
    holiday_client_bill_rate: Decimal | None = Field(default=None, ge=0)
    on_call_client_bill_rate: Decimal | None = Field(default=None, ge=0)
    callback_client_bill_rate: Decimal | None = Field(default=None, ge=0)

    taxable_base_hourly_pay: Decimal = Field(gt=0)
    housing_stipend_per_hour: Decimal = Field(default=ZERO, ge=0)
    meals_incidentals_stipend_per_hour: Decimal = Field(default=ZERO, ge=0)
    clinician_holiday_pay_rate: Decimal | None = Field(default=None, ge=0)
    clinician_on_call_pay_rate: Decimal = Field(default=ZERO, ge=0)
    callback_pay_rate: Decimal | None = Field(default=None, ge=0)

    additional_expected_ot_hours: Decimal = Field(default=ZERO, ge=0)
    holiday_hours: Decimal = Field(default=ZERO, ge=0)
    on_call_hours: Decimal = Field(default=ZERO, ge=0)
    callback_hours: Decimal = Field(default=ZERO, ge=0)
    orientation_hours: Decimal = Field(default=ZERO, ge=0)
    national_double_time_hours: Decimal = Field(default=ZERO, ge=0)
    national_ot_rule: Literal["standard_ot", "48_regular_no_ot"] = "standard_ot"

    employee_benefits_enabled: bool = False

    assignment_stipend: Decimal = Field(default=ZERO, ge=0)
    sign_on_bonus: Decimal = Field(default=ZERO, ge=0)
    completion_bonus: Decimal = Field(default=ZERO, ge=0)
    travel_reimbursement: Decimal = Field(default=ZERO, ge=0)
    other_reimbursement: Decimal = Field(default=ZERO, ge=0)

    @model_validator(mode="after")
    def validate_rates_for_used_components(self):
        if self.additional_expected_ot_hours > 0 and self.ot_client_bill_rate is None:
            raise ValueError("OT client bill rate is required when OT hours are used")
        if self.holiday_hours > 0:
            if self.holiday_client_bill_rate is None:
                raise ValueError("Holiday client bill rate is required when holiday hours are used")
            if self.clinician_holiday_pay_rate is None:
                raise ValueError("Clinician holiday pay rate is required when holiday hours are used")
        if self.on_call_hours > 0 and self.on_call_client_bill_rate is None:
            raise ValueError("On-call client bill rate is required when on-call hours are used")
        if self.callback_hours > 0 and self.callback_client_bill_rate is None:
            raise ValueError("Callback client bill rate is required when callback hours are used")
        if self.profile == "nursing_rehab_ca_w2" and self.national_double_time_hours != 0:
            raise ValueError("California double-time is calculated automatically")
        return self


class W2PayPackageResult(StrictModel):
    profile: Literal["nursing_rehab_ca_w2", "nursing_rehab_national_w2"]
    scheduled_weekly_hours: Decimal
    automatic_ot_hours: Decimal
    additional_expected_ot_hours: Decimal
    double_time_hours: Decimal
    regular_hours: Decimal
    holiday_hours: Decimal
    on_call_hours: Decimal
    callback_hours: Decimal
    total_paid_hours: Decimal
    eligible_stipend_hours: Decimal

    gross_client_billing_per_week: Decimal
    taxable_wages_per_week: Decimal
    recurring_non_taxable_cost_per_week: Decimal
    weekly_clinician_package: Decimal

    orientation_one_time_cost: Decimal
    bonus_burden_one_time_cost: Decimal
    other_one_time_cost_assignment: Decimal

    def to_margin_input(
        self,
        source: W2PayPackageInput,
        *,
        msp_fee_rate_override: Decimal | None = None,
    ) -> MarginInput:
        return MarginInput(
            profile=source.profile,
            division=source.division,
            customer_type=source.customer_type,
            contract_type=source.contract_type,
            candidate_source=source.candidate_source,
            assignment_weeks_equivalent=source.contract_weeks,
            gross_client_billing_per_week=self.gross_client_billing_per_week,
            taxable_wages_per_week=self.taxable_wages_per_week,
            recurring_non_taxable_cost_per_week=self.recurring_non_taxable_cost_per_week,
            other_one_time_cost_assignment=self.other_one_time_cost_assignment,
            employee_benefits_enabled=source.employee_benefits_enabled,
            msp_fee_rate_override=msp_fee_rate_override,
            actual_worked_hours_per_week=self.total_paid_hours,
            shifts_per_week=source.shifts_per_week,
        )


def build_w2_pay_package(
    value: W2PayPackageInput,
    assumptions: CostAssumptionSet,
) -> W2PayPackageResult:
    if value.profile != assumptions.profile:
        raise ValueError("Pay package profile and assumption profile must match")

    scheduled = value.shift_length_hours * value.shifts_per_week

    if value.profile == "nursing_rehab_ca_w2":
        daily_ot = max(min(value.shift_length_hours, Decimal("12")) - Decimal("8"), ZERO) * value.shifts_per_week
        dt_hours = max(value.shift_length_hours - Decimal("12"), ZERO) * value.shifts_per_week
        weekly_ot = max(scheduled - Decimal("40") - dt_hours, ZERO)
        auto_ot = max(daily_ot, weekly_ot)
    else:
        dt_hours = value.national_double_time_hours
        auto_ot = (
            ZERO
            if value.national_ot_rule == "48_regular_no_ot"
            else max(scheduled - Decimal("40") - dt_hours, ZERO)
        )

    if auto_ot + value.additional_expected_ot_hours > 0 and value.ot_client_bill_rate is None:
        raise ValueError("OT client bill rate is required when OT hours apply")
    if dt_hours > 0 and value.double_time_client_bill_rate is None:
        raise ValueError("Double-time client bill rate is required when double-time hours apply")

    regular_hours = max(
        scheduled - auto_ot - dt_hours - value.holiday_hours,
        ZERO,
    )
    total_paid = (
        regular_hours
        + auto_ot
        + value.additional_expected_ot_hours
        + dt_hours
        + value.holiday_hours
        + value.on_call_hours
        + value.callback_hours
    )
    stipend_hours = max(total_paid - value.on_call_hours, ZERO)

    ot_bill_rate = value.ot_client_bill_rate or ZERO
    dt_bill_rate = value.double_time_client_bill_rate or ZERO
    holiday_bill_rate = value.holiday_client_bill_rate or ZERO
    on_call_bill_rate = value.on_call_client_bill_rate or ZERO
    callback_bill_rate = value.callback_client_bill_rate or ZERO

    gross_billing = (
        regular_hours * value.regular_client_bill_rate
        + (auto_ot + value.additional_expected_ot_hours) * ot_bill_rate
        + dt_hours * dt_bill_rate
        + value.holiday_hours * holiday_bill_rate
        + value.on_call_hours * on_call_bill_rate
        + value.callback_hours * callback_bill_rate
    )

    holiday_pay_rate = value.clinician_holiday_pay_rate or ZERO
    callback_pay_rate = value.callback_pay_rate or value.taxable_base_hourly_pay
    ot_pay_rate = value.taxable_base_hourly_pay * Decimal("1.5")
    dt_pay_rate = value.taxable_base_hourly_pay * Decimal("2")

    taxable_wages = (
        regular_hours * value.taxable_base_hourly_pay
        + (auto_ot + value.additional_expected_ot_hours) * ot_pay_rate
        + dt_hours * dt_pay_rate
        + value.holiday_hours * holiday_pay_rate
        + value.on_call_hours * value.clinician_on_call_pay_rate
        + value.callback_hours * callback_pay_rate
    )

    non_taxable = stipend_hours * (
        value.housing_stipend_per_hour
        + value.meals_incidentals_stipend_per_hour
    )

    orientation_hours = ZERO if value.contract_type == "extension" else value.orientation_hours
    orientation_clinician_payment = orientation_hours * (
        value.taxable_base_hourly_pay
        + value.housing_stipend_per_hour
        + value.meals_incidentals_stipend_per_hour
    )
    orientation_taxable = orientation_hours * value.taxable_base_hourly_pay
    orientation_burden = orientation_taxable * (
        assumptions.payroll_tax_rate + assumptions.workers_comp_rate
    )
    orientation_sick = orientation_taxable * assumptions.sick_leave_reserve_hours_per_hour * (
        Decimal("1") + assumptions.payroll_tax_rate + assumptions.workers_comp_rate
    )
    orientation_cost = orientation_clinician_payment + orientation_burden + orientation_sick

    bonuses = value.sign_on_bonus + value.completion_bonus
    bonus_burden = bonuses * (
        Decimal("1") + assumptions.payroll_tax_rate + assumptions.workers_comp_rate
    )

    one_time = (
        orientation_cost
        + bonus_burden
        + value.assignment_stipend
        + value.travel_reimbursement
        + value.other_reimbursement
    )

    return W2PayPackageResult(
        profile=value.profile,
        scheduled_weekly_hours=_q(scheduled),
        automatic_ot_hours=_q(auto_ot),
        additional_expected_ot_hours=_q(value.additional_expected_ot_hours),
        double_time_hours=_q(dt_hours),
        regular_hours=_q(regular_hours),
        holiday_hours=_q(value.holiday_hours),
        on_call_hours=_q(value.on_call_hours),
        callback_hours=_q(value.callback_hours),
        total_paid_hours=_q(total_paid),
        eligible_stipend_hours=_q(stipend_hours),
        gross_client_billing_per_week=_q(gross_billing),
        taxable_wages_per_week=_q(taxable_wages),
        recurring_non_taxable_cost_per_week=_q(non_taxable),
        weekly_clinician_package=_q(taxable_wages + non_taxable),
        orientation_one_time_cost=_q(orientation_cost),
        bonus_burden_one_time_cost=_q(bonus_burden),
        other_one_time_cost_assignment=_q(one_time),
    )

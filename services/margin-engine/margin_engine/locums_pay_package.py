from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Literal

from pydantic import Field, model_validator

from .models import CostAssumptionSet, MarginInput, StrictModel


ZERO = Decimal("0")


def _q(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


def _hourly_equivalent(rate_type: str, amount: Decimal, shift_hours: Decimal) -> Decimal:
    if rate_type == "hourly":
        return amount
    if rate_type == "24_hour_call":
        return amount / Decimal("24")
    if shift_hours <= 0:
        return ZERO
    return amount / shift_hours


def _per_shift(rate_type: str, amount: Decimal, shift_hours: Decimal) -> Decimal:
    if rate_type == "hourly":
        return amount * shift_hours
    return amount


class LocumsPayPackageInput(StrictModel):
    worker_classification: Literal["w2", "1099"]
    assignment_type: Literal["per_diem", "contract", "travel_contract"] = "contract"
    customer_type: Literal["direct", "msp_vms"]
    contract_type: Literal["new_contract", "extension"] = "new_contract"
    candidate_source: Literal["internal_database", "vivian", "referral", "job_board", "other"] = "internal_database"

    planned_per_diem_shifts: Decimal = Field(default=ZERO, ge=0)
    shifts_per_week: Decimal = Field(gt=0)
    contract_weeks: Decimal = Field(gt=0)
    shift_length_hours: Decimal = Field(gt=0)

    client_rate_type: Literal["hourly", "per_shift", "daily", "24_hour_call"] = "hourly"
    client_rate_amount: Decimal = Field(gt=0)
    provider_rate_type: Literal["hourly", "per_shift", "daily", "24_hour_call"] = "hourly"
    provider_rate_amount: Decimal = Field(gt=0)

    client_ot_rate: Decimal | None = Field(default=None, ge=0)
    client_dt_rate: Decimal | None = Field(default=None, ge=0)

    callback_included: bool = False
    callback_hours_per_shift: Decimal = Field(default=ZERO, ge=0)
    callbacks_per_week: Decimal = Field(default=ZERO, ge=0)
    minimum_guaranteed_hours_per_callback: Decimal = Field(default=ZERO, ge=0)
    callback_client_bill_rate: Decimal = Field(default=ZERO, ge=0)
    callback_provider_pay_rate: Decimal = Field(default=ZERO, ge=0)

    standby_included: bool = False
    standby_rate_type: Literal["hourly", "per_shift", "daily", "24_hour_call"] = "hourly"
    standby_units_per_shift: Decimal = Field(default=ZERO, ge=0)
    client_standby_bill_rate: Decimal = Field(default=ZERO, ge=0)
    provider_standby_pay_rate: Decimal = Field(default=ZERO, ge=0)
    compensable_standby_hours_per_week: Decimal = Field(default=ZERO, ge=0)

    orientation_required: bool = False
    orientation_hours_assignment: Decimal = Field(default=ZERO, ge=0)
    orientation_client_bill_rate: Decimal = Field(default=ZERO, ge=0)
    orientation_provider_pay_rate: Decimal = Field(default=ZERO, ge=0)
    regular_stipends_during_orientation: bool = True

    employee_benefits_enabled: bool = False

    housing_daily_cost: Decimal = Field(default=ZERO, ge=0)
    housing_days_per_week: Decimal = Field(default=ZERO, ge=0)
    meals_incidentals_daily_cost: Decimal = Field(default=ZERO, ge=0)
    meals_incidentals_days_per_week: Decimal = Field(default=ZERO, ge=0)
    rental_car_weekly_cost: Decimal = Field(default=ZERO, ge=0)
    mileage_reimbursement_rate: Decimal = Field(default=ZERO, ge=0)
    approved_miles_per_week: Decimal = Field(default=ZERO, ge=0)
    other_weekly_assignment_cost: Decimal = Field(default=ZERO, ge=0)

    airfare: Decimal = Field(default=ZERO, ge=0)
    state_license: Decimal = Field(default=ZERO, ge=0)
    dea_registration: Decimal = Field(default=ZERO, ge=0)
    other_one_time_travel_cost: Decimal = Field(default=ZERO, ge=0)
    sign_on_bonus: Decimal = Field(default=ZERO, ge=0)
    completion_bonus: Decimal = Field(default=ZERO, ge=0)
    other_one_time_cost: Decimal = Field(default=ZERO, ge=0)

    @model_validator(mode="after")
    def validate_assignment(self):
        if self.assignment_type == "per_diem" and self.planned_per_diem_shifts <= 0:
            raise ValueError("Planned per diem shifts are required for Per Diem assignments")
        if self.callback_included and self.callback_client_bill_rate <= 0:
            raise ValueError("Callback client bill rate is required when callback is included")
        if self.callback_included and self.callback_provider_pay_rate <= 0:
            raise ValueError("Callback provider pay rate is required when callback is included")
        if self.standby_included and self.client_standby_bill_rate <= 0:
            raise ValueError("Standby client bill rate is required when standby is included")
        if self.standby_included and self.provider_standby_pay_rate <= 0:
            raise ValueError("Standby provider pay rate is required when standby is included")
        if self.orientation_required and self.orientation_hours_assignment > 0:
            if self.orientation_provider_pay_rate <= 0:
                raise ValueError("Orientation provider pay rate is required")
        return self


class LocumsPayPackageResult(StrictModel):
    profile: Literal["locums_ca_w2", "locums_national_1099"]
    total_shifts: Decimal
    assignment_weeks_equivalent: Decimal
    scheduled_hours_assignment: Decimal
    scheduled_hours_per_week: Decimal

    client_hourly_equivalent: Decimal
    provider_hourly_equivalent: Decimal
    scheduled_client_bill_per_shift: Decimal
    scheduled_provider_pay_per_shift: Decimal

    callback_bill_assignment: Decimal
    callback_provider_pay_assignment: Decimal
    standby_bill_assignment: Decimal
    standby_provider_pay_assignment: Decimal
    orientation_bill_assignment: Decimal
    orientation_provider_pay_assignment: Decimal

    gross_client_billing_assignment: Decimal
    gross_client_billing_per_week: Decimal

    provider_compensation_assignment: Decimal
    provider_compensation_per_week: Decimal
    california_ot_dt_premium_per_week: Decimal

    recurring_non_taxable_cost_per_week: Decimal
    other_one_time_cost_assignment: Decimal
    actual_worked_hours_per_week: Decimal

    def to_margin_input(
        self,
        source: LocumsPayPackageInput,
        *,
        msp_fee_rate_override: Decimal | None = None,
    ) -> MarginInput:
        common = dict(
            profile=self.profile,
            division="locum_tenens",
            customer_type=source.customer_type,
            contract_type=source.contract_type,
            candidate_source=source.candidate_source,
            assignment_weeks_equivalent=self.assignment_weeks_equivalent,
            gross_client_billing_per_week=self.gross_client_billing_per_week,
            recurring_non_taxable_cost_per_week=self.recurring_non_taxable_cost_per_week,
            other_one_time_cost_assignment=self.other_one_time_cost_assignment,
            employee_benefits_enabled=source.employee_benefits_enabled,
            msp_fee_rate_override=msp_fee_rate_override,
            actual_worked_hours_per_week=self.actual_worked_hours_per_week,
            shifts_per_week=source.shifts_per_week,
        )
        if self.profile == "locums_national_1099":
            common["contractor_compensation_per_week"] = self.provider_compensation_per_week
        else:
            common["taxable_wages_per_week"] = (
                self.provider_compensation_per_week + self.california_ot_dt_premium_per_week
            )
        return MarginInput(**common)


def build_locums_pay_package(
    value: LocumsPayPackageInput,
    assumptions: CostAssumptionSet,
) -> LocumsPayPackageResult:
    profile = "locums_ca_w2" if value.worker_classification == "w2" else "locums_national_1099"
    if assumptions.profile != profile:
        raise ValueError("Locums pay package and assumption profile must match")

    if value.assignment_type == "per_diem":
        total_shifts = value.planned_per_diem_shifts
        weeks = total_shifts / value.shifts_per_week
    else:
        weeks = value.contract_weeks
        total_shifts = weeks * value.shifts_per_week

    scheduled_hours_assignment = total_shifts * value.shift_length_hours
    scheduled_hours_week = scheduled_hours_assignment / weeks

    client_hourly = _hourly_equivalent(
        value.client_rate_type, value.client_rate_amount, value.shift_length_hours
    )
    provider_hourly = _hourly_equivalent(
        value.provider_rate_type, value.provider_rate_amount, value.shift_length_hours
    )
    scheduled_client_per_shift = _per_shift(
        value.client_rate_type, value.client_rate_amount, value.shift_length_hours
    )
    scheduled_provider_per_shift = _per_shift(
        value.provider_rate_type, value.provider_rate_amount, value.shift_length_hours
    )

    scheduled_client_assignment = scheduled_client_per_shift * total_shifts
    scheduled_provider_assignment = scheduled_provider_per_shift * total_shifts

    callback_hours_week = ZERO
    if value.callback_included:
        raw_callback_hours = value.callback_hours_per_shift * value.shifts_per_week
        guaranteed = value.callbacks_per_week * value.minimum_guaranteed_hours_per_callback
        callback_hours_week = max(raw_callback_hours, guaranteed)
    callback_hours_assignment = callback_hours_week * weeks
    callback_bill_assignment = callback_hours_assignment * value.callback_client_bill_rate
    callback_provider_assignment = callback_hours_assignment * value.callback_provider_pay_rate

    standby_units_assignment = (
        value.standby_units_per_shift * total_shifts if value.standby_included else ZERO
    )
    standby_bill_assignment = standby_units_assignment * value.client_standby_bill_rate
    standby_provider_assignment = standby_units_assignment * value.provider_standby_pay_rate

    orientation_hours = (
        ZERO if value.contract_type == "extension" or not value.orientation_required
        else value.orientation_hours_assignment
    )
    orientation_bill_assignment = orientation_hours * value.orientation_client_bill_rate
    orientation_provider_assignment = orientation_hours * value.orientation_provider_pay_rate

    bonuses = value.sign_on_bonus + value.completion_bonus

    ca_ot_dt_premium_week = ZERO
    if profile == "locums_ca_w2":
        shift = value.shift_length_hours
        scheduled_daily_ot = max(min(shift, Decimal("12")) - Decimal("8"), ZERO) * value.shifts_per_week
        scheduled_dt = max(shift - Decimal("12"), ZERO) * value.shifts_per_week
        weekly_ot_requirement = max(
            scheduled_hours_week + callback_hours_week - Decimal("40") - scheduled_dt,
            ZERO,
        )
        legal_ot = max(scheduled_daily_ot, weekly_ot_requirement)
        legal_dt = scheduled_dt

        if legal_ot > 0 and value.client_ot_rate is None:
            raise ValueError("Client OT rate is required when California OT applies")
        if legal_dt > 0 and value.client_dt_rate is None:
            raise ValueError("Client double-time rate is required when California DT applies")

        scheduled_regular_hours_week = max(
            scheduled_hours_week - legal_ot - legal_dt,
            ZERO,
        )
        scheduled_regular_bill_week = scheduled_regular_hours_week * client_hourly
        scheduled_ot_bill_week = legal_ot * (value.client_ot_rate or ZERO)
        scheduled_dt_bill_week = legal_dt * (value.client_dt_rate or ZERO)
        scheduled_client_assignment = (
            scheduled_regular_bill_week + scheduled_ot_bill_week + scheduled_dt_bill_week
        ) * weeks

        straight_time_week = (
            scheduled_hours_week * provider_hourly
            + callback_hours_week * value.callback_provider_pay_rate
            + (
                value.compensable_standby_hours_per_week * value.provider_standby_pay_rate
                if value.standby_included else ZERO
            )
        )
        regular_rate_denominator = (
            scheduled_hours_week
            + callback_hours_week
            + (value.compensable_standby_hours_per_week if value.standby_included else ZERO)
        )
        weighted_regular_rate = (
            straight_time_week / regular_rate_denominator
            if regular_rate_denominator > 0 else provider_hourly
        )
        ca_ot_dt_premium_week = (
            legal_ot * weighted_regular_rate * Decimal("0.5")
            + legal_dt * weighted_regular_rate
        )
        scheduled_provider_assignment = scheduled_provider_per_shift * total_shifts

    gross_client_assignment = (
        scheduled_client_assignment
        + callback_bill_assignment
        + standby_bill_assignment
        + orientation_bill_assignment
    )

    provider_comp_assignment = (
        scheduled_provider_assignment
        + callback_provider_assignment
        + standby_provider_assignment
        + orientation_provider_assignment
        + bonuses
    )

    weekly_travel = (
        value.housing_daily_cost * value.housing_days_per_week
        + value.meals_incidentals_daily_cost * value.meals_incidentals_days_per_week
        + value.rental_car_weekly_cost
        + value.mileage_reimbursement_rate * value.approved_miles_per_week
        + value.other_weekly_assignment_cost
    )
    one_time_travel = (
        value.airfare
        + value.state_license
        + value.dea_registration
        + value.other_one_time_travel_cost
        + value.other_one_time_cost
    )

    if profile == "locums_ca_w2":
        # W-2 bonuses are taxable one-time compensation and must carry employer
        # payroll/workers-comp burden outside weekly wages.
        bonus_burden = bonuses * (
            Decimal("1") + assumptions.payroll_tax_rate + assumptions.workers_comp_rate
        )
        provider_comp_assignment -= bonuses
        one_time_travel += bonus_burden

    provider_comp_week = provider_comp_assignment / weeks
    gross_client_week = gross_client_assignment / weeks

    actual_worked_week = (
        scheduled_hours_week + callback_hours_week
        + (value.compensable_standby_hours_per_week if value.standby_included else ZERO)
    )

    return LocumsPayPackageResult(
        profile=profile,
        total_shifts=_q(total_shifts),
        assignment_weeks_equivalent=_q(weeks),
        scheduled_hours_assignment=_q(scheduled_hours_assignment),
        scheduled_hours_per_week=_q(scheduled_hours_week),
        client_hourly_equivalent=_q(client_hourly),
        provider_hourly_equivalent=_q(provider_hourly),
        scheduled_client_bill_per_shift=_q(scheduled_client_per_shift),
        scheduled_provider_pay_per_shift=_q(scheduled_provider_per_shift),
        callback_bill_assignment=_q(callback_bill_assignment),
        callback_provider_pay_assignment=_q(callback_provider_assignment),
        standby_bill_assignment=_q(standby_bill_assignment),
        standby_provider_pay_assignment=_q(standby_provider_assignment),
        orientation_bill_assignment=_q(orientation_bill_assignment),
        orientation_provider_pay_assignment=_q(orientation_provider_assignment),
        gross_client_billing_assignment=_q(gross_client_assignment),
        gross_client_billing_per_week=_q(gross_client_week),
        provider_compensation_assignment=_q(provider_comp_assignment),
        provider_compensation_per_week=_q(provider_comp_week),
        california_ot_dt_premium_per_week=_q(ca_ot_dt_premium_week),
        recurring_non_taxable_cost_per_week=_q(weekly_travel),
        other_one_time_cost_assignment=_q(one_time_travel),
        actual_worked_hours_per_week=_q(actual_worked_week),
    )

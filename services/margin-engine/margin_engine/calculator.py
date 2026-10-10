from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from .models import (
    CostAssumptionSet,
    CostComponent,
    MarginInput,
    MarginResult,
)


ZERO = Decimal("0")
WEEKS_PER_YEAR = Decimal("52")
MONTHS_PER_YEAR = Decimal("12")


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


def _rate(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.0000000001"), rounding=ROUND_HALF_UP)


def _onboarding_cost(value: MarginInput, assumptions: CostAssumptionSet) -> Decimal:
    if value.contract_type == "extension":
        return ZERO
    if value.division == "nursing_allied":
        return assumptions.nursing_allied_onboarding_cost
    if value.division == "rehabilitation":
        return assumptions.rehabilitation_onboarding_cost
    return assumptions.locums_onboarding_cost


def _sourcing_cost(value: MarginInput, assumptions: CostAssumptionSet) -> Decimal:
    if value.contract_type == "extension":
        return ZERO
    if value.candidate_source == "vivian":
        return assumptions.vivian_sourcing_cost
    if value.candidate_source == "referral":
        return assumptions.referral_sourcing_cost
    return ZERO


def _benefit_cost_per_week(value: MarginInput, assumptions: CostAssumptionSet) -> Decimal:
    if not value.employee_benefits_enabled:
        return ZERO
    monthly = (
        assumptions.medical_monthly_premium
        + assumptions.dental_monthly_premium
        + assumptions.vision_monthly_premium
    )
    return monthly * MONTHS_PER_YEAR / WEEKS_PER_YEAR * assumptions.employer_benefit_contribution


def _guideline_status(gm_percent: Decimal, assumptions: CostAssumptionSet) -> str:
    if gm_percent < 0:
        return "negative_gm"

    bands = assumptions.guideline_bands
    recruiter_floor = bands.recruiter_guideline_min_margin
    manager_discussion_floor = bands.delivery_manager_discussion_min_margin

    if recruiter_floor is None and manager_discussion_floor is None:
        return "policy_unconfigured"

    if manager_discussion_floor is not None and gm_percent < manager_discussion_floor:
        return "discuss_leadership"

    if recruiter_floor is not None and gm_percent < recruiter_floor:
        return "discuss_delivery_manager"

    return "within_guideline"


def calculate_margin(value: MarginInput, assumptions: CostAssumptionSet) -> MarginResult:
    if value.profile != assumptions.profile:
        raise ValueError("Input profile and assumption profile must match")

    weeks = value.assignment_weeks_equivalent
    msp_rate = (
        ZERO
        if value.customer_type == "direct"
        else (
            value.msp_fee_rate_override
            if value.msp_fee_rate_override is not None
            else assumptions.default_msp_fee_rate
        )
    )

    gross_billing = value.gross_client_billing_per_week
    msp_fee = gross_billing * msp_rate
    net_billing = gross_billing - msp_fee

    components: list[CostComponent] = []

    def recurring(key: str, label: str, per_week: Decimal):
        per_week = _money(per_week)
        components.append(CostComponent(
            key=key,
            label=label,
            per_week=per_week,
            assignment_total=_money(per_week * weeks),
            category="recurring_cost",
        ))
        return per_week

    base_comp = (
        value.contractor_compensation_per_week
        if value.profile == "locums_national_1099"
        else value.taxable_wages_per_week
    )

    recurring_total = ZERO
    recurring_total += recurring(
        "base_compensation",
        "Contractor Compensation" if value.profile == "locums_national_1099" else "Taxable Wages",
        base_comp,
    )
    recurring_total += recurring(
        "non_taxable_recurring",
        "Recurring Non-Taxable Assignment Cost",
        value.recurring_non_taxable_cost_per_week,
    )

    if value.profile != "locums_national_1099":
        payroll = value.taxable_wages_per_week * assumptions.payroll_tax_rate
        workers_comp = value.taxable_wages_per_week * assumptions.workers_comp_rate
        sick_base = (
            value.taxable_wages_per_week
            * assumptions.sick_leave_reserve_hours_per_hour
        )
        sick_burden = sick_base * (
            Decimal("1") + assumptions.payroll_tax_rate + assumptions.workers_comp_rate
        )
        recurring_total += recurring("payroll_taxes", "Employer Payroll Taxes", payroll)
        recurring_total += recurring("workers_comp", "Workers' Compensation", workers_comp)
        recurring_total += recurring(
            "sick_leave_reserve",
            "Paid Sick Leave Reserve + Burden",
            sick_burden,
        )
        recurring_total += recurring(
            "employer_benefits",
            "Employer Medical / Dental / Vision",
            _benefit_cost_per_week(value, assumptions),
        )
    else:
        workers_comp = value.contractor_compensation_per_week * assumptions.workers_comp_rate
        recurring_total += recurring(
            "workers_comp",
            "Workers' Compensation Reserve",
            workers_comp,
        )

    recurring_total += recurring(
        "professional_liability",
        "Professional Liability / Malpractice",
        net_billing * assumptions.professional_liability_rate,
    )
    recurring_total += recurring(
        "factoring",
        "Factoring Fee",
        net_billing * assumptions.factoring_rate,
    )
    recurring_total += recurring(
        "overhead",
        "Internal Overhead",
        net_billing * assumptions.overhead_rate,
    )
    recurring_total += recurring(
        "other_recurring",
        "Other Recurring Cost",
        value.other_recurring_cost_per_week,
    )

    onboarding = _onboarding_cost(value, assumptions)
    sourcing = _sourcing_cost(value, assumptions)
    other_one_time = value.other_one_time_cost_assignment

    one_time_components = [
        ("onboarding", "Credentialing / Onboarding", onboarding),
        ("candidate_source", "Candidate Source Cost", sourcing),
        ("other_one_time", "Other One-Time Assignment Costs", other_one_time),
    ]
    one_time_total = ZERO
    for key, label, amount in one_time_components:
        amount = _money(amount)
        one_time_total += amount
        components.append(CostComponent(
            key=key,
            label=label,
            per_week=_money(amount / weeks),
            assignment_total=amount,
            category="one_time_cost",
        ))

    allocated_one_time = one_time_total / weeks
    total_cost_week = recurring_total + allocated_one_time
    gm_week = net_billing - total_cost_week
    gm_assignment = gm_week * weeks
    gm_percent = ZERO if net_billing == 0 else gm_week / net_billing

    commissionable = (
        value.commissionable_net_profit_override
        if value.commissionable_net_profit_override is not None
        else gm_assignment
    )
    commission = commissionable * assumptions.commission_rate

    return MarginResult(
        profile=value.profile,
        assumption_version=assumptions.version,
        effective_msp_fee_rate=_rate(msp_rate),
        gross_client_billing_per_week=_money(gross_billing),
        msp_vms_fee_per_week=_money(msp_fee),
        net_client_billing_per_week=_money(net_billing),
        recurring_cost_per_week=_money(recurring_total),
        one_time_cost_assignment=_money(one_time_total),
        allocated_one_time_cost_per_week=_money(allocated_one_time),
        total_cost_per_week=_money(total_cost_week),
        gross_margin_per_week=_money(gm_week),
        gross_margin_assignment=_money(gm_assignment),
        gross_margin_percent=_rate(gm_percent),
        gross_margin_per_actual_hour=(
            _money(gm_week / value.actual_worked_hours_per_week)
            if value.actual_worked_hours_per_week else None
        ),
        gross_margin_per_shift=(
            _money(gm_week / value.shifts_per_week)
            if value.shifts_per_week else None
        ),
        commissionable_net_profit=_money(commissionable),
        projected_recruiter_commission=_money(commission),
        guideline_status=_guideline_status(gm_percent, assumptions),
        cost_components=components,
    )

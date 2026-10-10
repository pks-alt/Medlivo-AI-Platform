from decimal import Decimal

from .models import ApprovalBands, CostAssumptionSet


def seed_assumptions(profile: str) -> CostAssumptionSet:
    common = dict(
        professional_liability_rate=Decimal("0.025"),
        factoring_rate=Decimal("0.024"),
        overhead_rate=Decimal("0.035"),
        default_msp_fee_rate=Decimal("0.06"),
        commission_rate=Decimal("0.03"),
    )

    if profile == "nursing_rehab_ca_w2":
        return CostAssumptionSet(
            profile=profile,
            version="workbook-2026-10-ca-w2-v1",
            payroll_tax_rate=Decimal("0.106"),
            workers_comp_rate=Decimal("0.034"),
            sick_leave_reserve_hours_per_hour=Decimal("0.03333333333333333"),
            medical_monthly_premium=Decimal("400"),
            dental_monthly_premium=Decimal("75"),
            vision_monthly_premium=Decimal("20"),
            employer_benefit_contribution=Decimal("0.5"),
            nursing_allied_onboarding_cost=Decimal("850"),
            rehabilitation_onboarding_cost=Decimal("500"),
            vivian_sourcing_cost=Decimal("1400"),
            **common,
        )

    if profile == "nursing_rehab_national_w2":
        return CostAssumptionSet(
            profile=profile,
            version="workbook-2026-10-national-w2-v1",
            payroll_tax_rate=Decimal("0.106"),
            workers_comp_rate=Decimal("0.015"),
            sick_leave_reserve_hours_per_hour=Decimal("0.03333333333333333"),
            medical_monthly_premium=Decimal("400"),
            dental_monthly_premium=Decimal("75"),
            vision_monthly_premium=Decimal("20"),
            employer_benefit_contribution=Decimal("0.5"),
            nursing_allied_onboarding_cost=Decimal("850"),
            rehabilitation_onboarding_cost=Decimal("500"),
            vivian_sourcing_cost=Decimal("1400"),
            **common,
        )

    if profile == "locums_ca_w2":
        return CostAssumptionSet(
            profile=profile,
            version="workbook-2026-10-locums-ca-w2-v1",
            payroll_tax_rate=Decimal("0.106"),
            workers_comp_rate=Decimal("0.034"),
            sick_leave_reserve_hours_per_hour=Decimal("0.03333333333333333"),
            medical_monthly_premium=Decimal("400"),
            dental_monthly_premium=Decimal("75"),
            vision_monthly_premium=Decimal("20"),
            employer_benefit_contribution=Decimal("0.5"),
            locums_onboarding_cost=Decimal("1200"),
            vivian_sourcing_cost=Decimal("1400"),
            referral_sourcing_cost=Decimal("500"),
            approval_bands=ApprovalBands(
                legacy_workbook_approval_floor=Decimal("0.05")
            ),
            **common,
        )

    if profile == "locums_national_1099":
        return CostAssumptionSet(
            profile=profile,
            version="workbook-2026-10-locums-1099-v1",
            workers_comp_rate=Decimal("0.034"),
            locums_onboarding_cost=Decimal("1200"),
            vivian_sourcing_cost=Decimal("1400"),
            referral_sourcing_cost=Decimal("500"),
            approval_bands=ApprovalBands(
                legacy_workbook_approval_floor=Decimal("0.10")
            ),
            **common,
        )

    raise ValueError("Unsupported calculation profile")

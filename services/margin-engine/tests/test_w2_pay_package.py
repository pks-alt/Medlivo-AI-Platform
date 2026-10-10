from decimal import Decimal

import pytest

from margin_engine import (
    W2PayPackageInput,
    build_w2_pay_package,
    calculate_margin,
    seed_assumptions,
)


def d(value):
    return Decimal(str(value))


def test_ca_nursing_default_workbook_package_matches_weekly_inputs():
    assumptions = seed_assumptions("nursing_rehab_ca_w2")
    source = W2PayPackageInput(
        profile="nursing_rehab_ca_w2",
        division="nursing_allied",
        customer_type="msp_vms",
        contract_type="new_contract",
        candidate_source="vivian",
        contract_weeks=d(13),
        shift_length_hours=d(8),
        shifts_per_week=d(5),
        regular_client_bill_rate=d(139),
        ot_client_bill_rate=d(139),
        double_time_client_bill_rate=d(139),
        holiday_client_bill_rate=d(0),
        on_call_client_bill_rate=d(0),
        callback_client_bill_rate=d(0),
        taxable_base_hourly_pay=d(33),
        housing_stipend_per_hour=d(38),
        meals_incidentals_stipend_per_hour=d(28),
        clinician_holiday_pay_rate=d(0),
        clinician_on_call_pay_rate=d(0),
        callback_pay_rate=d(33),
        orientation_hours=d(12),
    )
    package = build_w2_pay_package(source, assumptions)

    assert package.scheduled_weekly_hours == d("40.000000")
    assert package.automatic_ot_hours == d("0.000000")
    assert package.double_time_hours == d("0.000000")
    assert package.regular_hours == d("40.000000")
    assert package.total_paid_hours == d("40.000000")
    assert package.gross_client_billing_per_week == d("5560.000000")
    assert package.taxable_wages_per_week == d("1320.000000")
    assert package.recurring_non_taxable_cost_per_week == d("2640.000000")
    assert package.weekly_clinician_package == d("3960.000000")
    assert package.orientation_one_time_cost == d("1258.488000")

    margin = calculate_margin(
        package.to_margin_input(source, msp_fee_rate_override=d("0.065")),
        assumptions,
    )
    assert abs(margin.gross_margin_per_week - d("297.073908")) <= d("0.00001")


def test_national_nursing_default_workbook_package_matches_weekly_inputs():
    assumptions = seed_assumptions("nursing_rehab_national_w2")
    source = W2PayPackageInput(
        profile="nursing_rehab_national_w2",
        division="nursing_allied",
        customer_type="msp_vms",
        contract_weeks=d(13),
        shift_length_hours=d(12),
        shifts_per_week=d(3),
        regular_client_bill_rate=d(107),
        ot_client_bill_rate=d(107),
        taxable_base_hourly_pay=d(18),
        housing_stipend_per_hour=d("30.5"),
        meals_incidentals_stipend_per_hour=d(28),
        callback_pay_rate=d(18),
        orientation_hours=d(12),
    )
    package = build_w2_pay_package(source, assumptions)

    assert package.scheduled_weekly_hours == d("36.000000")
    assert package.automatic_ot_hours == d("0.000000")
    assert package.regular_hours == d("36.000000")
    assert package.gross_client_billing_per_week == d("3852.000000")
    assert package.taxable_wages_per_week == d("648.000000")
    assert package.recurring_non_taxable_cost_per_week == d("2106.000000")
    assert package.orientation_one_time_cost == d("952.207200")

    margin = calculate_margin(
        package.to_margin_input(source, msp_fee_rate_override=d("0.065")),
        assumptions,
    )
    assert abs(margin.gross_margin_per_week - d("196.138689")) <= d("0.00001")


def test_california_daily_ot_is_automatic():
    assumptions = seed_assumptions("nursing_rehab_ca_w2")
    source = W2PayPackageInput(
        profile="nursing_rehab_ca_w2",
        division="rehabilitation",
        customer_type="direct",
        contract_weeks=d(13),
        shift_length_hours=d(12),
        shifts_per_week=d(3),
        regular_client_bill_rate=d(100),
        ot_client_bill_rate=d(150),
        double_time_client_bill_rate=d(200),
        taxable_base_hourly_pay=d(30),
    )
    package = build_w2_pay_package(source, assumptions)
    assert package.scheduled_weekly_hours == d("36.000000")
    assert package.automatic_ot_hours == d("12.000000")
    assert package.double_time_hours == d("0.000000")
    assert package.regular_hours == d("24.000000")
    assert package.taxable_wages_per_week == d("1260.000000")


def test_california_double_time_is_automatic():
    assumptions = seed_assumptions("nursing_rehab_ca_w2")
    source = W2PayPackageInput(
        profile="nursing_rehab_ca_w2",
        division="rehabilitation",
        customer_type="direct",
        contract_weeks=d(13),
        shift_length_hours=d(13),
        shifts_per_week=d(3),
        regular_client_bill_rate=d(100),
        ot_client_bill_rate=d(150),
        double_time_client_bill_rate=d(200),
        taxable_base_hourly_pay=d(30),
    )
    package = build_w2_pay_package(source, assumptions)
    assert package.automatic_ot_hours == d("12.000000")
    assert package.double_time_hours == d("3.000000")
    assert package.regular_hours == d("24.000000")


def test_national_standard_ot_and_48_regular_rule_are_distinct():
    assumptions = seed_assumptions("nursing_rehab_national_w2")
    common = dict(
        profile="nursing_rehab_national_w2",
        division="nursing_allied",
        customer_type="direct",
        contract_weeks=d(13),
        shift_length_hours=d(12),
        shifts_per_week=d(4),
        regular_client_bill_rate=d(100),
        ot_client_bill_rate=d(150),
        taxable_base_hourly_pay=d(30),
    )
    standard = build_w2_pay_package(W2PayPackageInput(**common), assumptions)
    no_ot = build_w2_pay_package(
        W2PayPackageInput(**common, national_ot_rule="48_regular_no_ot"),
        assumptions,
    )
    assert standard.automatic_ot_hours == d("8.000000")
    assert standard.regular_hours == d("40.000000")
    assert no_ot.automatic_ot_hours == d("0.000000")
    assert no_ot.regular_hours == d("48.000000")


def test_on_call_hours_do_not_receive_stipends():
    assumptions = seed_assumptions("nursing_rehab_national_w2")
    source = W2PayPackageInput(
        profile="nursing_rehab_national_w2",
        division="nursing_allied",
        customer_type="direct",
        contract_weeks=d(13),
        shift_length_hours=d(8),
        shifts_per_week=d(5),
        regular_client_bill_rate=d(100),
        taxable_base_hourly_pay=d(30),
        housing_stipend_per_hour=d(20),
        meals_incidentals_stipend_per_hour=d(10),
        on_call_hours=d(10),
        on_call_client_bill_rate=d(10),
        clinician_on_call_pay_rate=d(5),
    )
    package = build_w2_pay_package(source, assumptions)
    assert package.total_paid_hours == d("50.000000")
    assert package.eligible_stipend_hours == d("40.000000")
    assert package.recurring_non_taxable_cost_per_week == d("1200.000000")


def test_callback_defaults_to_base_taxable_pay_rate():
    assumptions = seed_assumptions("nursing_rehab_national_w2")
    source = W2PayPackageInput(
        profile="nursing_rehab_national_w2",
        division="rehabilitation",
        customer_type="direct",
        contract_weeks=d(13),
        shift_length_hours=d(8),
        shifts_per_week=d(5),
        regular_client_bill_rate=d(100),
        taxable_base_hourly_pay=d(30),
        callback_hours=d(4),
        callback_client_bill_rate=d(120),
    )
    package = build_w2_pay_package(source, assumptions)
    assert package.taxable_wages_per_week == d("1320.000000")


def test_orientation_is_suppressed_for_extension():
    assumptions = seed_assumptions("nursing_rehab_ca_w2")
    source = W2PayPackageInput(
        profile="nursing_rehab_ca_w2",
        division="rehabilitation",
        customer_type="direct",
        contract_type="extension",
        contract_weeks=d(13),
        shift_length_hours=d(8),
        shifts_per_week=d(5),
        regular_client_bill_rate=d(100),
        taxable_base_hourly_pay=d(30),
        orientation_hours=d(12),
    )
    package = build_w2_pay_package(source, assumptions)
    assert package.orientation_one_time_cost == d("0.000000")


def test_bonuses_are_loaded_with_payroll_and_workers_comp_burden():
    assumptions = seed_assumptions("nursing_rehab_national_w2")
    source = W2PayPackageInput(
        profile="nursing_rehab_national_w2",
        division="nursing_allied",
        customer_type="direct",
        contract_weeks=d(13),
        shift_length_hours=d(8),
        shifts_per_week=d(5),
        regular_client_bill_rate=d(100),
        taxable_base_hourly_pay=d(30),
        sign_on_bonus=d(1000),
        completion_bonus=d(500),
    )
    package = build_w2_pay_package(source, assumptions)
    expected = d(1500) * (d(1) + d("0.106") + d("0.015"))
    assert package.bonus_burden_one_time_cost == expected.quantize(d("0.000001"))


def test_missing_ot_bill_rate_fails_closed_when_california_ot_applies():
    assumptions = seed_assumptions("nursing_rehab_ca_w2")
    source = W2PayPackageInput(
        profile="nursing_rehab_ca_w2",
        division="rehabilitation",
        customer_type="direct",
        contract_weeks=d(13),
        shift_length_hours=d(12),
        shifts_per_week=d(3),
        regular_client_bill_rate=d(100),
        taxable_base_hourly_pay=d(30),
    )
    with pytest.raises(ValueError, match="OT client bill rate"):
        build_w2_pay_package(source, assumptions)


def test_missing_double_time_bill_rate_fails_closed_when_dt_applies():
    assumptions = seed_assumptions("nursing_rehab_ca_w2")
    source = W2PayPackageInput(
        profile="nursing_rehab_ca_w2",
        division="rehabilitation",
        customer_type="direct",
        contract_weeks=d(13),
        shift_length_hours=d(13),
        shifts_per_week=d(3),
        regular_client_bill_rate=d(100),
        ot_client_bill_rate=d(150),
        taxable_base_hourly_pay=d(30),
    )
    with pytest.raises(ValueError, match="Double-time client bill rate"):
        build_w2_pay_package(source, assumptions)

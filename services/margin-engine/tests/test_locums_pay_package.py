from decimal import Decimal

import pytest

from margin_engine import (
    LocumsPayPackageInput,
    build_locums_pay_package,
    calculate_margin,
    seed_assumptions,
)


def d(value):
    return Decimal(str(value))


def test_ca_locums_w2_default_workbook_regression():
    assumptions = seed_assumptions("locums_ca_w2")
    source = LocumsPayPackageInput(
        worker_classification="w2",
        assignment_type="contract",
        customer_type="msp_vms",
        contract_type="new_contract",
        candidate_source="internal_database",
        shifts_per_week=d(5),
        contract_weeks=d(13),
        shift_length_hours=d(8),
        client_rate_type="hourly",
        client_rate_amount=d(220),
        provider_rate_type="hourly",
        provider_rate_amount=d(130),
    )
    package = build_locums_pay_package(source, assumptions)

    assert package.profile == "locums_ca_w2"
    assert package.total_shifts == d("65.000000")
    assert package.assignment_weeks_equivalent == d("13.000000")
    assert package.scheduled_hours_per_week == d("40.000000")
    assert package.gross_client_billing_per_week == d("8800.000000")
    assert package.provider_compensation_per_week == d("5200.000000")
    assert package.california_ot_dt_premium_per_week == d("0.000000")

    margin = calculate_margin(
        package.to_margin_input(source, msp_fee_rate_override=d("0.085")),
        assumptions,
    )
    assert abs(margin.net_client_billing_per_week - d("8052")) <= d("0.00001")
    assert abs(margin.total_cost_per_week - d("6894.275692")) <= d("0.00001")
    assert abs(margin.gross_margin_per_week - d("1157.724308")) <= d("0.00001")
    assert abs(margin.gross_margin_assignment - d("15050.416")) <= d("0.00001")


def test_locums_1099_default_workbook_regression():
    assumptions = seed_assumptions("locums_national_1099")
    source = LocumsPayPackageInput(
        worker_classification="1099",
        assignment_type="contract",
        customer_type="msp_vms",
        contract_type="new_contract",
        candidate_source="internal_database",
        planned_per_diem_shifts=d(5),
        shifts_per_week=d(2),
        contract_weeks=d(13),
        shift_length_hours=d(10),
        client_rate_type="hourly",
        client_rate_amount=d(410),
        provider_rate_type="hourly",
        provider_rate_amount=d(280),
    )
    package = build_locums_pay_package(source, assumptions)

    assert package.profile == "locums_national_1099"
    assert package.total_shifts == d("26.000000")
    assert package.assignment_weeks_equivalent == d("13.000000")
    assert package.scheduled_client_bill_per_shift == d("4100.000000")
    assert package.scheduled_provider_pay_per_shift == d("2800.000000")
    assert package.gross_client_billing_per_week == d("8200.000000")
    assert package.provider_compensation_per_week == d("5600.000000")

    margin = calculate_margin(
        package.to_margin_input(source, msp_fee_rate_override=d("0.05")),
        assumptions,
    )
    assert abs(margin.net_client_billing_per_week - d("7790")) <= d("0.00001")
    assert abs(margin.total_cost_per_week - d("6537.067692")) <= d("0.00001")
    assert abs(margin.gross_margin_per_week - d("1252.932308")) <= d("0.00001")
    assert abs(margin.gross_margin_assignment - d("16288.12")) <= d("0.00001")
    assert abs(margin.gross_margin_per_shift - d("626.4661538")) <= d("0.00001")


def test_1099_per_diem_uses_planned_shift_count():
    assumptions = seed_assumptions("locums_national_1099")
    source = LocumsPayPackageInput(
        worker_classification="1099",
        assignment_type="per_diem",
        customer_type="direct",
        planned_per_diem_shifts=d(5),
        shifts_per_week=d(2),
        contract_weeks=d(13),
        shift_length_hours=d(8),
        client_rate_type="per_shift",
        client_rate_amount=d(2500),
        provider_rate_type="per_shift",
        provider_rate_amount=d(1800),
    )
    package = build_locums_pay_package(source, assumptions)
    assert package.total_shifts == d("5.000000")
    assert package.assignment_weeks_equivalent == d("2.500000")
    assert package.gross_client_billing_assignment == d("12500.000000")
    assert package.provider_compensation_assignment == d("9000.000000")


def test_1099_callback_standby_orientation_are_assignment_components():
    assumptions = seed_assumptions("locums_national_1099")
    source = LocumsPayPackageInput(
        worker_classification="1099",
        assignment_type="contract",
        customer_type="direct",
        shifts_per_week=d(2),
        contract_weeks=d(4),
        shift_length_hours=d(10),
        client_rate_type="hourly",
        client_rate_amount=d(400),
        provider_rate_type="hourly",
        provider_rate_amount=d(250),
        callback_included=True,
        callback_hours_per_shift=d(2),
        callback_client_bill_rate=d(500),
        callback_provider_pay_rate=d(300),
        standby_included=True,
        standby_units_per_shift=d(1),
        client_standby_bill_rate=d(1000),
        provider_standby_pay_rate=d(600),
        orientation_required=True,
        orientation_hours_assignment=d(8),
        orientation_client_bill_rate=d(400),
        orientation_provider_pay_rate=d(250),
    )
    package = build_locums_pay_package(source, assumptions)
    assert package.callback_bill_assignment == d("8000.000000")
    assert package.callback_provider_pay_assignment == d("4800.000000")
    assert package.standby_bill_assignment == d("8000.000000")
    assert package.standby_provider_pay_assignment == d("4800.000000")
    assert package.orientation_bill_assignment == d("3200.000000")
    assert package.orientation_provider_pay_assignment == d("2000.000000")


def test_1099_bonuses_are_in_contractor_compensation_for_wc_reserve():
    assumptions = seed_assumptions("locums_national_1099")
    source = LocumsPayPackageInput(
        worker_classification="1099",
        assignment_type="contract",
        customer_type="direct",
        shifts_per_week=d(1),
        contract_weeks=d(10),
        shift_length_hours=d(8),
        client_rate_type="hourly",
        client_rate_amount=d(500),
        provider_rate_type="hourly",
        provider_rate_amount=d(300),
        sign_on_bonus=d(1000),
        completion_bonus=d(500),
    )
    package = build_locums_pay_package(source, assumptions)
    assert package.provider_compensation_assignment == d("25500.000000")


def test_ca_w2_bonus_is_loaded_as_one_time_employer_cost():
    assumptions = seed_assumptions("locums_ca_w2")
    source = LocumsPayPackageInput(
        worker_classification="w2",
        assignment_type="contract",
        customer_type="direct",
        shifts_per_week=d(5),
        contract_weeks=d(13),
        shift_length_hours=d(8),
        client_rate_type="hourly",
        client_rate_amount=d(220),
        provider_rate_type="hourly",
        provider_rate_amount=d(130),
        sign_on_bonus=d(1000),
        completion_bonus=d(500),
    )
    package = build_locums_pay_package(source, assumptions)
    expected = d(1500) * (d(1) + d("0.106") + d("0.034"))
    assert package.other_one_time_cost_assignment == expected.quantize(d("0.000001"))
    assert package.provider_compensation_per_week == d("5200.000000")


def test_ca_w2_automatic_ot_requires_client_ot_rate():
    assumptions = seed_assumptions("locums_ca_w2")
    source = LocumsPayPackageInput(
        worker_classification="w2",
        assignment_type="contract",
        customer_type="direct",
        shifts_per_week=d(3),
        contract_weeks=d(13),
        shift_length_hours=d(12),
        client_rate_type="hourly",
        client_rate_amount=d(220),
        provider_rate_type="hourly",
        provider_rate_amount=d(130),
    )
    with pytest.raises(ValueError, match="Client OT rate"):
        build_locums_pay_package(source, assumptions)


def test_ca_w2_ot_premium_is_automatic():
    assumptions = seed_assumptions("locums_ca_w2")
    source = LocumsPayPackageInput(
        worker_classification="w2",
        assignment_type="contract",
        customer_type="direct",
        shifts_per_week=d(3),
        contract_weeks=d(13),
        shift_length_hours=d(12),
        client_rate_type="hourly",
        client_rate_amount=d(220),
        provider_rate_type="hourly",
        provider_rate_amount=d(130),
        client_ot_rate=d(330),
        client_dt_rate=d(440),
    )
    package = build_locums_pay_package(source, assumptions)
    assert package.california_ot_dt_premium_per_week == d("780.000000")


def test_extension_suppresses_orientation():
    assumptions = seed_assumptions("locums_national_1099")
    source = LocumsPayPackageInput(
        worker_classification="1099",
        assignment_type="contract",
        customer_type="direct",
        contract_type="extension",
        shifts_per_week=d(2),
        contract_weeks=d(13),
        shift_length_hours=d(10),
        client_rate_type="hourly",
        client_rate_amount=d(410),
        provider_rate_type="hourly",
        provider_rate_amount=d(280),
        orientation_required=True,
        orientation_hours_assignment=d(8),
        orientation_client_bill_rate=d(410),
        orientation_provider_pay_rate=d(280),
    )
    package = build_locums_pay_package(source, assumptions)
    assert package.orientation_bill_assignment == d("0.000000")
    assert package.orientation_provider_pay_assignment == d("0.000000")

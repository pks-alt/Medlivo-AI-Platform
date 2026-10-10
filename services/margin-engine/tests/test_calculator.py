from decimal import Decimal

from margin_engine import GuidelineBands, MarginInput, calculate_margin, seed_assumptions


def d(value):
    return Decimal(str(value))


MONEY_TOLERANCE = Decimal("0.00001")
RATE_TOLERANCE = Decimal("0.000000001")


def assert_money_close(actual, expected):
    assert abs(actual - d(expected)) <= MONEY_TOLERANCE


def assert_rate_close(actual, expected):
    assert abs(actual - d(expected)) <= RATE_TOLERANCE


def test_california_nursing_workbook_regression():
    assumptions = seed_assumptions("nursing_rehab_ca_w2")
    result = calculate_margin(
        MarginInput(
            profile="nursing_rehab_ca_w2",
            division="nursing_allied",
            customer_type="msp_vms",
            contract_type="new_contract",
            candidate_source="vivian",
            assignment_weeks_equivalent=d(13),
            gross_client_billing_per_week=d(5560),
            taxable_wages_per_week=d(1320),
            recurring_non_taxable_cost_per_week=d(2640),
            other_one_time_cost_assignment=d("1258.488"),
            msp_fee_rate_override=d("0.065"),
            actual_worked_hours_per_week=d(40),
        ),
        assumptions,
    )
    assert_money_close(result.net_client_billing_per_week, "5198.600000")
    assert_money_close(result.total_cost_per_week, "4901.526092")
    assert_money_close(result.gross_margin_per_week, "297.073908")
    assert_money_close(result.gross_margin_assignment, "3861.960800")
    assert_rate_close(result.gross_margin_percent, "0.0571449829")


def test_national_nursing_workbook_regression():
    assumptions = seed_assumptions("nursing_rehab_national_w2")
    result = calculate_margin(
        MarginInput(
            profile="nursing_rehab_national_w2",
            division="nursing_allied",
            customer_type="msp_vms",
            contract_type="new_contract",
            candidate_source="vivian",
            assignment_weeks_equivalent=d(13),
            gross_client_billing_per_week=d(3852),
            taxable_wages_per_week=d(648),
            recurring_non_taxable_cost_per_week=d(2106),
            other_one_time_cost_assignment=d("952.2072"),
            msp_fee_rate_override=d("0.065"),
            actual_worked_hours_per_week=d(36),
        ),
        assumptions,
    )
    assert_money_close(result.net_client_billing_per_week, "3601.620000")
    assert_money_close(result.total_cost_per_week, "3405.481311")
    assert_money_close(result.gross_margin_per_week, "196.138689")
    assert_money_close(result.gross_margin_assignment, "2549.802957")
    assert_rate_close(result.gross_margin_percent, "0.0544584629")


def test_ca_locums_w2_workbook_regression():
    assumptions = seed_assumptions("locums_ca_w2")
    result = calculate_margin(
        MarginInput(
            profile="locums_ca_w2",
            division="locum_tenens",
            customer_type="msp_vms",
            assignment_weeks_equivalent=d(13),
            gross_client_billing_per_week=d(8800),
            taxable_wages_per_week=d(5200),
            msp_fee_rate_override=d("0.085"),
            actual_worked_hours_per_week=d(40),
            shifts_per_week=d(5),
        ),
        assumptions,
    )
    assert_money_close(result.net_client_billing_per_week, "8052.000000")
    assert_money_close(result.total_cost_per_week, "6894.275692")
    assert_money_close(result.gross_margin_per_week, "1157.724308")
    assert_money_close(result.gross_margin_assignment, "15050.415999")
    assert_rate_close(result.gross_margin_percent, "0.1437809622")
    assert_money_close(result.gross_margin_per_actual_hour, "28.943108")


def test_locums_1099_workbook_regression():
    assumptions = seed_assumptions("locums_national_1099")
    result = calculate_margin(
        MarginInput(
            profile="locums_national_1099",
            division="locum_tenens",
            customer_type="msp_vms",
            assignment_weeks_equivalent=d(13),
            gross_client_billing_per_week=d(8200),
            contractor_compensation_per_week=d(5600),
            msp_fee_rate_override=d("0.05"),
            actual_worked_hours_per_week=d(20),
            shifts_per_week=d(2),
        ),
        assumptions,
    )
    assert_money_close(result.net_client_billing_per_week, "7790.000000")
    assert_money_close(result.total_cost_per_week, "6537.067692")
    assert_money_close(result.gross_margin_per_week, "1252.932308")
    assert_money_close(result.gross_margin_assignment, "16288.119999")
    assert_rate_close(result.gross_margin_percent, "0.1608385504")
    assert_money_close(result.gross_margin_per_shift, "626.466154")


def test_direct_customer_has_zero_msp_fee_even_with_default_assumption():
    assumptions = seed_assumptions("nursing_rehab_national_w2")
    result = calculate_margin(
        MarginInput(
            profile="nursing_rehab_national_w2",
            division="rehabilitation",
            customer_type="direct",
            assignment_weeks_equivalent=d(13),
            gross_client_billing_per_week=d(4000),
            taxable_wages_per_week=d(1000),
        ),
        assumptions,
    )
    assert result.effective_msp_fee_rate == d("0E-10")
    assert result.msp_vms_fee_per_week == d("0.000000")
    assert result.net_client_billing_per_week == d("4000.000000")


def test_extension_suppresses_onboarding_and_sourcing():
    assumptions = seed_assumptions("nursing_rehab_ca_w2")
    result = calculate_margin(
        MarginInput(
            profile="nursing_rehab_ca_w2",
            division="rehabilitation",
            customer_type="direct",
            contract_type="extension",
            candidate_source="vivian",
            assignment_weeks_equivalent=d(13),
            gross_client_billing_per_week=d(5000),
            taxable_wages_per_week=d(1200),
        ),
        assumptions,
    )
    components = {x.key: x for x in result.cost_components}
    assert components["onboarding"].assignment_total == d("0.000000")
    assert components["candidate_source"].assignment_total == d("0.000000")


def test_benefits_use_monthly_to_weekly_employer_share():
    assumptions = seed_assumptions("locums_ca_w2")
    result = calculate_margin(
        MarginInput(
            profile="locums_ca_w2",
            division="locum_tenens",
            customer_type="direct",
            assignment_weeks_equivalent=d(13),
            gross_client_billing_per_week=d(10000),
            taxable_wages_per_week=d(5000),
            employee_benefits_enabled=True,
        ),
        assumptions,
    )
    components = {x.key: x for x in result.cost_components}
    expected = (d(400) + d(75) + d(20)) * d(12) / d(52) * d("0.5")
    assert components["employer_benefits"].per_week == expected.quantize(d("0.000001"))


def test_configured_guidelines_flag_delivery_manager_and_leadership_discussion():
    assumptions = seed_assumptions("locums_national_1099").model_copy(
        update={
            "guideline_bands": GuidelineBands(
                recruiter_guideline_min_margin=d("0.20"),
                delivery_manager_discussion_min_margin=d("0.10"),
                legacy_workbook_floor=d("0.10"),
            )
        }
    )
    manager = calculate_margin(
        MarginInput(
            profile="locums_national_1099",
            division="locum_tenens",
            customer_type="direct",
            assignment_weeks_equivalent=d(13),
            gross_client_billing_per_week=d(8000),
            contractor_compensation_per_week=d(6000),
        ),
        assumptions,
    )
    assert manager.guideline_status == "discuss_delivery_manager"

    executive = calculate_margin(
        MarginInput(
            profile="locums_national_1099",
            division="locum_tenens",
            customer_type="direct",
            assignment_weeks_equivalent=d(13),
            gross_client_billing_per_week=d(7000),
            contractor_compensation_per_week=d(6000),
        ),
        assumptions,
    )
    assert executive.guideline_status == "discuss_leadership"


def test_negative_gm_is_hard_exception():
    assumptions = seed_assumptions("locums_national_1099").model_copy(
        update={
            "guideline_bands": GuidelineBands(
                recruiter_guideline_min_margin=d("0.20"),
                delivery_manager_discussion_min_margin=d("0.10"),
            )
        }
    )
    result = calculate_margin(
        MarginInput(
            profile="locums_national_1099",
            division="locum_tenens",
            customer_type="direct",
            assignment_weeks_equivalent=d(13),
            gross_client_billing_per_week=d(5000),
            contractor_compensation_per_week=d(6000),
        ),
        assumptions,
    )
    assert result.gross_margin_per_week < 0
    assert result.guideline_status == "negative_gm"


def test_projected_commission_is_three_percent_of_commissionable_net_profit():
    assumptions = seed_assumptions("locums_national_1099")
    result = calculate_margin(
        MarginInput(
            profile="locums_national_1099",
            division="locum_tenens",
            customer_type="direct",
            assignment_weeks_equivalent=d(10),
            gross_client_billing_per_week=d(10000),
            contractor_compensation_per_week=d(7000),
            commissionable_net_profit_override=d(20000),
        ),
        assumptions,
    )
    assert result.commissionable_net_profit == d("20000.000000")
    assert result.projected_recruiter_commission == d("600.000000")


def test_recruiter_can_finalize_within_guideline():
    assumptions = seed_assumptions("locums_national_1099").model_copy(
        update={
            "guideline_bands": GuidelineBands(
                recruiter_guideline_min_margin=d("0.10"),
                delivery_manager_discussion_min_margin=d("0.05"),
                legacy_workbook_floor=d("0.10"),
            )
        }
    )
    result = calculate_margin(
        MarginInput(
            profile="locums_national_1099",
            division="locum_tenens",
            customer_type="direct",
            assignment_weeks_equivalent=d(13),
            gross_client_billing_per_week=d(10000),
            contractor_compensation_per_week=d(6000),
        ),
        assumptions,
    )
    assert result.guideline_status == "within_guideline"

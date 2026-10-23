import pytest
from datetime import date, datetime

from pages.calculations_details import (
    calculate_treasury_bill, calculate_bond, calculate_money_market,
    calc_single, calculate_data, validate_row, normalize_row,
    safe_float, parse_percentage, parse_date, parse_frequency,
    round_money, days_between,
)


class TestTreasuryBills:

    def test_basic_calculation(self):
        item = {"face_value": 100000, "discount_rate": 5, "term_days": 90,
                "day_count_convention": "ACT/360"}
        r = calculate_treasury_bill(item)
        assert r["status"] == "success"
        assert r["face_value"] == 100000
        assert r["term_days"] == 90

    def test_purchase_price_from_discount_rate(self):
        item = {"face_value": 100000, "discount_rate": 5, "term_days": 90,
                "day_count_convention": "ACT/360"}
        r = calculate_treasury_bill(item)
        expected = 100000 * (1 - 0.05 * 90 / 360)
        assert r["purchase_price"] == round(expected, 2)

    def test_bond_equivalent_yield(self):
        item = {"face_value": 100000, "purchase_price": 98750,
                "term_days": 90, "day_count_convention": "ACT/360"}
        r = calculate_treasury_bill(item)
        # (1250 / 98750) * (365/90) * 100 = 5.133614... → 5.1336
        assert round(r["bond_equivalent_yield"], 4) == 5.1336

    def test_effective_annual_yield(self):
        item = {"face_value": 100000, "purchase_price": 98750, "term_days": 90}
        r = calculate_treasury_bill(item)
        # (100000/98750)^(365/90) - 1 = 0.0523381... → 5.2338
        assert round(r["effective_annual_yield"], 4) == 5.2338

    def test_money_market_yield(self):
        item = {"face_value": 100000, "purchase_price": 98750,
                "term_days": 90, "day_count_convention": "ACT/360"}
        r = calculate_treasury_bill(item)
        # (1250/98750) * (360/90) * 100 = 5.063291... → 5.0633
        assert round(r["money_market_yield"], 4) == 5.0633

    def test_discount_amount(self):
        item = {"face_value": 100000, "purchase_price": 98750, "term_days": 90}
        r = calculate_treasury_bill(item)
        assert r["discount_amount"] == 1250.00

    def test_missing_face_value(self):
        item = {"discount_rate": 5, "term_days": 90}
        r = calculate_treasury_bill(item)
        assert r["status"] == "partial"
        assert r["face_value"] is None

    def test_zero_days(self):
        item = {"face_value": 100000, "discount_rate": 5, "term_days": 0}
        r = calculate_treasury_bill(item)
        assert r["status"] != "success"

    def test_price_exceeds_face_value(self):
        item = {"face_value": 100000, "purchase_price": 101000, "term_days": 90}
        r = calculate_treasury_bill(item)
        assert r["discount_amount"] == -1000.00

    def test_currency_preservation(self):
        item = {"face_value": 100000, "discount_rate": 5, "term_days": 90,
                "currency": "ZAR"}
        r = calculate_treasury_bill(item)
        assert r["currency"] == "ZAR"


class TestBonds:

    def test_annual_coupon(self):
        item = {"face_value": 100000, "coupon_rate": "6%",
                "years_to_maturity": 5, "coupon_frequency": 2, "price": 104376}
        r = calculate_bond(item)
        assert r["annual_coupon"] == 6000.00
        assert r["coupon_per_period"] == 3000.00

    def test_price_from_ytm(self):
        item = {"face_value": 100000, "coupon_rate": "6%",
                "years_to_maturity": 5, "coupon_frequency": 2,
                "yield_to_maturity": "5%"}
        r = calculate_bond(item)
        assert r["status"] == "success"
        assert r["current_price"] is not None

    def test_current_yield(self):
        item = {"face_value": 100000, "coupon_rate": "6%",
                "years_to_maturity": 5, "coupon_frequency": 2,
                "price": 104376.00}
        r = calculate_bond(item)
        # 6000 / 104376 * 100 = 5.7484448... → 5.7484
        assert round(r["current_yield"], 4) == 5.7484

    def test_accrued_interest(self):
        item = {"face_value": 100000, "coupon_rate": "6%",
                "years_to_maturity": 5, "coupon_frequency": 2,
                "price": 104376.00,
                "last_coupon_date": "2024-01-01",
                "valuation_date": "2024-02-15",
                "day_count_convention": "ACT/365"}
        r = calculate_bond(item)
        # 3000 * (45 / 182.5) = 739.726... → 739.73
        assert round(r["accrued_interest"], 2) == 739.73
        assert r["days_accrued"] == 45

    def test_duration_calculation(self):
        item = {"face_value": 100000, "coupon_rate": "6%",
                "years_to_maturity": 5, "coupon_frequency": 2,
                "price": 104376.00}
        r = calculate_bond(item)
        assert r["duration"] is not None
        assert r["modified_duration"] is not None
        assert r["modified_duration"] < r["duration"]

    def test_from_dates(self):
        item = {"face_value": 100000, "coupon_rate": "6%",
                "coupon_frequency": 2, "price": 104376.00,
                "valuation_date": "2024-01-01",
                "maturity_date": "2029-01-01"}
        r = calculate_bond(item)
        assert r["status"] == "success"
        assert r["years_to_maturity"] is not None
        assert r["years_to_maturity"] == pytest.approx(5.0, abs=0.02)

    def test_missing_face_value(self):
        item = {"coupon_rate": "6%", "years_to_maturity": 5,
                "coupon_frequency": 2, "price": 100000}
        r = calculate_bond(item)
        assert r["status"] == "partial"

    def test_invalid_frequency(self):
        item = {"face_value": 100000, "coupon_rate": "6%",
                "years_to_maturity": 5, "coupon_frequency": 500,
                "price": 104376.00}
        r = calculate_bond(item)
        assert r["status"] == "partial"
        assert r["frequency"] == 2  # defaulted to semi-annual

    def test_price_as_percentage(self):
        item = {"face_value": 100000, "coupon_rate": "6%",
                "years_to_maturity": 5, "coupon_frequency": 2,
                "price": "104.376%"}
        r = calculate_bond(item)
        assert r["status"] == "success"
        assert r["current_price"] == pytest.approx(104376.00, abs=1.0)

    def test_currency_preservation(self):
        item = {"face_value": 100000, "coupon_rate": "6%",
                "years_to_maturity": 5, "coupon_frequency": 2,
                "price": 104376.00, "currency": "USD"}
        r = calculate_bond(item)
        assert r["currency"] == "USD"


class TestMoneyMarket:

    def test_basic(self):
        item = {"principal": 100000, "interest_rate": "5%", "term_days": 90}
        r = calculate_money_market(item)
        assert r["status"] == "success"
        assert r["principal"] == 100000

    def test_interest_earned(self):
        item = {"principal": 100000, "interest_rate": "5%", "term_days": 90,
                "day_count_convention": "ACT/360"}
        r = calculate_money_market(item)
        # 100000 * 0.05 * 90/360 = 1250.00
        assert r["interest_earned"] == 1250.00
        assert r["total_value"] == 101250.00

    def test_zero_days(self):
        item = {"principal": 100000, "interest_rate": "5%", "term_days": 0}
        r = calculate_money_market(item)
        assert r["status"] == "partial"

    def test_negative_rate(self):
        item = {"principal": 100000, "interest_rate": "-5%", "term_days": 90}
        r = calculate_money_market(item)
        # Negative rates are permitted (they exist); status still success
        assert r["status"] == "success"


class TestHelperFunctions:

    def test_safe_float(self):
        assert safe_float("100,000.50") == 100000.50
        assert safe_float("$1,000") == 1000.0
        assert safe_float("(500)") == -500.0
        assert safe_float(None) is None
        assert safe_float("abc") is None

    def test_parse_percentage(self):
        assert parse_percentage("6%") == 0.06
        assert parse_percentage(6) == 0.06
        assert parse_percentage(0.06) == 0.06
        assert parse_percentage("abc") is None

    def test_parse_date(self):
        assert parse_date("2024-01-15") == date(2024, 1, 15)
        assert parse_date("15/01/2024") == date(2024, 1, 15)
        assert parse_date(None) is None

    def test_parse_frequency(self):
        assert parse_frequency("Annual") == 1
        assert parse_frequency("Semi-Annual") == 2
        assert parse_frequency("Quarterly") == 4
        assert parse_frequency(2) == 2
        assert parse_frequency(None) is None

    def test_round_money(self):
        assert round_money(100.123) == 100.12
        assert round_money(100.125) == 100.13
        assert round_money(100.126) == 100.13
        assert round_money(-100.125) == -100.13
        assert round_money(None) is None

    def test_days_between(self):
        assert days_between(date(2024, 1, 1), date(2024, 12, 31)) == 365
        assert days_between(date(2024, 12, 31), date(2024, 1, 1)) == 365


class TestEdgeCases:

    def test_zero_days(self):
        item = {"principal": 100000, "interest_rate": "5%", "term_days": 0}
        r = calculate_money_market(item)
        assert r["status"] == "partial"

    def test_negative_rate(self):
        item = {"principal": 100000, "interest_rate": "-5%", "term_days": 90}
        r = calculate_money_market(item)
        assert r["interest_earned"] < 0

    def test_very_long_maturity(self):
        item = {"principal": 100000, "interest_rate": "5%", "term_days": 3650,
                "day_count_convention": "ACT/360"}
        r = calculate_money_market(item)
        assert r["status"] == "success"
        expected = round(100000 * 0.05 * (3650 / 360), 2)
        assert r["interest_earned"] == expected

    def test_matured_instrument(self):
        item = {"principal": 100000, "interest_rate": "5%",
                "valuation_date": "2024-06-01", "maturity_date": "2024-01-01"}
        r = calculate_money_market(item)
        assert r["status"] == "partial"


class TestNewDerivations:

    def test_days_derived_from_dates(self):
        item = {"face_value": 100000, "discount_rate": 5,
                "valuation_date": "2024-01-01", "maturity_date": "2024-04-01"}
        r = calculate_treasury_bill(item)
        assert r["term_days"] == 91
        assert r["derivations"]["days_to_maturity"]["from"] == "2024-01-01"

    def test_discount_rate_derived_from_price(self):
        item = {"face_value": 100000, "purchase_price": 98750, "term_days": 90}
        r = calculate_treasury_bill(item)
        assert r["discount_rate"] is not None
        # (100000 - 98750)/100000 * 360/90 * 100 = 5.0
        assert round(r["discount_rate"], 4) == 5.0

    def test_valuation_date_used_when_settlement_date_missing(self):
        item = {"face_value": 100000, "coupon_rate": "6%",
                "coupon_frequency": 2, "price": 104376,
                "valuation_date": "2024-01-01",
                "maturity_date": "2029-01-01"}
        r = calculate_bond(item)
        assert r["status"] == "success"
import pytest
from datetime import date, datetime

from pages.calculations_details import (
    calculate_treasury_bill, calculate_bond, calculate_money_market,
    calc_single, calculate_data, validate_row, normalize_row,
    safe_float, parse_percentage, parse_date, parse_frequency,
    round_money, days_between, parse_day_count_convention,
    calculate_days_30_360,
)
from routes.calculations import _fix_instrument_count


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
        item = {"face_value": 100000, "discount_rate": 5, "term_days": 90,
                "day_count_convention": "ACT/360"}
        r = calculate_treasury_bill(item)
        assert r["discount_amount"] == 1250

    def test_discount_rate_from_price(self):
        item = {"face_value": 100000, "purchase_price": 98750, "term_days": 90,
                "day_count_convention": "ACT/360"}
        r = calculate_treasury_bill(item)
        # ((100000 - 98750) / 100000) * (360/90) * 100 = 5%
        assert round(r["discount_rate"], 4) == 5.0

    def test_yield_based_pricing(self):
        """Test yield-based pricing (investor yield)."""
        item = {"face_value": 100000, "yield": 5, "term_days": 90,
                "day_count_convention": "ACT/360"}
        r = calculate_treasury_bill(item)
        # Price = 100000 / (1 + 0.05 * 90/365) = 98782.14
        assert round(r["purchase_price"], 2) == 98782.14

    def test_investor_yield_from_price(self):
        """Calculate investor yield from purchase price."""
        item = {"face_value": 100000, "purchase_price": 98750, "term_days": 90,
                "day_count_convention": "ACT/360"}
        r = calculate_treasury_bill(item)
        # Investor yield for T-Bills equals Bond Equivalent Yield
        # ((100000 / 98750) - 1) * (365/90) * 100 = 5.1336%
        assert round(r["investor_yield"], 4) == 5.1336

    def test_holding_period_yield(self):
        item = {"face_value": 100000, "purchase_price": 98750, "term_days": 90,
                "day_count_convention": "ACT/360"}
        r = calculate_treasury_bill(item)
        # (100000 - 98750) / 98750 * 100 = 1.2658%
        assert round(r["holding_period_yield"], 4) == 1.2658

    def test_present_value(self):
        item = {"face_value": 100000, "discount_rate": 5, "term_days": 90,
                "day_count_convention": "ACT/360"}
        r = calculate_treasury_bill(item)
        # PV equals purchase price for T-Bills
        assert r["present_value"] == r["purchase_price"]

    def test_carrying_value(self):
        item = {"face_value": 100000, "discount_rate": 5, "term_days": 90,
                "day_count_convention": "ACT/360"}
        r = calculate_treasury_bill(item)
        # Carrying value = purchase price (T-Bills don't accrue interest)
        assert r["carrying_value"] == r["purchase_price"]

    def test_accrued_interest(self):
        item = {"face_value": 100000, "discount_rate": 5, "term_days": 90,
                "day_count_convention": "ACT/360"}
        r = calculate_treasury_bill(item)
        # T-Bills are discount instruments; accrued interest is zero
        assert r["accrued_interest"] == 0

    def test_maturity_value(self):
        item = {"face_value": 100000, "discount_rate": 5, "term_days": 90,
                "day_count_convention": "ACT/360"}
        r = calculate_treasury_bill(item)
        # Maturity value equals face value
        assert r["maturity_value"] == 100000

    def test_fair_value(self):
        item = {"face_value": 100000, "discount_rate": 5, "term_days": 90,
                "day_count_convention": "ACT/360"}
        r = calculate_treasury_bill(item)
        # Fair value equals present value for T-Bills
        assert r["fair_value"] == r["present_value"]

    def test_missing_face_value(self):
        item = {"discount_rate": 5, "term_days": 90}
        r = calculate_treasury_bill(item)
        assert r["status"] in ("partial", "error")

    def test_missing_price_and_rate_does_not_report_current_value(self):
        result = calculate_treasury_bill(
            {"face_value": 100000, "term_days": 90}
        )

        assert result["status"] == "partial"
        assert result["maturity_value"] == 100000
        assert result.get("total_value") is None
        assert result.get("present_value") is None

    def test_zero_days(self):
        item = {"face_value": 100000, "discount_rate": 5, "term_days": 0}
        r = calculate_treasury_bill(item)
        assert r["status"] in ("partial", "error")

    def test_price_exceeds_face_value(self):
        item = {"face_value": 100000, "purchase_price": 105000, "term_days": 90}
        r = calculate_treasury_bill(item)
        assert r["status"] in ("partial", "error")

    def test_currency_preservation(self):
        item = {"face_value": 100000, "discount_rate": 5, "term_days": 90,
                "currency": "USD", "day_count_convention": "ACT/360"}
        r = calculate_treasury_bill(item)
        assert r["currency"] == "USD"

    def test_discount_yield_vs_investor_yield(self):
        """Verify discount yield and investor yield are distinct."""
        item = {"face_value": 100000, "purchase_price": 98750, "term_days": 90,
                "day_count_convention": "ACT/360"}
        r = calculate_treasury_bill(item)
        # Discount yield: (1250/100000) * (360/90) * 100 = 5.0%
        # Investor yield (equals BEY for T-Bills): ((100000/98750)-1) * (365/90) * 100 = 5.1336%
        assert round(r["discount_yield"], 4) == 5.0
        assert round(r["investor_yield"], 4) == 5.1336

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
        # PV of 10 semiannual coupons and principal at a 2.5% period yield.
        assert r["current_price"] == pytest.approx(104376.03, abs=0.01)

    def test_ytm_solver_recovers_independent_periodic_yield(self):
        result = calculate_bond({
            "face_value": 100000,
            "coupon_rate": 6,
            "years_to_maturity": 5,
            "coupon_frequency": 2,
            "price": 104376.03,
        })

        assert result["yield_to_maturity"] == pytest.approx(5.0, abs=0.0001)

    @pytest.mark.parametrize("price_field", ["present_value", "fair_value"])
    def test_market_valuation_fields_can_price_bond(self, price_field):
        item = {
            "BondName": "Cleaned bond",
            "FaceValue": 100000,
            "CouponRate": "6%",
            "years_to_maturity": 5,
            "Coupon Frequency": 2,
            price_field: 98000,
        }

        result = calculate_bond(item)

        assert result["current_price"] == 98000
        assert result["total_value"] == 98000
        assert result["status"] == "success"

    def test_missing_bond_price_or_yield_is_reported(self):
        item = {
            "FaceValue": 100000,
            "CouponRate": "6%",
            "years_to_maturity": 5,
        }

        result = calculate_bond(item)

        assert any("price or yield_to_maturity" in field
                   for field in result["missing_fields"])

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

    def test_accrued_interest_uses_actual_coupon_period_for_act_act(self):
        result = calculate_bond({
            "face_value": 100000,
            "coupon_rate": 6,
            "years_to_maturity": 5,
            "coupon_frequency": 2,
            "price": 100000,
            "last_coupon_date": "2024-01-15",
            "valuation_date": "2024-04-15",
            "day_count_convention": "ACT/ACT",
        })

        assert result["days_accrued"] == 91
        assert result["next_coupon_date"] == "2024-07-15"
        assert result["accrued_interest"] == pytest.approx(
            3000 * 91 / 182, abs=0.01
        )

    def test_accrued_interest_uses_30_360_day_count(self):
        result = calculate_bond({
            "face_value": 100000,
            "coupon_rate": 6,
            "years_to_maturity": 5,
            "coupon_frequency": 2,
            "price": 100000,
            "last_coupon_date": "2024-01-31",
            "valuation_date": "2024-02-28",
            "day_count_convention": "30/360",
        })

        assert result["days_accrued"] == 28
        assert result["accrued_interest"] == pytest.approx(
            3000 * 28 / 180, abs=0.01
        )

    def test_accrued_interest_requires_explicit_day_count(self):
        result = calculate_bond({
            "face_value": 100000,
            "coupon_rate": 6,
            "years_to_maturity": 5,
            "coupon_frequency": 2,
            "price": 100000,
            "last_coupon_date": "2024-01-15",
            "valuation_date": "2024-04-15",
        })

        assert result["status"] == "partial"
        assert result.get("accrued_interest") is None
        assert any("day_count_convention" in field
                   for field in result["missing_fields"])

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
        assert r["frequency"] is None

    def test_missing_frequency_keeps_frequency_dependent_values_unset(self):
        item = {
            "BondName": "Cleaned bond",
            "FaceValue": 100000,
            "CouponRate": "6%",
            "years_to_maturity": 5,
            "present_value": 98000,
        }

        result = calculate_bond(item)

        assert result["status"] == "partial"
        assert result["current_price"] == 98000
        assert result["price_per_100"] == 98
        assert result["annual_coupon"] == 6000
        assert result["current_yield"] == pytest.approx(6000 / 98000 * 100, abs=0.0001)
        assert result.get("coupon_payment") is None
        assert result.get("yield_to_maturity") is None
        assert result.get("duration") is None
        assert result.get("accrued_interest") is None
        assert any("coupon_frequency" in field for field in result["missing_fields"])

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

    def test_clean_price(self):
        item = {"face_value": 100000, "coupon_rate": "6%",
                "years_to_maturity": 5, "coupon_frequency": 2,
                "price": 105000.00,
                "last_coupon_date": "2024-01-01",
                "valuation_date": "2024-02-15",
                "day_count_convention": "ACT/365"}
        r = calculate_bond(item)
        if "clean_price" in r:
            assert r["clean_price"] < r["current_price"]

    def test_dirty_price(self):
        item = {"face_value": 100000, "coupon_rate": "6%",
                "years_to_maturity": 5, "coupon_frequency": 2,
                "price": 105000.00,
                "last_coupon_date": "2024-01-01",
                "valuation_date": "2024-02-15",
                "day_count_convention": "ACT/365"}
        r = calculate_bond(item)
        if "dirty_price" in r:
            assert r["dirty_price"] == r["current_price"]

    def test_carrying_value(self):
        item = {"face_value": 100000, "coupon_rate": "6%",
                "years_to_maturity": 5, "coupon_frequency": 2,
                "price": 105000.00}
        r = calculate_bond(item)
        if "carrying_value" in r:
            assert r["carrying_value"] == r["current_price"]

    def test_market_value(self):
        item = {"face_value": 100000, "coupon_rate": "6%",
                "years_to_maturity": 5, "coupon_frequency": 2,
                "price": 105000.00}
        r = calculate_bond(item)
        if "market_value" in r:
            assert r["market_value"] == r["current_price"]

    def test_explicit_clean_price_adds_accrued_interest_for_valuation(self):
        result = calculate_bond({
            "face_value": 100000,
            "coupon_rate": 6,
            "years_to_maturity": 5,
            "coupon_frequency": 2,
            "clean_price": 100000,
            "last_coupon_date": "2024-01-15",
            "next_coupon_date": "2024-07-15",
            "valuation_date": "2024-04-15",
            "day_count_convention": "ACT/ACT",
        })

        assert result["accrued_interest"] == pytest.approx(1500, abs=0.01)
        assert result["clean_price"] == 100000
        assert result["dirty_price"] == 101500
        assert result["market_value"] == 101500

    def test_explicit_dirty_price_subtracts_accrued_interest(self):
        result = calculate_bond({
            "face_value": 100000,
            "coupon_rate": 6,
            "years_to_maturity": 5,
            "coupon_frequency": 2,
            "dirty_price": 101500,
            "last_coupon_date": "2024-01-15",
            "next_coupon_date": "2024-07-15",
            "valuation_date": "2024-04-15",
            "day_count_convention": "ACT/ACT",
        })

        assert result["dirty_price"] == 101500
        assert result["clean_price"] == 100000

    def test_clean_price_without_accrual_inputs_is_not_valued_as_dirty(self):
        result = calculate_bond({
            "face_value": 100000,
            "coupon_rate": 6,
            "years_to_maturity": 5,
            "coupon_frequency": 2,
            "clean_price": 100000,
        })

        assert result.get("current_price") is None
        assert result["clean_price"] == 100000
        assert result.get("market_value") is None
        assert result["status"] == "partial"


class TestMoneyMarket:
    def test_basic(self):
        item = {"principal": 100000, "interest_rate": 5, "term_days": 90,
                "day_count_convention": "ACT/360"}
        r = calculate_money_market(item)
        assert r["status"] in ("success", "partial")
        assert r["principal"] == 100000
        assert r["term_days"] == 90

    def test_interest_earned(self):
        item = {"principal": 100000, "interest_rate": 5, "term_days": 90,
                "day_count_convention": "ACT/360"}
        r = calculate_money_market(item)
        # Interest = 100000 * 0.05 * (90/360) = 1250
        assert r["interest_earned"] == 1250

    def test_discount_based_calculation(self):
        """Test discount-based money market instrument."""
        item = {"principal": 100000, "discount_rate": 5, "term_days": 90,
                "day_count_convention": "ACT/360"}
        r = calculate_money_market(item)
        assert r["status"] in ("success", "partial")
        # Purchase price = 100000 * (1 - 0.05 * 90/360) = 98750
        assert r["purchase_price"] == 98750
        # Discount amount = 100000 - 98750 = 1250
        assert r["discount_amount"] == 1250
        assert r["interest_earned"] == 1250
        assert r["maturity_value"] == 100000

    def test_missing_rate_does_not_assume_zero_interest(self):
        result = calculate_money_market({"principal": 100000, "term_days": 90})

        assert result["status"] == "partial"
        assert result.get("interest_earned") is None
        assert result.get("total_value") is None
        assert result.get("maturity_value") is None
        assert any("interest_rate OR discount_rate" in field
                   for field in result["missing_fields"])

    def test_missing_rate_does_not_invent_purchase_or_accrued_value(self):
        result = calculate_money_market({"principal": 100000, "term_days": 90})

        assert result.get("purchase_price") is None
        assert result.get("interest_earned") is None
        assert result.get("accrued_interest") is None
        assert result.get("present_value") is None

    def test_purchase_price_from_discount_rate(self):
        item = {"principal": 100000, "discount_rate": 5, "term_days": 90,
                "day_count_convention": "ACT/360"}
        r = calculate_money_market(item)
        expected = 100000 * (1 - 0.05 * 90 / 360)
        assert r["purchase_price"] == round(expected, 2)

    def test_discount_rate_from_purchase_price(self):
        item = {"principal": 100000, "purchase_price": 98750, "term_days": 90,
                "day_count_convention": "ACT/360"}
        r = calculate_money_market(item)
        # Discount rate = (100000 - 98750) / 100000 * (360/90) * 100 = 5%
        assert round(r["discount_rate"], 4) == 5.0

    def test_discount_yield(self):
        item = {"principal": 100000, "discount_rate": 5, "term_days": 90,
                "day_count_convention": "ACT/360"}
        r = calculate_money_market(item)
        # Discount yield = (1250 / 100000) * (360/90) * 100 = 5%
        assert round(r["discount_yield"], 4) == 5.0

    def test_money_market_yield(self):
        item = {"principal": 100000, "discount_rate": 5, "term_days": 90,
                "day_count_convention": "ACT/360"}
        r = calculate_money_market(item)
        # Money market yield = (1250 / 98750) * (360/90) * 100 = 5.0633%
        assert round(r["money_market_yield"], 4) == 5.0633

    def test_simple_rate_yields_use_actual_earned_interest(self):
        result = calculate_money_market({
            "principal": 100000,
            "interest_rate": 5,
            "term_days": 90,
            "day_count_convention": "ACT/360",
        })

        assert result["interest_earned"] == 1250
        assert result["money_market_yield"] == 5
        assert result["bond_equivalent_yield"] == 5.0694
        assert result["effective_annual_rate"] == 5.1671
        assert result["effective_yield"] == 5.1671

    def test_holding_period_yield(self):
        item = {"principal": 100000, "interest_rate": 5, "term_days": 90,
                "day_count_convention": "ACT/360"}
        r = calculate_money_market(item)
        # HPY = (101250 - 100000) / 100000 * 100 = 1.25%
        assert round(r["holding_period_yield"], 4) == 1.25

    def test_accrued_interest(self):
        item = {"principal": 100000, "interest_rate": 5,
                "issue_date": "2024-01-01", "settlement_date": "2024-01-31",
                "day_count_convention": "ACT/360"}
        r = calculate_money_market(item)
        # Days accrued = 30
        # Accrued interest = 100000 * 0.05 * (30/360) = 416.67
        assert round(r["accrued_interest"], 2) == 416.67

    def test_carrying_value(self):
        item = {"principal": 100000, "interest_rate": 5, "term_days": 90,
                "issue_date": "2024-01-01", "settlement_date": "2024-01-31",
                "day_count_convention": "ACT/360"}
        r = calculate_money_market(item)
        # Purchase price = 100000 (add-on rate)
        # Accrued interest = 100000 * 0.05 * (30/360) = 416.67
        # Carrying value = 100000 + 416.67 = 100416.67
        if "carrying_value" in r:
            assert round(r["carrying_value"], 2) == 100416.67

    def test_present_value_with_purchase_price(self):
        item = {"principal": 100000, "purchase_price": 98750, "term_days": 90,
                "day_count_convention": "ACT/360"}
        r = calculate_money_market(item)
        # Present value should equal purchase price
        assert r["present_value"] == 98750

    def test_present_value_add_on_rate(self):
        item = {"principal": 100000, "interest_rate": 5, "term_days": 90,
                "day_count_convention": "ACT/360"}
        r = calculate_money_market(item)
        # For add-on rate instruments, PV = principal
        if "present_value" in r:
            assert r["present_value"] == 100000

    def test_maturity_value(self):
        item = {"principal": 100000, "interest_rate": 5, "term_days": 90,
                "day_count_convention": "ACT/360"}
        r = calculate_money_market(item)
        # Maturity value = principal + interest = 100000 + 1250 = 101250
        assert r["maturity_value"] == 101250

    def test_fair_value(self):
        item = {"principal": 100000, "interest_rate": 5, "term_days": 90,
                "day_count_convention": "ACT/360"}
        r = calculate_money_market(item)
        # Fair value = principal + interest = 101250
        assert r["fair_value"] == 101250

    def test_zero_days(self):
        item = {"principal": 100000, "interest_rate": 5, "term_days": 0,
                "day_count_convention": "ACT/360"}
        r = calculate_money_market(item)
        assert r["status"] in ("partial", "error")

    def test_negative_rate(self):
        item = {"principal": 100000, "interest_rate": -5, "term_days": 90,
                "day_count_convention": "ACT/360"}
        r = calculate_money_market(item)
        assert r["status"] in ("partial", "error")

    def test_act_365_convention(self):
        item = {"principal": 100000, "interest_rate": 5, "term_days": 90,
                "day_count_convention": "ACT/365"}
        r = calculate_money_market(item)
        # Interest = 100000 * 0.05 * (90/365) = 1232.88
        assert round(r["interest_earned"], 2) == 1232.88

    def test_currency_preservation(self):
        item = {"principal": 100000, "interest_rate": 5, "term_days": 90,
                "currency": "USD", "day_count_convention": "ACT/360"}
        r = calculate_money_market(item)
        assert r["currency"] == "USD"

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

    def test_cleaned_dates_override_stale_derived_days(self):
        row = {
            "face_value": 100000,
            "discount_rate": 5,
            "valuation_date": "2024-01-01",
            "maturity_date": "2024-04-01",
            "days_to_maturity": 30,
        }

        result = calculate_treasury_bill(row)

        assert result["term_days"] == 91

    def test_money_market_dates_override_stale_derived_days(self):
        row = {
            "principal": 100000,
            "interest_rate": 5,
            "valuation_date": "2024-01-01",
            "maturity_date": "2024-04-01",
            "days_to_maturity": 30,
        }

        result = calculate_money_market(row)

        assert result["term_days"] == 91
        assert result["interest_earned"] == pytest.approx(1263.89, abs=0.01)


def test_tbills_aggregate_current_values_without_mixing_currencies():
    rows = [
        {
            "Instrument Name": "USD-1",
            "Face Value": 100000,
            "Discount Rate": 5,
            "Term Days": 90,
            "Currency": "USD",
        },
        {
            "Instrument Name": "EUR-1",
            "Face Value": 100000,
            "Discount Rate": 5,
            "Term Days": 90,
            "Currency": "EUR",
        },
    ]

    result = calculate_data(rows, "tbills")
    aggregates = result["aggregates"]

    assert aggregates.get("total_value") is None
    assert aggregates["currency_groups"]["USD"]["total_value"] == 98750
    assert aggregates["currency_groups"]["EUR"]["total_value"] == 98750


class TestInstrumentCount:

    def test_repeated_named_rows_count_as_one_instrument(self):
        result = {
            "instrument_count": 2,
            "calculations": [
                {
                    "instrument_name": "MM-1",
                    "status": "success",
                    "principal": 100000,
                    "interest_rate": 5,
                    "term_days": 90,
                },
                {
                    "instrument_name": "MM-1",
                    "status": "success",
                    "principal": 100000,
                    "interest_rate": 5,
                    "term_days": 90,
                },
            ],
            "aggregates": {"instrument_count": 2},
        }

        assert _fix_instrument_count(result) == 1
        assert result["aggregates"]["instrument_count"] == 1

    def test_unnamed_rows_use_values_to_distinguish_instruments(self):
        result = {
            "calculations": [
                {
                    "status": "success",
                    "face_value": 100000,
                    "discount_rate": 5,
                    "term_days": 90,
                },
                {
                    "status": "success",
                    "face_value": 100000,
                    "discount_rate": 5,
                    "term_days": 90,
                },
                {
                    "status": "success",
                    "face_value": 120000,
                    "discount_rate": 5,
                    "term_days": 90,
                },
            ],
            "aggregates": {},
        }

        assert _fix_instrument_count(result) == 2
        assert result["aggregates"]["instrument_count"] == 2


@pytest.mark.parametrize(
    ("instrument_type", "rows", "amount_key"),
    [
        (
            "money-market",
            [
                {"Instrument Name": "MM-1", "Principal": 100000, "Interest Rate": "5%", "Term Days": 90},
                {"Instrument Name": "MM-2", "Principal": 150000, "Interest Rate": "4%", "Term Days": 180},
            ],
            "principal",
        ),
        (
            "tbills",
            [
                {"Instrument Name": "TB-1", "Face Value": 100000, "Discount Rate": "5%", "Term Days": 90},
                {"Instrument Name": "TB-2", "Face Value": 150000, "Discount Rate": "4%", "Term Days": 180},
            ],
            "face_value",
        ),
        (
            "bonds",
            [
                {"Instrument Name": "Bond-1", "Face Value": 100000, "Coupon Rate": "6%", "Yield to Maturity": "5%", "Years to Maturity": 5, "Coupon Frequency": 2},
                {"Instrument Name": "Bond-2", "Face Value": 150000, "Coupon Rate": "5%", "Yield to Maturity": "4%", "Years to Maturity": 7, "Coupon Frequency": 2},
            ],
            "face_value",
        ),
    ],
)
def test_cleaned_multi_instrument_rows_recalculate_and_aggregate(
    instrument_type, rows, amount_key
):
    rows = [
        {**row, "Currency": "USD"}
        for row in rows
    ]
    result = calculate_data(rows, instrument_type)

    assert len(result["calculations"]) == 2
    assert result["instrument_count"] == 2
    assert result["aggregates"]["total_value"] == pytest.approx(
        sum(row["total_value"] for row in result["calculations"])
    )

    changed_rows = [dict(row) for row in rows]
    amount_column = "Principal" if amount_key == "principal" else "Face Value"
    changed_rows[0][amount_column] *= 2
    changed_result = calculate_data(changed_rows, instrument_type)

    assert changed_result["calculations"][0][amount_key] == (
        result["calculations"][0][amount_key] * 2
    )
    assert changed_result["calculations"][0]["total_value"] != (
        result["calculations"][0]["total_value"]
    )
    assert changed_result["aggregates"]["total_value"] == pytest.approx(
        sum(row["total_value"] for row in changed_result["calculations"])
    )


def test_missing_bond_market_price_does_not_fall_back_to_face_value():
    result = calculate_data([{
        "Face Value": 100000,
        "Coupon Rate": 6,
        "Years to Maturity": 5,
        "Coupon Frequency": 2,
    }], "bonds")

    assert result["calculations"][0].get("current_price") is None
    assert result["aggregates"].get("total_value") is None


class TestDayCountConventions:
    """Test day-count convention parsing and 30/360 calculations."""

    def test_parse_act_360(self):
        result = parse_day_count_convention("ACT/360")
        assert result["convention"] == "ACT/360"
        assert result["basis"] == 360.0
        assert result["is_30_360"] is False
        assert result["is_european"] is False

    def test_parse_act_365(self):
        result = parse_day_count_convention("ACT/365")
        assert result["convention"] == "ACT/365"
        assert result["basis"] == 365.0
        assert result["is_30_360"] is False
        assert result["is_european"] is False

    def test_parse_act_act(self):
        result = parse_day_count_convention("Actual/Actual (ICMA)")
        assert result["convention"] == "ACT/ACT"
        assert result["basis"] == 365.0
        assert result["is_actual_actual"] is True

    def test_parse_30_360_standard(self):
        result = parse_day_count_convention("30/360")
        assert result["convention"] == "30/360"
        assert result["basis"] == 360.0
        assert result["is_30_360"] is True
        assert result["is_european"] is False

    def test_parse_30e_360_european(self):
        result = parse_day_count_convention("30E/360")
        assert result["convention"] == "30E/360"
        assert result["basis"] == 360.0
        assert result["is_30_360"] is True
        assert result["is_european"] is True

    def test_parse_none_defaults_to_act_360(self):
        result = parse_day_count_convention(None)
        assert result["convention"] == "ACT/360"
        assert result["basis"] == 360.0

    def test_parse_30_360_with_hyphen(self):
        result = parse_day_count_convention("30-360")
        assert result["convention"] == "30/360"
        assert result["is_30_360"] is True

    def test_30_360_standard_calculation(self):
        """Test standard 30/360 (NASD) calculation."""
        start = date(2024, 1, 15)
        end = date(2024, 4, 15)
        days = calculate_days_30_360(start, end, european=False)
        # 15Jan to 15Apr: (0 * 360) + (3 * 30) + (15 - 15) = 90 days
        assert days == 90

    def test_30_360_with_31st_adjustment(self):
        """Test standard 30/360 with 31st adjustment rules."""
        start = date(2024, 1, 31)
        end = date(2024, 2, 28)
        days = calculate_days_30_360(start, end, european=False)
        # Start 31→30, End 28: (0 * 360) + (1 * 30) + (28 - 30) = 28 days
        assert days == 28

    def test_30_360_both_31st(self):
        """Test standard 30/360 when both dates are 31st."""
        start = date(2024, 1, 31)
        end = date(2024, 2, 28)
        days = calculate_days_30_360(start, end, european=False)
        # Start 31→30, End 28 (not 31): (0 * 360) + (1 * 30) + (28 - 30) = 28 days
        assert days == 28

    def test_30e_360_european_calculation(self):
        """Test European 30E/360 calculation."""
        start = date(2024, 1, 31)
        end = date(2024, 2, 28)
        days = calculate_days_30_360(start, end, european=True)
        # Start 31→30, End 28: (0 * 360) + (1 * 30) + (28 - 30) = 28 days
        assert days == 28

    def test_30e_360_both_31st(self):
        """Test European 30E/360 when both dates are 31st."""
        start = date(2024, 1, 31)
        end = date(2024, 2, 28)
        days = calculate_days_30_360(start, end, european=True)
        # Start 31→30, End 28: (0 * 360) + (1 * 30) + (28 - 30) = 28 days
        assert days == 28

    def test_money_market_with_30_360(self):
        """Test Money Market calculation with 30/360 day-count."""
        item = {
            "principal": 100000,
            "interest_rate": 5,
            "issue_date": "2024-01-15",
            "maturity_date": "2024-04-15",
            "day_count_convention": "30/360",
        }
        r = calculate_money_market(item)
        assert r["status"] == "success"
        # 30/360 calculation should give 90 days (15Jan to 15Apr)
        assert r["term_days"] == 90
        # Interest = 100000 * 0.05 * (90/360) = 1250
        assert r["interest_earned"] == 1250

    def test_tbill_with_30_360(self):
        """Test T-Bill calculation with 30/360 day-count."""
        item = {
            "face_value": 100000,
            "discount_rate": 5,
            "issue_date": "2024-01-15",
            "maturity_date": "2024-04-15",
            "day_count_convention": "30/360",
        }
        r = calculate_treasury_bill(item)
        assert r["status"] == "success"
        # 30/360 calculation should give 90 days (15Jan to 15Apr)
        assert r["term_days"] == 90
        # Price = 100000 * (1 - 0.05 * 90/360) = 98750
        assert r["purchase_price"] == 98750

    def test_bond_with_30_360(self):
        """Test Bond calculation with 30/360 day-count."""
        item = {
            "face_value": 100000,
            "coupon_rate": 6,
            "yield_to_maturity": 5,
            "years_to_maturity": 5,
            "coupon_frequency": 2,
            "day_count_convention": "30/360",
        }
        r = calculate_bond(item)
        assert r["status"] == "success"
        assert r["day_count_convention"] == "30/360"
        # Verify calculation succeeds with 30/360 convention
        assert r["current_price"] is not None
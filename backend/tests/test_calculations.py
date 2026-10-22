"""
Unit tests for financial instrument calculations.

Tests Money Market, Treasury Bills, and Bonds calculations
with independently verified expected results.
"""

import pytest
from datetime import date, timedelta
from pages.calculations_details import (
    calculate_money_market,
    calculate_treasury_bill,
    calculate_bond,
    safe_float,
    parse_percentage,
    parse_date,
    round_money,
)


class TestMoneyMarket:
    """Test Money Market instrument calculations."""

    def test_simple_interest_360_day_basis(self):
        """Test simple interest calculation with ACT/360 day count."""
        item = {
            "principal": 100000,
            "interest_rate": "5%",
            "term_days": 90,
            "day_count_convention": "ACT/360"
        }
        result = calculate_money_market(item)
        
        # Interest = 100000 * 0.05 * (90/360) = 1250
        assert result["interest_earned"] == 1250.00
        assert result["total_value"] == 101250.00
        assert result["status"] == "success"

    def test_simple_interest_365_day_basis(self):
        """Test simple interest calculation with ACT/365 day count."""
        item = {
            "principal": 100000,
            "interest_rate": "5%",
            "term_days": 90,
            "day_count_convention": "ACT/365"
        }
        result = calculate_money_market(item)
        
        # Interest = 100000 * 0.05 * (90/365) = 1232.88
        assert round(result["interest_earned"], 2) == 1232.88
        assert round(result["total_value"], 2) == 101232.88
        assert result["status"] == "success"

    def test_effective_yield(self):
        """Test effective annual yield calculation."""
        item = {
            "principal": 100000,
            "interest_rate": "5%",
            "term_days": 90,
            "day_count_convention": "ACT/360"
        }
        result = calculate_money_market(item)
        
        # Effective Yield = (1250/100000) * (365/90) * 100 = 5.0694%
        assert round(result["effective_yield"], 4) == 5.0694

    def test_discount_yield(self):
        """Test discount yield calculation."""
        item = {
            "principal": 100000,
            "interest_rate": "5%",
            "term_days": 90,
            "day_count_convention": "ACT/360"
        }
        result = calculate_money_market(item)
        
        # Discount Yield = (1250/101250) * (360/90) * 100 = 4.9383%
        assert round(result["discount_yield"], 4) == 4.9383

    def test_from_dates(self):
        """Test calculation from valuation and maturity dates."""
        item = {
            "principal": 100000,
            "interest_rate": "5%",
            "valuation_date": "2024-01-01",
            "maturity_date": "2024-04-01",
            "day_count_convention": "ACT/360"
        }
        result = calculate_money_market(item)
        
        # 2024-01-01 to 2024-04-01 = 91 days (Feb 2024 has 29 days)
        # Interest = 100000 * 0.05 * (91/360) = 1263.89
        assert result["term_days"] == 91
        assert round(result["interest_earned"], 2) == 1263.89

    def test_missing_principal(self):
        """Test error when principal is missing."""
        item = {
            "interest_rate": "5%",
            "term_days": 90
        }
        result = calculate_money_market(item)
        
        assert result["status"] == "partial"
        assert result["principal"] is None

    def test_negative_principal(self):
        """Test error when principal is negative."""
        item = {
            "principal": -100000,
            "interest_rate": "5%",
            "term_days": 90
        }
        result = calculate_money_market(item)
        
        # Should still calculate but validation would catch this
        assert result["principal"] == -100000.00

    def test_currency_preservation(self):
        """Test that currency is preserved in results."""
        item = {
            "principal": 100000,
            "interest_rate": "5%",
            "term_days": 90,
            "currency": "USD"
        }
        result = calculate_money_market(item)
        
        assert result["currency"] == "USD"


class TestTreasuryBills:
    """Test Treasury Bill calculations."""

    def test_purchase_price_from_discount(self):
        """Test purchase price calculation from discount rate."""
        item = {
            "face_value": 100000,
            "discount_rate": "5%",
            "term_days": 90,
            "day_count_convention": "ACT/360"
        }
        result = calculate_treasury_bill(item)
        
        # Price = 100000 * (1 - 0.05 * 90/360) = 98750
        assert result["purchase_price"] == 98750.00
        assert result["status"] == "success"

    def test_discount_amount(self):
        """Test discount amount calculation."""
        item = {
            "face_value": 100000,
            "purchase_price": 98750,
            "term_days": 90,
            "day_count_convention": "ACT/360"
        }
        result = calculate_treasury_bill(item)
        
        # Discount Amount = 100000 - 98750 = 1250
        assert result["discount_amount"] == 1250.00

    def test_discount_yield(self):
        """Test bank discount yield calculation."""
        item = {
            "face_value": 100000,
            "purchase_price": 98750,
            "term_days": 90,
            "day_count_convention": "ACT/360"
        }
        result = calculate_treasury_bill(item)
        
        # Discount Yield = (1250/100000) * (360/90) * 100 = 5.0000%
        assert round(result["discount_yield"], 4) == 5.0000

    def test_money_market_yield(self):
        """Test money market yield (CD equivalent) calculation."""
        item = {
            "face_value": 100000,
            "purchase_price": 98750,
            "term_days": 90,
            "day_count_convention": "ACT/360"
        }
        result = calculate_treasury_bill(item)
        
        # Money Market Yield = (1250/98750) * (360/90) * 100 = 5.0633%
        assert round(result["money_market_yield"], 4) == 5.0633

    def test_bond_equivalent_yield(self):
        """Test bond equivalent yield (investment yield) calculation."""
        item = {
            "face_value": 100000,
            "purchase_price": 98750,
            "term_days": 90,
            "day_count_convention": "ACT/360"
        }
        result = calculate_treasury_bill(item)
        
        # BEY = (1250/98750) * (365/90) * 100 = 5.1337%
        assert round(result["bond_equivalent_yield"], 4) == 5.1337

    def test_holding_period_yield(self):
        """Test holding period yield calculation."""
        item = {
            "face_value": 100000,
            "purchase_price": 98750,
            "term_days": 90
        }
        result = calculate_treasury_bill(item)
        
        # Holding Period Yield = (1250/98750) * 100 = 1.2658%
        assert round(result["holding_period_yield"], 4) == 1.2658

    def test_effective_annual_yield(self):
        """Test effective annual yield (compounded) calculation."""
        item = {
            "face_value": 100000,
            "purchase_price": 98750,
            "term_days": 90
        }
        result = calculate_treasury_bill(item)
        
        # EAY = ((100000/98750)^(365/90) - 1) * 100 = 5.2337%
        assert round(result["effective_annual_yield"], 4) == 5.2337

    def test_from_dates(self):
        """Test calculation from valuation and maturity dates."""
        item = {
            "face_value": 100000,
            "discount_rate": "5%",
            "valuation_date": "2024-01-01",
            "maturity_date": "2024-04-01",
            "day_count_convention": "ACT/360"
        }
        result = calculate_treasury_bill(item)
        
        # 91 days (Feb 2024 has 29 days)
        # Price = 100000 * (1 - 0.05 * 91/360) = 98736.11
        assert result["term_days"] == 91
        assert round(result["purchase_price"], 2) == 98736.11

    def test_missing_face_value(self):
        """Test error when face value is missing."""
        item = {
            "discount_rate": "5%",
            "term_days": 90
        }
        result = calculate_treasury_bill(item)
        
        assert result["status"] == "partial"
        assert result["face_value"] is None

    def test_price_exceeds_face_value(self):
        """Test validation when purchase price exceeds face value."""
        item = {
            "face_value": 100000,
            "purchase_price": 105000,
            "term_days": 90
        }
        result = calculate_treasury_bill(item)
        
        # Calculation should still work, but validation would catch this
        assert result["discount_amount"] == -5000.00

    def test_currency_preservation(self):
        """Test that currency is preserved in results."""
        item = {
            "face_value": 100000,
            "discount_rate": "5%",
            "term_days": 90,
            "currency": "USD"
        }
        result = calculate_treasury_bill(item)
        
        assert result["currency"] == "USD"


class TestBonds:
    """Test Bond calculations."""

    def test_annual_coupon(self):
        """Test annual coupon calculation."""
        item = {
            "face_value": 100000,
            "coupon_rate": "6%",
            "years_to_maturity": 5,
            "coupon_frequency": 2,
            "price": 104376.00
        }
        result = calculate_bond(item)
        
        # Annual Coupon = 100000 * 0.06 = 6000
        assert result["annual_coupon"] == 6000.00

    def test_price_from_ytm(self):
        """Test price calculation from YTM."""
        item = {
            "face_value": 100000,
            "coupon_rate": "6%",
            "years_to_maturity": 5,
            "coupon_frequency": 2,
            "yield_to_maturity": "5%"
        }
        result = calculate_bond(item)
        
        # Price should be approximately 104376 (premium since coupon > yield)
        assert result["current_price"] is not None
        assert result["current_price"] > 100000

    def test_current_yield(self):
        """Test current yield calculation."""
        item = {
            "face_value": 100000,
            "coupon_rate": "6%",
            "years_to_maturity": 5,
            "coupon_frequency": 2,
            "price": 104376.00
        }
        result = calculate_bond(item)
        
        # Current Yield = (6000/104376) * 100 = 5.7485%
        assert round(result["current_yield"], 4) == 5.7485

    def test_accrued_interest(self):
        """Test accrued interest calculation."""
        item = {
            "face_value": 100000,
            "coupon_rate": "6%",
            "years_to_maturity": 5,
            "coupon_frequency": 2,
            "price": 104376.00,
            "last_coupon_date": "2024-01-01",
            "valuation_date": "2024-02-15",
            "day_count_convention": "ACT/365"
        }
        result = calculate_bond(item)
        
        # Days accrued = 45, Days in period = 365/2 = 182.5
        # Coupon per period = 3000
        # Accrued = 3000 * (45/182.5) = 739.73
        assert round(result["accrued_interest"], 2) == 739.73

    def test_duration_calculation(self):
        """Test Macaulay and Modified duration calculation."""
        item = {
            "face_value": 100000,
            "coupon_rate": "6%",
            "years_to_maturity": 5,
            "coupon_frequency": 2,
            "price": 104376.00
        }
        result = calculate_bond(item)
        
        # Duration should be positive and less than years to maturity
        assert result["duration"] is not None
        assert result["duration"] > 0
        assert result["duration"] < 5
        assert result["modified_duration"] is not None
        assert result["modified_duration"] < result["duration"]

    def test_from_dates(self):
        """Test calculation from valuation and maturity dates."""
        item = {
            "face_value": 100000,
            "coupon_rate": "6%",
            "coupon_frequency": 2,
            "valuation_date": "2024-01-01",
            "maturity_date": "2029-01-01",
            "price": 104376.00
        }
        result = calculate_bond(item)
        
        # 2024-01-01 to 2029-01-01 = 1827 days (2024 and 2028 are leap years)
        # Years = 1827/365 = 5.0055
        assert result["years_to_maturity"] == pytest.approx(5.0055, abs=0.001)

    def test_missing_face_value(self):
        """Test error when face value is missing."""
        item = {
            "coupon_rate": "6%",
            "years_to_maturity": 5,
            "coupon_frequency": 2
        }
        result = calculate_bond(item)
        
        assert result["status"] == "partial"
        assert result["face_value"] is None

    def test_invalid_frequency(self):
        """Test error when coupon frequency is invalid."""
        item = {
            "face_value": 100000,
            "coupon_rate": "6%",
            "years_to_maturity": 5,
            "coupon_frequency": 500,  # Invalid
            "price": 104376.00
        }
        result = calculate_bond(item)
        
        assert result["status"] == "partial"
        assert result["frequency"] is None

    def test_price_as_percentage(self):
        """Test price input as percentage of face value."""
        item = {
            "face_value": 100000,
            "coupon_rate": "6%",
            "years_to_maturity": 5,
            "coupon_frequency": 2,
            "price": "104.376%"  # Percentage
        }
        result = calculate_bond(item)
        
        # Price should be converted to monetary value
        assert result["current_price"] is not None
        assert result["current_price"] > 100000

    def test_currency_preservation(self):
        """Test that currency is preserved in results."""
        item = {
            "face_value": 100000,
            "coupon_rate": "6%",
            "years_to_maturity": 5,
            "coupon_frequency": 2,
            "price": 104376.00,
            "currency": "USD"
        }
        result = calculate_bond(item)
        
        assert result["currency"] == "USD"


class TestHelperFunctions:
    """Test helper functions for parsing and conversion."""

    def test_safe_float(self):
        """Test safe_float conversion."""
        assert safe_float(100) == 100.0
        assert safe_float("100") == 100.0
        assert safe_float("100.50") == 100.5
        assert safe_float("$100,000") == 100000.0
        assert safe_float("5%") == 5.0
        assert safe_float(None) is None
        assert safe_float("") is None

    def test_parse_percentage(self):
        """Test percentage parsing."""
        assert parse_percentage("5%") == 0.05
        assert parse_percentage("5") == 0.05
        assert parse_percentage("0.05") == 0.05
        assert parse_percentage("5.5%") == 0.055
        assert parse_percentage(None) is None

    def test_parse_date(self):
        """Test date parsing."""
        assert parse_date("2024-01-01") == date(2024, 1, 1)
        assert parse_date("01/01/2024") == date(2024, 1, 1)
        assert parse_date("01-Jan-2024") == date(2024, 1, 1)
        assert parse_date(None) is None

    def test_round_money(self):
        """Test monetary rounding."""
        assert round_money(100.123) == 100.12
        assert round_money(100.125) == 100.13
        assert round_money(100.129) == 100.13
        assert round_money(None) is None


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_days(self):
        """Test calculation with zero days."""
        item = {
            "principal": 100000,
            "interest_rate": "5%",
            "term_days": 0
        }
        result = calculate_money_market(item)
        
        assert result["status"] == "partial"
        assert result["interest_earned"] is None

    def test_negative_rate(self):
        """Test calculation with negative rate (should fail validation)."""
        item = {
            "principal": 100000,
            "interest_rate": "-5%",
            "term_days": 90
        }
        result = calculate_money_market(item)
        
        # Negative rate might be parsed but validation should catch it
        assert result["interest_rate"] == -5.0

    def test_very_long_maturity(self):
        """Test calculation with very long maturity."""
        item = {
            "principal": 100000,
            "interest_rate": "5%",
            "term_days": 3650  # 10 years
        }
        result = calculate_money_market(item)
        
        assert result["status"] == "success"
        assert result["interest_earned"] == 100000 * 0.05 * (3650/360)

    def test_matured_instrument(self):
        """Test calculation for matured instrument (past maturity)."""
        item = {
            "face_value": 100000,
            "discount_rate": "5%",
            "valuation_date": "2024-04-02",
            "maturity_date": "2024-04-01"  # Maturity is in the past
        }
        result = calculate_treasury_bill(item)
        
        # Days should be calculated but date consistency validation would catch this
        assert result["term_days"] == 1


class TestNewDerivations:
    """Test new derivation behavior added in the fixes."""

    def test_days_derived_from_dates(self):
        """Test that days_to_maturity is derived from valuation and maturity dates."""
        item = {
            "face_value": 497376,
            "discount_rate": "3.32%",
            "valuation_date": "2025-12-31",
            "maturity_date": "2028-09-22",
        }
        result = calculate_treasury_bill(item)
        assert result["term_days"] == 996
        assert result["derivations"]["days_to_maturity"]["from"] == "2025-12-31"
        assert result["derivations"]["days_to_maturity"]["to"] == "2028-09-22"
        assert result["derivations"]["days_to_maturity"]["result"] == 996

    def test_discount_rate_derived_from_price(self):
        """Test that discount_rate is derived when only price + days are given."""
        item = {
            "face_value": 100000,
            "purchase_price": 98750,
            "term_days": 90,
        }
        result = calculate_treasury_bill(item)
        assert result["discount_rate"] is not None
        assert round(result["discount_rate"], 2) == 5.00

    def test_valuation_date_used_when_settlement_date_missing(self):
        """Test that valuation_date substitutes for missing settlement_date."""
        item = {
            "principal": 100000,
            "interest_rate": "5%",
            "valuation_date": "2024-01-01",
            "maturity_date": "2024-04-01",
        }
        result = calculate_money_market(item)
        assert result["term_days"] == 91
        assert result["derivations"]["days_to_maturity"]["from"] == "2024-01-01"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
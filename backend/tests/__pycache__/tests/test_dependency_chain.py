"""
End-to-end verification for the calculation dependency chain.

Run:  pytest tests/test_dependency_chain.py -v

Covers:
  - Money Market, T-Bills, Bonds happy paths
  - Trade-Date-only fallback (no valuation_date, no term_days)
  - Rounding discipline (raw values propagate, only flat fields round)
  - Duplicate field elimination (aggregates don't multiply)
  - Missing prerequisites cascade safely
  - Benchmark Rate normalization (fraction vs percent)
  - Cross-call freshness (no module-level state)
"""

import math
import pytest
from decimal import Decimal, ROUND_HALF_UP

from pages.calculations_details import (
    calculate_money_market,
    calculate_treasury_bill,
    calculate_bond,
    calculate_data,
    _benchmark_to_percent,
    _rate,
    _half_up,
    round_money,
    round_time,
)


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────
def approx(a, b, rel=1e-9, abs_=1e-6):
    return math.isclose(a, b, rel_tol=rel, abs_tol=abs_)


def deriv(r, name):
    d = r.get("derivations", {}).get(name)
    assert d is not None, f"derivation '{name}' missing from result"
    return d


# ─────────────────────────────────────────────────────────────
# 1. MONEY MARKET
# ─────────────────────────────────────────────────────────────
class TestMoneyMarket:

    def test_explicit_term_days(self):
        """The canonical path — term_days input, no dates needed."""
        r = calculate_money_market({
            "principal": 100_000,
            "interest_rate": "5%",
            "term_days": 90,
            "day_count_convention": "ACT/360",
        })
        assert r["status"] == "success"
        assert r["term_days"] == 90
        assert r["principal"] == 100_000.00
        assert r["interest_rate"] == 5.0000

        # raw interest = 100000 * 0.05 * 90/360 = 1250.0
        assert approx(deriv(r, "interest_earned")["result_raw"], 1250.0)
        assert r["interest_earned"] == 1250.00
        assert r["total_interest"] == 1250.00

        # total = principal + raw interest
        assert approx(deriv(r, "total_value")["result_raw"], 101_250.0)
        assert r["total_value"] == 101_250.00
        assert r["maturity_value"] == 101_250.00
        assert r["fair_value"] == 101_250.00

        # discount_yield = (1250/101250) * 4 * 100 = 4.938271...
        assert approx(deriv(r, "discount_yield")["result_raw"],
                      1250.0 / 101_250.0 * 4 * 100.0)
        assert r["discount_yield"] == 4.9383

        # effective_annual_rate = (1250/100000) * (365/90) * 100 = 5.069444...
        assert approx(deriv(r, "effective_annual_rate")["result_raw"],
                      1250.0 / 100_000.0 * (365.0 / 90.0) * 100.0)
        assert r["effective_annual_rate"] == 5.0694
        assert r["annual_yield"] == r["effective_annual_rate"]

        # present_value = principal
        assert r["present_value"] == 100_000.00

    def test_trade_date_fallback(self):
        """
        THE FIX: cleaned data provides Trade Date + Maturity Date but NOT
        valuation_date and NOT term_days. Interest must still compute.
        """
        r = calculate_money_market({
            "principal": 18_000_000,
            "interest_rate": "10.16%",
            "trade_date": "2024-01-15",
            "maturity_date": "2024-04-15",
            "day_count_convention": "ACT/360",
        })
        assert r["status"] == "success"

        # 2024-01-15 → 2024-04-15 = 91 days (leap year)
        assert r["term_days"] == 91

        expected_interest = 18_000_000 * 0.1016 * (91.0 / 360.0)
        assert approx(deriv(r, "interest_earned")["result_raw"], expected_interest)
        assert r["interest_earned"] == round_money(expected_interest)
        assert r["interest_earned"] > 0
        assert r["total_interest"] == r["interest_earned"]

        assert r["total_value"] > 0
        assert r["total_value"] == round_money(18_000_000 + expected_interest)
        assert r["maturity_value"] == r["total_value"]
        assert r["fair_value"] == r["total_value"]
        assert r["present_value"] == 18_000_000.00

    def test_issue_date_fallback_when_trade_absent(self):
        """issue_date is the second-order fallback."""
        r = calculate_money_market({
            "principal": 100_000,
            "interest_rate": "5%",
            "issue_date": "2024-01-01",
            "maturity_date": "2024-04-01",
        })
        assert r["status"] == "success"
        assert r["term_days"] == 91

    def test_valuation_date_wins_when_present(self):
        """valuation_date takes precedence over issue_date."""
        r = calculate_money_market({
            "principal": 100_000,
            "interest_rate": "5%",
            "valuation_date": "2024-02-01",
            "issue_date": "2024-01-01",          # should be ignored
            "maturity_date": "2024-04-01",
        })
        assert r["term_days"] == 60                 # Feb 1 → Apr 1

    def test_missing_principal_skips_dependents(self):
        r = calculate_money_market({
            "interest_rate": "5%",
            "term_days": 90,
        })
        assert r["status"] == "partial"
        assert deriv(r, "interest_earned")["status"] == "skipped"
        assert deriv(r, "total_value")["status"] == "skipped"
        assert r["interest_earned"] is None if "interest_earned" in r else True

    def test_missing_days_skips_interest(self):
        r = calculate_money_market({
            "principal": 100_000,
            "interest_rate": "5%",
        })
        assert r["status"] == "partial"
        assert deriv(r, "days_to_maturity")["status"] == "skipped"
        assert deriv(r, "interest_earned")["status"] == "skipped"

    def test_zero_days_rejected(self):
        r = calculate_money_market({
            "principal": 100_000,
            "interest_rate": "5%",
            "valuation_date": "2024-06-01",
            "maturity_date": "2024-06-01",
        })
        assert r["status"] == "partial"
        assert deriv(r, "days_to_maturity")["status"] == "failed"

    def test_benchmark_rate_normalisation(self):
        # fraction form
        r1 = calculate_money_market({
            "principal": 100_000, "interest_rate": "5%", "term_days": 90,
        }, benchmark_yield=0.0441)
        assert r1["yield_curve_rate"] == 4.4100

        # percent form — must NOT become 441%
        r2 = calculate_money_market({
            "principal": 100_000, "interest_rate": "5%", "term_days": 90,
        }, benchmark_yield=4.41)
        assert r2["yield_curve_rate"] == 4.4100

        # None
        r3 = calculate_money_market({
            "principal": 100_000, "interest_rate": "5%", "term_days": 90,
        })
        assert r3["yield_curve_rate"] is None


# ─────────────────────────────────────────────────────────────
# 2. T-BILLS
# ─────────────────────────────────────────────────────────────
class TestTreasuryBill:

    def test_price_given(self):
        r = calculate_treasury_bill({
            "face_value": 100_000,
            "purchase_price": 98_750,
            "term_days": 90,
            "day_count_convention": "ACT/360",
        })
        assert r["status"] == "success"
        assert r["purchase_price"] == 98_750.00
        assert r["discount_amount"] == 1_250.00

        # THE FIX: present_value must equal the purchase price, not 99,987.50
        assert r["present_value"] == 98_750.00
        assert r["fair_value"] == 98_750.00

        assert r["discount_rate"] == 5.0000
        assert r["discount_yield"] == 5.0000
        assert r["money_market_yield"] == 5.0633
        assert r["bond_equivalent_yield"] == 5.1336
        assert r["holding_period_yield"] == 1.2658
        assert r["effective_annual_yield"] == 5.2338
        assert r["total_value"] == 100_000.00           # face
        assert r["maturity_value"] == 100_000.00

    def test_rate_given_derives_price(self):
        r = calculate_treasury_bill({
            "face_value": 100_000,
            "discount_rate": "5%",
            "term_days": 90,
            "day_count_convention": "ACT/360",
        })
        assert r["status"] == "success"
        assert r["purchase_price"] == 98_750.00
        assert r["discount_amount"] == 1_250.00
        assert r["present_value"] == 98_750.00
        assert r["fair_value"] == 98_750.00

    def test_trade_date_fallback(self):
        r = calculate_treasury_bill({
            "face_value": 100_000,
            "purchase_price": 98_750,
            "trade_date": "2024-01-01",
            "maturity_date": "2024-04-01",
        })
        assert r["status"] == "success"
        assert r["term_days"] == 91
        assert r["bond_equivalent_yield"] > 0
        assert r["present_value"] == 98_750.00

    def test_conflicting_inputs_warns(self):
        r = calculate_treasury_bill({
            "face_value": 100_000,
            "purchase_price": 99_000,
            "discount_rate": "5%",           # inconsistent with price
            "term_days": 90,
        })
        assert "warning" in r
        assert "purchase_price takes precedence" in r["warning"]
        # price wins: implied rate = 1000/100000 * 360/90 = 4.0%
        assert r["discount_rate"] == 4.0000

    def test_missing_prerequisites_skip_derived(self):
        r = calculate_treasury_bill({
            "face_value": 100_000,
            "term_days": 90,
        })
        assert r["status"] == "partial"
        assert deriv(r, "purchase_price")["status"] == "skipped"
        assert deriv(r, "discount_yield")["status"] == "skipped"

    def test_benchmark_normalisation(self):
        r = calculate_treasury_bill({
            "face_value": 100_000, "purchase_price": 98_750, "term_days": 90,
        }, benchmark_yield=0.0441)
        assert r["yield_curve_rate"] == 4.4100


# ─────────────────────────────────────────────────────────────
# 3. BONDS
# ─────────────────────────────────────────────────────────────
class TestBonds:

    def test_full_bond_from_ytm(self):
        r = calculate_bond({
            "face_value": 100_000,
            "coupon_rate": "6%",
            "years_to_maturity": 5,
            "coupon_frequency": 2,
            "yield_to_maturity": "5%",
        })
        assert r["status"] == "success"
        assert r["annual_coupon"] == 6_000.00
        assert r["coupon_payment"] == 3_000.00
        assert r["coupon_per_period"] == 3_000.00
        assert r["current_price"] == pytest.approx(104_376.02, abs=0.05)
        assert r["total_value"] == r["current_price"]
        assert r["present_value"] == r["current_price"]
        assert r["fair_value"] == r["current_price"]
        assert r["yield_to_maturity"] == 5.0000
        assert r["ytm_source"] == "input"
        assert r["current_yield"] == pytest.approx(5.7484, abs=0.001)
        assert r["macaulay_duration"] == pytest.approx(4.4856, abs=0.01)
        assert r["modified_duration"] == pytest.approx(4.3762, abs=0.01)
        assert 0 < r["modified_duration"] < r["macaulay_duration"]
        assert r["dv01"] == pytest.approx(45.68, abs=0.1)

    def test_bond_price_given_solves_ytm(self):
        r = calculate_bond({
            "face_value": 100_000,
            "coupon_rate": "6%",
            "years_to_maturity": 5,
            "coupon_frequency": 2,
            "price": 104_376,
        })
        assert r["status"] == "success"
        assert r["ytm_source"] == "solved_from_price"
        assert r["yield_to_maturity"] == pytest.approx(5.0, abs=0.01)

    def test_bond_input_ytm_wins_over_solver(self):
        r = calculate_bond({
            "face_value": 100_000,
            "coupon_rate": "6%",
            "years_to_maturity": 5,
            "coupon_frequency": 2,
            "price": 100_000,
            "yield_to_maturity": "7%",
        })
        assert r["yield_to_maturity"] == 7.0000
        assert r["ytm_source"] == "input"
        assert "warning" in r

    def test_bond_trade_date_fallback(self):
        r = calculate_bond({
            "face_value": 100_000,
            "coupon_rate": "6%",
            "coupon_frequency": 2,
            "trade_date": "2024-01-15",
            "maturity_date": "2029-01-15",
            "yield_to_maturity": "5%",
        })
        assert r["status"] == "success"
        assert r["years_to_maturity"] == pytest.approx(5.0, abs=0.02)
        assert r["current_price"] is not None

    def test_bond_defaults_frequency_when_missing(self):
        r = calculate_bond({
            "face_value": 100_000,
            "coupon_rate": "6%",
            "years_to_maturity": 5,
            "yield_to_maturity": "5%",
        })
        assert r["frequency"] == 2
        assert r["status"] == "partial"
        assert "defaulted to semi-annual" in r["warning"]

    def test_bond_missing_coupon_rate_skips_chain(self):
        r = calculate_bond({
            "face_value": 100_000,
            "years_to_maturity": 5,
            "coupon_frequency": 2,
            "price": 100_000,
        })
        assert r["status"] == "partial"
        assert deriv(r, "annual_coupon")["status"] == "skipped"
        assert deriv(r, "current_yield")["status"] == "skipped"


# ─────────────────────────────────────────────────────────────
# 4. AGGREGATES (multi-row)
# ─────────────────────────────────────────────────────────────
class TestAggregates:

    def test_multi_row_sum_no_duplicates(self):
        """Aggregates sum per-row values exactly once."""
        rows = [
            {"principal": 100_000, "interest_rate": "5%", "term_days": 90},
            {"principal": 200_000, "interest_rate": "6%", "term_days": 180},
        ]
        out = calculate_data(rows, "money-market")
        assert out["status"] == "success"
        assert out["instrument_count"] == 2

        i1 = 100_000 * 0.05 * (90.0 / 360.0)      # 1250.0
        i2 = 200_000 * 0.06 * (180.0 / 360.0)     # 6000.0
        agg = out["aggregates"]

        assert agg["total_principal"] == 300_000.00
        assert agg["total_interest"] == round_money(i1 + i2)
        assert agg["total_value"] == round_money(300_000 + i1 + i2)
        assert agg["avg_rate"] == 5.5000
        # weighted: (100000*5 + 200000*6)/300000 = 5.6667
        assert agg["weighted_avg_rate"] == pytest.approx(5.6667, abs=0.0001)

    def test_multi_row_trade_date_fallback(self):
        rows = [
            {"principal": 18_000_000, "interest_rate": "10.16%",
             "trade_date": "2024-01-15", "maturity_date": "2024-04-15"},
            {"principal": 5_000_000, "interest_rate": "9.5%",
             "trade_date": "2024-02-01", "maturity_date": "2024-05-01"},
        ]
        out = calculate_data(rows, "money-market")
        assert out["status"] == "success"
        assert out["instrument_count"] == 2
        agg = out["aggregates"]
        assert agg["total_interest"] > 0
        assert agg["total_value"] > agg["total_principal"]
        assert agg["avg_rate"] == pytest.approx(9.83, abs=0.01)

    def test_multi_row_tbills_present_value(self):
        rows = [
            {"face_value": 100_000, "purchase_price": 98_750, "term_days": 90},
            {"face_value": 200_000, "purchase_price": 195_000, "term_days": 180},
        ]
        out = calculate_data(rows, "tbills")
        agg = out["aggregates"]
        assert agg["total_face_value"] == 300_000.00
        assert agg["total_purchase_price"] == 293_750.00
        assert agg["total_discount"] == 6_250.00
        assert agg["present_value"] == 293_750.00
        assert agg["fair_value"] == 293_750.00

    def test_multi_row_bonds(self):
        rows = [
            {"face_value": 100_000, "coupon_rate": "6%",
             "years_to_maturity": 5, "coupon_frequency": 2,
             "yield_to_maturity": "5%"},
            {"face_value": 100_000, "coupon_rate": "8%",
             "years_to_maturity": 10, "coupon_frequency": 2,
             "yield_to_maturity": "7%"},
        ]
        out = calculate_data(rows, "bonds")
        agg = out["aggregates"]
        assert agg["total_face_value"] == 200_000.00
        assert agg["total_market_value"] > 0
        assert agg["total_value"] == agg["total_market_value"]
        assert agg["avg_coupon_rate"] == 7.0000
        assert agg["weighted_avg_coupon"] == 7.0000


# ─────────────────────────────────────────────────────────────
# 5. FRESHNESS
# ─────────────────────────────────────────────────────────────
class TestFreshness:

    def test_no_module_state(self):
        r1 = calculate_money_market({
            "principal": 100_000, "interest_rate": "5%", "term_days": 90,
        })
        r2 = calculate_money_market({
            "principal": 200_000, "interest_rate": "3%", "term_days": 180,
        })
        assert r1["interest_earned"] == 1_250.00
        assert r2["interest_earned"] == 3_000.00
        assert r1["interest_earned"] != r2["interest_earned"]

    def test_no_stale_between_instrument_types(self):
        mm = calculate_money_market({
            "principal": 100_000, "interest_rate": "5%", "term_days": 90,
        })
        tb = calculate_treasury_bill({
            "face_value": 100_000, "purchase_price": 98_750, "term_days": 90,
        })
        assert mm["instrument_type"] == "money-market"
        assert tb["instrument_type"] == "tbills"
        assert mm["interest_earned"] == 1_250.00
        assert tb["discount_amount"] == 1_250.00


# ─────────────────────────────────────────────────────────────
# 6. PRIMITIVES
# ─────────────────────────────────────────────────────────────
class TestPrimitives:

    def test_benchmark_to_percent(self):
        assert _benchmark_to_percent(0.0441) == 4.4100
        assert _benchmark_to_percent(4.41) == 4.4100
        assert _benchmark_to_percent(0.05) == 5.0000
        assert _benchmark_to_percent(5.00) == 5.0000
        assert _benchmark_to_percent(None) is None
        assert _benchmark_to_percent("bad") is None

    def test_rate_half_up(self):
        # financial rounding: 0.125 → 0.13, not banker's 0.12
        assert _rate(100.125) == 100.1250
        assert _rate(5.00005) == 5.0001
        assert _rate(None) is None

    def test_round_money_half_up(self):
        assert round_money(100.125) == 100.13
        assert round_money(100.124) == 100.12
        assert round_money(-100.125) == -100.13
        assert round_money(None) is None

    def test_round_time_whole_number(self):
        assert round_time(90.4) == 90
        assert round_time(90.5) == 91             # half-up, not banker's 90
        assert round_time(90.6) == 91
        assert round_time(None) is None
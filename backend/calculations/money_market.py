from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from utils.rounding import (
    round_percentage, round_money, round_value, auto_round_by_field_name,
)


_DATE_FORMATS = (
    "%Y-%m-%d", "%Y/%m/%d",
    "%d-%m-%Y", "%d/%m/%Y",
    "%m-%d-%Y", "%m/%d/%Y",
    "%d-%m-%y", "%d/%m/%y",
    "%m-%d-%y", "%m/%d/%y",
    "%d %b %Y", "%d-%b-%Y",
    "%d %b %y", "%d-%b-%y",
    "%d %B %Y", "%d-%B-%Y",
    "%b %d, %Y", "%b %d %Y",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
)


def _parse_date(value: Any) -> Optional[date]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)):
        n = float(value)
        if 1 <= n <= 2958465:
            return (datetime(1899, 12, 30) + timedelta(days=int(n))).date()
        return None
    s = str(value).strip()
    if not s:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _parse_percentage(value: Any) -> Optional[float]:
    if value is None or value == "" or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        v = float(value)
        return v / 100.0 if v > 1 else v
    s = str(value).strip()
    if not s:
        return None
    had_pct = s.endswith("%")
    if had_pct:
        s = s.rstrip("%").strip()
    s = s.replace(",", "").replace(" ", "")
    try:
        v = float(s)
    except ValueError:
        return None
    if had_pct:
        return v / 100.0
    return v / 100.0 if v > 1 else v


def _parse_float(value: Any) -> Optional[float]:
    if value is None or value == "" or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().replace(",", "").replace("$", "").replace(" ", "")
    if not s:
        return None
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1]
    try:
        return float(s)
    except ValueError:
        return None


def _basis_from(day_count: Any, default: float = 365.0) -> float:
    s = str(day_count or "").upper()
    if "365" in s:
        return 365.0
    if "360" in s:
        return 360.0
    return default


class MoneyMarketCalculator:
    def __init__(self):
        self.day_count_convention = 365
        self.compounding_frequency = 1

    def calculate_all_metrics(self, inputs: Dict,
                              benchmark_yield: Optional[float] = None,
                              inflation_rate: Optional[float] = None) -> Dict:
        results: Dict = {}
        derivations: Dict = {}
        validation_errors: List[str] = []

        face_value = _parse_float(inputs.get('face_value'))
        principal = _parse_float(inputs.get('principal') or inputs.get('amount'))
        interest_rate = _parse_percentage(
            inputs.get('interest_rate') or inputs.get('rate')
        )
        discount_rate = _parse_percentage(inputs.get('discount_rate'))
        purchase_price = _parse_float(
            inputs.get('purchase_price')
            or inputs.get('current_price')
            or inputs.get('price')
        )
        compounding_frequency = _parse_float(
            inputs.get('compounding_frequency', self.compounding_frequency)
        ) or 1
        compounding_frequency = int(compounding_frequency)

        day_count_input = inputs.get('day_count_convention', 'ACT/365')
        basis = _basis_from(day_count_input, self.day_count_convention)

        issue_date = _parse_date(inputs.get('issue_date'))
        maturity_date = _parse_date(inputs.get('maturity_date'))
        settlement_date = _parse_date(
            inputs.get('settlement_date') or inputs.get('valuation_date')
        )
        provided_days = _parse_float(
            inputs.get('days_to_maturity') or inputs.get('term_days')
        )

        # ---- Days to maturity ----
        days_to_maturity = None
        if provided_days is not None and provided_days > 0:
            days_to_maturity = int(provided_days)
            derivations['days_to_maturity'] = {
                'formula': 'provided directly',
                'result': days_to_maturity,
                'unit': 'days',
            }
        elif settlement_date and maturity_date:
            days_to_maturity = (maturity_date - settlement_date).days
            derivations['days_to_maturity'] = {
                'formula': 'maturity_date - valuation_date',
                'from': settlement_date.isoformat(),
                'to': maturity_date.isoformat(),
                'result': days_to_maturity,
                'unit': 'days',
            }
            if days_to_maturity < 0:
                validation_errors.append(
                    f"Maturity date {maturity_date.isoformat()} is before valuation date "
                    f"{settlement_date.isoformat()}"
                )
                days_to_maturity = None
        else:
            validation_errors.append(
                "Missing days_to_maturity (or both Valuation Date and Maturity Date)"
            )

        if days_to_maturity is not None and days_to_maturity <= 0:
            validation_errors.append("days_to_maturity must be greater than zero")
            days_to_maturity = None

        results['days_to_maturity'] = days_to_maturity
        results['term_days'] = days_to_maturity

        # ---- Auxiliary day counts ----
        if issue_date and settlement_date:
            results['days_since_issue'] = (settlement_date - issue_date).days
            derivations['days_since_issue'] = {
                'formula': 'valuation_date - issue_date',
                'from': issue_date.isoformat(),
                'to': settlement_date.isoformat(),
                'result': results['days_since_issue'],
                'unit': 'days',
            }
        if issue_date and maturity_date:
            total = (maturity_date - issue_date).days
            results['total_term_days'] = total
            derivations['total_term_days'] = {
                'formula': 'maturity_date - issue_date',
                'from': issue_date.isoformat(),
                'to': maturity_date.isoformat(),
                'result': total,
                'unit': 'days',
            }
            if issue_date and settlement_date:
                results['remaining_days'] = total - (settlement_date - issue_date).days

        if days_to_maturity is not None:
            results['time_to_maturity'] = round_value(days_to_maturity / basis, 4)
        else:
            results['time_to_maturity'] = None

        results['face_value'] = round_money(face_value) if face_value is not None else None
        results['principal'] = round_money(principal) if principal is not None else None
        results['day_count_convention'] = str(day_count_input)

        # ---- Interest-based calculations ----
        if (principal is not None and principal > 0
                and interest_rate is not None and days_to_maturity):

            simple_interest = principal * interest_rate * (days_to_maturity / basis)
            results['simple_interest'] = round_money(simple_interest)
            results['interest_earned'] = round_money(simple_interest)
            derivations['simple_interest'] = {
                'formula': 'principal * interest_rate * days / basis',
                'inputs': {
                    'principal': principal, 'interest_rate': interest_rate,
                    'days': days_to_maturity, 'basis': basis,
                },
                'result': results['simple_interest'],
            }

            if compounding_frequency > 1 and results.get('time_to_maturity'):
                t = results['time_to_maturity']
                compound = principal * (
                    (1 + interest_rate / compounding_frequency)
                    ** (compounding_frequency * t)
                ) - principal
                results['compound_interest'] = round_money(compound)

            present_value = principal / (1 + interest_rate * (days_to_maturity / basis))
            results['present_value'] = round_money(present_value)
            results['fair_value'] = results['present_value']
            results['market_value'] = results['present_value']
            results['settlement_amount'] = results['present_value']
            results['investment_cost'] = results['present_value']
            results['net_investment'] = results['present_value']
            derivations['present_value'] = {
                'formula': 'principal / (1 + interest_rate * days / basis)',
                'result': results['present_value'],
            }

            redemption = principal + simple_interest
            results['redemption_value'] = round_money(redemption)
            results['gross_investment'] = round_money(principal)
            results['investment_return'] = round_money(redemption - present_value)

            hpy = (redemption - present_value) / present_value if present_value else None
            if hpy is not None:
                results['holding_period_yield'] = round_percentage(hpy * 100)

            t = days_to_maturity / basis
            if t > 0 and hpy is not None:
                annualized_hpy = hpy / t
                results['annualized_holding_period_yield'] = round_percentage(annualized_hpy * 100)

            mmy = (principal - present_value) / present_value * (basis / days_to_maturity)
            results['money_market_yield'] = round_percentage(mmy * 100)

            effective = (1 + interest_rate / compounding_frequency) ** compounding_frequency - 1
            results['effective_yield'] = round_percentage(effective * 100)
            results['effective_annual_rate'] = results['effective_yield']
            results['annual_percentage_yield'] = results['effective_yield']

            current_yield = simple_interest / present_value if present_value else None
            if current_yield is not None:
                results['current_yield'] = round_percentage(current_yield * 100)

            ytm = (redemption - present_value) / present_value / t if t > 0 else None
            if ytm is not None:
                results['yield_to_maturity'] = round_percentage(ytm * 100)

            results['nominal_annual_rate'] = round_percentage(interest_rate * 100)

        # ---- Discount-based calculations ----
        if (discount_rate is not None and face_value is not None
                and face_value > 0 and days_to_maturity):

            discount_amount = face_value * discount_rate * days_to_maturity / basis
            results['discount_amount'] = round_money(discount_amount)
            derivations['discount_amount'] = {
                'formula': 'face_value * discount_rate * days / basis',
                'result': results['discount_amount'],
            }

            discount_price = face_value - discount_amount
            results['purchase_price'] = round_money(discount_price)
            results['present_value'] = round_money(discount_price)

            results['annual_discount_rate'] = round_percentage(discount_rate * 100)
            results['discount_rate'] = round_percentage(discount_rate * 100)

        # ---- Benchmark ----
        if benchmark_yield is not None:
            results['benchmark_yield'] = round_percentage(benchmark_yield * 100)
            results['benchmark_yield_comparison'] = round_percentage(benchmark_yield * 100)
            if results.get('yield_to_maturity') is not None:
                spread = results['yield_to_maturity'] / 100 - benchmark_yield
                results['benchmark_spread'] = round_percentage(spread * 100)
                results['risk_free_spread'] = results['benchmark_spread']

        # ---- Real yield ----
        if inflation_rate is not None and results.get('yield_to_maturity') is not None:
            real = (1 + results['yield_to_maturity'] / 100) / (1 + inflation_rate) - 1
            results['real_yield'] = round_percentage(real * 100)

        results['derivations'] = derivations
        results['validation_errors'] = validation_errors
        results['calculation_status'] = 'partial_success' if validation_errors else 'success'
        return results


def calculate_money_market(inputs: Dict, benchmark_yield: Optional[float] = None,
                           inflation_rate: Optional[float] = None) -> Dict:
    calculator = MoneyMarketCalculator()
    results = calculator.calculate_all_metrics(inputs, benchmark_yield, inflation_rate)
    return {key: auto_round_by_field_name(key, value) for key, value in results.items()}
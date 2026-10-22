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


def _parse_frequency(value: Any) -> Optional[int]:
    if value is None or value == "" or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        v = int(value)
        return v if v in (1, 2, 4, 12) else None
    s = str(value).strip().lower()
    mapping = {
        'annual': 1, 'annually': 1, 'yearly': 1, '1': 1,
        'once per year': 1, 'once': 1, 'bullet': 1, 'zero': 1, 'none': 1,
        'semi-annual': 2, 'semiannual': 2, 'semi-annually': 2,
        'semiannually': 2, 'semi annual': 2, 'semi annually': 2,
        'biannual': 2, 'bi-annual': 2, 'half-yearly': 2, 'half yearly': 2,
        'twice per year': 2, '2': 2,
        'quarterly': 4, 'quarter': 4, '4': 4, 'four times per year': 4,
        'monthly': 12, 'month': 12, '12': 12, 'twelve times per year': 12,
    }
    return mapping.get(s)


def _basis_from(day_count: Any, default: float = 365.0) -> float:
    s = str(day_count or "").upper()
    if "365" in s:
        return 365.0
    if "360" in s:
        return 360.0
    return default


def _last_coupon_date(issue_date: Optional[date],
                      settlement_date: Optional[date],
                      frequency: int) -> Optional[date]:
    if not issue_date or not settlement_date or frequency <= 0:
        return issue_date
    elapsed = (settlement_date - issue_date).days
    if elapsed <= 0:
        return issue_date
    period_days = 365.0 / frequency
    periods = int(elapsed / period_days)
    return issue_date + timedelta(days=int(round(periods * period_days)))


def _next_coupon_date(last_coupon_date: Optional[date],
                      frequency: int) -> Optional[date]:
    if not last_coupon_date or frequency <= 0:
        return None
    period_days = 365.0 / frequency
    return last_coupon_date + timedelta(days=int(round(period_days)))


class BondsCalculator:
    def __init__(self):
        self.day_count_convention = 365
        self.compounding_frequency = 2

    def calculate_all_metrics(self, inputs, benchmark_yield=None,
                              benchmark_curve=None, inflation_rate=None,
                              valuation_date=None):
        results: Dict = {}
        derivations: Dict = {}
        validation_errors: List[str] = []

        face_value = _parse_float(inputs.get('face_value') or inputs.get('par_value'))
        coupon_rate = _parse_percentage(
            inputs.get('coupon_rate') or inputs.get('interest_rate')
        )
        ytm_input = _parse_percentage(
            inputs.get('yield_to_maturity') or inputs.get('ytm') or inputs.get('yield')
        )
        market_price = _parse_float(
            inputs.get('market_price')
            or inputs.get('clean_price')
            or inputs.get('price')
            or inputs.get('current_price')
        )

        day_count_input = inputs.get('day_count_convention', 'ACT/365')
        basis = _basis_from(day_count_input, self.day_count_convention)

        frequency = _parse_frequency(
            inputs.get('coupon_frequency') or inputs.get('frequency')
        )
        if frequency is None or frequency not in (1, 2, 4, 12):
            frequency = None

        issue_date = _parse_date(inputs.get('issue_date'))
        maturity_date = _parse_date(inputs.get('maturity_date'))
        settlement_date = _parse_date(
            inputs.get('settlement_date')
            or inputs.get('valuation_date')
            or valuation_date
        )
        call_date = _parse_date(inputs.get('call_date'))
        call_price = _parse_float(inputs.get('call_price'))
        put_date = _parse_date(inputs.get('put_date'))
        put_price = _parse_float(inputs.get('put_price'))

        provided_years = _parse_float(inputs.get('years_to_maturity'))
        provided_days = _parse_float(inputs.get('days_to_maturity'))

        # ---- Time to maturity ----
        years_to_maturity: Optional[float] = None
        days_to_maturity: Optional[int] = None

        if provided_years is not None and provided_years > 0:
            years_to_maturity = float(provided_years)
            days_to_maturity = int(round(years_to_maturity * 365))
            derivations['years_to_maturity'] = {
                'formula': 'provided directly',
                'result': round(years_to_maturity, 4),
                'unit': 'years',
            }
        elif provided_days is not None and provided_days > 0:
            days_to_maturity = int(provided_days)
            years_to_maturity = days_to_maturity / 365.0
        elif settlement_date and maturity_date:
            days_to_maturity = (maturity_date - settlement_date).days
            years_to_maturity = days_to_maturity / 365.0
            derivations['days_to_maturity'] = {
                'formula': 'maturity_date - valuation_date',
                'from': settlement_date.isoformat(),
                'to': maturity_date.isoformat(),
                'result': days_to_maturity,
                'unit': 'days',
            }
            derivations['years_to_maturity'] = {
                'formula': 'days_to_maturity / 365',
                'result': round(years_to_maturity, 4),
                'unit': 'years',
            }
            if days_to_maturity < 0:
                validation_errors.append(
                    f"Maturity date {maturity_date.isoformat()} is before valuation date "
                    f"{settlement_date.isoformat()}"
                )
                years_to_maturity = None
                days_to_maturity = None
        else:
            validation_errors.append(
                "Cannot determine time to maturity: missing maturity_date + settlement_date"
            )

        results['years_to_maturity'] = (round_value(years_to_maturity, 4)
                                        if years_to_maturity else None)
        results['days_to_maturity'] = days_to_maturity
        results['time_to_maturity'] = results['years_to_maturity']

        # ---- Face value + coupon ----
        results['face_value'] = round_money(face_value) if face_value is not None else None
        results['par_value'] = results['face_value']
        results['coupon_rate'] = (round_percentage(coupon_rate * 100)
                                  if coupon_rate is not None else None)
        results['coupon_frequency'] = frequency

        coupon_payment = None
        if face_value is not None and coupon_rate is not None and frequency:
            annual_coupon = face_value * coupon_rate
            results['annual_coupon'] = round_money(annual_coupon)
            coupon_payment = annual_coupon / frequency
            results['coupon_payment'] = round_money(coupon_payment)

        # ---- Price / YTM resolution ----
        price = market_price
        ytm = ytm_input

        can_solve = (face_value is not None and face_value > 0
                     and coupon_rate is not None
                     and years_to_maturity is not None and years_to_maturity > 0
                     and frequency is not None and frequency > 0)

        if price is None and ytm is not None and can_solve:
            price = self._calculate_clean_price(
                face_value, coupon_rate, ytm, years_to_maturity, frequency
            )
            derivations['clean_price'] = {
                'formula': 'PV(coupons) + PV(face) discounted at ytm/frequency',
                'inputs': {
                    'face_value': face_value, 'coupon_rate': coupon_rate,
                    'ytm': ytm, 'years': years_to_maturity, 'frequency': frequency,
                },
                'result': round(price, 2) if price else None,
            }

        if price is not None and ytm is None and can_solve:
            solved = self._solve_yield(
                price, face_value, face_value, coupon_rate,
                years_to_maturity, frequency
            )
            if solved is not None:
                ytm = solved
                derivations['yield_to_maturity'] = {
                    'formula': 'solve: price = PV(coupons) + PV(face)',
                    'inputs': {
                        'price': price, 'face_value': face_value,
                        'coupon_rate': coupon_rate, 'years': years_to_maturity,
                        'frequency': frequency,
                    },
                    'result': round(ytm * 100, 4),
                    'unit': '%',
                }

        if price is None and ytm is None:
            validation_errors.append(
                "Need either market_price or yield_to_maturity to value the bond"
            )

        if price is not None and price > 0:
            results['clean_price'] = round_money(price)
            results['present_value'] = results['clean_price']
            results['fair_value'] = results['clean_price']
            results['market_value'] = results['clean_price']
            results['current_price'] = results['clean_price']

        if ytm is not None:
            results['yield_to_maturity'] = round_percentage(ytm * 100)

        # ---- Accrued interest using last coupon date ----
        if (face_value is not None and coupon_rate is not None
                and frequency and settlement_date):
            annual_coupon = face_value * coupon_rate
            coupon_payment = annual_coupon / frequency
            last_coupon = _last_coupon_date(issue_date, settlement_date, frequency)
            if last_coupon:
                days_accrued = (settlement_date - last_coupon).days
                days_in_period = basis / frequency
                if days_in_period > 0:
                    accrued = coupon_payment * (days_accrued / days_in_period)
                    results['accrued_interest'] = round_money(accrued)
                    results['days_accrued'] = days_accrued
                    results['days_in_coupon_period'] = int(round(days_in_period))
                    derivations['accrued_interest'] = {
                        'formula': 'coupon_payment * (days_accrued / days_in_period)',
                        'inputs': {
                            'coupon_payment': round(coupon_payment, 2),
                            'days_accrued': days_accrued,
                            'days_in_period': int(round(days_in_period)),
                            'last_coupon_date': last_coupon.isoformat(),
                            'settlement_date': settlement_date.isoformat(),
                        },
                        'result': round(accrued, 2),
                    }
                    next_coupon = _next_coupon_date(last_coupon, frequency)
                    if next_coupon:
                        results['next_coupon_date'] = next_coupon.isoformat()
                        results['days_to_next_coupon'] = (next_coupon - settlement_date).days
                        derivations['days_to_next_coupon'] = {
                            'formula': 'next_coupon_date - valuation_date',
                            'from': settlement_date.isoformat(),
                            'to': next_coupon.isoformat(),
                            'result': results['days_to_next_coupon'],
                            'unit': 'days',
                        }

        if (results.get('clean_price') is not None
                and results.get('accrued_interest') is not None):
            results['dirty_price'] = round_money(
                results['clean_price'] + results['accrued_interest']
            )
            results['settlement_value'] = results['dirty_price']

        # ---- Premium / discount / redemption ----
        if face_value is not None:
            results['redemption_value'] = round_money(face_value)
        if results.get('clean_price') is not None and face_value is not None:
            if results['clean_price'] > face_value:
                results['premium'] = round_money(results['clean_price'] - face_value)
                results['discount'] = round_money(0)
            elif results['clean_price'] < face_value:
                results['discount'] = round_money(face_value - results['clean_price'])
                results['premium'] = round_money(0)
            else:
                results['premium'] = round_money(0)
                results['discount'] = round_money(0)

        # ---- Current yield ----
        if (results.get('annual_coupon') is not None
                and results.get('clean_price')
                and results['clean_price'] > 0):
            cy = results['annual_coupon'] / results['clean_price'] * 100
            results['current_yield'] = round_percentage(cy)

        # ---- Durations, convexity, DV01 ----
        if (ytm is not None and face_value is not None
                and coupon_rate is not None
                and years_to_maturity and frequency):
            mac = self._calculate_macaulay_duration(
                face_value, coupon_rate, ytm, years_to_maturity, frequency
            )
            results['macaulay_duration'] = round_value(mac, 4) if mac is not None else None
            results['duration'] = results['macaulay_duration']

            mod = self._calculate_modified_duration(mac, ytm, frequency)
            results['modified_duration'] = round_value(mod, 4) if mod is not None else None

            conv = self._calculate_convexity(
                face_value, coupon_rate, ytm, years_to_maturity, frequency
            )
            results['convexity'] = round_value(conv, 4) if conv is not None else None

            if results.get('clean_price') and mod is not None:
                dv01 = results['clean_price'] * mod * 0.0001
                results['dv01'] = round_value(dv01, 4)
                results['pvbp'] = results['dv01']

        # ---- YTC / YTP / YTW ----
        if (call_date and call_price and settlement_date
                and face_value is not None and coupon_rate is not None
                and frequency and results.get('clean_price')):
            years_to_call = (call_date - settlement_date).days / 365.0
            if years_to_call > 0:
                ytc = self._solve_yield(
                    results['clean_price'], call_price, face_value,
                    coupon_rate, years_to_call, frequency
                )
                if ytc is not None:
                    results['yield_to_call'] = round_percentage(ytc * 100)

        if (put_date and put_price and settlement_date
                and face_value is not None and coupon_rate is not None
                and frequency and results.get('clean_price')):
            years_to_put = (put_date - settlement_date).days / 365.0
            if years_to_put > 0:
                ytp = self._solve_yield(
                    results['clean_price'], put_price, face_value,
                    coupon_rate, years_to_put, frequency
                )
                if ytp is not None:
                    results['yield_to_put'] = round_percentage(ytp * 100)

        if ytm is not None:
            candidates = [ytm]
            if results.get('yield_to_call') is not None:
                candidates.append(results['yield_to_call'] / 100)
            if results.get('yield_to_put') is not None:
                candidates.append(results['yield_to_put'] / 100)
            results['yield_to_worst'] = round_percentage(min(candidates) * 100)

        # ---- Effective annual yield ----
        if ytm is not None and frequency:
            eay = (1 + ytm / frequency) ** frequency - 1
            results['effective_annual_yield'] = round_percentage(eay * 100)

        # ---- Benchmark ----
        if benchmark_yield is not None:
            results['benchmark_yield'] = round_percentage(benchmark_yield * 100)
            results['benchmark_yield_comparison'] = round_percentage(benchmark_yield * 100)
            if results.get('yield_to_maturity') is not None:
                spread = results['yield_to_maturity'] / 100 - benchmark_yield
                results['benchmark_spread'] = round_percentage(spread * 100)
                results['g_spread'] = results['benchmark_spread']

        # ---- Real yield ----
        if inflation_rate is not None and results.get('yield_to_maturity') is not None:
            real = (1 + results['yield_to_maturity'] / 100) / (1 + inflation_rate) - 1
            results['real_yield'] = round_percentage(real * 100)

        # ---- Holding period return (only if price is user-supplied, not YTM-derived) ----
        if (market_price is not None and results.get('coupon_payment') is not None
                and years_to_maturity and frequency and results.get('clean_price')):
            annual_coupon = results['coupon_payment'] * frequency
            total_coupons = annual_coupon * years_to_maturity
            hpr = (total_coupons + (face_value - results['clean_price'])) / results['clean_price'] / years_to_maturity
            results['holding_period_return'] = round_percentage(hpr * 100)
            results['coupon_income'] = round_money(total_coupons)
            results['capital_gain_loss'] = round_money(face_value - results['clean_price'])
            results['total_return'] = round_money(total_coupons + (face_value - results['clean_price']))

        if valuation_date:
            results['valuation_date'] = valuation_date
            results['Valuation Date'] = valuation_date

        results['derivations'] = derivations
        results['validation_errors'] = validation_errors
        results['calculation_status'] = 'partial_success' if validation_errors else 'success'
        return results

    # ---- Helpers ----

    def _calculate_coupon_payment(self, face_value, coupon_rate, frequency):
        if face_value is None or coupon_rate is None or not frequency:
            return None
        return face_value * coupon_rate / frequency

    def _calculate_clean_price(self, face_value, coupon_rate, ytm,
                               years, frequency):
        coupon_payment = self._calculate_coupon_payment(face_value, coupon_rate, frequency)
        if coupon_payment is None or years is None or years <= 0:
            return None
        n = max(1, int(round(years * frequency)))
        r = ytm / frequency
        if r <= -1:
            return None
        try:
            pv = sum(coupon_payment / ((1 + r) ** t) for t in range(1, n + 1))
            pv += face_value / ((1 + r) ** n)
            return pv
        except (OverflowError, ZeroDivisionError):
            return None

    def _solve_yield(self, current_price, final_cash_flow, face_value,
                     coupon_rate, years, frequency):
        if not current_price or current_price <= 0:
            return None
        if not final_cash_flow or final_cash_flow <= 0:
            return None
        if not face_value or face_value <= 0:
            return None
        if coupon_rate is None or years is None or years <= 0:
            return None
        if not frequency or frequency <= 0:
            return None

        n = max(1, int(round(years * frequency)))
        coupon = face_value * coupon_rate / frequency

        def pv(y):
            r = y / frequency
            if r <= -1:
                return float('inf')
            try:
                total = sum(coupon / ((1 + r) ** t) for t in range(1, n + 1))
                total += final_cash_flow / ((1 + r) ** n)
                return total
            except (OverflowError, ZeroDivisionError):
                return float('inf')

        lo, hi = -0.99, 10.0
        f_lo = pv(lo) - current_price
        f_hi = pv(hi) - current_price
        if f_lo * f_hi > 0:
            return None
        for _ in range(200):
            mid = (lo + hi) / 2
            f_mid = pv(mid) - current_price
            if abs(f_mid) < 1e-6 or (hi - lo) < 1e-10:
                return mid
            if f_mid * f_lo < 0:
                hi = mid
            else:
                lo = mid
                f_lo = f_mid
        return (lo + hi) / 2

    def _calculate_macaulay_duration(self, face_value, coupon_rate, ytm,
                                     years, frequency):
        coupon_payment = self._calculate_coupon_payment(face_value, coupon_rate, frequency)
        clean_price = self._calculate_clean_price(
            face_value, coupon_rate, ytm, years, frequency
        )
        if coupon_payment is None or clean_price is None or clean_price == 0:
            return None
        n = max(1, int(round(years * frequency)))
        r = ytm / frequency
        if r <= -1:
            return None
        try:
            weighted = sum(
                t * coupon_payment / ((1 + r) ** t) for t in range(1, n + 1)
            )
            weighted += n * face_value / ((1 + r) ** n)
            return (weighted / clean_price) / frequency
        except (OverflowError, ZeroDivisionError):
            return None

    def _calculate_modified_duration(self, macaulay_duration, ytm, frequency):
        if macaulay_duration is None or ytm is None or not frequency:
            return None
        return macaulay_duration / (1 + ytm / frequency)

    def _calculate_convexity(self, face_value, coupon_rate, ytm,
                             years, frequency):
        coupon_payment = self._calculate_coupon_payment(face_value, coupon_rate, frequency)
        clean_price = self._calculate_clean_price(
            face_value, coupon_rate, ytm, years, frequency
        )
        if coupon_payment is None or clean_price is None or clean_price == 0:
            return None
        n = max(1, int(round(years * frequency)))
        r = ytm / frequency
        if r <= -1:
            return None
        try:
            total = 0.0
            for t in range(1, n + 1):
                pv = coupon_payment / ((1 + r) ** t)
                total += (t * (t + 1) * pv) / ((1 + r) ** 2)
            pv_face = face_value / ((1 + r) ** n)
            total += (n * (n + 1) * pv_face) / ((1 + r) ** 2)
            return total / clean_price / (frequency ** 2)
        except (OverflowError, ZeroDivisionError):
            return None


def calculate_bonds(inputs, benchmark_yield=None, benchmark_curve=None,
                    inflation_rate=None, valuation_date=None):
    calculator = BondsCalculator()
    results = calculator.calculate_all_metrics(
        inputs, benchmark_yield, benchmark_curve, inflation_rate, valuation_date
    )
    return {key: auto_round_by_field_name(key, value) for key, value in results.items()}
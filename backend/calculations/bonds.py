from datetime import datetime
from typing import Dict, Optional, List
from utils.rounding import (
    round_percentage, round_money, round_value, auto_round_by_field_name
)
from utils.calculation_dependencies import CalculationDependencyEngine


class BondsCalculator:

    def __init__(self):
        self.day_count_convention = 365
        self.compounding_frequency = 2
        self.dependency_engine = CalculationDependencyEngine()

    def calculate_all_metrics(self, inputs, benchmark_yield=None,
                              benchmark_curve=None, inflation_rate=None,
                              valuation_date=None):
        results = {}
        validation_errors = []

        face_value = inputs.get('face_value')
        coupon_rate = inputs.get('coupon_rate')
        yield_to_maturity = inputs.get('yield_to_maturity')
        years_to_maturity = inputs.get('years_to_maturity')
        coupon_frequency = inputs.get('coupon_frequency', self.compounding_frequency)
        issue_date = inputs.get('issue_date')
        maturity_date = inputs.get('maturity_date')
        call_date = inputs.get('call_date')
        call_price = inputs.get('call_price')
        put_date = inputs.get('put_date')
        put_price = inputs.get('put_price')
        market_price = inputs.get('market_price')
        day_count_convention = inputs.get('day_count_convention', self.day_count_convention)
        settlement_date = valuation_date if valuation_date else inputs.get('settlement_date')

        available_fields = {
            'face_value': face_value,
            'coupon_rate': coupon_rate,
            'yield_to_maturity': yield_to_maturity,
            'years_to_maturity': years_to_maturity,
            'coupon_frequency': coupon_frequency,
            'settlement_date': settlement_date,
            'issue_date': issue_date,
            'maturity_date': maturity_date,
            'call_date': call_date,
            'call_price': call_price,
            'put_date': put_date,
            'put_price': put_price,
            'market_price': market_price,
            'day_count_convention': day_count_convention,
        }

        if maturity_date and settlement_date:
            validation = self.dependency_engine.validate_calculation(
                'term_to_maturity', available_fields, 'bonds'
            )
            if validation.can_calculate:
                years_to_maturity = self._calculate_years_to_maturity(
                    settlement_date, maturity_date, day_count_convention
                )
                days_to_maturity = self._calculate_days_to_maturity(settlement_date, maturity_date)
                results['years_to_maturity'] = round_value(years_to_maturity, 2)
                results['days_to_maturity'] = days_to_maturity
                available_fields['years_to_maturity'] = years_to_maturity
                available_fields['days_to_maturity'] = days_to_maturity
            else:
                validation_errors.append(self.dependency_engine.get_missing_fields_message(validation))
                results['years_to_maturity'] = None
                results['days_to_maturity'] = None
        elif years_to_maturity is not None:
            days_to_maturity = int(years_to_maturity * 365)
            results['years_to_maturity'] = round_value(years_to_maturity, 2)
            results['days_to_maturity'] = days_to_maturity
        else:
            validation_errors.append("Cannot calculate time to maturity: missing maturity_date and settlement_date")
            results['years_to_maturity'] = None
            results['days_to_maturity'] = None

        results['time_to_maturity'] = (
            round_value(years_to_maturity, 2) if years_to_maturity is not None else None
        )

        if face_value is not None:
            results['face_value'] = round_money(face_value)
            results['par_value'] = round_money(face_value)
        else:
            results['face_value'] = None
            results['par_value'] = None

        if face_value is not None and coupon_rate is not None:
            available_fields['face_value'] = face_value
            available_fields['coupon_rate'] = coupon_rate
            available_fields['coupon_frequency'] = coupon_frequency
            validation = self.dependency_engine.validate_calculation(
                'coupon_payment', available_fields, 'bonds'
            )
            if validation.can_calculate:
                coupon_payment = self._calculate_coupon_payment(face_value, coupon_rate, coupon_frequency)
                results['coupon_payment'] = round_money(coupon_payment)
                available_fields['coupon_payment'] = coupon_payment
            else:
                validation_errors.append(self.dependency_engine.get_missing_fields_message(validation))
                results['coupon_payment'] = None

        results['coupon_rate'] = (
            round_percentage(coupon_rate * 100) if coupon_rate is not None else None
        )

        if yield_to_maturity is not None and face_value is not None and years_to_maturity is not None:
            available_fields['yield_to_maturity'] = yield_to_maturity
            available_fields['years_to_maturity'] = years_to_maturity

            validation = self.dependency_engine.validate_calculation(
                'bond_price', available_fields, 'bonds'
            )
            if validation.can_calculate:
                clean_price = self._calculate_clean_price(
                    face_value, coupon_rate, yield_to_maturity, years_to_maturity, coupon_frequency
                )
                results['clean_price'] = round_money(clean_price)
                available_fields['clean_price'] = clean_price
            else:
                validation_errors.append(self.dependency_engine.get_missing_fields_message(validation))
                results['clean_price'] = None

            if results.get('clean_price') is not None:
                results['present_value'] = results['clean_price']
                results['fair_value'] = results['clean_price']
                results['market_value'] = results['clean_price']

            if settlement_date and issue_date and coupon_rate is not None:
                coupon_payment = self._calculate_coupon_payment(face_value, coupon_rate, coupon_frequency)
                accrued_interest = self._calculate_accrued_interest(
                    coupon_payment, coupon_frequency, settlement_date, issue_date
                )
                if accrued_interest is not None:
                    results['accrued_interest'] = round_money(accrued_interest)
                    available_fields['accrued_interest'] = accrued_interest

            if results.get('clean_price') is not None and results.get('accrued_interest') is not None:
                results['dirty_price'] = round_money(
                    results['clean_price'] + results['accrued_interest']
                )

            if results.get('dirty_price') is not None:
                results['settlement_value'] = results['dirty_price']

            if face_value is not None:
                results['redemption_value'] = round_money(face_value)

            if results.get('clean_price') is not None:
                if results['clean_price'] > face_value:
                    results['premium'] = round_money(results['clean_price'] - face_value)
                    results['discount'] = round_money(0)
                elif results['clean_price'] < face_value:
                    results['discount'] = round_money(face_value - results['clean_price'])
                    results['premium'] = round_money(0)
                else:
                    results['premium'] = round_money(0)
                    results['discount'] = round_money(0)

            if results.get('coupon_payment') is not None and results.get('clean_price') is not None:
                current_yield = self._calculate_current_yield(
                    results['coupon_payment'], results['clean_price'], coupon_frequency
                )
                results['current_yield'] = round_percentage(current_yield * 100)

            if results.get('clean_price') is not None:
                macaulay_duration = self._calculate_macaulay_duration(
                    face_value, coupon_rate, yield_to_maturity, years_to_maturity, coupon_frequency
                )
                results['macaulay_duration'] = round_value(macaulay_duration, 4)

                modified_duration = self._calculate_modified_duration(
                    macaulay_duration, yield_to_maturity, coupon_frequency
                )
                results['modified_duration'] = round_value(modified_duration, 4)

                convexity = self._calculate_convexity(
                    face_value, coupon_rate, yield_to_maturity, years_to_maturity, coupon_frequency
                )
                results['convexity'] = round_value(convexity, 4)

                dv01 = self._calculate_dv01(results['clean_price'], modified_duration)
                results['dv01'] = round_value(dv01, 4)
                results['pvbp'] = round_value(dv01, 4)

            if call_date and call_price and settlement_date:
                years_to_call = self._calculate_years_to_maturity(
                    settlement_date, call_date, day_count_convention
                )
                ytc = self._calculate_yield_to_call(
                    face_value, call_price, coupon_rate, years_to_call, coupon_frequency
                )
                results['yield_to_call'] = round_percentage(ytc * 100)

            if put_date and put_price and settlement_date:
                years_to_put = self._calculate_years_to_maturity(
                    settlement_date, put_date, day_count_convention
                )
                ytp = self._calculate_yield_to_put(
                    face_value, put_price, coupon_rate, years_to_put, coupon_frequency
                )
                results['yield_to_put'] = round_percentage(ytp * 100)

            if 'yield_to_call' in results or 'yield_to_put' in results:
                yields = [yield_to_maturity]
                if 'yield_to_call' in results:
                    yields.append(results['yield_to_call'] / 100)
                if 'yield_to_put' in results:
                    yields.append(results['yield_to_put'] / 100)
                results['yield_to_worst'] = round_percentage(min(yields) * 100)

        if market_price is not None and face_value is not None and years_to_maturity is not None:
            available_fields['market_price'] = market_price
            available_fields['face_value'] = face_value
            available_fields['years_to_maturity'] = years_to_maturity
            validation = self.dependency_engine.validate_calculation(
                'yield_to_maturity', available_fields, 'bonds'
            )
            if validation.can_calculate:
                ytm = self._calculate_yield_to_maturity(
                    market_price, face_value, coupon_rate, years_to_maturity, coupon_frequency
                )
                results['yield_to_maturity'] = round_percentage(ytm * 100)
                available_fields['yield_to_maturity'] = ytm
            else:
                validation_errors.append(self.dependency_engine.get_missing_fields_message(validation))
                results['yield_to_maturity'] = None

        if benchmark_yield is not None:
            if results.get('yield_to_maturity') is not None:
                benchmark_spread = (results['yield_to_maturity'] / 100) - benchmark_yield
                results['benchmark_spread'] = round_percentage(benchmark_spread * 100)
                results['g_spread'] = results['benchmark_spread']

            results['benchmark_yield'] = round_percentage(benchmark_yield * 100)
            results['benchmark_yield_comparison'] = round_percentage(benchmark_yield * 100)

            if benchmark_curve and face_value is not None and years_to_maturity is not None:
                results['benchmark_valuation'] = round_money(
                    self._calculate_benchmark_curve_valuation(
                        face_value, coupon_rate, benchmark_curve, years_to_maturity, coupon_frequency
                    )
                )

        if inflation_rate is not None and results.get('yield_to_maturity') is not None:
            real_yield = self._calculate_real_yield(
                results['yield_to_maturity'] / 100, inflation_rate
            )
            results['real_yield'] = round_percentage(real_yield * 100)

        if results.get('yield_to_maturity') is not None:
            eay = self._calculate_effective_annual_yield(
                results['yield_to_maturity'] / 100, coupon_frequency
            )
            results['effective_annual_yield'] = round_percentage(eay * 100)

        if market_price is not None and results.get('clean_price') is not None:
            if results.get('coupon_payment') is not None and years_to_maturity is not None:
                hpr = self._calculate_holding_period_return(
                    results['clean_price'], results['coupon_payment'], years_to_maturity, coupon_frequency
                )
                results['holding_period_return'] = round_percentage(hpr * 100)

        if results.get('clean_price') is not None:
            if results.get('coupon_payment') is not None and years_to_maturity is not None:
                coupon_income = results['coupon_payment'] * years_to_maturity * coupon_frequency
                results['coupon_income'] = round_money(coupon_income)

                if market_price is not None:
                    capital_gain_loss = market_price - results['clean_price']
                    results['capital_gain_loss'] = round_money(capital_gain_loss)
                    total_return = coupon_income + capital_gain_loss
                    results['total_return'] = round_money(total_return)
                    if results['clean_price'] > 0:
                        results['total_return_percentage'] = round_percentage(
                            total_return / results['clean_price'] * 100
                        )

        if valuation_date:
            results['valuation_date'] = valuation_date
            results['Valuation Date'] = valuation_date

        if validation_errors:
            results['validation_errors'] = validation_errors
            results['calculation_status'] = 'partial_success'
        else:
            results['calculation_status'] = 'success'

        return results

    def _calculate_years_to_maturity(self, settlement_date, maturity_date, day_count_convention=365):
        settlement = datetime.strptime(settlement_date, '%Y-%m-%d')
        maturity = datetime.strptime(maturity_date, '%Y-%m-%d')
        return (maturity - settlement).days / day_count_convention

    def _calculate_days_to_maturity(self, settlement_date, maturity_date):
        settlement = datetime.strptime(settlement_date, '%Y-%m-%d')
        maturity = datetime.strptime(maturity_date, '%Y-%m-%d')
        return (maturity - settlement).days

    def _calculate_days_accrued(self, issue_date, settlement_date):
        issue = datetime.strptime(issue_date, '%Y-%m-%d')
        settlement = datetime.strptime(settlement_date, '%Y-%m-%d')
        return (settlement - issue).days

    def _calculate_days_to_next_coupon(self, settlement_date, coupon_frequency):
        days_per_period = self.day_count_convention / coupon_frequency
        return int(days_per_period)

    def _calculate_coupon_payment(self, face_value, coupon_rate, coupon_frequency):
        return face_value * coupon_rate / coupon_frequency

    def _calculate_accrued_interest(self, coupon_payment, coupon_frequency,
                                    settlement_date, issue_date):
        if not settlement_date or not issue_date:
            return None
        settlement = datetime.strptime(settlement_date, '%Y-%m-%d')
        issue = datetime.strptime(issue_date, '%Y-%m-%d')
        days_accrued = (settlement - issue).days
        days_per_period = self.day_count_convention / coupon_frequency
        return coupon_payment * (days_accrued / days_per_period)

    def _calculate_clean_price(self, face_value, coupon_rate, yield_to_maturity,
                               years_to_maturity, coupon_frequency):
        coupon_payment = self._calculate_coupon_payment(face_value, coupon_rate, coupon_frequency)
        periods = int(years_to_maturity * coupon_frequency)
        period_yield = yield_to_maturity / coupon_frequency
        pv_coupons = sum(
            coupon_payment / ((1 + period_yield) ** t)
            for t in range(1, periods + 1)
        )
        pv_face = face_value / ((1 + period_yield) ** periods)
        return pv_coupons + pv_face

    def _calculate_current_yield(self, coupon_payment, clean_price, coupon_frequency):
        return (coupon_payment * coupon_frequency) / clean_price

    def _calculate_yield_to_maturity(self, clean_price, face_value,
                                     coupon_rate, years_to_maturity, coupon_frequency):
        coupon_payment = self._calculate_coupon_payment(face_value, coupon_rate, coupon_frequency)
        periods = max(1, int(years_to_maturity * coupon_frequency))
        ytm = coupon_rate if coupon_rate is not None else 0.05

        for _ in range(100):
            pv_coupons = sum(
                coupon_payment / ((1 + ytm / coupon_frequency) ** t)
                for t in range(1, periods + 1)
            )
            pv_face = face_value / ((1 + ytm / coupon_frequency) ** periods)
            price = pv_coupons + pv_face

            derivative = sum(
                -t * coupon_payment / ((1 + ytm / coupon_frequency) ** (t + 1)) / coupon_frequency
                for t in range(1, periods + 1)
            )
            derivative += (
                -periods * face_value
                / ((1 + ytm / coupon_frequency) ** (periods + 1))
                / coupon_frequency
            )
            if derivative == 0:
                break
            new_ytm = ytm - (price - clean_price) / derivative
            if abs(new_ytm - ytm) < 0.0001:
                break
            ytm = new_ytm

        return ytm

    def _calculate_yield_to_call(self, face_value, call_price, coupon_rate,
                                 years_to_call, coupon_frequency):
        coupon_payment = self._calculate_coupon_payment(face_value, coupon_rate, coupon_frequency)
        periods = max(1, int(years_to_call * coupon_frequency))
        ytc = coupon_rate

        for _ in range(100):
            pv_coupons = sum(
                coupon_payment / ((1 + ytc / coupon_frequency) ** t)
                for t in range(1, periods + 1)
            )
            pv_call = call_price / ((1 + ytc / coupon_frequency) ** periods)
            price = pv_coupons + pv_call

            derivative = sum(
                -t * coupon_payment / ((1 + ytc / coupon_frequency) ** (t + 1)) / coupon_frequency
                for t in range(1, periods + 1)
            )
            derivative += (
                -periods * call_price
                / ((1 + ytc / coupon_frequency) ** (periods + 1))
                / coupon_frequency
            )
            if derivative == 0:
                break
            new_ytc = ytc - (price - face_value) / derivative
            if abs(new_ytc - ytc) < 0.0001:
                break
            ytc = new_ytc

        return ytc

    def _calculate_yield_to_put(self, face_value, put_price, coupon_rate,
                                years_to_put, coupon_frequency):
        return self._calculate_yield_to_call(
            face_value, put_price, coupon_rate, years_to_put, coupon_frequency
        )

    def _calculate_effective_annual_yield(self, yield_to_maturity, coupon_frequency):
        return (1 + yield_to_maturity / coupon_frequency) ** coupon_frequency - 1

    def _calculate_real_yield(self, nominal_yield, inflation_rate):
        return (1 + nominal_yield) / (1 + inflation_rate) - 1

    def _calculate_macaulay_duration(self, face_value, coupon_rate, yield_to_maturity,
                                     years_to_maturity, coupon_frequency):
        coupon_payment = self._calculate_coupon_payment(face_value, coupon_rate, coupon_frequency)
        periods = int(years_to_maturity * coupon_frequency)
        period_yield = yield_to_maturity / coupon_frequency
        clean_price = self._calculate_clean_price(
            face_value, coupon_rate, yield_to_maturity, years_to_maturity, coupon_frequency
        )

        weighted_time = 0
        for t in range(1, periods + 1):
            weighted_time += t * coupon_payment / ((1 + period_yield) ** t)
        weighted_time += periods * face_value / ((1 + period_yield) ** periods)

        return (weighted_time / clean_price) / coupon_frequency

    def _calculate_modified_duration(self, macaulay_duration, yield_to_maturity, coupon_frequency):
        return macaulay_duration / (1 + yield_to_maturity / coupon_frequency)

    def _calculate_effective_duration(self, modified_duration, yield_to_maturity):
        return modified_duration / (1 + yield_to_maturity)

    def _calculate_dollar_duration(self, clean_price, modified_duration):
        return clean_price * modified_duration

    def _calculate_convexity(self, face_value, coupon_rate, yield_to_maturity,
                             years_to_maturity, coupon_frequency):
        coupon_payment = self._calculate_coupon_payment(face_value, coupon_rate, coupon_frequency)
        periods = int(years_to_maturity * coupon_frequency)
        period_yield = yield_to_maturity / coupon_frequency
        clean_price = self._calculate_clean_price(
            face_value, coupon_rate, yield_to_maturity, years_to_maturity, coupon_frequency
        )

        convexity_sum = 0
        for t in range(1, periods + 1):
            pv = coupon_payment / ((1 + period_yield) ** t)
            convexity_sum += (t * (t + 1) * pv) / ((1 + period_yield) ** 2)

        pv_face = face_value / ((1 + period_yield) ** periods)
        convexity_sum += (periods * (periods + 1) * pv_face) / ((1 + period_yield) ** 2)

        return convexity_sum / clean_price / (coupon_frequency ** 2)

    def _calculate_dv01(self, clean_price, modified_duration):
        return clean_price * modified_duration * 0.0001

    def _calculate_price_change(self, clean_price, modified_duration, yield_change):
        return -clean_price * modified_duration * yield_change

    def _calculate_holding_period_return(self, clean_price, coupon_payment,
                                         years_to_maturity, coupon_frequency):
        annual_coupon = coupon_payment * coupon_frequency
        total_coupons = annual_coupon * years_to_maturity
        return (total_coupons + (100 - clean_price)) / clean_price / years_to_maturity

    def _calculate_total_return(self, clean_price, face_value, coupon_rate,
                                years_to_maturity, coupon_frequency):
        coupon_payment = self._calculate_coupon_payment(face_value, coupon_rate, coupon_frequency)
        periods = int(years_to_maturity * coupon_frequency)
        total_coupons = coupon_payment * periods
        return (total_coupons + face_value - clean_price) / clean_price / years_to_maturity

    def _calculate_zero_coupon_price(self, face_value, yield_to_maturity, years_to_maturity):
        return face_value / ((1 + yield_to_maturity) ** years_to_maturity)

    def _calculate_benchmark_curve_valuation(self, face_value, coupon_rate,
                                             benchmark_curve, years_to_maturity, coupon_frequency):
        closest_yield = min(benchmark_curve, key=lambda x: abs(x[0] - years_to_maturity))[1]
        return self._calculate_clean_price(
            face_value, coupon_rate, closest_yield, years_to_maturity, coupon_frequency
        )

    def _calculate_z_spread(self, face_value, coupon_rate, clean_price,
                            years_to_maturity, coupon_frequency, benchmark_curve):
        coupon_payment = self._calculate_coupon_payment(face_value, coupon_rate, coupon_frequency)
        periods = int(years_to_maturity * coupon_frequency)
        avg_benchmark_yield = sum(y for _, y in benchmark_curve) / len(benchmark_curve)

        z_spread = 0.01
        for _ in range(100):
            pv_coupons = sum(
                coupon_payment / ((1 + (avg_benchmark_yield + z_spread) / coupon_frequency) ** t)
                for t in range(1, periods + 1)
            )
            pv_face = face_value / ((1 + (avg_benchmark_yield + z_spread) / coupon_frequency) ** periods)
            price = pv_coupons + pv_face
            if abs(price - clean_price) < 0.01:
                break
            z_spread += 0.0001 if price > clean_price else -0.0001
        return z_spread


def calculate_bonds(inputs, benchmark_yield=None, benchmark_curve=None,
                    inflation_rate=None, valuation_date=None):
    calculator = BondsCalculator()
    results = calculator.calculate_all_metrics(
        inputs, benchmark_yield, benchmark_curve, inflation_rate, valuation_date
    )
    return {key: auto_round_by_field_name(key, value) for key, value in results.items()}
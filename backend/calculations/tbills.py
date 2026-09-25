"""
Treasury Bills (T-Bills) Valuation Calculations
Every calculation uses actual uploaded values, no fallback defaults.
"""

from datetime import datetime
from typing import Dict, Optional
from utils.rounding import (
    round_percentage, round_money, round_value, auto_round_by_field_name,
)
from utils.calculation_dependencies import CalculationDependencyEngine


class TBillsCalculator:
    def __init__(self):
        self.day_count_convention = 360
        self.bond_day_count = 365
        self.dependency_engine = CalculationDependencyEngine()

    def calculate_all_metrics(self, inputs: Dict,
                              benchmark_yield: Optional[float] = None,
                              inflation_rate: Optional[float] = None) -> Dict:
        results: Dict = {}
        validation_errors = []

        face_value = inputs.get('face_value')
        discount_rate = inputs.get('discount_rate')
        purchase_price = inputs.get('purchase_price')
        issue_date = inputs.get('issue_date')
        maturity_date = inputs.get('maturity_date')
        settlement_date = inputs.get('settlement_date')
        days_to_maturity = inputs.get('days_to_maturity')
        day_count_convention = inputs.get('day_count_convention', self.day_count_convention)

        available_fields = {
            'face_value': face_value,
            'discount_rate': discount_rate,
            'purchase_price': purchase_price,
            'issue_date': issue_date,
            'maturity_date': maturity_date,
            'settlement_date': settlement_date,
            'days_to_maturity': days_to_maturity,
            'day_count_convention': day_count_convention,
        }

        if maturity_date and settlement_date:
            v = self.dependency_engine.validate_calculation(
                'days_to_maturity', available_fields, 'tbills')
            if v.can_calculate:
                days_to_maturity = self._calculate_days_to_maturity(settlement_date, maturity_date)
                results['days_to_maturity'] = days_to_maturity
                available_fields['days_to_maturity'] = days_to_maturity
            else:
                validation_errors.append(self.dependency_engine.get_missing_fields_message(v))
                results['days_to_maturity'] = None
        elif days_to_maturity is not None:
            results['days_to_maturity'] = days_to_maturity
        else:
            validation_errors.append("Cannot calculate days to maturity: missing settlement_date and maturity_date")
            results['days_to_maturity'] = None

        if issue_date and settlement_date:
            results['days_since_issue'] = self._calculate_days_since_issue(issue_date, settlement_date)

        if issue_date and maturity_date:
            total_days = self._calculate_days_to_maturity(issue_date, maturity_date)
            if settlement_date:
                remaining = total_days - self._calculate_days_since_issue(issue_date, settlement_date)
            elif days_to_maturity is not None:
                remaining = days_to_maturity
            else:
                remaining = None
            results['remaining_days'] = remaining

        if days_to_maturity is not None:
            results['time_to_maturity'] = round_value(days_to_maturity / day_count_convention, 4)
        else:
            results['time_to_maturity'] = None

        results['face_value'] = round_money(face_value) if face_value is not None else None
        results['nominal_value'] = results['face_value']

        if discount_rate is not None and face_value is not None:
            available_fields['discount_rate'] = discount_rate
            available_fields['face_value'] = face_value
            available_fields['days_to_maturity'] = days_to_maturity
            available_fields['day_count_convention'] = day_count_convention

            v = self.dependency_engine.validate_calculation(
                'discount_amount', available_fields, 'tbills')
            if v.can_calculate:
                results['discount_amount'] = round_money(
                    self._calculate_discount_amount(face_value, discount_rate,
                                                    days_to_maturity, day_count_convention))
            else:
                validation_errors.append(self.dependency_engine.get_missing_fields_message(v))
                results['discount_amount'] = None

            # Compute price ONLY if not supplied - never overwrite real data
            if days_to_maturity is not None:
                if purchase_price is None:
                    purchase_price = self._calculate_purchase_price(
                        face_value, discount_rate, days_to_maturity, day_count_convention)
                results['purchase_price'] = round_money(purchase_price)
                results['present_value'] = results['purchase_price']
                available_fields['purchase_price'] = purchase_price

            if 'purchase_price' in results:
                results['fair_value'] = results['purchase_price']
                results['market_value'] = results['purchase_price']

            results['discount_rate'] = round_percentage(discount_rate * 100)
            results['bank_discount_yield'] = round_percentage(discount_rate * 100)

            if purchase_price is not None and days_to_maturity is not None:
                bey = self._calculate_bond_equivalent_yield(
                    purchase_price, face_value, days_to_maturity)
                results['bond_equivalent_yield'] = round_percentage(bey * 100)
                results['yield_to_maturity'] = round_percentage(bey * 100)

                eay = self._calculate_effective_annual_yield(bey, days_to_maturity)
                results['effective_annual_yield'] = round_percentage(eay * 100)

                hpy = self._calculate_holding_period_yield(purchase_price, face_value)
                results['holding_period_yield'] = round_percentage(hpy * 100)

                ahpy = self._calculate_annualized_holding_period_yield(hpy, days_to_maturity)
                results['annualized_holding_period_yield'] = round_percentage(ahpy * 100)

                mmy = self._calculate_money_market_yield(face_value, purchase_price, days_to_maturity)
                results['money_market_yield'] = round_percentage(mmy * 100)

                results['current_market_yield'] = round_percentage(bey * 100)

            if purchase_price is not None:
                results['settlement_amount'] = round_money(purchase_price)
                results['net_proceeds'] = round_money(purchase_price)
                results['investment_cost'] = round_money(purchase_price)
                results['clean_price'] = round_money(purchase_price)
                results['dirty_price'] = round_money(purchase_price)
            if face_value is not None:
                results['maturity_value'] = round_money(face_value)
                results['gross_proceeds'] = round_money(face_value)
            if face_value is not None and purchase_price is not None:
                results['gain_loss_maturity'] = round_money(face_value - purchase_price)

            if 'holding_period_yield' in results and results['holding_period_yield'] is not None:
                results['percentage_return'] = results['holding_period_yield']

            if purchase_price is not None and days_to_maturity is not None:
                dv01 = self._calculate_dv01(purchase_price, days_to_maturity)
                results['dv01'] = round_value(dv01, 4)
                results['sensitivity_yield_changes'] = round_value(dv01, 4)

        if benchmark_yield is not None:
            if results.get('bond_equivalent_yield') is not None:
                spread = (results['bond_equivalent_yield'] / 100) - benchmark_yield
                results['benchmark_spread'] = round_percentage(spread * 100)
            results['benchmark_yield'] = round_percentage(benchmark_yield * 100)
            results['benchmark_yield_comparison'] = round_percentage(benchmark_yield * 100)
            if face_value is not None and days_to_maturity is not None:
                results['benchmark_valuation'] = round_money(
                    self._calculate_benchmark_valuation(face_value, benchmark_yield,
                                                        days_to_maturity, day_count_convention))

        if inflation_rate is not None and results.get('bond_equivalent_yield') is not None:
            real = self._calculate_real_yield(results['bond_equivalent_yield'] / 100, inflation_rate)
            results['real_yield'] = round_percentage(real * 100)

        results['validation_errors'] = validation_errors
        results['calculation_status'] = 'partial_success' if validation_errors else 'success'
        return results

    def _calculate_days_to_maturity(self, settlement_date: str, maturity_date: str) -> int:
        return (datetime.strptime(maturity_date, '%Y-%m-%d')
                - datetime.strptime(settlement_date, '%Y-%m-%d')).days

    def _calculate_days_since_issue(self, issue_date: str, settlement_date: str) -> int:
        return (datetime.strptime(settlement_date, '%Y-%m-%d')
                - datetime.strptime(issue_date, '%Y-%m-%d')).days

    def _calculate_discount_amount(self, face_value, discount_rate, days, basis=360):
        if days is None or basis is None:
            return None
        return face_value * discount_rate * (days / basis)

    def _calculate_purchase_price(self, face_value, discount_rate, days, basis=360):
        da = self._calculate_discount_amount(face_value, discount_rate, days, basis)
        if da is None:
            return None
        return face_value - da

    def _calculate_bond_equivalent_yield(self, purchase_price, face_value, days):
        if purchase_price is None or purchase_price == 0 or days is None:
            return None
        discount = face_value - purchase_price
        return (discount / purchase_price) * (self.bond_day_count / days)

    def _calculate_effective_annual_yield(self, bey, days):
        if days is None or days == 0:
            return None
        periods = self.bond_day_count / days
        return (1 + bey / periods) ** periods - 1

    def _calculate_holding_period_yield(self, purchase_price, face_value):
        if purchase_price is None or purchase_price == 0:
            return None
        return (face_value - purchase_price) / purchase_price

    def _calculate_annualized_holding_period_yield(self, hpy, days):
        if days is None:
            return None
        return hpy * (self.bond_day_count / days)

    def _calculate_money_market_yield(self, face_value, purchase_price, days):
        if purchase_price is None or purchase_price == 0 or days is None:
            return None
        return (face_value - purchase_price) / purchase_price * (self.bond_day_count / days)

    def _calculate_dv01(self, purchase_price, days):
        if days is None:
            return None
        return purchase_price * (days / self.bond_day_count) * 0.0001

    def _calculate_benchmark_valuation(self, face_value, benchmark_yield, days, basis=360):
        if days is None or basis is None:
            return None
        return face_value / (1 + benchmark_yield * (days / basis))

    def _calculate_real_yield(self, nominal_yield, inflation_rate):
        if inflation_rate is None:
            return None
        return (1 + nominal_yield) / (1 + inflation_rate) - 1


def calculate_tbills(inputs: Dict, benchmark_yield: Optional[float] = None,
                     inflation_rate: Optional[float] = None) -> Dict:
    results = TBillsCalculator().calculate_all_metrics(
        inputs, benchmark_yield, inflation_rate)
    return {k: auto_round_by_field_name(k, v) for k, v in results.items()}
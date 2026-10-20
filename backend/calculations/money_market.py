from datetime import datetime
from typing import Dict, Optional
from utils.rounding import (
    round_percentage, round_money, round_value, auto_round_by_field_name
)
from utils.calculation_dependencies import CalculationDependencyEngine


class MoneyMarketCalculator:

    def __init__(self):
        self.day_count_convention = 365
        self.compounding_frequency = 1
        self.dependency_engine = CalculationDependencyEngine()

    def calculate_all_metrics(self, inputs: Dict,
                              benchmark_yield: Optional[float] = None,
                              inflation_rate: Optional[float] = None) -> Dict:
        results = {}
        validation_errors = []

        face_value = inputs.get('face_value')
        principal = inputs.get('principal')
        interest_rate = inputs.get('interest_rate')
        discount_rate = inputs.get('discount_rate')
        purchase_price = inputs.get('purchase_price')
        issue_date = inputs.get('issue_date')
        maturity_date = inputs.get('maturity_date')
        settlement_date = inputs.get('settlement_date')
        days_to_maturity = inputs.get('days_to_maturity')
        compounding_frequency = inputs.get('compounding_frequency', self.compounding_frequency)
        day_count_convention = inputs.get('day_count_convention', self.day_count_convention)

        available_fields = {
            'face_value': face_value,
            'principal': principal,
            'interest_rate': interest_rate,
            'discount_rate': discount_rate,
            'purchase_price': purchase_price,
            'issue_date': issue_date,
            'maturity_date': maturity_date,
            'settlement_date': settlement_date,
            'days_to_maturity': days_to_maturity,
            'compounding_frequency': compounding_frequency,
            'day_count_convention': day_count_convention,
        }

        if maturity_date and settlement_date:
            validation = self.dependency_engine.validate_calculation(
                'term_days_to_maturity', available_fields, 'money-market'
            )
            if validation.can_calculate:
                days_to_maturity = self._calculate_days_to_maturity(settlement_date, maturity_date)
                results['days_to_maturity'] = days_to_maturity
                available_fields['days_to_maturity'] = days_to_maturity
            else:
                validation_errors.append(self.dependency_engine.get_missing_fields_message(validation))
                results['days_to_maturity'] = None
        elif days_to_maturity is not None:
            results['days_to_maturity'] = days_to_maturity
        else:
            validation_errors.append(
                "Cannot calculate days to maturity: missing settlement_date and maturity_date"
            )
            results['days_to_maturity'] = None

        # Reject zero/negative days — yields are undefined.
        if results.get('days_to_maturity') is not None and results['days_to_maturity'] <= 0:
            validation_errors.append(
                "days_to_maturity must be greater than zero for a valid calculation"
            )

        if issue_date and maturity_date:
            total_days = self._calculate_days_to_maturity(issue_date, maturity_date)
            if settlement_date:
                days_since_issue = self._calculate_days_since_issue(issue_date, settlement_date)
                results['remaining_days'] = total_days - days_since_issue
            else:
                results['remaining_days'] = None

        if days_to_maturity is not None:
            time_to_maturity = days_to_maturity / day_count_convention
            results['time_to_maturity'] = round_value(time_to_maturity, 4)
        else:
            time_to_maturity = None
            results['time_to_maturity'] = None

        results['face_value'] = round_money(face_value) if face_value is not None else None
        results['principal'] = round_money(principal) if principal is not None else None

        if principal is not None and interest_rate is not None:
            available_fields['principal'] = principal
            available_fields['interest_rate'] = interest_rate
            available_fields['days_to_maturity'] = days_to_maturity
            available_fields['day_count_convention'] = day_count_convention

            validation = self.dependency_engine.validate_calculation(
                'simple_interest', available_fields, 'money-market'
            )
            if validation.can_calculate:
                simple_interest = self._calculate_simple_interest(
                    principal, interest_rate, days_to_maturity, day_count_convention
                )
                results['simple_interest'] = round_money(simple_interest)
                results['interest_earned'] = round_money(simple_interest)
                available_fields['interest_earned'] = simple_interest
            else:
                validation_errors.append(self.dependency_engine.get_missing_fields_message(validation))
                results['simple_interest'] = None
                results['interest_earned'] = None

            if compounding_frequency > 1 and days_to_maturity is not None:
                available_fields['compounding_frequency'] = compounding_frequency
                compound_interest = self._calculate_compound_interest(
                    principal, interest_rate, time_to_maturity, compounding_frequency
                )
                results['compound_interest'] = round_money(compound_interest)

            validation = self.dependency_engine.validate_calculation(
                'present_value', available_fields, 'money-market'
            )
            if validation.can_calculate:
                present_value = self._calculate_present_value(
                    principal, interest_rate, time_to_maturity, day_count_convention
                )
                results['present_value'] = round_money(present_value)
                if purchase_price is None:
                    results['purchase_price'] = round_money(present_value)
            else:
                validation_errors.append(self.dependency_engine.get_missing_fields_message(validation))
                results['present_value'] = None

            if results.get('present_value') is not None:
                results['fair_value'] = results['present_value']
                results['market_value'] = results['present_value']
                results['settlement_amount'] = results['present_value']
                results['investment_cost'] = results['present_value']
                results['net_investment'] = results['present_value']

            if results.get('interest_earned') is not None:
                results['redemption_value'] = round_money(principal + results['interest_earned'])

            results['gross_investment'] = round_money(principal)

            if results.get('redemption_value') is not None and results.get('present_value') is not None:
                results['investment_return'] = round_money(
                    results['redemption_value'] - results['present_value']
                )

            hpy = None
            if results.get('present_value') is not None and results.get('redemption_value') is not None:
                hpy = self._calculate_holding_period_yield(
                    results['present_value'], results['redemption_value']
                )
                if hpy is not None:
                    results['holding_period_yield'] = round_percentage(hpy * 100)

            if hpy is not None and time_to_maturity is not None:
                annualized_hpy = self._calculate_annualized_holding_period_yield(hpy, time_to_maturity)
                if annualized_hpy is not None:
                    results['annualized_holding_period_yield'] = round_percentage(annualized_hpy * 100)

            if (results.get('present_value') is not None
                    and days_to_maturity is not None and days_to_maturity > 0):
                mm_yield = self._calculate_money_market_yield(
                    principal, results['present_value'], days_to_maturity, day_count_convention
                )
                if mm_yield is not None:
                    results['money_market_yield'] = round_percentage(mm_yield * 100)

            validation = self.dependency_engine.validate_calculation(
                'effective_annual_yield', available_fields, 'money-market'
            )
            if validation.can_calculate:
                effective_yield = self._calculate_effective_yield(interest_rate, compounding_frequency)
                results['effective_yield'] = round_percentage(effective_yield * 100)
            else:
                validation_errors.append(self.dependency_engine.get_missing_fields_message(validation))
                results['effective_yield'] = None

            if results.get('interest_earned') is not None and results.get('present_value') is not None:
                current_yield = self._calculate_current_yield(
                    results['interest_earned'], results['present_value']
                )
                if current_yield is not None:
                    results['current_yield'] = round_percentage(current_yield * 100)

            if (results.get('present_value') is not None
                    and results.get('redemption_value') is not None
                    and time_to_maturity is not None):
                ytm = self._calculate_yield_to_maturity(
                    results['present_value'], results['redemption_value'], time_to_maturity
                )
                if ytm is not None:
                    results['yield_to_maturity'] = round_percentage(ytm * 100)

            results['nominal_annual_rate'] = round_percentage(interest_rate * 100)

            results['effective_annual_rate'] = results.get('effective_yield')
            if results.get('effective_yield') is not None:
                results['annual_percentage_yield'] = results['effective_yield']

        if discount_rate is not None and face_value is not None:
            available_fields['discount_rate'] = discount_rate
            available_fields['face_value'] = face_value
            available_fields['days_to_maturity'] = days_to_maturity
            available_fields['day_count_convention'] = day_count_convention

            validation = self.dependency_engine.validate_calculation(
                'discount_amount', available_fields, 'money-market'
            )
            if validation.can_calculate:
                discount_amount = self._calculate_discount_amount(
                    face_value, discount_rate, days_to_maturity, day_count_convention
                )
                results['discount_amount'] = round_money(discount_amount)
            else:
                validation_errors.append(self.dependency_engine.get_missing_fields_message(validation))
                results['discount_amount'] = None

            if days_to_maturity is not None:
                discount_price = self._calculate_discount_price(
                    face_value, discount_rate, days_to_maturity, day_count_convention
                )
                results['purchase_price'] = round_money(discount_price)
                results['present_value'] = round_money(discount_price)

            results['annual_discount_rate'] = round_percentage(discount_rate * 100)
            results['discount_rate'] = round_percentage(discount_rate * 100)

        if benchmark_yield is not None:
            if results.get('yield_to_maturity') is not None:
                spread = (results['yield_to_maturity'] / 100) - benchmark_yield
                results['benchmark_spread'] = round_percentage(spread * 100)
                results['risk_free_spread'] = round_percentage(spread * 100)

            results['benchmark_yield'] = round_percentage(benchmark_yield * 100)
            results['benchmark_yield_comparison'] = round_percentage(benchmark_yield * 100)

            if face_value is not None and time_to_maturity is not None:
                results['benchmark_valuation'] = round_money(
                    self._calculate_benchmark_valuation(
                        face_value, benchmark_yield, time_to_maturity, day_count_convention
                    )
                )

        if inflation_rate is not None and results.get('yield_to_maturity') is not None:
            real_yield = self._calculate_real_yield(
                results['yield_to_maturity'] / 100, inflation_rate
            )
            if real_yield is not None:
                results['real_yield'] = round_percentage(real_yield * 100)

        if validation_errors:
            results['validation_errors'] = validation_errors
            results['calculation_status'] = 'partial_success'
        else:
            results['calculation_status'] = 'success'

        return results

    def _calculate_days_to_maturity(self, settlement_date, maturity_date):
        settlement = datetime.strptime(settlement_date, '%Y-%m-%d')
        maturity = datetime.strptime(maturity_date, '%Y-%m-%d')
        return (maturity - settlement).days

    def _calculate_days_since_issue(self, issue_date, settlement_date):
        issue = datetime.strptime(issue_date, '%Y-%m-%d')
        settlement = datetime.strptime(settlement_date, '%Y-%m-%d')
        return (settlement - issue).days

    def _calculate_simple_interest(self, principal, interest_rate, days_to_maturity,
                                   day_count_convention=365):
        if days_to_maturity is None or not day_count_convention:
            return None
        return principal * interest_rate * (days_to_maturity / day_count_convention)

    def _calculate_compound_interest(self, principal, interest_rate,
                                     time_to_maturity, compounding_frequency):
        if time_to_maturity is None:
            return None
        future = principal * (1 + interest_rate / compounding_frequency) ** (
            compounding_frequency * time_to_maturity
        )
        return future - principal

    def _calculate_present_value(self, principal, interest_rate, time_to_maturity,
                                 day_count_convention=365):
        if time_to_maturity is None or not day_count_convention:
            return None
        return principal / (1 + interest_rate * time_to_maturity)

    def _calculate_discount_amount(self, face_value, discount_rate, days_to_maturity,
                                   day_count_convention=365):
        if days_to_maturity is None or not day_count_convention:
            return None
        return face_value * discount_rate * (days_to_maturity / day_count_convention)

    def _calculate_discount_price(self, face_value, discount_rate, days_to_maturity,
                                  day_count_convention=365):
        discount = self._calculate_discount_amount(
            face_value, discount_rate, days_to_maturity, day_count_convention
        )
        if discount is None:
            return None
        return face_value - discount

    def _calculate_holding_period_yield(self, present_value, redemption_value):
        if not present_value:
            return None
        return (redemption_value - present_value) / present_value

    def _calculate_annualized_holding_period_yield(self, hpy, time_to_maturity):
        if not time_to_maturity:
            return None
        return hpy / time_to_maturity

    def _calculate_money_market_yield(self, principal, present_value, days_to_maturity,
                                      day_count_convention=365):
        if not present_value or not days_to_maturity or not day_count_convention:
            return None
        return (principal - present_value) / present_value * (
            day_count_convention / days_to_maturity
        )

    def _calculate_effective_yield(self, interest_rate, compounding_frequency):
        return (1 + interest_rate / compounding_frequency) ** compounding_frequency - 1

    def _calculate_current_yield(self, interest_earned, present_value):
        if not present_value:
            return None
        return interest_earned / present_value

    def _calculate_yield_to_maturity(self, present_value, redemption_value, time_to_maturity):
        if not present_value or not time_to_maturity:
            return None
        return (redemption_value - present_value) / present_value / time_to_maturity

    def _calculate_apy(self, interest_rate, compounding_frequency):
        return (1 + interest_rate / compounding_frequency) ** compounding_frequency - 1

    def _calculate_benchmark_valuation(self, face_value, benchmark_yield, time_to_maturity,
                                       day_count_convention=365):
        if time_to_maturity is None or not day_count_convention:
            return None
        return face_value / (1 + benchmark_yield * time_to_maturity)

    def _calculate_real_yield(self, nominal_yield, inflation_rate):
        if inflation_rate is None:
            return None
        return (1 + nominal_yield) / (1 + inflation_rate) - 1


def calculate_money_market(inputs: Dict, benchmark_yield: Optional[float] = None,
                           inflation_rate: Optional[float] = None) -> Dict:
    calculator = MoneyMarketCalculator()
    results = calculator.calculate_all_metrics(inputs, benchmark_yield, inflation_rate)
    return {key: auto_round_by_field_name(key, value) for key, value in results.items()}
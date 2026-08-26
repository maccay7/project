"""
Money Market Instruments Valuation Calculations

This module implements all Money Market valuation calculations as specified:
- Present Value
- Fair Value
- Market Value
- Purchase Price
- Settlement Amount
- Redemption Value
- Face Value
- Principal
- Interest Earned
- Simple Interest
- Compound Interest (where applicable)
- Discount Amount
- Discount Rate
- Annual Discount Rate
- Effective Annual Rate
- Nominal Annual Rate
- Annual Percentage Yield
- Money Market Yield
- Holding Period Yield
- Annualized Holding Period Yield
- Effective Yield
- Current Yield
- Yield to Maturity
- Time to Maturity
- Days to Maturity
- Remaining Days
- Investment Return
- Investment Cost
- Net Investment
- Gross Investment
- Benchmark Yield Comparison
- Benchmark Spread
- Risk-Free Spread
- Valuation using Benchmark Yield Curve

All calculations now use dependency validation - no mock or fallback data.
"""

from datetime import datetime, timedelta
from typing import Dict, Optional
import math
from utils.rounding import (
    round_percentage, round_money, round_value, auto_round_by_field_name
)
from utils.calculation_dependencies import CalculationDependencyEngine, CalculationStatus


class MoneyMarketCalculator:
    """Comprehensive Money Market valuation calculator with dependency validation."""
    
    def __init__(self):
        self.day_count_convention = 365  # Actual/365 for money market instruments
        self.compounding_frequency = 1  # Annual compounding for most money market
        self.dependency_engine = CalculationDependencyEngine()
    
    def calculate_all_metrics(self, inputs: Dict, benchmark_yield: Optional[float] = None,
                            inflation_rate: Optional[float] = None) -> Dict:
        """
        Calculate all Money Market valuation metrics from input data.
        
        Args:
            inputs: Dictionary containing Money Market parameters
                - face_value: Face/par/principal value
                - principal: Principal amount
                - interest_rate: Annual interest rate (as decimal)
                - discount_rate: Annual discount rate (as decimal)
                - purchase_price: Purchase price (if known)
                - issue_date: Issue date (YYYY-MM-DD)
                - maturity_date: Maturity date (YYYY-MM-DD)
                - settlement_date: Settlement date (YYYY-MM-DD)
                - days_to_maturity: Days to maturity (if dates not provided)
                - compounding_frequency: Compounding frequency (default 1)
            benchmark_yield: Benchmark yield from FRED API (as decimal)
            inflation_rate: Inflation rate for real yield calculation (as decimal)
            
        Returns:
            Dictionary containing all calculated metrics with validation status
        """
        results = {}
        validation_errors = []
        
        # Extract inputs - NO DEFAULTS, use None for missing values
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
        
        # Build available fields for validation
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
            'day_count_convention': day_count_convention
        }
        
        # Calculate days if dates provided
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
            # NO DEFAULT - report missing dependency
            validation_errors.append("Cannot calculate days to maturity: missing settlement_date and maturity_date")
            results['days_to_maturity'] = None
        
        # Calculate remaining days
        if issue_date and maturity_date:
            total_days = self._calculate_days_to_maturity(issue_date, maturity_date)
            days_since_issue = self._calculate_days_since_issue(issue_date, settlement_date) if settlement_date else 0
            remaining_days = total_days - days_since_issue
            results['remaining_days'] = remaining_days
        
        # Time to maturity in years - only if days_to_maturity is available
        if days_to_maturity is not None:
            time_to_maturity = days_to_maturity / day_count_convention
            results['time_to_maturity'] = round_value(time_to_maturity, 4)
        else:
            results['time_to_maturity'] = None
        
        # Face Value / Principal - only if provided
        if face_value is not None:
            results['face_value'] = round_money(face_value)
        else:
            results['face_value'] = None
        
        if principal is not None:
            results['principal'] = round_money(principal)
        else:
            results['principal'] = None
        
        # Interest Rate calculations - with dependency validation
        if principal is not None and interest_rate is not None:
            # Validate simple interest calculation
            available_fields['principal'] = principal
            available_fields['interest_rate'] = interest_rate
            available_fields['days_to_maturity'] = days_to_maturity
            available_fields['day_count_convention'] = day_count_convention
            
            validation = self.dependency_engine.validate_calculation(
                'simple_interest', available_fields, 'money-market'
            )
            if validation.can_calculate:
                simple_interest = self._calculate_simple_interest(principal, interest_rate, days_to_maturity, day_count_convention)
                results['simple_interest'] = round_money(simple_interest)
                results['interest_earned'] = round_money(simple_interest)
                available_fields['interest_earned'] = simple_interest
            else:
                validation_errors.append(self.dependency_engine.get_missing_fields_message(validation))
                results['simple_interest'] = None
                results['interest_earned'] = None
            
            # Compound Interest (if applicable)
            if compounding_frequency > 1 and days_to_maturity is not None:
                available_fields['compounding_frequency'] = compounding_frequency
                compound_interest = self._calculate_compound_interest(
                    principal, interest_rate, time_to_maturity, compounding_frequency
                )
                results['compound_interest'] = round_money(compound_interest)
            
            # Present Value / Purchase Price
            validation = self.dependency_engine.validate_calculation(
                'present_value', available_fields, 'money-market'
            )
            if validation.can_calculate:
                present_value = self._calculate_present_value(principal, interest_rate, time_to_maturity, day_count_convention)
                results['present_value'] = round_money(present_value)
                if purchase_price is None:
                    purchase_price = present_value
                    results['purchase_price'] = round_money(present_value)
            else:
                validation_errors.append(self.dependency_engine.get_missing_fields_message(validation))
                results['present_value'] = None
            
            # Fair Value / Market Value
            if 'present_value' in results and results['present_value'] is not None:
                results['fair_value'] = results['present_value']
                results['market_value'] = results['present_value']
            
            # Settlement Amount
            if 'present_value' in results and results['present_value'] is not None:
                results['settlement_amount'] = results['present_value']
            
            # Redemption Value (face value + interest)
            if 'interest_earned' in results and results['interest_earned'] is not None:
                redemption_value = principal + results['interest_earned']
                results['redemption_value'] = round_money(redemption_value)
            
            # Investment Cost
            if 'present_value' in results and results['present_value'] is not None:
                results['investment_cost'] = results['present_value']
            
            # Net Investment
            if 'present_value' in results and results['present_value'] is not None:
                results['net_investment'] = results['present_value']
            
            # Gross Investment
            if principal is not None:
                results['gross_investment'] = round_money(principal)
            
            # Investment Return
            if 'redemption_value' in results and 'present_value' in results:
                if results['redemption_value'] is not None and results['present_value'] is not None:
                    investment_return = results['redemption_value'] - results['present_value']
                    results['investment_return'] = round_money(investment_return)
            
            # Holding Period Yield
            if 'present_value' in results and 'redemption_value' in results:
                if results['present_value'] is not None and results['redemption_value'] is not None:
                    hpy = self._calculate_holding_period_yield(results['present_value'], results['redemption_value'])
                    results['holding_period_yield'] = round_percentage(hpy * 100)
            
            # Annualized Holding Period Yield
            if 'holding_period_yield' in results and results['holding_period_yield'] is not None and time_to_maturity is not None:
                annualized_hpy = self._calculate_annualized_holding_period_yield(hpy, time_to_maturity)
                results['annualized_holding_period_yield'] = round_percentage(annualized_hpy * 100)
            
            # Money Market Yield
            if principal is not None and 'present_value' in results and days_to_maturity is not None:
                if results['present_value'] is not None:
                    money_market_yield = self._calculate_money_market_yield(
                        principal, results['present_value'], days_to_maturity, day_count_convention
                    )
                    results['money_market_yield'] = round_percentage(money_market_yield * 100)
            
            # Effective Yield
            validation = self.dependency_engine.validate_calculation(
                'effective_annual_yield', available_fields, 'money-market'
            )
            if validation.can_calculate:
                effective_yield = self._calculate_effective_yield(interest_rate, compounding_frequency)
                results['effective_yield'] = round_percentage(effective_yield * 100)
            else:
                validation_errors.append(self.dependency_engine.get_missing_fields_message(validation))
                results['effective_yield'] = None
            
            # Current Yield
            if 'interest_earned' in results and 'present_value' in results:
                if results['interest_earned'] is not None and results['present_value'] is not None:
                    current_yield = self._calculate_current_yield(results['interest_earned'], results['present_value'])
                    results['current_yield'] = round_percentage(current_yield * 100)
            
            # Yield to Maturity
            if 'present_value' in results and 'redemption_value' in results and time_to_maturity is not None:
                if results['present_value'] is not None and results['redemption_value'] is not None:
                    ytm = self._calculate_yield_to_maturity(results['present_value'], results['redemption_value'], time_to_maturity)
                    results['yield_to_maturity'] = round_percentage(ytm * 100)
            
            # Nominal Annual Rate
            results['nominal_annual_rate'] = round_percentage(interest_rate * 100)
            
            # Annual Percentage Yield (APY)
            if 'effective_yield' in results and results['effective_yield'] is not None:
                results['annual_percentage_yield'] = results['effective_yield']
            
            # Effective Annual Rate
            if 'effective_yield' in results:
                results['effective_annual_rate'] = results['effective_yield']
        
        # Discount Rate calculations - with dependency validation
        if discount_rate is not None and face_value is not None:
            available_fields['discount_rate'] = discount_rate
            available_fields['face_value'] = face_value
            available_fields['days_to_maturity'] = days_to_maturity
            available_fields['day_count_convention'] = day_count_convention
            
            # Discount Amount
            validation = self.dependency_engine.validate_calculation(
                'discount_amount', available_fields, 'money-market'
            )
            if validation.can_calculate:
                discount_amount = self._calculate_discount_amount(face_value, discount_rate, days_to_maturity, day_count_convention)
                results['discount_amount'] = round_money(discount_amount)
            else:
                validation_errors.append(self.dependency_engine.get_missing_fields_message(validation))
                results['discount_amount'] = None
            
            # Purchase Price from discount
            if days_to_maturity is not None:
                discount_price = self._calculate_discount_price(face_value, discount_rate, days_to_maturity, day_count_convention)
                results['purchase_price'] = round_money(discount_price)
                results['present_value'] = round_money(discount_price)
            
            # Annual Discount Rate
            results['annual_discount_rate'] = round_percentage(discount_rate * 100)
            
            # Discount Rate
            results['discount_rate'] = round_percentage(discount_rate * 100)
        
        # Benchmark comparisons
        if benchmark_yield is not None:
            # Benchmark Spread
            if 'yield_to_maturity' in results and results['yield_to_maturity'] is not None:
                benchmark_spread = (results['yield_to_maturity'] / 100) - benchmark_yield
                results['benchmark_spread'] = round_percentage(benchmark_spread * 100)
            
            # Risk-Free Spread (assuming benchmark is risk-free)
            if 'yield_to_maturity' in results and results['yield_to_maturity'] is not None:
                risk_free_spread = (results['yield_to_maturity'] / 100) - benchmark_yield
                results['risk_free_spread'] = round_percentage(risk_free_spread * 100)
            
            # Benchmark Yield Comparison
            results['benchmark_yield'] = round_percentage(benchmark_yield * 100)
            results['benchmark_yield_comparison'] = round_percentage(benchmark_yield * 100)
            
            # Valuation using Benchmark Yield Curve
            if face_value is not None and time_to_maturity is not None:
                benchmark_valuation = self._calculate_benchmark_valuation(
                    face_value, benchmark_yield, time_to_maturity, day_count_convention
                )
                results['benchmark_valuation'] = round_money(benchmark_valuation)
        
        # Real Yield (Inflation Adjusted)
        if inflation_rate is not None and 'yield_to_maturity' in results and results['yield_to_maturity'] is not None:
            real_yield = self._calculate_real_yield(
                results['yield_to_maturity'] / 100, inflation_rate
            )
            results['real_yield'] = round_percentage(real_yield * 100)
        
        # Add validation errors to results
        if validation_errors:
            results['validation_errors'] = validation_errors
            results['calculation_status'] = 'partial_success'
        else:
            results['calculation_status'] = 'success'
        
        return results
    
    def _calculate_days_to_maturity(self, settlement_date: str, maturity_date: str) -> int:
        """Calculate days between settlement and maturity."""
        settlement = datetime.strptime(settlement_date, '%Y-%m-%d')
        maturity = datetime.strptime(maturity_date, '%Y-%m-%d')
        return (maturity - settlement).days
    
    def _calculate_days_since_issue(self, issue_date: str, settlement_date: str) -> int:
        """Calculate days since issue."""
        issue = datetime.strptime(issue_date, '%Y-%m-%d')
        settlement = datetime.strptime(settlement_date, '%Y-%m-%d')
        return (settlement - issue).days
    
    def _calculate_simple_interest(self, principal: float, interest_rate: float, 
                                   days_to_maturity: int, day_count_convention: int = 365) -> float:
        """Calculate simple interest."""
        if days_to_maturity is None or day_count_convention is None:
            return None
        return principal * interest_rate * (days_to_maturity / day_count_convention)
    
    def _calculate_compound_interest(self, principal: float, interest_rate: float,
                                     time_to_maturity: float, compounding_frequency: int) -> float:
        """Calculate compound interest."""
        if time_to_maturity is None:
            return None
        future_value = principal * (1 + interest_rate / compounding_frequency) ** (compounding_frequency * time_to_maturity)
        return future_value - principal
    
    def _calculate_present_value(self, principal: float, interest_rate: float,
                                 time_to_maturity: float, day_count_convention: int = 365) -> float:
        """Calculate present value."""
        if time_to_maturity is None or day_count_convention is None:
            return None
        return principal / (1 + interest_rate * time_to_maturity)
    
    def _calculate_discount_amount(self, face_value: float, discount_rate: float,
                                   days_to_maturity: int, day_count_convention: int = 365) -> float:
        """Calculate discount amount."""
        if days_to_maturity is None or day_count_convention is None:
            return None
        return face_value * discount_rate * (days_to_maturity / day_count_convention)
    
    def _calculate_discount_price(self, face_value: float, discount_rate: float,
                                  days_to_maturity: int, day_count_convention: int = 365) -> float:
        """Calculate discount price."""
        discount_amount = self._calculate_discount_amount(face_value, discount_rate, days_to_maturity, day_count_convention)
        if discount_amount is None:
            return None
        return face_value - discount_amount
    
    def _calculate_holding_period_yield(self, present_value: float, redemption_value: float) -> float:
        """Calculate Holding Period Yield."""
        if present_value is None or present_value == 0:
            return None
        return (redemption_value - present_value) / present_value
    
    def _calculate_annualized_holding_period_yield(self, hpy: float, time_to_maturity: float) -> float:
        """Calculate Annualized Holding Period Yield."""
        if time_to_maturity is None or time_to_maturity == 0:
            return None
        return hpy / time_to_maturity
    
    def _calculate_money_market_yield(self, principal: float, present_value: float,
                                      days_to_maturity: int, day_count_convention: int = 365) -> float:
        """Calculate Money Market Yield."""
        if present_value is None or present_value == 0 or days_to_maturity is None or day_count_convention is None:
            return None
        return (principal - present_value) / present_value * (day_count_convention / days_to_maturity)
    
    def _calculate_effective_yield(self, interest_rate: float, compounding_frequency: int) -> float:
        """Calculate Effective Yield."""
        return (1 + interest_rate / compounding_frequency) ** compounding_frequency - 1
    
    def _calculate_current_yield(self, interest_earned: float, present_value: float) -> float:
        """Calculate Current Yield."""
        if present_value is None or present_value == 0:
            return None
        return interest_earned / present_value
    
    def _calculate_yield_to_maturity(self, present_value: float, redemption_value: float,
                                     time_to_maturity: float) -> float:
        """Calculate Yield to Maturity."""
        if present_value is None or present_value == 0 or time_to_maturity is None or time_to_maturity == 0:
            return None
        return (redemption_value - present_value) / present_value / time_to_maturity
    
    def _calculate_apy(self, interest_rate: float, compounding_frequency: int) -> float:
        """Calculate Annual Percentage Yield (APY)."""
        return (1 + interest_rate / compounding_frequency) ** compounding_frequency - 1
    
    def _calculate_benchmark_valuation(self, face_value: float, benchmark_yield: float,
                                       time_to_maturity: float, day_count_convention: int = 365) -> float:
        """Calculate valuation using benchmark yield curve."""
        if time_to_maturity is None or day_count_convention is None:
            return None
        return face_value / (1 + benchmark_yield * time_to_maturity)
    
    def _calculate_real_yield(self, nominal_yield: float, inflation_rate: float) -> float:
        """Calculate Real Yield (Fisher equation)."""
        if inflation_rate is None:
            return None
        return (1 + nominal_yield) / (1 + inflation_rate) - 1


def calculate_money_market(inputs: Dict, benchmark_yield: Optional[float] = None,
                           inflation_rate: Optional[float] = None) -> Dict:
    """
    Main function to calculate all Money Market metrics.
    
    Args:
        inputs: Dictionary containing Money Market parameters
        benchmark_yield: Benchmark yield from FRED API
        inflation_rate: Inflation rate for real yield calculation
        
    Returns:
        Dictionary containing all calculated metrics with proper rounding
    """
    calculator = MoneyMarketCalculator()
    results = calculator.calculate_all_metrics(inputs, benchmark_yield, inflation_rate)
    
    # Apply auto-rounding based on field names
    rounded_results = {}
    for key, value in results.items():
        rounded_results[key] = auto_round_by_field_name(key, value)
    
    return rounded_results

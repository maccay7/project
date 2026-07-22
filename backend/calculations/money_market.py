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
"""

from datetime import datetime, timedelta
from typing import Dict, Optional
import math
from utils.rounding import (
    round_percentage, round_money, round_value, auto_round_by_field_name
)


class MoneyMarketCalculator:
    """Comprehensive Money Market valuation calculator."""
    
    def __init__(self):
        self.day_count_convention = 365  # Actual/365 for money market instruments
        self.compounding_frequency = 1  # Annual compounding for most money market
    
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
            Dictionary containing all calculated metrics
        """
        results = {}
        
        # Extract inputs with defaults
        face_value = inputs.get('face_value', 0)
        principal = inputs.get('principal', face_value)
        interest_rate = inputs.get('interest_rate', 0)
        discount_rate = inputs.get('discount_rate', 0)
        purchase_price = inputs.get('purchase_price')
        issue_date = inputs.get('issue_date')
        maturity_date = inputs.get('maturity_date')
        settlement_date = inputs.get('settlement_date')
        days_to_maturity = inputs.get('days_to_maturity')
        compounding_frequency = inputs.get('compounding_frequency', self.compounding_frequency)
        
        # Calculate days if dates provided
        if maturity_date and settlement_date:
            days_to_maturity = self._calculate_days_to_maturity(settlement_date, maturity_date)
            results['days_to_maturity'] = days_to_maturity
        elif days_to_maturity:
            results['days_to_maturity'] = days_to_maturity
        else:
            days_to_maturity = 90  # Default 90-day money market instrument
            results['days_to_maturity'] = days_to_maturity
        
        # Calculate remaining days
        if issue_date and maturity_date:
            total_days = self._calculate_days_to_maturity(issue_date, maturity_date)
            days_since_issue = self._calculate_days_since_issue(issue_date, settlement_date) if settlement_date else 0
            remaining_days = total_days - days_since_issue
            results['remaining_days'] = remaining_days
        
        # Time to maturity in years
        time_to_maturity = days_to_maturity / self.day_count_convention
        results['time_to_maturity'] = round_value(time_to_maturity, 4)
        
        # Face Value / Principal
        results['face_value'] = round_money(face_value)
        results['principal'] = round_money(principal)
        
        # Interest Rate calculations
        if interest_rate and principal:
            # Simple Interest
            simple_interest = self._calculate_simple_interest(principal, interest_rate, days_to_maturity)
            results['simple_interest'] = round_money(simple_interest)
            results['interest_earned'] = round_money(simple_interest)
            
            # Compound Interest (if applicable)
            if compounding_frequency > 1:
                compound_interest = self._calculate_compound_interest(
                    principal, interest_rate, time_to_maturity, compounding_frequency
                )
                results['compound_interest'] = round_money(compound_interest)
            
            # Present Value / Purchase Price
            present_value = self._calculate_present_value(principal, interest_rate, time_to_maturity)
            results['present_value'] = round_money(present_value)
            results['purchase_price'] = round_money(present_value)
            
            if not purchase_price:
                purchase_price = present_value
            
            # Fair Value / Market Value
            results['fair_value'] = round_money(present_value)
            results['market_value'] = round_money(present_value)
            
            # Settlement Amount
            results['settlement_amount'] = round_money(present_value)
            
            # Redemption Value (face value + interest)
            redemption_value = principal + simple_interest
            results['redemption_value'] = round_money(redemption_value)
            
            # Investment Cost
            results['investment_cost'] = round_money(present_value)
            
            # Net Investment
            results['net_investment'] = round_money(present_value)
            
            # Gross Investment
            results['gross_investment'] = round_money(principal)
            
            # Investment Return
            investment_return = redemption_value - present_value
            results['investment_return'] = round_money(investment_return)
            
            # Holding Period Yield
            hpy = self._calculate_holding_period_yield(present_value, redemption_value)
            results['holding_period_yield'] = round_percentage(hpy * 100)
            
            # Annualized Holding Period Yield
            annualized_hpy = self._calculate_annualized_holding_period_yield(hpy, time_to_maturity)
            results['annualized_holding_period_yield'] = round_percentage(annualized_hpy * 100)
            
            # Money Market Yield
            money_market_yield = self._calculate_money_market_yield(
                principal, present_value, days_to_maturity
            )
            results['money_market_yield'] = round_percentage(money_market_yield * 100)
            
            # Effective Yield
            effective_yield = self._calculate_effective_yield(interest_rate, compounding_frequency)
            results['effective_yield'] = round_percentage(effective_yield * 100)
            
            # Current Yield
            current_yield = self._calculate_current_yield(simple_interest, present_value)
            results['current_yield'] = round_percentage(current_yield * 100)
            
            # Yield to Maturity
            ytm = self._calculate_yield_to_maturity(present_value, redemption_value, time_to_maturity)
            results['yield_to_maturity'] = round_percentage(ytm * 100)
            
            # Nominal Annual Rate
            results['nominal_annual_rate'] = round_percentage(interest_rate * 100)
            
            # Annual Percentage Yield (APY)
            apy = self._calculate_apy(interest_rate, compounding_frequency)
            results['annual_percentage_yield'] = round_percentage(apy * 100)
            
            # Effective Annual Rate
            results['effective_annual_rate'] = round_percentage(effective_yield * 100)
        
        # Discount Rate calculations
        if discount_rate and face_value:
            # Discount Amount
            discount_amount = self._calculate_discount_amount(face_value, discount_rate, days_to_maturity)
            results['discount_amount'] = round_money(discount_amount)
            
            # Purchase Price from discount
            discount_price = self._calculate_discount_price(face_value, discount_rate, days_to_maturity)
            results['purchase_price'] = round_money(discount_price)
            results['present_value'] = round_money(discount_price)
            
            # Annual Discount Rate
            results['annual_discount_rate'] = round_percentage(discount_rate * 100)
            
            # Discount Rate
            results['discount_rate'] = round_percentage(discount_rate * 100)
        
        # Benchmark comparisons
        if benchmark_yield is not None:
            # Benchmark Spread
            if 'yield_to_maturity' in results:
                benchmark_spread = (results['yield_to_maturity'] / 100) - benchmark_yield
                results['benchmark_spread'] = round_percentage(benchmark_spread * 100)
            
            # Risk-Free Spread (assuming benchmark is risk-free)
            if 'yield_to_maturity' in results:
                risk_free_spread = (results['yield_to_maturity'] / 100) - benchmark_yield
                results['risk_free_spread'] = round_percentage(risk_free_spread * 100)
            
            # Benchmark Yield Comparison
            results['benchmark_yield'] = round_percentage(benchmark_yield * 100)
            results['benchmark_yield_comparison'] = round_percentage(benchmark_yield * 100)
            
            # Valuation using Benchmark Yield Curve
            if face_value and time_to_maturity:
                benchmark_valuation = self._calculate_benchmark_valuation(
                    face_value, benchmark_yield, time_to_maturity
                )
                results['benchmark_valuation'] = round_money(benchmark_valuation)
        
        # Real Yield (Inflation Adjusted)
        if inflation_rate is not None and 'yield_to_maturity' in results:
            real_yield = self._calculate_real_yield(
                results['yield_to_maturity'] / 100, inflation_rate
            )
            results['real_yield'] = round_percentage(real_yield * 100)
        
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
                                   days_to_maturity: int) -> float:
        """Calculate simple interest."""
        return principal * interest_rate * (days_to_maturity / self.day_count_convention)
    
    def _calculate_compound_interest(self, principal: float, interest_rate: float,
                                     time_to_maturity: float, compounding_frequency: int) -> float:
        """Calculate compound interest."""
        future_value = principal * (1 + interest_rate / compounding_frequency) ** (compounding_frequency * time_to_maturity)
        return future_value - principal
    
    def _calculate_present_value(self, principal: float, interest_rate: float,
                                 time_to_maturity: float) -> float:
        """Calculate present value."""
        return principal / (1 + interest_rate * time_to_maturity)
    
    def _calculate_discount_amount(self, face_value: float, discount_rate: float,
                                   days_to_maturity: int) -> float:
        """Calculate discount amount."""
        return face_value * discount_rate * (days_to_maturity / self.day_count_convention)
    
    def _calculate_discount_price(self, face_value: float, discount_rate: float,
                                  days_to_maturity: int) -> float:
        """Calculate discount price."""
        discount_amount = self._calculate_discount_amount(face_value, discount_rate, days_to_maturity)
        return face_value - discount_amount
    
    def _calculate_holding_period_yield(self, present_value: float, redemption_value: float) -> float:
        """Calculate Holding Period Yield."""
        return (redemption_value - present_value) / present_value
    
    def _calculate_annualized_holding_period_yield(self, hpy: float, time_to_maturity: float) -> float:
        """Calculate Annualized Holding Period Yield."""
        return hpy / time_to_maturity if time_to_maturity > 0 else hpy
    
    def _calculate_money_market_yield(self, principal: float, present_value: float,
                                      days_to_maturity: int) -> float:
        """Calculate Money Market Yield."""
        return (principal - present_value) / present_value * (self.day_count_convention / days_to_maturity)
    
    def _calculate_effective_yield(self, interest_rate: float, compounding_frequency: int) -> float:
        """Calculate Effective Yield."""
        return (1 + interest_rate / compounding_frequency) ** compounding_frequency - 1
    
    def _calculate_current_yield(self, interest_earned: float, present_value: float) -> float:
        """Calculate Current Yield."""
        return interest_earned / present_value
    
    def _calculate_yield_to_maturity(self, present_value: float, redemption_value: float,
                                     time_to_maturity: float) -> float:
        """Calculate Yield to Maturity."""
        return (redemption_value - present_value) / present_value / time_to_maturity
    
    def _calculate_apy(self, interest_rate: float, compounding_frequency: int) -> float:
        """Calculate Annual Percentage Yield (APY)."""
        return (1 + interest_rate / compounding_frequency) ** compounding_frequency - 1
    
    def _calculate_benchmark_valuation(self, face_value: float, benchmark_yield: float,
                                       time_to_maturity: float) -> float:
        """Calculate valuation using benchmark yield curve."""
        return face_value / (1 + benchmark_yield * time_to_maturity)
    
    def _calculate_real_yield(self, nominal_yield: float, inflation_rate: float) -> float:
        """Calculate Real Yield (Fisher equation)."""
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

"""
Treasury Bills (T-Bills) Valuation Calculations

This module implements all T-Bills valuation calculations as specified:
- Present Value (Purchase Price)
- Fair Value
- Face Value
- Nominal Value
- Discount Amount
- Discount Rate
- Bank Discount Yield
- Bond Equivalent Yield (BEY)
- Effective Annual Yield (EAY)
- Holding Period Yield (HPY)
- Annualized Holding Period Yield
- Money Market Yield
- Yield to Maturity (where applicable)
- Days to Maturity
- Days Since Issue
- Remaining Days
- Time to Maturity
- Accrued Interest (if applicable)
- Settlement Amount
- Maturity Value
- Net Proceeds
- Gross Proceeds
- Investment Cost
- Gain/Loss at Maturity
- Percentage Return
- Real Yield (Inflation Adjusted)
- Current Market Yield
- Benchmark Spread
- Benchmark Yield Comparison
- Clean Price
- Dirty Price (if applicable)
- Valuation using Benchmark Yield Curve
- Sensitivity to Yield Changes

All calculations now use dependency validation - no mock or fallback data.
"""

from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import math
from utils.rounding import (
    round_percentage, round_money, round_value, auto_round_by_field_name
)
from utils.calculation_dependencies import CalculationDependencyEngine, CalculationStatus


class TBillsCalculator:
    """Comprehensive T-Bills valuation calculator with dependency validation."""
    
    def __init__(self):
        self.day_count_convention = 360  # Bank discount basis for T-Bills
        self.bond_day_count = 365  # Bond equivalent yield uses 365 days
        self.dependency_engine = CalculationDependencyEngine()
    
    def calculate_all_metrics(self, inputs: Dict, benchmark_yield: Optional[float] = None,
                            inflation_rate: Optional[float] = None) -> Dict:
        """
        Calculate all T-Bills valuation metrics from input data.
        
        Args:
            inputs: Dictionary containing T-Bills parameters
                - face_value: Face/par value of the T-Bill
                - discount_rate: Annual discount rate (as decimal, e.g., 0.05 for 5%)
                - purchase_price: Purchase price (if known)
                - issue_date: Issue date (YYYY-MM-DD)
                - maturity_date: Maturity date (YYYY-MM-DD)
                - settlement_date: Settlement date (YYYY-MM-DD)
                - days_to_maturity: Days to maturity (if dates not provided)
            benchmark_yield: Benchmark yield from FRED API (as decimal)
            inflation_rate: Inflation rate for real yield calculation (as decimal)
            
        Returns:
            Dictionary containing all calculated metrics with validation status
        """
        results = {}
        validation_errors = []
        
        # Extract inputs - NO DEFAULTS, use None for missing values
        face_value = inputs.get('face_value')
        discount_rate = inputs.get('discount_rate')
        purchase_price = inputs.get('purchase_price')
        issue_date = inputs.get('issue_date')
        maturity_date = inputs.get('maturity_date')
        settlement_date = inputs.get('settlement_date')
        days_to_maturity = inputs.get('days_to_maturity')
        day_count_convention = inputs.get('day_count_convention', self.day_count_convention)
        
        # Build available fields for validation
        available_fields = {
            'face_value': face_value,
            'discount_rate': discount_rate,
            'purchase_price': purchase_price,
            'issue_date': issue_date,
            'maturity_date': maturity_date,
            'settlement_date': settlement_date,
            'days_to_maturity': days_to_maturity,
            'day_count_convention': day_count_convention
        }
        
        # Calculate days if dates provided
        if maturity_date and settlement_date:
            validation = self.dependency_engine.validate_calculation(
                'days_to_maturity', available_fields, 'tbills'
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
        
        # Calculate days since issue
        if issue_date and settlement_date:
            days_since_issue = self._calculate_days_since_issue(issue_date, settlement_date)
            results['days_since_issue'] = days_since_issue
        
        # Calculate remaining days
        if issue_date and maturity_date:
            total_days = self._calculate_days_to_maturity(issue_date, maturity_date)
            remaining_days = total_days - days_since_issue if days_since_issue else days_to_maturity
            results['remaining_days'] = remaining_days
        
        # Time to maturity in years - only if days_to_maturity is available
        if days_to_maturity is not None:
            time_to_maturity = days_to_maturity / day_count_convention
            results['time_to_maturity'] = round_value(time_to_maturity, 4)
        else:
            results['time_to_maturity'] = None
        
        # Face Value / Nominal Value - only if provided
        if face_value is not None:
            results['face_value'] = round_money(face_value)
            results['nominal_value'] = round_money(face_value)
        else:
            results['face_value'] = None
            results['nominal_value'] = None
        
        # Core calculations - with dependency validation
        if discount_rate is not None and face_value is not None:
            available_fields['discount_rate'] = discount_rate
            available_fields['face_value'] = face_value
            available_fields['days_to_maturity'] = days_to_maturity
            available_fields['day_count_convention'] = day_count_convention
            
            # Discount Amount
            validation = self.dependency_engine.validate_calculation(
                'discount_amount', available_fields, 'tbills'
            )
            if validation.can_calculate:
                discount_amount = self._calculate_discount_amount(face_value, discount_rate, days_to_maturity, day_count_convention)
                results['discount_amount'] = round_money(discount_amount)
            else:
                validation_errors.append(self.dependency_engine.get_missing_fields_message(validation))
                results['discount_amount'] = None
            
            # Purchase Price (Present Value) if not provided
            if days_to_maturity is not None:
                if purchase_price is None:
                    purchase_price = self._calculate_purchase_price(face_value, discount_rate, days_to_maturity, day_count_convention)
                results['purchase_price'] = round_money(purchase_price)
                results['present_value'] = round_money(purchase_price)
                available_fields['purchase_price'] = purchase_price
            
            # Fair Value (same as purchase price for T-Bills)
            if 'purchase_price' in results:
                results['fair_value'] = results['purchase_price']
                results['market_value'] = results['purchase_price']
            
            # Discount Rate (input)
            results['discount_rate'] = round_percentage(discount_rate * 100)
            
            # Bank Discount Yield
            bank_discount_yield = self._calculate_bank_discount_yield(discount_rate)
            results['bank_discount_yield'] = round_percentage(bank_discount_yield * 100)
            
            # Bond Equivalent Yield (BEY)
            if purchase_price is not None and days_to_maturity is not None:
                bey = self._calculate_bond_equivalent_yield(purchase_price, face_value, days_to_maturity)
                results['bond_equivalent_yield'] = round_percentage(bey * 100)
                results['yield_to_maturity'] = round_percentage(bey * 100)  # YTM = BEY for T-Bills
                
                # Effective Annual Yield (EAY)
                eay = self._calculate_effective_annual_yield(bey, days_to_maturity)
                results['effective_annual_yield'] = round_percentage(eay * 100)
                
                # Holding Period Yield (HPY)
                hpy = self._calculate_holding_period_yield(purchase_price, face_value)
                results['holding_period_yield'] = round_percentage(hpy * 100)
                
                # Annualized Holding Period Yield
                annualized_hpy = self._calculate_annualized_holding_period_yield(hpy, days_to_maturity)
                results['annualized_holding_period_yield'] = round_percentage(annualized_hpy * 100)
                
                # Money Market Yield
                money_market_yield = self._calculate_money_market_yield(face_value, purchase_price, days_to_maturity)
                results['money_market_yield'] = round_percentage(money_market_yield * 100)
                
                # Current Market Yield
                current_market_yield = self._calculate_current_market_yield(purchase_price, face_value, days_to_maturity)
                results['current_market_yield'] = round_percentage(current_market_yield * 100)
            
            # Settlement Amount
            if purchase_price is not None:
                results['settlement_amount'] = round_money(purchase_price)
            
            # Maturity Value
            if face_value is not None:
                results['maturity_value'] = round_money(face_value)
            
            # Net Proceeds
            if purchase_price is not None:
                results['net_proceeds'] = round_money(purchase_price)
            
            # Gross Proceeds
            if face_value is not None:
                results['gross_proceeds'] = round_money(face_value)
            
            # Investment Cost
            if purchase_price is not None:
                results['investment_cost'] = round_money(purchase_price)
            
            # Gain/Loss at Maturity
            if face_value is not None and purchase_price is not None:
                gain_loss = face_value - purchase_price
                results['gain_loss_maturity'] = round_money(gain_loss)
            
            # Percentage Return
            if 'holding_period_yield' in results and results['holding_period_yield'] is not None:
                results['percentage_return'] = results['holding_period_yield']
            
            # Clean Price (same as purchase price for T-Bills)
            if purchase_price is not None:
                results['clean_price'] = round_money(purchase_price)
            
            # Dirty Price (same as clean price for T-Bills - no accrued interest)
            if purchase_price is not None:
                results['dirty_price'] = round_money(purchase_price)
            
            # Sensitivity to Yield Changes (DV01)
            if purchase_price is not None and days_to_maturity is not None:
                dv01 = self._calculate_dv01(purchase_price, days_to_maturity)
                results['dv01'] = round_value(dv01, 4)
                results['sensitivity_yield_changes'] = round_value(dv01, 4)
        
        # Benchmark comparisons
        if benchmark_yield is not None:
            # Benchmark Spread
            if 'bond_equivalent_yield' in results and results['bond_equivalent_yield'] is not None:
                benchmark_spread = (results['bond_equivalent_yield'] / 100) - benchmark_yield
                results['benchmark_spread'] = round_percentage(benchmark_spread * 100)
            
            # Benchmark Yield Comparison
            results['benchmark_yield'] = round_percentage(benchmark_yield * 100)
            results['benchmark_yield_comparison'] = round_percentage(benchmark_yield * 100)
            
            # Valuation using Benchmark Yield Curve
            if face_value is not None and days_to_maturity is not None:
                benchmark_valuation = self._calculate_benchmark_valuation(
                    face_value, benchmark_yield, days_to_maturity, day_count_convention
                )
                results['benchmark_valuation'] = round_money(benchmark_valuation)
        
        # Real Yield (Inflation Adjusted)
        if inflation_rate is not None and 'bond_equivalent_yield' in results and results['bond_equivalent_yield'] is not None:
            real_yield = self._calculate_real_yield(
                results['bond_equivalent_yield'] / 100, inflation_rate
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
    
    def _calculate_discount_amount(self, face_value: float, discount_rate: float, 
                                   days_to_maturity: int, day_count_convention: int = 360) -> float:
        """Calculate discount amount."""
        if days_to_maturity is None or day_count_convention is None:
            return None
        return face_value * discount_rate * (days_to_maturity / day_count_convention)
    
    def _calculate_purchase_price(self, face_value: float, discount_rate: float,
                                  days_to_maturity: int, day_count_convention: int = 360) -> float:
        """Calculate purchase price (present value)."""
        discount_amount = self._calculate_discount_amount(face_value, discount_rate, days_to_maturity, day_count_convention)
        if discount_amount is None:
            return None
        return face_value - discount_amount
    
    def _calculate_bank_discount_yield(self, discount_rate: float) -> float:
        """Bank discount yield is the same as the discount rate."""
        return discount_rate
    
    def _calculate_bond_equivalent_yield(self, purchase_price: float, face_value: float,
                                       days_to_maturity: int) -> float:
        """Calculate Bond Equivalent Yield (BEY)."""
        if purchase_price is None or purchase_price == 0 or days_to_maturity is None:
            return None
        discount = face_value - purchase_price
        return (discount / purchase_price) * (self.bond_day_count / days_to_maturity)
    
    def _calculate_effective_annual_yield(self, bey: float, days_to_maturity: int) -> float:
        """Calculate Effective Annual Yield (EAY)."""
        if days_to_maturity is None or days_to_maturity == 0:
            return None
        periods_per_year = self.bond_day_count / days_to_maturity
        return (1 + bey / periods_per_year) ** periods_per_year - 1
    
    def _calculate_holding_period_yield(self, purchase_price: float, face_value: float) -> float:
        """Calculate Holding Period Yield (HPY)."""
        if purchase_price is None or purchase_price == 0:
            return None
        return (face_value - purchase_price) / purchase_price
    
    def _calculate_annualized_holding_period_yield(self, hpy: float, days_to_maturity: int) -> float:
        """Calculate Annualized Holding Period Yield."""
        if days_to_maturity is None:
            return None
        return hpy * (self.bond_day_count / days_to_maturity)
    
    def _calculate_money_market_yield(self, face_value: float, purchase_price: float,
                                     days_to_maturity: int) -> float:
        """Calculate Money Market Yield."""
        if purchase_price is None or purchase_price == 0 or days_to_maturity is None:
            return None
        return (face_value - purchase_price) / purchase_price * (self.bond_day_count / days_to_maturity)
    
    def _calculate_current_market_yield(self, purchase_price: float, face_value: float,
                                       days_to_maturity: int) -> float:
        """Calculate Current Market Yield."""
        return self._calculate_bond_equivalent_yield(purchase_price, face_value, days_to_maturity)
    
    def _calculate_dv01(self, purchase_price: float, days_to_maturity: int) -> float:
        """Calculate DV01 (Price Value of a Basis Point)."""
        if days_to_maturity is None:
            return None
        # Approximate DV01 for T-Bills
        time_to_maturity = days_to_maturity / self.bond_day_count
        return purchase_price * time_to_maturity * 0.0001
    
    def _calculate_benchmark_valuation(self, face_value: float, benchmark_yield: float,
                                      days_to_maturity: int, day_count_convention: int = 360) -> float:
        """Calculate valuation using benchmark yield curve."""
        if days_to_maturity is None or day_count_convention is None:
            return None
        time_to_maturity = days_to_maturity / day_count_convention
        return face_value / (1 + benchmark_yield * time_to_maturity)
    
    def _calculate_real_yield(self, nominal_yield: float, inflation_rate: float) -> float:
        """Calculate Real Yield (Fisher equation)."""
        if inflation_rate is None:
            return None
        return (1 + nominal_yield) / (1 + inflation_rate) - 1


def calculate_tbills(inputs: Dict, benchmark_yield: Optional[float] = None,
                    inflation_rate: Optional[float] = None) -> Dict:
    """
    Main function to calculate all T-Bills metrics.
    
    Args:
        inputs: Dictionary containing T-Bills parameters
        benchmark_yield: Benchmark yield from FRED API
        inflation_rate: Inflation rate for real yield calculation
        
    Returns:
        Dictionary containing all calculated metrics with proper rounding
    """
    calculator = TBillsCalculator()
    results = calculator.calculate_all_metrics(inputs, benchmark_yield, inflation_rate)
    
    # Apply auto-rounding based on field names
    rounded_results = {}
    for key, value in results.items():
        rounded_results[key] = auto_round_by_field_name(key, value)
    
    return rounded_results

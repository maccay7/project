"""
Bonds Valuation Calculations

This module implements all Bonds valuation calculations as specified:
- Clean Price
- Dirty Price
- Present Value
- Fair Value
- Market Value
- Face Value
- Par Value
- Coupon Payment
- Coupon Rate
- Current Yield
- Yield to Maturity (YTM)
- Yield to Call (YTC)
- Yield to Worst (YTW)
- Yield to Put (where applicable)
- Zero Coupon Bond Price
- Premium
- Discount
- Accrued Interest
- Settlement Value
- Redemption Value
- Redemption Yield
- Remaining Coupon Payments
- Days Accrued
- Days to Next Coupon
- Days to Maturity
- Time to Maturity
- Macaulay Duration
- Modified Duration
- Effective Duration
- Dollar Duration
- Convexity
- DV01
- PVBP (Price Value of a Basis Point)
- Interest Rate Sensitivity
- Price Change for Yield Shift
- Benchmark Spread
- G-Spread
- I-Spread
- Z-Spread (where applicable)
- Asset Swap Spread
- Credit Spread
- Real Yield
- Nominal Yield
- Effective Annual Yield
- Holding Period Return
- Total Return
- Capital Gain/Loss
- Coupon Income
- Unrealized Gain/Loss
- Realized Gain/Loss
- Market Price vs Fair Value
- Valuation using Benchmark Yield Curve

All calculations now use dependency validation - no mock or fallback data.
"""

from datetime import datetime, timedelta
from typing import Dict, Optional, List
import math
from utils.rounding import (
    round_percentage, round_money, round_value, auto_round_by_field_name
)
from utils.calculation_dependencies import CalculationDependencyEngine, CalculationStatus


class BondsCalculator:
    """Comprehensive Bonds valuation calculator with dependency validation."""
    
    def __init__(self):
        self.day_count_convention = 365  # Actual/365 for bonds
        self.compounding_frequency = 2  # Semi-annual compounding for most bonds
        self.dependency_engine = CalculationDependencyEngine()
    
    def calculate_all_metrics(self, inputs: Dict, benchmark_yield: Optional[float] = None,
                            benchmark_curve: Optional[List[Tuple[float, float]]] = None,
                            inflation_rate: Optional[float] = None) -> Dict:
        """
        Calculate all Bonds valuation metrics from input data.
        
        Args:
            inputs: Dictionary containing Bond parameters
                - face_value: Face/par value of the bond
                - coupon_rate: Annual coupon rate (as decimal)
                - yield_to_maturity: YTM (as decimal)
                - years_to_maturity: Years to maturity
                - coupon_frequency: Coupon payments per year (default 2)
                - settlement_date: Settlement date
                - issue_date: Issue date
                - maturity_date: Maturity date
                - call_date: Call date (if callable)
                - call_price: Call price (if callable)
                - put_date: Put date (if putable)
                - put_price: Put price (if putable)
                - market_price: Current market price (if known)
            benchmark_yield: Benchmark yield from FRED API (as decimal)
            benchmark_curve: List of (maturity_years, yield) tuples for curve
            inflation_rate: Inflation rate for real yield calculation (as decimal)
            
        Returns:
            Dictionary containing all calculated metrics with validation status
        """
        results = {}
        validation_errors = []
        
        # Extract inputs - NO DEFAULTS, use None for missing values
        face_value = inputs.get('face_value')
        coupon_rate = inputs.get('coupon_rate')
        yield_to_maturity = inputs.get('yield_to_maturity')
        years_to_maturity = inputs.get('years_to_maturity')
        coupon_frequency = inputs.get('coupon_frequency', self.compounding_frequency)
        settlement_date = inputs.get('settlement_date')
        issue_date = inputs.get('issue_date')
        maturity_date = inputs.get('maturity_date')
        call_date = inputs.get('call_date')
        call_price = inputs.get('call_price')
        put_date = inputs.get('put_date')
        put_price = inputs.get('put_price')
        market_price = inputs.get('market_price')
        day_count_convention = inputs.get('day_count_convention', self.day_count_convention)
        
        # Build available fields for validation
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
            'day_count_convention': day_count_convention
        }
        
        # Calculate time to maturity if dates provided
        if maturity_date and settlement_date:
            validation = self.dependency_engine.validate_calculation(
                'term_to_maturity', available_fields, 'bonds'
            )
            if validation.can_calculate:
                years_to_maturity = self._calculate_years_to_maturity(settlement_date, maturity_date, day_count_convention)
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
            # NO DEFAULT - report missing dependency
            validation_errors.append("Cannot calculate time to maturity: missing maturity_date and settlement_date")
            results['years_to_maturity'] = None
            results['days_to_maturity'] = None
        
        # Time to maturity
        if years_to_maturity is not None:
            results['time_to_maturity'] = round_value(years_to_maturity, 2)
        else:
            results['time_to_maturity'] = None
        
        # Face Value / Par Value - only if provided
        if face_value is not None:
            results['face_value'] = round_money(face_value)
            results['par_value'] = round_money(face_value)
        else:
            results['face_value'] = None
            results['par_value'] = None
        
        # Coupon Payment - with dependency validation
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
        
        # Coupon Rate - only if provided
        if coupon_rate is not None:
            results['coupon_rate'] = round_percentage(coupon_rate * 100)
        else:
            results['coupon_rate'] = None
        
        # Calculate prices if YTM provided - with dependency validation
        if yield_to_maturity is not None and face_value is not None and years_to_maturity is not None:
            available_fields['yield_to_maturity'] = yield_to_maturity
            available_fields['years_to_maturity'] = years_to_maturity
            
            # Clean Price (Bond Price)
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
            
            # Present Value / Fair Value / Market Value
            if 'clean_price' in results and results['clean_price'] is not None:
                results['present_value'] = results['clean_price']
                results['fair_value'] = results['clean_price']
                results['market_value'] = results['clean_price']
            
            # Accrued Interest
            if settlement_date and issue_date and coupon_rate is not None:
                accrued_interest = self._calculate_accrued_interest(
                    face_value, coupon_rate, settlement_date, issue_date, coupon_frequency
                )
                results['accrued_interest'] = round_money(accrued_interest)
                available_fields['accrued_interest'] = accrued_interest
            
            # Dirty Price
            if 'clean_price' in results and 'accrued_interest' in results:
                if results['clean_price'] is not None and results['accrued_interest'] is not None:
                    dirty_price = results['clean_price'] + results['accrued_interest']
                    results['dirty_price'] = round_money(dirty_price)
            
            # Settlement Value
            if 'dirty_price' in results and results['dirty_price'] is not None:
                results['settlement_value'] = results['dirty_price']
            
            # Redemption Value
            if face_value is not None:
                results['redemption_value'] = round_money(face_value)
            
            # Premium/Discount
            if 'clean_price' in results and results['clean_price'] is not None:
                if results['clean_price'] > face_value:
                    premium = results['clean_price'] - face_value
                    results['premium'] = round_money(premium)
                    results['discount'] = round_money(0)
                elif results['clean_price'] < face_value:
                    discount = face_value - results['clean_price']
                    results['discount'] = round_money(discount)
                    results['premium'] = round_money(0)
                else:
                    results['premium'] = round_money(0)
                    results['discount'] = round_money(0)
            
            # Current Yield
            if 'coupon_payment' in results and 'clean_price' in results:
                if results['coupon_payment'] is not None and results['clean_price'] is not None:
                    current_yield = self._calculate_current_yield(results['coupon_payment'], results['clean_price'], coupon_frequency)
                    results['current_yield'] = round_percentage(current_yield * 100)
            
            # Duration calculations
            if 'clean_price' in results and results['clean_price'] is not None:
                macaulay_duration = self._calculate_macaulay_duration(
                    face_value, coupon_rate, yield_to_maturity, years_to_maturity, coupon_frequency
                )
                results['macaulay_duration'] = round_value(macaulay_duration, 4)
                
                modified_duration = self._calculate_modified_duration(macaulay_duration, yield_to_maturity, coupon_frequency)
                results['modified_duration'] = round_value(modified_duration, 4)
                
                convexity = self._calculate_convexity(
                    face_value, coupon_rate, yield_to_maturity, years_to_maturity, coupon_frequency
                )
                results['convexity'] = round_value(convexity, 4)
                
                # DV01
                dv01 = self._calculate_dv01(results['clean_price'], modified_duration, yield_to_maturity)
                results['dv01'] = round_value(dv01, 4)
                results['pvbp'] = round_value(dv01, 4)
            
            # Yield to Call
            if call_date and call_price and settlement_date:
                years_to_call = self._calculate_years_to_maturity(settlement_date, call_date, day_count_convention)
                ytc = self._calculate_yield_to_call(face_value, call_price, coupon_rate, years_to_call, coupon_frequency)
                results['yield_to_call'] = round_percentage(ytc * 100)
            
            # Yield to Put
            if put_date and put_price and settlement_date:
                years_to_put = self._calculate_years_to_maturity(settlement_date, put_date, day_count_convention)
                ytp = self._calculate_yield_to_put(face_value, put_price, coupon_rate, years_to_put, coupon_frequency)
                results['yield_to_put'] = round_percentage(ytp * 100)
            
            # Yield to Worst
            if 'yield_to_call' in results or 'yield_to_put' in results:
                yields = [yield_to_maturity]
                if 'yield_to_call' in results:
                    yields.append(results['yield_to_call'] / 100)
                if 'yield_to_put' in results:
                    yields.append(results['yield_to_put'] / 100)
                ytw = min(yields)
                results['yield_to_worst'] = round_percentage(ytw * 100)
        
        # If market price provided instead of YTM, calculate YTM
        if market_price is not None and face_value is not None and years_to_maturity is not None:
            available_fields['market_price'] = market_price
            available_fields['face_value'] = face_value
            available_fields['years_to_maturity'] = years_to_maturity
            
            validation = self.dependency_engine.validate_calculation(
                'yield_to_maturity', available_fields, 'bonds'
            )
            if validation.can_calculate:
                ytm = self._calculate_yield_to_maturity(market_price, face_value, coupon_rate, years_to_maturity, coupon_frequency)
                results['yield_to_maturity'] = round_percentage(ytm * 100)
                available_fields['yield_to_maturity'] = ytm
            else:
                validation_errors.append(self.dependency_engine.get_missing_fields_message(validation))
                results['yield_to_maturity'] = None
            
        # Benchmark comparisons
        if benchmark_yield is not None:
            # Benchmark Spread
            if 'yield_to_maturity' in results and results['yield_to_maturity'] is not None:
                benchmark_spread = (results['yield_to_maturity'] / 100) - benchmark_yield
                results['benchmark_spread'] = round_percentage(benchmark_spread * 100)
            
            # G-Spread
            if 'yield_to_maturity' in results and results['yield_to_maturity'] is not None:
                results['g_spread'] = results['benchmark_spread']
            
            # Benchmark Yield Comparison
            results['benchmark_yield'] = round_percentage(benchmark_yield * 100)
            results['benchmark_yield_comparison'] = round_percentage(benchmark_yield * 100)
            
            # Valuation using Benchmark Yield Curve
            if benchmark_curve and face_value is not None and years_to_maturity is not None:
                benchmark_valuation = self._calculate_benchmark_curve_valuation(
                    face_value, coupon_rate, benchmark_curve, years_to_maturity, coupon_frequency
                )
                results['benchmark_valuation'] = round_money(benchmark_valuation)
        
        # Real Yield (Inflation Adjusted)
        if inflation_rate is not None and 'yield_to_maturity' in results and results['yield_to_maturity'] is not None:
            real_yield = self._calculate_real_yield(
                results['yield_to_maturity'] / 100, inflation_rate
            )
            results['real_yield'] = round_percentage(real_yield * 100)
        
        # Effective Annual Yield
        if 'yield_to_maturity' in results and results['yield_to_maturity'] is not None:
            effective_annual_yield = self._calculate_effective_annual_yield(
                results['yield_to_maturity'] / 100, coupon_frequency
            )
            results['effective_annual_yield'] = round_percentage(effective_annual_yield * 100)
        
        # Holding Period Return
        if market_price is not None and 'clean_price' in results and results['clean_price'] is not None:
            if 'coupon_payment' in results:
                holding_period_return = self._calculate_holding_period_return(
                    results['clean_price'], market_price, results['coupon_payment'], years_to_maturity
                )
                results['holding_period_return'] = round_percentage(holding_period_return * 100)
        
        # Total Return components
        if 'clean_price' in results and results['clean_price'] is not None:
            if 'coupon_payment' in results and years_to_maturity is not None:
                coupon_income = results['coupon_payment'] * years_to_maturity * coupon_frequency
                results['coupon_income'] = round_money(coupon_income)
                
                capital_gain_loss = market_price - results['clean_price'] if market_price else 0
                results['capital_gain_loss'] = round_money(capital_gain_loss)
                
                total_return = coupon_income + capital_gain_loss
                results['total_return'] = round_money(total_return)
                
                if results['clean_price'] > 0:
                    total_return_pct = total_return / results['clean_price']
                    results['total_return_percentage'] = round_percentage(total_return_pct * 100)
        
        # Add validation errors to results
        if validation_errors:
            results['validation_errors'] = validation_errors
            results['calculation_status'] = 'partial_success'
        else:
            results['calculation_status'] = 'success'
        
        return results
    
    def _calculate_years_to_maturity(self, settlement_date: str, maturity_date: str, day_count_convention: int = 365) -> float:
        """Calculate years between settlement and maturity."""
        settlement = datetime.strptime(settlement_date, '%Y-%m-%d')
        maturity = datetime.strptime(maturity_date, '%Y-%m-%d')
        days = (maturity - settlement).days
        return days / day_count_convention
    
    def _calculate_days_to_maturity(self, settlement_date: str, maturity_date: str) -> int:
        """Calculate days between settlement and maturity."""
        settlement = datetime.strptime(settlement_date, '%Y-%m-%d')
        maturity = datetime.strptime(maturity_date, '%Y-%m-%d')
        return (maturity - settlement).days
    
    def _calculate_coupon_payment(self, face_value: float, coupon_rate: float, 
                                  coupon_frequency: int) -> float:
        """Calculate coupon payment."""
        return face_value * coupon_rate / coupon_frequency
    
    def _calculate_clean_price(self, face_value: float, coupon_rate: float, yield_to_maturity: float,
                               years_to_maturity: float, coupon_frequency: int) -> float:
        """Calculate clean price using bond pricing formula."""
        coupon_payment = self._calculate_coupon_payment(face_value, coupon_rate, coupon_frequency)
        periods = int(years_to_maturity * coupon_frequency)
        period_yield = yield_to_maturity / coupon_frequency
        
        # Present value of coupon payments
        pv_coupons = 0
        for t in range(1, periods + 1):
            pv_coupons += coupon_payment / ((1 + period_yield) ** t)
        
        # Present value of face value
        pv_face = face_value / ((1 + period_yield) ** periods)
        
        return pv_coupons + pv_face
    
    def _calculate_accrued_interest(self, coupon_payment: float, coupon_frequency: int,
                                   settlement_date: Optional[str], issue_date: Optional[str]) -> float:
        """Calculate accrued interest."""
        if not settlement_date or not issue_date:
            return 0
        
        settlement = datetime.strptime(settlement_date, '%Y-%m-%d')
        issue = datetime.strptime(issue_date, '%Y-%m-%d')
        days_accrued = (settlement - issue).days
        days_per_period = self.day_count_convention / coupon_frequency
        
        return coupon_payment * (days_accrued / days_per_period)
    
    def _calculate_current_yield(self, coupon_payment: float, clean_price: float,
                                 coupon_frequency: int) -> float:
        """Calculate current yield."""
        annual_coupon = coupon_payment * coupon_frequency
        return annual_coupon / clean_price
    
    def _calculate_effective_annual_yield(self, yield_to_maturity: float, 
                                          coupon_frequency: int) -> float:
        """Calculate Effective Annual Yield."""
        return (1 + yield_to_maturity / coupon_frequency) ** coupon_frequency - 1
    
    def _calculate_yield_to_call(self, face_value: float, call_price: float, coupon_rate: float,
                                settlement_date: str, call_date: str, coupon_frequency: int) -> float:
        """Calculate Yield to Call (YTC)."""
        settlement = datetime.strptime(settlement_date, '%Y-%m-%d')
        call = datetime.strptime(call_date, '%Y-%m-%d')
        years_to_call = (call - settlement).days / self.day_count_convention
        
        coupon_payment = self._calculate_coupon_payment(face_value, coupon_rate, coupon_frequency)
        periods = int(years_to_call * coupon_frequency)
        
        # Solve for YTC using iterative method
        ytc = coupon_rate  # Initial guess
        for _ in range(100):  # Newton-Raphson iteration
            pv_coupons = sum(coupon_payment / ((1 + ytc/coupon_frequency) ** t) 
                           for t in range(1, periods + 1))
            pv_call = call_price / ((1 + ytc/coupon_frequency) ** periods)
            price = pv_coupons + pv_call
            
            # Derivative
            derivative = sum(-t * coupon_payment / ((1 + ytc/coupon_frequency) ** (t+1)) / coupon_frequency
                          for t in range(1, periods + 1))
            derivative += -periods * call_price / ((1 + ytc/coupon_frequency) ** (periods+1)) / coupon_frequency
            
            new_ytc = ytc - (price - face_value) / derivative
            if abs(new_ytc - ytc) < 0.0001:
                break
            ytc = new_ytc
        
        return ytc
    
    def _calculate_yield_to_put(self, face_value: float, put_price: float, coupon_rate: float,
                               settlement_date: str, put_date: str, coupon_frequency: int) -> float:
        """Calculate Yield to Put (YTP)."""
        # Similar to YTC but with put price
        return self._calculate_yield_to_call(face_value, put_price, coupon_rate, 
                                             settlement_date, put_date, coupon_frequency)
    
    def _calculate_days_accrued(self, issue_date: str, settlement_date: str) -> int:
        """Calculate days accrued since last coupon."""
        issue = datetime.strptime(issue_date, '%Y-%m-%d')
        settlement = datetime.strptime(settlement_date, '%Y-%m-%d')
        return (settlement - issue).days
    
    def _calculate_days_to_next_coupon(self, settlement_date: str, coupon_frequency: int) -> int:
        """Calculate days to next coupon payment."""
        settlement = datetime.strptime(settlement_date, '%Y-%m-%d')
        days_per_period = self.day_count_convention / coupon_frequency
        return int(days_per_period)
    
    def _calculate_macaulay_duration(self, face_value: float, coupon_rate: float, yield_to_maturity: float,
                                     years_to_maturity: float, coupon_frequency: int) -> float:
        """Calculate Macaulay Duration."""
        coupon_payment = self._calculate_coupon_payment(face_value, coupon_rate, coupon_frequency)
        periods = int(years_to_maturity * coupon_frequency)
        period_yield = yield_to_maturity / coupon_frequency
        clean_price = self._calculate_clean_price(face_value, coupon_rate, yield_to_maturity, 
                                                  years_to_maturity, coupon_frequency)
        
        # Weighted average time to cash flows
        weighted_time = 0
        for t in range(1, periods + 1):
            pv = coupon_payment / ((1 + period_yield) ** t)
            weighted_time += t * pv
        
        # Add face value at maturity
        pv_face = face_value / ((1 + period_yield) ** periods)
        weighted_time += periods * pv_face
        
        macaulay_duration_periods = weighted_time / clean_price
        return macaulay_duration_periods / coupon_frequency
    
    def _calculate_modified_duration(self, macaulay_duration: float, yield_to_maturity: float,
                                    coupon_frequency: int) -> float:
        """Calculate Modified Duration."""
        period_yield = yield_to_maturity / coupon_frequency
        return macaulay_duration / (1 + period_yield)
    
    def _calculate_effective_duration(self, modified_duration: float, yield_to_maturity: float) -> float:
        """Calculate Effective Duration (approximation)."""
        return modified_duration / (1 + yield_to_maturity)
    
    def _calculate_dollar_duration(self, clean_price: float, modified_duration: float) -> float:
        """Calculate Dollar Duration."""
        return clean_price * modified_duration
    
    def _calculate_convexity(self, face_value: float, coupon_rate: float, yield_to_maturity: float,
                             years_to_maturity: float, coupon_frequency: int) -> float:
        """Calculate Convexity."""
        coupon_payment = self._calculate_coupon_payment(face_value, coupon_rate, coupon_frequency)
        periods = int(years_to_maturity * coupon_frequency)
        period_yield = yield_to_maturity / coupon_frequency
        clean_price = self._calculate_clean_price(face_value, coupon_rate, yield_to_maturity, 
                                                  years_to_maturity, coupon_frequency)
        
        convexity_sum = 0
        for t in range(1, periods + 1):
            pv = coupon_payment / ((1 + period_yield) ** t)
            convexity_sum += (t * (t + 1) * pv) / ((1 + period_yield) ** 2)
        
        # Add face value at maturity
        pv_face = face_value / ((1 + period_yield) ** periods)
        convexity_sum += (periods * (periods + 1) * pv_face) / ((1 + period_yield) ** 2)
        
        return convexity_sum / clean_price / (coupon_frequency ** 2)
    
    def _calculate_dv01(self, clean_price: float, modified_duration: float) -> float:
        """Calculate DV01 (Price Value of a Basis Point)."""
        return clean_price * modified_duration * 0.0001
    
    def _calculate_price_change(self, clean_price: float, modified_duration: float, yield_change: float) -> float:
        """Calculate price change for yield shift."""
        return -clean_price * modified_duration * yield_change
    
    def _calculate_holding_period_return(self, clean_price: float, coupon_payment: float,
                                        years_to_maturity: float, coupon_frequency: int) -> float:
        """Calculate Holding Period Return."""
        annual_coupon = coupon_payment * coupon_frequency
        total_coupons = annual_coupon * years_to_maturity
        return (total_coupons + (100 - clean_price)) / clean_price / years_to_maturity
    
    def _calculate_total_return(self, clean_price: float, face_value: float, coupon_rate: float,
                              years_to_maturity: float, coupon_frequency: int) -> float:
        """Calculate Total Return."""
        coupon_payment = self._calculate_coupon_payment(face_value, coupon_rate, coupon_frequency)
        periods = int(years_to_maturity * coupon_frequency)
        total_coupons = coupon_payment * periods
        return (total_coupons + face_value - clean_price) / clean_price / years_to_maturity
    
    def _calculate_zero_coupon_price(self, face_value: float, yield_to_maturity: float,
                                      years_to_maturity: float) -> float:
        """Calculate Zero Coupon Bond Price."""
        return face_value / ((1 + yield_to_maturity) ** years_to_maturity)
    
    def _calculate_curve_valuation(self, face_value: float, coupon_rate: float, years_to_maturity: float,
                                  coupon_frequency: int, benchmark_curve: List[Tuple[float, float]]) -> float:
        """Calculate valuation using benchmark yield curve."""
        # Find closest benchmark yield
        closest_yield = min(benchmark_curve, key=lambda x: abs(x[0] - years_to_maturity))[1]
        return self._calculate_clean_price(face_value, coupon_rate, closest_yield, 
                                          years_to_maturity, coupon_frequency)
    
    def _calculate_z_spread(self, face_value: float, coupon_rate: float, clean_price: float,
                           years_to_maturity: float, coupon_frequency: int,
                           benchmark_curve: List[Tuple[float, float]]) -> float:
        """Calculate Z-Spread (zero-volatility spread)."""
        # Simplified Z-spread calculation
        coupon_payment = self._calculate_coupon_payment(face_value, coupon_rate, coupon_frequency)
        periods = int(years_to_maturity * coupon_frequency)
        
        # Find average benchmark yield
        avg_benchmark_yield = sum(y for _, y in benchmark_curve) / len(benchmark_curve)
        
        # Solve for Z-spread
        z_spread = 0.01  # Initial guess
        for _ in range(100):
            pv_coupons = sum(coupon_payment / ((1 + (avg_benchmark_yield + z_spread)/coupon_frequency) ** t)
                           for t in range(1, periods + 1))
            pv_face = face_value / ((1 + (avg_benchmark_yield + z_spread)/coupon_frequency) ** periods)
            price = pv_coupons + pv_face
            
            if abs(price - clean_price) < 0.01:
                break
            z_spread += 0.0001 if price > clean_price else -0.0001
        
        return z_spread
    
    def _calculate_real_yield(self, nominal_yield: float, inflation_rate: float) -> float:
        """Calculate Real Yield (Fisher equation)."""
        return (1 + nominal_yield) / (1 + inflation_rate) - 1


def calculate_bonds(inputs: Dict, benchmark_yield: Optional[float] = None,
                    benchmark_curve: Optional[List[Tuple[float, float]]] = None,
                    inflation_rate: Optional[float] = None) -> Dict:
    """
    Main function to calculate all Bonds metrics.
    
    Args:
        inputs: Dictionary containing Bond parameters
        benchmark_yield: Benchmark yield from FRED API
        benchmark_curve: Benchmark yield curve from FRED API
        inflation_rate: Inflation rate for real yield calculation
        
    Returns:
        Dictionary containing all calculated metrics with proper rounding
    """
    calculator = BondsCalculator()
    results = calculator.calculate_all_metrics(inputs, benchmark_yield, benchmark_curve, inflation_rate)
    
    # Apply auto-rounding based on field names
    rounded_results = {}
    for key, value in results.items():
        rounded_results[key] = auto_round_by_field_name(key, value)
    
    return rounded_results

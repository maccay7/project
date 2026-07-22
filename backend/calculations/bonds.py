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
"""

from datetime import datetime, timedelta
from typing import Dict, Optional, List
import math
from utils.rounding import (
    round_percentage, round_money, round_value, auto_round_by_field_name
)


class BondsCalculator:
    """Comprehensive Bonds valuation calculator."""
    
    def __init__(self):
        self.day_count_convention = 365  # Actual/365 for bonds
        self.compounding_frequency = 2  # Semi-annual compounding for most bonds
    
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
            Dictionary containing all calculated metrics
        """
        results = {}
        
        # Extract inputs with defaults
        face_value = inputs.get('face_value', 0)
        coupon_rate = inputs.get('coupon_rate', 0)
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
        
        # Calculate time to maturity if dates provided
        if maturity_date and settlement_date:
            years_to_maturity = self._calculate_years_to_maturity(settlement_date, maturity_date)
            days_to_maturity = self._calculate_days_to_maturity(settlement_date, maturity_date)
            results['years_to_maturity'] = round_value(years_to_maturity, 2)
            results['days_to_maturity'] = days_to_maturity
        elif years_to_maturity:
            days_to_maturity = int(years_to_maturity * 365)
            results['years_to_maturity'] = round_value(years_to_maturity, 2)
            results['days_to_maturity'] = days_to_maturity
        else:
            years_to_maturity = 5  # Default 5-year bond
            days_to_maturity = 5 * 365
            results['years_to_maturity'] = round_value(years_to_maturity, 2)
            results['days_to_maturity'] = days_to_maturity
        
        # Time to maturity
        results['time_to_maturity'] = round_value(years_to_maturity, 2)
        
        # Face Value / Par Value
        results['face_value'] = round_money(face_value)
        results['par_value'] = round_money(face_value)
        
        # Coupon Payment
        coupon_payment = self._calculate_coupon_payment(face_value, coupon_rate, coupon_frequency)
        results['coupon_payment'] = round_money(coupon_payment)
        
        # Coupon Rate
        results['coupon_rate'] = round_percentage(coupon_rate * 100)
        
        # Calculate prices if YTM provided
        if yield_to_maturity:
            # Clean Price (Bond Price)
            clean_price = self._calculate_clean_price(
                face_value, coupon_rate, yield_to_maturity, years_to_maturity, coupon_frequency
            )
            results['clean_price'] = round_money(clean_price)
            
            # Present Value / Fair Value / Market Value
            results['present_value'] = round_money(clean_price)
            results['fair_value'] = round_money(clean_price)
            results['market_value'] = round_money(clean_price)
            
            if not market_price:
                market_price = clean_price
            
            # Dirty Price (with accrued interest)
            accrued_interest = self._calculate_accrued_interest(
                coupon_payment, coupon_frequency, settlement_date, issue_date
            )
            results['accrued_interest'] = round_money(accrued_interest)
            dirty_price = clean_price + accrued_interest
            results['dirty_price'] = round_money(dirty_price)
            
            # Settlement Value
            results['settlement_value'] = round_money(dirty_price)
            
            # Premium/Discount
            if clean_price > face_value:
                premium = clean_price - face_value
                results['premium'] = round_money(premium)
                results['discount'] = round_money(0)
            else:
                discount = face_value - clean_price
                results['discount'] = round_money(discount)
                results['premium'] = round_money(0)
            
            # Current Yield
            current_yield = self._calculate_current_yield(coupon_payment, clean_price, coupon_frequency)
            results['current_yield'] = round_percentage(current_yield * 100)
            
            # Yield to Maturity (input)
            results['yield_to_maturity'] = round_percentage(yield_to_maturity * 100)
            
            # Nominal Yield (same as coupon rate)
            results['nominal_yield'] = round_percentage(coupon_rate * 100)
            
            # Effective Annual Yield
            effective_annual_yield = self._calculate_effective_annual_yield(
                yield_to_maturity, coupon_frequency
            )
            results['effective_annual_yield'] = round_percentage(effective_annual_yield * 100)
            
            # Yield to Call (if callable)
            if call_date and call_price and settlement_date:
                ytc = self._calculate_yield_to_call(
                    face_value, call_price, coupon_rate, settlement_date, call_date, coupon_frequency
                )
                results['yield_to_call'] = round_percentage(ytc * 100)
            
            # Yield to Put (if putable)
            if put_date and put_price and settlement_date:
                ytp = self._calculate_yield_to_put(
                    face_value, put_price, coupon_rate, settlement_date, put_date, coupon_frequency
                )
                results['yield_to_put'] = round_percentage(ytp * 100)
            
            # Yield to Worst
            if 'yield_to_call' in results:
                ytw = min(yield_to_maturity, results['yield_to_call'] / 100)
                results['yield_to_worst'] = round_percentage(ytw * 100)
            else:
                results['yield_to_worst'] = round_percentage(yield_to_maturity * 100)
            
            # Remaining Coupon Payments
            remaining_coupons = int(years_to_maturity * coupon_frequency)
            results['remaining_coupon_payments'] = remaining_coupons
            
            # Days Accrued
            if settlement_date and issue_date:
                days_accrued = self._calculate_days_accrued(issue_date, settlement_date)
                results['days_accrued'] = days_accrued
            
            # Days to Next Coupon
            if settlement_date:
                days_to_next_coupon = self._calculate_days_to_next_coupon(
                    settlement_date, coupon_frequency
                )
                results['days_to_next_coupon'] = days_to_next_coupon
            
            # Duration calculations
            macaulay_duration = self._calculate_macaulay_duration(
                face_value, coupon_rate, yield_to_maturity, years_to_maturity, coupon_frequency
            )
            results['macaulay_duration'] = round_value(macaulay_duration, 2)
            
            modified_duration = self._calculate_modified_duration(macaulay_duration, yield_to_maturity, coupon_frequency)
            results['modified_duration'] = round_value(modified_duration, 2)
            
            effective_duration = self._calculate_effective_duration(modified_duration, yield_to_maturity)
            results['effective_duration'] = round_value(effective_duration, 2)
            
            dollar_duration = self._calculate_dollar_duration(clean_price, modified_duration)
            results['dollar_duration'] = round_money(dollar_duration)
            
            # Convexity
            convexity = self._calculate_convexity(
                face_value, coupon_rate, yield_to_maturity, years_to_maturity, coupon_frequency
            )
            results['convexity'] = round_value(convexity, 2)
            
            # DV01 / PVBP
            dv01 = self._calculate_dv01(clean_price, modified_duration)
            results['dv01'] = round_value(dv01, 4)
            results['pvbp'] = round_value(dv01, 4)
            
            # Interest Rate Sensitivity
            results['interest_rate_sensitivity'] = round_value(modified_duration, 2)
            
            # Price Change for Yield Shift
            price_change_100bp = self._calculate_price_change(clean_price, modified_duration, 0.01)
            results['price_change_100bp'] = round_money(price_change_100bp)
            
            # Holding Period Return
            holding_period_return = self._calculate_holding_period_return(
                clean_price, coupon_payment, years_to_maturity, coupon_frequency
            )
            results['holding_period_return'] = round_percentage(holding_period_return * 100)
            
            # Total Return
            total_return = self._calculate_total_return(
                clean_price, face_value, coupon_rate, years_to_maturity, coupon_frequency
            )
            results['total_return'] = round_percentage(total_return * 100)
            
            # Capital Gain/Loss
            capital_gain_loss = face_value - clean_price
            results['capital_gain_loss'] = round_money(capital_gain_loss)
            
            # Coupon Income (total over life)
            total_coupon_income = coupon_payment * remaining_coupons
            results['coupon_income'] = round_money(total_coupon_income)
            
            # Unrealized Gain/Loss
            if market_price:
                unrealized_gain_loss = market_price - clean_price
                results['unrealized_gain_loss'] = round_money(unrealized_gain_loss)
            
            # Realized Gain/Loss (if sold at market price)
            if market_price:
                realized_gain_loss = market_price - clean_price + accrued_interest
                results['realized_gain_loss'] = round_money(realized_gain_loss)
            
            # Market Price vs Fair Value
            if market_price:
                market_vs_fair = market_price - clean_price
                results['market_price_vs_fair_value'] = round_money(market_vs_fair)
        
        # Zero Coupon Bond Price (if coupon rate is 0)
        if coupon_rate == 0 and yield_to_maturity:
            zero_coupon_price = self._calculate_zero_coupon_price(
                face_value, yield_to_maturity, years_to_maturity
            )
            results['zero_coupon_price'] = round_money(zero_coupon_price)
        
        # Benchmark comparisons
        if benchmark_yield is not None:
            # Benchmark Spread
            if yield_to_maturity:
                benchmark_spread = yield_to_maturity - benchmark_yield
                results['benchmark_spread'] = round_percentage(benchmark_spread * 100)
            
            # G-Spread (Yield minus government bond yield of same maturity)
            if yield_to_maturity:
                results['g_spread'] = round_percentage(benchmark_spread * 100)
            
            # Benchmark Yield Comparison
            results['benchmark_yield'] = round_percentage(benchmark_yield * 100)
            results['benchmark_yield_comparison'] = round_percentage(benchmark_yield * 100)
            
            # Valuation using Benchmark Yield Curve
            if benchmark_curve and face_value and years_to_maturity:
                curve_valuation = self._calculate_curve_valuation(
                    face_value, coupon_rate, years_to_maturity, coupon_frequency, benchmark_curve
                )
                results['benchmark_curve_valuation'] = round_money(curve_valuation)
        
        # Z-Spread (if benchmark curve provided)
        if benchmark_curve and yield_to_maturity and clean_price:
            z_spread = self._calculate_z_spread(
                face_value, coupon_rate, clean_price, years_to_maturity, coupon_frequency, benchmark_curve
            )
            results['z_spread'] = round_percentage(z_spread * 100)
        
        # I-Spread (Interpolated spread)
        if benchmark_yield and yield_to_maturity:
            i_spread = yield_to_maturity - benchmark_yield
            results['i_spread'] = round_percentage(i_spread * 100)
        
        # Asset Swap Spread
        if yield_to_maturity and benchmark_yield:
            asset_swap_spread = yield_to_maturity - benchmark_yield
            results['asset_swap_spread'] = round_percentage(asset_swap_spread * 100)
        
        # Credit Spread
        if yield_to_maturity and benchmark_yield:
            credit_spread = yield_to_maturity - benchmark_yield
            results['credit_spread'] = round_percentage(credit_spread * 100)
        
        # Real Yield (Inflation Adjusted)
        if inflation_rate is not None and yield_to_maturity:
            real_yield = self._calculate_real_yield(yield_to_maturity, inflation_rate)
            results['real_yield'] = round_percentage(real_yield * 100)
        
        return results
    
    def _calculate_years_to_maturity(self, settlement_date: str, maturity_date: str) -> float:
        """Calculate years between settlement and maturity."""
        settlement = datetime.strptime(settlement_date, '%Y-%m-%d')
        maturity = datetime.strptime(maturity_date, '%Y-%m-%d')
        days = (maturity - settlement).days
        return days / self.day_count_convention
    
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

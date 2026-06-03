import math
from typing import List, Dict, Any, Union

def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

def parse_percentage(value: Any) -> float:
    val = safe_float(value, 0.0)
    # If value > 1, assume it's a percentage (e.g., 5.0 = 5%)
    if val > 1:
        return val / 100.0
    return val

def normalize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Normalise column names to a standard set of keys."""
    if not isinstance(row, dict):
        return {}
    
    aliases = {
        'date': ['date', 'transaction date', 'trade date', 'settlement date', 'value date', 'start date', 'issue date'],
        'instrument': ['instrument', 'security', 'name', 'description', 'asset', 'issuer'],
        'rate': ['rate', 'interest rate', 'coupon rate', 'discount rate', 'yield', 'return', 'apr'],
        'amount': ['amount', 'face value', 'facevalue', 'value', 'price', 'notional', 'principal', 'investment'],
        'maturity_date': ['maturitydate', 'maturity date', 'maturity', 'matures', 'end date', 'due date', 'expiry date'],
        'days_to_maturity': ['daystomaturity', 'days to maturity', 'tenor', 'days', 'term', 'duration days'],
        'principal': ['principal', 'amount', 'face value', 'notional', 'investment amount'],
        'interest_rate': ['interestrate', 'interest rate', 'rate', 'coupon', 'yield'],
        'discount_rate': ['discountrate', 'discount rate', 'discount', 'rate'],
        'price': ['price', 'market price', 'current price', 'purchase price', 'bid price', 'ask price'],
        'face_value': ['facevalue', 'face value', 'face', 'value', 'amount', 'principal', 'par value', 'nominal'],
        'bond_name': ['bondname', 'bond name', 'bond', 'security', 'issuer', 'description', 'name'],
        'coupon_rate': ['couponrate', 'coupon rate', 'coupon', 'rate', 'interest rate', 'annual coupon'],
        'yield': ['yield', 'yield to maturity', 'ytm', 'return', 'effective yield'],
        'issue_date': ['issuedate', 'issue date', 'issued', 'issuance date', 'start date'],
        'frequency': ['frequency', 'payment frequency', 'coupon frequency', 'period', 'semiannual', 'quarterly', 'annual'],
        'accrued_interest': ['accruedinterest', 'accrued interest', 'accrued', 'interest accrued'],
        'redemption_value': ['redemptionvalue', 'redemption value', 'call value', 'maturity value'],
        'tbill_name': ['tbillname', 't-bill name', 'tbill', 't bill', 'security', 'instrument', 'treasury bill'],
        'purchase_price': ['purchaseprice', 'purchase price', 'buy price', 'price paid'],
        'term_days': ['termdays', 'term_days', 'term days', 'days', 'tenor', 'duration days'],
        'current_price': ['currentprice', 'current_price', 'price', 'market price'],
        'years_to_maturity': ['yearstomaturity', 'years_to_maturity', 'years', 'maturity years']
    }
    
    def normalize_key(key: str) -> str:
        return ''.join(ch for ch in key.lower() if ch.isalnum())
    
    norm_to_canon = {}
    for canon, variants in aliases.items():
        for v in variants:
            norm_to_canon[normalize_key(v)] = canon
    
    normalized = {}
    for orig_key, value in row.items():
        nk = normalize_key(orig_key)
        if nk in norm_to_canon:
            normalized[norm_to_canon[nk]] = value
        else:
            normalized[orig_key] = value
    return normalized

def calculate_treasury_bill(item: Dict[str, Any]) -> Dict[str, Any]:
    face = safe_float(item.get('face_value', 1000))
    price = safe_float(item.get('purchase_price') or item.get('current_price') or face)
    days = safe_float(item.get('term_days', 91))
    
    if price <= 0:
        price = face
    if days <= 0:
        days = 91
    
    # Bank discount yield (360 day count)
    discount_yield = ((face - price) / face) * (360 / days) * 100
    
    # Money market yield (360 day count)
    money_market_yield = ((face - price) / price) * (360 / days) * 100
    
    # Bond equivalent yield (365 day count)
    bond_equivalent_yield = ((face - price) / price) * (365 / days) * 100
    
    # Holding period yield
    holding_period_yield = ((face - price) / price) * 100
    
    return {
        'instrument_type': 'tbills',
        'face_value': round(face, 2),
        'purchase_price': round(price, 2),
        'term_days': int(days),
        'discount_yield': round(discount_yield, 2),
        'money_market_yield': round(money_market_yield, 2),
        'bond_equivalent_yield': round(bond_equivalent_yield, 2),
        'holding_period_yield': round(holding_period_yield, 2),
        'yield_curve_rate': round(money_market_yield, 2)  # primary market rate
    }

def calculate_bond(item: Dict[str, Any]) -> Dict[str, Any]:
    face = safe_float(item.get('face_value', 1000))
    coupon_rate = parse_percentage(item.get('coupon_rate', 0.05))
    price = safe_float(item.get('current_price') or item.get('price') or face)
    years = safe_float(item.get('years_to_maturity', 10))
    frequency = safe_float(item.get('frequency', 2))  # semi-annual by default
    
    if years <= 0:
        years = 10
    if price <= 0:
        price = face
    
    annual_coupon = coupon_rate * face
    coupon_per_period = annual_coupon / frequency
    periods = years * frequency
    
    # Approximate yield to maturity using bond approximation formula
    if periods > 0:
        ytm_approx = (coupon_per_period + (face - price) / periods) / ((face + price) / 2)
        ytm = ytm_approx * frequency * 100
    else:
        ytm = 0
    
    # Macaulay duration approximation (simple for fixed coupon)
    if ytm > 0:
        duration = (1 + ytm/100/frequency) / (ytm/100/frequency) - (1 + ytm/100/frequency + periods * (coupon_per_period/price - ytm/100/frequency)) / (coupon_per_period/price * ((1+ytm/100/frequency)**periods - 1) + ytm/100/frequency)
        duration = max(0, duration) / frequency
    else:
        duration = years
    
    return {
        'instrument_type': 'bonds',
        'face_value': round(face, 2),
        'current_price': round(price, 2),
        'coupon_rate': round(coupon_rate * 100, 2),
        'years_to_maturity': round(years, 2),
        'frequency': int(frequency),
        'yield_to_maturity': round(ytm, 2),
        'duration': round(duration, 2),
        'bond_equivalent_yield': round(ytm, 2),
        'yield_curve_rate': round(ytm, 2)
    }

def calculate_money_market(item: Dict[str, Any]) -> Dict[str, Any]:
    principal = safe_float(item.get('principal') or item.get('amount') or item.get('face_value', 1000))
    rate = parse_percentage(item.get('interest_rate') or item.get('rate', 0.05))
    days = safe_float(item.get('term_days') or item.get('days', 90))
    
    if days <= 0:
        days = 90
    if principal <= 0:
        principal = 1000
    
    # Simple interest (360 day count convention)
    interest = principal * rate * (days / 360)
    total_value = principal + interest
    
    # Discount yield (360 day count)
    discount_yield = (interest / total_value) * (360 / days) * 100
    
    # Effective yield (365 day count)
    effective_yield = (interest / principal) * (365 / days) * 100
    
    return {
        'instrument_type': 'money-market',
        'principal': round(principal, 2),
        'interest_rate': round(rate * 100, 2),
        'term_days': int(days),
        'interest_earned': round(interest, 2),
        'total_value': round(total_value, 2),
        'discount_yield': round(discount_yield, 2),
        'effective_yield': round(effective_yield, 2),
        'yield_curve_rate': round(effective_yield, 2)
    }

def calculate_data(data: List[Dict], instrument_type: str = 'tbills') -> Dict[str, Any]:
    if not isinstance(data, list) or len(data) == 0:
        return {
            'totalValue': 0,
            'instrumentCount': 0,
            'avgRate': 0,
            'weightedAvgRate': 0,
            'totalInterest': 0,
            'interestEarned': 0,
            'annualYield': 0,
            'effectiveAnnualRate': 0,
            'avgDaysToMaturity': 0,
            'totalPrincipal': 0,
            # Additional fields for specific types
            'avgCouponRate': 0,
            'weightedAvgCoupon': 0,
            'totalAnnualIncome': 0,
            'avgYTM': 0,
            'duration': 0,
            'avgDiscountRate': 0,
            'weightedAvgDiscount': 0,
            'totalDiscount': 0,
            'effectiveYield': 0,
            'bondEquivalentYield': 0,
            'totalPurchasePrice': 0,
            'avgInvestment': 0,
            'holdingPeriodYield': 0,
            'annualizedYield': 0,
            'pricePer100': 0
        }
    
    total_value = 0.0
    total_principal = 0.0
    total_rate_weighted = 0.0
    total_days = 0
    count = 0
    processed = []
    
    for row in data:
        norm = normalize_row(row)
        # Convert percentage strings/values to decimals if needed
        if 'coupon_rate' in norm:
            norm['coupon_rate'] = parse_percentage(norm['coupon_rate'])
        if 'interest_rate' in norm:
            norm['interest_rate'] = parse_percentage(norm['interest_rate'])
        if 'rate' in norm:
            norm['rate'] = parse_percentage(norm['rate'])
        
        if instrument_type == 'bonds':
            calc = calculate_bond(norm)
            rate = calc.get('yield_to_maturity', 0)
            value = calc.get('face_value', 0)
        elif instrument_type == 'money-market':
            calc = calculate_money_market(norm)
            rate = calc.get('effective_yield', 0)
            value = calc.get('principal', 0)
        else:  # tbills
            calc = calculate_treasury_bill(norm)
            rate = calc.get('money_market_yield', 0)
            value = calc.get('face_value', 0)
        
        processed.append(calc)
        total_value += value
        total_principal += value
        total_rate_weighted += rate * value
        total_days += calc.get('term_days', 0)
        count += 1
    
    avg_rate = total_rate_weighted / total_value if total_value > 0 else 0
    weighted_avg_rate = avg_rate
    avg_days = total_days / count if count > 0 else 0
    
    # Simple interest calculations (adjustable if needed)
    total_interest = total_value * (avg_rate / 100) * (avg_days / 360)
    interest_earned = total_interest
    
    result = {
        'totalValue': round(total_value, 2),
        'instrumentCount': count,
        'avgRate': round(avg_rate, 2),
        'weightedAvgRate': round(weighted_avg_rate, 2),
        'totalInterest': round(total_interest, 2),
        'interestEarned': round(interest_earned, 2),
        'annualYield': round(avg_rate, 2),
        'effectiveAnnualRate': round(avg_rate, 2),
        'avgDaysToMaturity': round(avg_days, 0),
        'totalPrincipal': round(total_principal, 2)
    }
    
    # Additional fields for specific instrument types
    if instrument_type == 'bonds':
        total_annual_income = total_value * (avg_rate / 100)
        result.update({
            'avgCouponRate': round(avg_rate, 2),
            'weightedAvgCoupon': round(weighted_avg_rate, 2),
            'totalAnnualIncome': round(total_annual_income, 2),
            'avgYTM': round(avg_rate, 2),
            'duration': round(sum(calc.get('duration', 0) * calc.get('face_value', 0) for calc in processed) / total_value if total_value > 0 else 0, 2)
        })
    elif instrument_type == 'tbills':
        total_discount = total_interest
        avg_investment = (total_value - total_interest) / count if count > 0 else 0
        result.update({
            'avgDiscountRate': round(avg_rate, 2),
            'weightedAvgDiscount': round(weighted_avg_rate, 2),
            'totalDiscount': round(total_discount, 2),
            'effectiveYield': round(avg_rate, 2),
            'bondEquivalentYield': round(avg_rate, 2),
            'totalPurchasePrice': round(total_value - total_interest, 2),
            'avgInvestment': round(avg_investment, 2),
            'holdingPeriodYield': round(avg_rate, 2),
            'annualizedYield': round(avg_rate, 2),
            'pricePer100': round(100 - (avg_rate * avg_days / 360), 2) if avg_rate > 0 else 100
        })
    else:  # money-market
        result.update({
            'discountYield': round(avg_rate, 2),
            'effectiveYield': round(avg_rate, 2)
        })
    
    result['calculations'] = processed
    return result
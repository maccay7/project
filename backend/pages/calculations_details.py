import math
from typing import List, Dict, Any, Union
from datetime import datetime, date

def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

def parse_percentage(value: Any) -> float:
    val = safe_float(value, 0.0)
    if val > 1:
        return val / 100.0
    return val

def parse_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value, '%Y-%m-%d').date()
        except ValueError:
            try:
                return datetime.strptime(value, '%d/%m/%Y').date()
            except ValueError:
                try:
                    return datetime.strptime(value, '%m/%d/%Y').date()
                except ValueError:
                    pass
    return date.today()

def days_between(date1: date, date2: date) -> int:
    return abs((date2 - date1).days)

# ===== 🔥 FIXED: Better normalization with more aliases =====
def normalize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(row, dict):
        return {}

    aliases = {
        'date': ['date', 'transaction date', 'trade date', 'settlement date', 'value date', 'start date', 'issue date',
                 'transactiondate', 'tradedate', 'settlementdate', 'valuedate', 'startdate', 'issuedate'],
        'instrument': ['instrument', 'security', 'name', 'description', 'asset', 'issuer', 'entity', 'company', 'ticker',
                       'symbol', 'counterparty'],
        'rate': ['rate', 'interest rate', 'coupon rate', 'discount rate', 'yield', 'return', 'apr', 'interestrate',
                 'couponrate', 'discountrate', 'annual rate', 'nominal rate'],
        'amount': ['amount', 'face value', 'facevalue', 'value', 'price', 'notional', 'principal', 'investment', 'face',
                   'nominal', 'par', 'principal amount', 'investment amount'],
        'maturity_date': ['maturitydate', 'maturity date', 'maturity', 'matures', 'end date', 'due date', 'expiry date',
                          'maturity_date', 'end_date', 'due_date', 'expiry_date'],
        'days_to_maturity': ['daystomaturity', 'days to maturity', 'tenor', 'days', 'term', 'duration days', 'term_days',
                             'termdays', 'duration', 'time to maturity'],
        'principal': ['principal', 'amount', 'face value', 'notional', 'investment amount', 'principal amount',
                      'initial investment', 'starting amount'],
        'interest_rate': ['interestrate', 'interest rate', 'rate', 'coupon', 'yield', 'annual rate', 'nominal rate',
                          'stated rate', 'coupon rate'],
        'discount_rate': ['discountrate', 'discount rate', 'discount', 'rate', 'bank discount', 'discount yield'],
        'price': ['price', 'market price', 'current price', 'purchase price', 'bid price', 'ask price', 'clean price',
                  'dirty price', 'currentprice', 'purchaseprice', 'marketprice'],
        'face_value': ['facevalue', 'face value', 'face', 'value', 'amount', 'principal', 'par value', 'nominal', 'par',
                       'notional amount'],
        'bond_name': ['bondname', 'bond name', 'bond', 'security', 'issuer', 'description', 'name', 'instrument name',
                      'security name'],
        'coupon_rate': ['couponrate', 'coupon rate', 'coupon', 'rate', 'interest rate', 'annual coupon', 'stated coupon',
                        'nominal coupon'],
        'yield': ['yield', 'yield to maturity', 'ytm', 'return', 'effective yield', 'current yield', 'annual yield',
                  'bond yield'],
        'issue_date': ['issuedate', 'issue date', 'issued', 'issuance date', 'start date', 'origination date',
                       'settlement date'],
        'frequency': ['frequency', 'payment frequency', 'coupon frequency', 'period', 'semiannual', 'quarterly', 'annual',
                      'semi-annual', 'payment period', 'coupon period'],
        'accrued_interest': ['accruedinterest', 'accrued interest', 'accrued', 'interest accrued', 'accrued amount'],
        'redemption_value': ['redemptionvalue', 'redemption value', 'call value', 'maturity value', 'redemption price',
                             'call price'],
        'tbill_name': ['tbillname', 't-bill name', 'tbill', 't bill', 'security', 'instrument', 'treasury bill',
                       'treasury', 'bill name'],
        'purchase_price': ['purchaseprice', 'purchase price', 'buy price', 'price paid', 'acquisition price',
                           'entry price'],
        'term_days': ['termdays', 'term_days', 'term days', 'days', 'tenor', 'duration days', 'maturity days',
                      'time to maturity days'],
        'current_price': ['currentprice', 'current_price', 'price', 'market price', 'trading price', 'spot price'],
        'years_to_maturity': ['yearstomaturity', 'years_to_maturity', 'years', 'maturity years',
                              'time to maturity years', 'remaining years'],
        'counterparty': ['counterparty', 'issuer', 'borrower', 'entity', 'company', 'bank', 'institution'],
        'currency': ['currency', 'ccy', 'curr', 'denomination', 'denom'],
        'country': ['country', 'nation', 'jurisdiction', 'region', 'market'],
        'settlement_date': ['settlementdate', 'settlement date', 'value date', 'value date', 'settlement'],
        'issue_price': ['issue price', 'issueprice', 'offering price', 'original price', 'par price'],
        'call_date': ['call date', 'calldate', 'call date', 'callable date', 'redemption date'],
        'put_date': ['put date', 'putdate', 'put date', 'puttable date'],
        'rating': ['rating', 'credit rating', 'credit rating', 'moody rating', 's&p rating', 'fitch rating'],
        'sector': ['sector', 'industry', 'segment', 'category', 'asset class'],
        'type': ['type', 'instrument type', 'security type', 'asset type', 'category']
    }

    def normalize_key(key: str) -> str:
        return ''.join(ch for ch in key.lower() if ch.isalnum())

    norm_to_canon = {}
    for canon, variants in aliases.items():
        for v in variants:
            norm_to_canon[normalize_key(v)] = canon

    normalized = {}
    confidence_scores = {}

    for orig_key, value in row.items():
        nk = normalize_key(orig_key)
        if nk in norm_to_canon:
            canonical = norm_to_canon[nk]
            if nk == normalize_key(canonical):
                confidence_scores[canonical] = 1.0
            elif canonical not in confidence_scores:
                confidence_scores[canonical] = 0.7
            normalized[canonical] = value
        else:
            normalized[orig_key] = value
            confidence_scores[orig_key] = 0.5

    if confidence_scores:
        normalized['_confidence_scores'] = confidence_scores

    return normalized

# ===== INSTRUMENT-SPECIFIC CALCULATION FUNCTIONS =====

def calculate_treasury_bill(item: Dict[str, Any]) -> Dict[str, Any]:
    face = safe_float(item.get('face_value', 1000))
    price = safe_float(item.get('purchase_price') or item.get('current_price') or face)
    days = safe_float(item.get('term_days', 91))

    if 'issue_date' in item and 'maturity_date' in item:
        issue_date = parse_date(item.get('issue_date'))
        maturity_date = parse_date(item.get('maturity_date'))
        calculated_days = days_between(issue_date, maturity_date)
        if calculated_days > 0:
            days = calculated_days

    if price <= 0:
        price = face
    if days <= 0:
        days = 91

    discount_yield = ((face - price) / face) * (360 / days) * 100 if face != 0 else 0.0
    money_market_yield = ((face - price) / price) * (360 / days) * 100 if price != 0 else 0.0
    bond_equivalent_yield = ((face - price) / price) * (365 / days) * 100 if price != 0 else 0.0
    holding_period_yield = ((face - price) / price) * 100 if price != 0 else 0.0
    effective_annual_yield = ((face / price) ** (365 / days) - 1) * 100 if price != 0 else 0.0

    return {
        'instrument_type': 'tbills',
        'face_value': round(face, 2),
        'purchase_price': round(price, 2),
        'term_days': int(days),
        'discount_yield': round(discount_yield, 2),
        'money_market_yield': round(money_market_yield, 2),
        'bond_equivalent_yield': round(bond_equivalent_yield, 2),
        'holding_period_yield': round(holding_period_yield, 2),
        'effective_annual_yield': round(effective_annual_yield, 2),
        'yield_curve_rate': round(money_market_yield, 2)
    }

def calculate_bond(item: Dict[str, Any]) -> Dict[str, Any]:
    face = safe_float(item.get('face_value', 1000))
    coupon_rate = parse_percentage(item.get('coupon_rate', 0.05))
    price = safe_float(item.get('current_price') or item.get('price') or face)
    years = safe_float(item.get('years_to_maturity', 10))
    frequency = safe_float(item.get('frequency', 2))

    if 'issue_date' in item and 'maturity_date' in item:
        issue_date = parse_date(item.get('issue_date'))
        maturity_date = parse_date(item.get('maturity_date'))
        calculated_days = days_between(issue_date, maturity_date)
        if calculated_days > 0:
            years = calculated_days / 365.0

    if years <= 0:
        years = 10
    if price <= 0:
        price = face

    annual_coupon = coupon_rate * face
    coupon_per_period = annual_coupon / frequency if frequency != 0 else 0
    periods = int(years * frequency) if frequency != 0 else 0

    ytm = 0.0
    if periods > 0 and (face + price) != 0:
        ytm_approx = (coupon_per_period + (face - price) / periods) / ((face + price) / 2)
        ytm = ytm_approx * frequency * 100

    duration = years  # fallback
    if ytm > 0 and frequency != 0:
        ytm_decimal = ytm / 100 / frequency
        if ytm_decimal > 0 and price != 0:
            c = coupon_per_period / price if price != 0 else 0
            y = ytm_decimal
            n = periods
            if y > 0 and c >= 0:
                numerator = (1 + y) / y - (1 + y + n * (c - y))
                denominator = c * ((1 + y) ** n - 1) + y
                if denominator != 0:
                    duration = max(0, numerator / denominator) / frequency
                else:
                    duration = years
            else:
                duration = years
        else:
            duration = years
    else:
        duration = years

    modified_duration = duration / (1 + ytm / 100 / frequency) if ytm > 0 and frequency != 0 else duration
    current_yield = (annual_coupon / price) * 100 if price > 0 else 0
    accrued_interest = annual_coupon * (years % 1) if years > 0 else 0

    return {
        'instrument_type': 'bonds',
        'face_value': round(face, 2),
        'current_price': round(price, 2),
        'coupon_rate': round(coupon_rate * 100, 2),
        'years_to_maturity': round(years, 2),
        'frequency': int(frequency),
        'yield_to_maturity': round(ytm, 2),
        'duration': round(duration, 2),
        'modified_duration': round(modified_duration, 2),
        'current_yield': round(current_yield, 2),
        'accrued_interest': round(accrued_interest, 2),
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

    interest = principal * rate * (days / 360)
    total_value = principal + interest

    discount_yield = (interest / total_value) * (360 / days) * 100 if total_value != 0 else 0.0
    effective_yield = (interest / principal) * (365 / days) * 100 if principal != 0 else 0.0

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

# ===== 🔥 FIXED: Main calculation function with proper grouping =====
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
            'pricePer100': 0,
            'calculations': []
        }

    # ===== GROUP BY INSTRUMENT NAME =====
    instrument_name_col = None
    name_variants = ['instrument', 'name', 'bond_name', 'tbill_name', 'issuer', 'security', 'description', 'counterparty',
                     'company', 'entity', 'instrument name']
    
    if data and len(data) > 0:
        first_row = data[0]
        for variant in name_variants:
            if variant in first_row:
                instrument_name_col = variant
                break
            for col in first_row.keys():
                if col.lower() == variant.lower() or variant.lower() in col.lower():
                    instrument_name_col = col
                    break
            if instrument_name_col:
                break
    
    # If still no column, try to find any column with 'name' or 'instrument'
    if not instrument_name_col and data:
        for col in first_row.keys():
            lower = col.lower()
            if 'name' in lower or 'instrument' in lower or 'security' in lower or 'bond' in lower or 'tbill' in lower:
                instrument_name_col = col
                break
    
    # If still none, use first column
    if not instrument_name_col and data:
        instrument_name_col = list(first_row.keys())[0]

    grouped = {}
    for row in data:
        name = 'Instrument'
        if instrument_name_col and row.get(instrument_name_col):
            name = str(row[instrument_name_col]).strip()
        elif row.get('Instrument'):
            name = str(row['Instrument']).strip()
        elif row.get('BondName'):
            name = str(row['BondName']).strip()
        elif row.get('TBillName'):
            name = str(row['TBillName']).strip()
        if not name or name == '':
            name = 'Instrument'
        if name not in grouped:
            grouped[name] = []
        grouped[name].append(row)

    unique_names = list(grouped.keys())
    instrument_count = len(unique_names)

    # ===== PROCESS EACH INSTRUMENT GROUP =====
    processed = []
    total_value = 0.0
    total_principal = 0.0
    total_rate_weighted = 0.0
    total_days = 0

    for name, rows in grouped.items():
        group_total_value = 0.0
        group_total_principal = 0.0
        group_total_rate = 0.0
        group_total_days = 0

        # Process each row in the group (should be one row per instrument)
        for row in rows:
            norm = normalize_row(row)
            # Normalize percentage fields
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

            # Add instrument name to the calculation result
            calc['instrument_name'] = name
            processed.append(calc)

            group_total_value += value
            group_total_principal += value
            group_total_rate += rate * value
            group_total_days += calc.get('term_days', 0)

        total_value += group_total_value
        total_principal += group_total_principal
        total_rate_weighted += group_total_rate
        total_days += group_total_days

    avg_rate = total_rate_weighted / total_value if total_value > 0 else 0
    weighted_avg_rate = avg_rate
    avg_days = total_days / instrument_count if instrument_count > 0 else 0

    total_interest = total_value * (avg_rate / 100) * (avg_days / 360) if avg_rate != 0 else 0
    interest_earned = total_interest

    # Build result with per-instrument calculations
    result = {
        'totalValue': round(total_value, 2),
        'instrumentCount': instrument_count,
        'avgRate': round(avg_rate, 2),
        'weightedAvgRate': round(weighted_avg_rate, 2),
        'totalInterest': round(total_interest, 2),
        'interestEarned': round(interest_earned, 2),
        'annualYield': round(avg_rate, 2),
        'effectiveAnnualRate': round(avg_rate, 2),
        'avgDaysToMaturity': round(avg_days, 0),
        'totalPrincipal': round(total_principal, 2),
        # 🔥 Include per-instrument calculations
        'calculations': processed
    }

    # Add instrument-specific aggregated fields
    if instrument_type == 'bonds':
        total_annual_income = total_value * (avg_rate / 100)
        total_duration_weighted = 0.0
        for calc in processed:
            total_duration_weighted += calc.get('duration', 0) * calc.get('face_value', 0)
        avg_duration = total_duration_weighted / total_value if total_value > 0 else 0
        result.update({
            'avgCouponRate': round(avg_rate, 2),
            'weightedAvgCoupon': round(weighted_avg_rate, 2),
            'totalAnnualIncome': round(total_annual_income, 2),
            'avgYTM': round(avg_rate, 2),
            'duration': round(avg_duration, 2)
        })
    elif instrument_type == 'tbills':
        total_discount = total_interest
        avg_investment = (total_value - total_interest) / instrument_count if instrument_count > 0 else 0
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
    else:
        result.update({
            'discountYield': round(avg_rate, 2),
            'effectiveYield': round(avg_rate, 2)
        })

    return result
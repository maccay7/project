import math


def safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def normalize_row(raw):
    """Normalize keys using common aliases and return a canonical dict."""
    if not isinstance(raw, dict):
        return {}
    # canonical -> list of possible aliases (normalized)
    aliases = {
        'face_value': ['facevalue', 'face_value', 'face value', 'par', 'principal'],
        'purchase_price': ['purchaseprice', 'purchase_price', 'purchase price', 'price', 'currentprice', 'current_price'],
        'term_days': ['termdays', 'term_days', 'term days', 'days'],
        'coupon_rate': ['couponrate', 'coupon_rate', 'coupon rate', 'coupon_rate_percent', 'coupon'],
        'current_price': ['currentprice', 'current_price', 'price'],
        'interest_rate': ['interestrate', 'interest_rate', 'rate'],
        'years_to_maturity': ['yearstomaturity', 'years_to_maturity', 'years', 'maturity_years']
    }

    def key_norm(k):
        return ''.join(ch for ch in k.lower() if ch.isalnum())

    norm = {}
    keys = {key_norm(k): k for k in raw.keys()}
    for canon, alist in aliases.items():
        found = None
        for a in alist:
            if key_norm(a) in keys:
                found = keys[key_norm(a)]
                break
        if found:
            norm[canon] = raw.get(found)
    # include any original entries not mapped
    for k, v in raw.items():
        if k not in norm:
            norm[k] = v
    return norm


def calculate_treasury_bill(item):
    principal = safe_float(item.get('face_value') or item.get('principal') or 1000)
    price = safe_float(item.get('purchase_price') or item.get('purchasePrice') or item.get('currentPrice') or principal)
    days = safe_float(item.get('term_days') or item.get('termDays') or item.get('days') or 91)
    if price <= 0:
        price = principal
    ytm = ((principal - price) / price) * (365 / days) * 100 if days else 0
    return {
        'instrument_type': 'treasury_bills',
        'purchase_price': round(price, 2),
        'face_value': round(principal, 2),
        'term_days': int(days),
        'yield_to_maturity': round(ytm, 2),
        'annual_yield': round(ytm, 2),
        'yield_curve_rate': round(ytm, 2)
    }


def calculate_bond(item):
    face = safe_float(item.get('face_value') or item.get('faceValue') or 1000)
    coupon_rate = safe_float(item.get('coupon_rate') or item.get('couponRate') or item.get('coupon_rate_percent') or 0.05)
    price = safe_float(item.get('current_price') or item.get('currentPrice') or item.get('price') or face)
    years = safe_float(item.get('years_to_maturity') or item.get('maturity_years') or item.get('years') or 10)
    annual_coupon = coupon_rate * face
    if price <= 0:
        price = face
    ytm = ((annual_coupon + (face - price) / years) / ((face + price) / 2)) * 100 if years else 0
    return {
        'instrument_type': 'bonds',
        'face_value': round(face, 2),
        'current_price': round(price, 2),
        'coupon_rate': round(coupon_rate * 100, 2),
        'years_to_maturity': int(years),
        'yield_to_maturity': round(ytm, 2),
        'bond_equivalent_yield': round(ytm, 2),
        'yield_curve_rate': round(ytm, 2)
    }


def calculate_money_market(item):
    principal = safe_float(item.get('principal') or item.get('face_value') or 1000)
    rate = safe_float(item.get('interest_rate') or item.get('rate') or 0.05)
    days = safe_float(item.get('term_days') or item.get('days') or 90)
    discount_yield = rate * 360 / days * 100 if days else 0
    effective_yield = (rate / (1 - rate * days / 360)) * 100 if days and rate < 1 else 0
    return {
        'instrument_type': 'money_market',
        'principal': round(principal, 2),
        'interest_rate': round(rate * 100, 2),
        'term_days': int(days),
        'discount_yield': round(discount_yield, 2),
        'effective_yield': round(effective_yield, 2),
        'yield_curve_rate': round(effective_yield, 2)
    }


def calculate_data(data, instrument_type='treasury_bills'):
    if not isinstance(data, list):
        return []
    calculations = []
    for item in data:
        row = normalize_row(item or {})
        # normalize percentage inputs: if coupon_rate > 1 assume percent
        try:
            if 'coupon_rate' in row:
                cr = safe_float(row.get('coupon_rate'))
                if cr > 1:
                    row['coupon_rate'] = cr / 100.0
            if 'interest_rate' in row:
                ir = safe_float(row.get('interest_rate'))
                if ir > 1:
                    row['interest_rate'] = ir / 100.0
        except Exception:
            pass

        if instrument_type == 'bonds':
            calculations.append(calculate_bond(row))
        elif instrument_type == 'money_market':
            calculations.append(calculate_money_market(row))
        else:
            calculations.append(calculate_treasury_bill(row))
    return calculations

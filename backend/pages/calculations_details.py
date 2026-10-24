import math
import re
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional


def _unwrap_cell(value):
    if isinstance(value, dict):
        for key in ('v', 'value', 'w', 'f'):
            if key in value and value[key] is not None:
                return _unwrap_cell(value[key])
        if 'richText' in value and isinstance(value['richText'], list):
            parts = []
            for chunk in value['richText']:
                if isinstance(chunk, dict) and 'text' in chunk:
                    parts.append(str(chunk['text']))
                elif isinstance(chunk, str):
                    parts.append(chunk)
            return ''.join(parts) if parts else None
        return None
    if isinstance(value, list):
        for item in value:
            u = _unwrap_cell(item)
            if u not in (None, ''):
                return u
        return None
    return value


def safe_float(value: Any) -> Optional[float]:
    value = _unwrap_cell(value)
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    if isinstance(value, str):
        cleaned = (value.strip()
                   .replace(",", "").replace("$", "").replace("€", "")
                   .replace("£", "").replace("%", "").replace(" ", ""))
        if cleaned == "":
            return None
        if cleaned.startswith("(") and cleaned.endswith(")"):
            cleaned = "-" + cleaned[1:-1]
        try:
            return float(cleaned)
        except (TypeError, ValueError):
            return None
    return None


def parse_percentage(value: Any) -> Optional[float]:
    value = _unwrap_cell(value)
    if value is None or value == "":
        return None
    try:
        if isinstance(value, str):
            v = value.strip()
            had_pct = v.endswith("%")
            if had_pct:
                v = v.rstrip("%").strip()
            v = v.replace(",", "").replace(" ", "")
            val = float(v)
            if had_pct:
                return val / 100.0
        else:
            val = float(value)
        if val > 1:
            return val / 100.0
        return val
    except (TypeError, ValueError):
        return None


def parse_frequency(value: Any) -> Optional[int]:
    value = _unwrap_cell(value)
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        v = value.strip().lower()
        frequency_map = {
            'annual': 1, 'annually': 1, 'yearly': 1, '1': 1, 'once per year': 1,
            'semi-annual': 2, 'semi-annually': 2, 'semiannual': 2,
            'semi annually': 2, 'semiannually': 2, 'semi annual': 2,
            'bi-annual': 2, 'biannual': 2, 'bi annual': 2,
            'half-yearly': 2, 'half yearly': 2, '2': 2, 'twice per year': 2,
            'quarterly': 4, 'quarter': 4, '4': 4, 'four times per year': 4,
            'monthly': 12, 'month': 12, '12': 12, 'twelve times per year': 12,
        }
        if v in frequency_map:
            return frequency_map[v]
        num_match = re.search(r'\d+', v)
        if num_match:
            num = int(num_match.group())
            if num in [1, 2, 4, 12]:
                return num
    return None


_DATE_FORMATS = (
    "%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%d/%m/%Y", "%d/%m/%y",
    "%Y/%m/%d", "%d-%m-%Y", "%m-%d-%Y", "%d-%m-%y", "%m-%d-%y",
    "%d.%m.%Y", "%d %b %Y", "%d-%b-%Y", "%d-%b-%y", "%d %b %y",
    "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S",
)


def parse_date(value: Any) -> Optional[date]:
    value = _unwrap_cell(value)
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)):
        try:
            n = float(value)
            if 1 <= n <= 2958465:
                return (datetime(1899, 12, 30) + timedelta(days=int(n))).date()
        except Exception:
            pass
        return None
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                continue
    return None


def round_money(value: Any) -> Optional[float]:
    val = safe_float(value)
    if val is None:
        return None
    return float(Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def round_time(value: Any) -> Optional[int]:
    val = safe_float(value)
    return None if val is None else int(round(val))


def _rate(value):
    """Round a percentage to 4 dp using half-up (not banker's)."""
    if value is None:
        return None
    try:
        return float(Decimal(str(value)).quantize(Decimal("0.0001"),
                                                   rounding=ROUND_HALF_UP))
    except Exception:
        return None


def days_between(d1: date, d2: date) -> int:
    return abs((d2 - d1).days)


def _days_derivation(val_d: Optional[date], mat_d: Optional[date],
                     days: Optional[int]) -> Optional[Dict[str, Any]]:
    if not (val_d and mat_d and days is not None):
        return None
    return {
        "from": val_d.isoformat(),
        "to": mat_d.isoformat(),
        "result": int(days),
        "unit": "days",
        "formula": "maturity_date - valuation_date",
    }


def _derivation(formula, inputs_dict, result_val, unit=None):
    """Uniform derivation record shape used by every calculate_* function."""
    d = {
        "formula": formula,
        "inputs": inputs_dict,
        "result": result_val,
    }
    if unit is not None:
        d["unit"] = unit
    return d


def _add_input_dates(result, val_d, mat_d, item):
    """Echo the parsed input dates back so the calculation-details popup
    can show them for every instrument type."""
    if val_d:
        result["valuation_date"] = val_d.isoformat()
    if mat_d:
        result["maturity_date"] = mat_d.isoformat()
    iss_d = parse_date(item.get("issue_date"))
    if iss_d:
        result["issue_date"] = iss_d.isoformat()
    settle_d = parse_date(item.get("settlement_date"))
    if settle_d:
        result["settlement_date"] = settle_d.isoformat()
    last_coupon_d = parse_date(item.get("last_coupon_date"))
    if last_coupon_d:
        result["last_coupon_date"] = last_coupon_d.isoformat()
    return result


SPECIFIC_ALIASES: Dict[str, List[str]] = {
    "face_value": [
        "face value", "facevalue", "face_value",
        "par value", "parvalue", "par_value",
        "redemption value", "redemptionvalue", "redemption_value",
        "maturity value", "maturityvalue", "maturity_value",
        "nominal value", "nominalvalue", "nominal_value",
    ],
    "coupon_rate": [
        "coupon rate", "couponrate", "coupon_rate",
        "coupon", "annual coupon", "annualcoupon",
        "fixed rate", "fixedrate",
        "nominal rate", "nominalrate",
        "stated rate", "statedrate",
        "interest rate", "interestrate",
    ],
    "coupon_frequency": [
        "coupon frequency", "couponfrequency", "coupon_frequency",
        "Coupon Frequency", "CouponFrequency", "Coupon_Frequency",
        "payment frequency", "paymentfrequency",
        "frequency", "coupon period", "payments per year",
    ],
    "principal": [
        "principal", "principle", "principal amount", "principle amount",
        "face value", "facevalue", "face_value", "face amount",
        "par value", "parvalue", "par amount",
        "nominal", "nominal amount", "nominal value",
        "notional", "notional amount",
        "investment amount", "initial investment", "initial amount",
        "starting balance", "opening balance", "deposit amount",
        "capital", "total cost", "purchase cost", "cost", "amount", "value",
        "outstanding principal", "current principal",
    ],
    "interest_rate": [
        "interest rate", "interestrate", "interest_rate",
        "annual rate", "annual interest rate",
        "nominal rate", "stated rate", "effective rate",
        "apr", "coupon", "coupon rate",
        "rate %", "rate%", "rate",
    ],
    "days_to_maturity": [
        "days to maturity", "daystomaturity", "days_to_maturity",
        "maturity days", "duration days", "contract days",
        "term days", "term_days", "termdays", "term in days",
        "tenor", "term", "days", "period",
    ],
    "term_days": [
        "term days", "termdays", "term_days",
        "days to maturity", "daystomaturity",
        "maturity days", "maturitydays",
        "tenor", "term", "days",
    ],
    "issue_date": [
        "issue date", "issuedate", "issue_date",
        "start date", "startdate", "start_date",
        "effective date", "effectivedate", "effective_date",
        "settlement date", "settlementdate", "settlement_date",
        "origination date", "value date", "valuedate", "value_date",
        "trade date", "tradedate", "trade_date",
    ],
    "last_coupon_date": [
        "last coupon date", "lastcoupondate", "last_coupon_date",
        "previous coupon date", "previouscoupondate", "previous_coupon_date",
    ],
    "maturity_date": [
        "maturity date", "maturitydate", "maturity_date",
        "end date", "enddate", "end_date",
        "due date", "duedate", "due_date",
        "redemption date", "redemptiondate", "redemption_date",
        "expiry date", "expirydate", "expiry_date",
        "termination date",
    ],
    "valuation_date": [
        "valuation", "valuation date", "valuationdate", "valuation_date",
        "portfolio date", "portfoliodate", "portfolio_date",
        "report date", "reportdate", "report_date",
        "as of date", "asofdate", "as_of_date",
        "date pfolio", "datepfolio",
    ],
    "purchase_price": [
        "purchase price", "purchaseprice", "purchase_price",
        "buy price", "buyprice", "buy_price",
        "acquisition price", "entry price",
        "price paid", "pricepaid", "price_paid",
        "issue price", "issueprice", "issue_price",
        "price",
    ],
    "current_price": ["current price", "currentprice", "current_price"],
    "settlement_amount": [
        "settlement amount", "settlementamount",
        "settlement value", "cash flow", "proceeds",
    ],
    "market_value": [
        "market value", "marketvalue", "market_value",
        "current value", "currentvalue",
        "fair value", "fairvalue",
        "present value", "presentvalue",
        "total value", "totalvalue",
    ],
    "portfolio_name": ["portfolio name", "pfolio name", "portfolio"],
    "security": [
        "security", "security id", "securityid",
        "instrument id", "instrumentid", "isin", "ticker",
    ],
    "instrument_name": [
        "instrument name", "instrumentname", "instrument_name",
        "bond name", "bondname", "bond_name",
        "t-bill name", "tbill name", "tbillname", "tbill_name",
        "treasury bill name",
        "security name", "securityname",
        "issuer", "parent company name", "parent company",
        "company", "entity",
        "short name", "shortname",
        "description",
        "name", "ticker", "symbol",
    ],
    "counterparty": [
        "counterparty", "counter party", "counter-party", "cp",
        "account name", "client name",
    ],
    "classification": ["classification", "category", "asset class", "type"],
    "currency": ["currency", "ccy", "iso code", "currency code"],
    "country": ["country", "jurisdiction", "domicile"],
    "sector": ["sector", "industry", "industry group"],
    "rating": ["credit rating", "rating", "moody", "s&p", "fitch"],
    "discount_rate": [
        "discount rate", "discountrate", "discount_rate",
        "bank discount", "bankdiscount",
        "discount yield", "discountyield",
        "t-bill rate", "tbillrate",
        "auction rate", "auctionrate",
        "discount",
    ],
    "auction_date": ["auction date", "auctiondate", "issue date", "settlement date"],
    "years_to_maturity": [
        "years to maturity", "yearstomaturity", "years_to_maturity",
        "maturity years", "maturityyears",
        "term years", "termyears",
        "duration years", "durationyears",
        "time to maturity", "timetomaturity",
        "years", "year",
    ],
    "yield": [
        "yield to maturity", "yieldtomaturity", "yield_to_maturity",
        "ytm", "market yield", "marketyield",
        "required return", "requiredreturn",
        "redemption yield", "redemptionyield",
        "yield",
    ],
    "call_date": ["call date", "calldate", "first call date"],
    "call_price": ["call price", "callprice", "call premium", "redemption price"],
    "put_date": ["put date", "putdate", "puttable date"],
    "put_price": ["put price", "putprice", "put premium"],
    "benchmark_rate": [
        "benchmark rate", "benchmarkrate",
        "risk-free rate", "riskfreerate",
        "government yield", "governmentyield",
        "treasury yield", "treasuryyield", "sofr",
    ],
    "credit_spread": [
        "credit spread", "creditspread",
        "g-spread", "gspread", "z-spread", "zspread",
        "asset swap spread", "oas",
    ],
    "inflation_rate": ["inflation rate", "inflationrate", "cpi", "inflation"],
    "instrument": ["instrument", "instrument type", "instrumenttype",
                   "asset type", "security type"],
    "exchange": ["exchange", "listing exchange", "trading venue"],
    "risk": ["risk", "risk level", "risklevel", "risk category"],
}


def _tokenize(s: str) -> set:
    return set(re.split(r"[\s_\-%\(\)\[\]/\.]+", str(s).lower().strip())) - {""}


def normalize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(row, dict):
        return {}
    normalized: Dict[str, Any] = {}
    consumed: set = set()

    for target, aliases in SPECIFIC_ALIASES.items():
        for alias in aliases:
            alias_l = alias.lower().strip()
            for src_key in row.keys():
                if src_key in consumed:
                    continue
                if str(src_key).lower().strip() == alias_l:
                    normalized[target] = _unwrap_cell(row[src_key])
                    consumed.add(src_key)
                    break
            if target in normalized:
                break

    for target, aliases in SPECIFIC_ALIASES.items():
        if target in normalized:
            continue
        for alias in aliases:
            alias_tokens = _tokenize(alias)
            if len(alias_tokens) < 2:
                continue
            for src_key in row.keys():
                if src_key in consumed:
                    continue
                if alias_tokens.issubset(_tokenize(src_key)):
                    normalized[target] = _unwrap_cell(row[src_key])
                    consumed.add(src_key)
                    break
            if target in normalized:
                break

    for key, value in row.items():
        if key not in consumed and key not in normalized:
            unwrapped = _unwrap_cell(value)
            if unwrapped is not None:
                normalized[key] = unwrapped

    return normalized


def _extract_instrument_name(row: Dict[str, Any]) -> Optional[str]:
    candidates = [
        "instrument_name", "BondName", "TBillName",
        "Instrument Name", "Security", "Name",
        "Ticker", "Symbol", "ISIN", "isin", "Security ID",
    ]
    for key in candidates:
        v = row.get(key)
        if v is None:
            continue
        s = str(v).strip()
        if s and s.lower() not in ("n/a", "na", "-", "none", "null", ""):
            return s
    return None


def validate_row(row: Dict[str, Any], instrument_type: str) -> Dict[str, Any]:
    if not isinstance(row, dict):
        return {"can_calculate": False,
                "missing_fields": ["row is not a dictionary"],
                "invalid_fields": [], "detected_fields": {},
                "normalized_row": {}, "all_source_keys": []}

    raw_coupon_frequency = (row.get('Coupon Frequency') or row.get('coupon_frequency')
                            or row.get('frequency') or row.get('instrument_type'))

    norm = normalize_row(row)
    missing: List[str] = []
    invalid: List[tuple] = []
    detected: Dict[str, Any] = {}

    def note(field):
        if norm.get(field) is not None:
            detected[field] = norm.get(field)

    if instrument_type == "bonds":
        face = safe_float(norm.get("face_value")) or safe_float(norm.get("principal"))
        note("face_value"); note("principal")
        if face is None:
            missing.append("face_value (aliases: Face Value, Principal, Par Value, Notional, Amount)")

        cr = parse_percentage(norm.get("coupon_rate")) or parse_percentage(norm.get("interest_rate"))
        note("coupon_rate"); note("interest_rate")
        if cr is None:
            missing.append("coupon_rate (aliases: Coupon Rate, Coupon, Interest Rate, Rate)")

        price = (safe_float(norm.get("price"))
                 or safe_float(norm.get("purchase_price"))
                 or safe_float(norm.get("current_price")))
        ytm = parse_percentage(norm.get("yield")) or parse_percentage(norm.get("yield_to_maturity"))
        note("price"); note("purchase_price"); note("current_price")
        note("yield"); note("yield_to_maturity")
        if price is None and ytm is None:
            missing.append("price or yield_to_maturity")

        years = safe_float(norm.get("years_to_maturity"))
        note("years_to_maturity"); note("valuation_date"); note("maturity_date")
        if years is None:
            val_d = parse_date(norm.get("valuation_date"))
            mat_d = parse_date(norm.get("maturity_date"))
            if val_d and mat_d and mat_d >= val_d:
                years = (mat_d - val_d).days / 365.0
            else:
                d2m = safe_float(norm.get("days_to_maturity"))
                if d2m is not None:
                    years = d2m / 365.0
        if years is None or years <= 0:
            missing.append("years_to_maturity (or Valuation Date + Maturity Date)")

        note("coupon_frequency"); note("frequency"); note("Coupon Frequency")

        if face is not None and face <= 0:
            invalid.append(("face_value", "must be > 0"))

        val_d = parse_date(norm.get("valuation_date"))
        mat_d = parse_date(norm.get("maturity_date"))
        iss_d = parse_date(norm.get("issue_date"))
        if val_d and mat_d and val_d > mat_d:
            invalid.append(("valuation_date", "must be on or before maturity_date"))
        if iss_d and mat_d and iss_d > mat_d:
            invalid.append(("issue_date", "must be on or before maturity_date"))

    elif instrument_type == "money-market":
        principal = (safe_float(norm.get("principal"))
                     or safe_float(norm.get("face_value"))
                     or safe_float(norm.get("amount")))
        note("principal"); note("face_value"); note("amount")
        if principal is None:
            missing.append("principal (aliases: Principal, Principle, Face Value, Amount, Notional)")
        elif principal <= 0:
            invalid.append(("principal", "must be > 0"))

        rate = (parse_percentage(norm.get("interest_rate"))
                or parse_percentage(norm.get("rate")))
        note("interest_rate"); note("rate")
        if rate is None:
            missing.append("interest_rate (aliases: Interest Rate, Rate, Coupon, Yield)")
        elif rate < 0:
            invalid.append(("interest_rate", "must be >= 0"))

        days = safe_float(norm.get("term_days")) or safe_float(norm.get("days_to_maturity"))
        note("term_days"); note("days_to_maturity")
        note("valuation_date"); note("maturity_date"); note("issue_date")
        if days is None:
            val_d = parse_date(norm.get("valuation_date"))
            mat_d = parse_date(norm.get("maturity_date"))
            if val_d and mat_d and mat_d >= val_d:
                days = (mat_d - val_d).days
        if days is None:
            iss_d = parse_date(norm.get("issue_date"))
            mat_d = parse_date(norm.get("maturity_date"))
            if iss_d and mat_d and mat_d >= iss_d:
                days = (mat_d - iss_d).days
        if days is None or days <= 0:
            missing.append("term_days (or Valuation Date + Maturity Date)")

        val_d = parse_date(norm.get("valuation_date"))
        mat_d = parse_date(norm.get("maturity_date"))
        iss_d = parse_date(norm.get("issue_date"))
        if val_d and mat_d and val_d > mat_d:
            invalid.append(("valuation_date", "must be on or before maturity_date"))
        if iss_d and mat_d and iss_d > mat_d:
            invalid.append(("issue_date", "must be on or before maturity_date"))

    else:
        face = safe_float(norm.get("face_value")) or safe_float(norm.get("principal"))
        note("face_value"); note("principal")
        if face is None:
            missing.append("face_value (aliases: Face Value, Principal, Par Value, Amount, Notional)")
        elif face <= 0:
            invalid.append(("face_value", "must be > 0"))

        days = safe_float(norm.get("term_days")) or safe_float(norm.get("days_to_maturity"))
        note("term_days"); note("days_to_maturity")
        note("valuation_date"); note("maturity_date"); note("issue_date")
        if days is None:
            val_d = parse_date(norm.get("valuation_date"))
            mat_d = parse_date(norm.get("maturity_date"))
            if val_d and mat_d and mat_d >= val_d:
                days = (mat_d - val_d).days
        if days is None:
            iss_d = parse_date(norm.get("issue_date"))
            mat_d = parse_date(norm.get("maturity_date"))
            if iss_d and mat_d and mat_d >= iss_d:
                days = (mat_d - iss_d).days
        if days is None or days <= 0:
            missing.append("term_days (or Valuation Date + Maturity Date)")

        price = (safe_float(norm.get("purchase_price"))
                 or safe_float(norm.get("price"))
                 or safe_float(norm.get("current_price")))
        disc = parse_percentage(norm.get("discount_rate"))
        note("purchase_price"); note("price"); note("current_price"); note("discount_rate")
        if price is None and disc is None:
            missing.append("purchase_price or discount_rate")

        if price is not None and face is not None and price > face:
            invalid.append(("purchase_price", "cannot exceed face value for discount instruments"))
        if disc is not None and disc < 0:
            invalid.append(("discount_rate", "must be >= 0"))

        val_d = parse_date(norm.get("valuation_date"))
        mat_d = parse_date(norm.get("maturity_date"))
        iss_d = parse_date(norm.get("issue_date"))
        if val_d and mat_d and val_d > mat_d:
            invalid.append(("valuation_date", "must be on or before maturity_date"))
        if iss_d and mat_d and iss_d > mat_d:
            invalid.append(("issue_date", "must be on or before maturity_date"))

    return {
        "can_calculate": len(missing) == 0 and len(invalid) == 0,
        "missing_fields": missing,
        "invalid_fields": [{"field": f, "reason": r} for f, r in invalid],
        "detected_fields": detected,
        "normalized_row": norm,
        "all_source_keys": list(row.keys()),
    }


def _solve_ytm(price, face, coupon_rate, years, frequency):
    if price is None or face is None or coupon_rate is None:
        return None
    if price <= 0 or face <= 0 or years is None or years <= 0 or frequency <= 0:
        return None
    n = max(1, int(round(years * frequency)))
    coupon = face * coupon_rate / frequency

    def pv(y):
        r = y / frequency
        if r <= -1:
            return float("inf")
        total = sum(coupon / ((1 + r) ** t) for t in range(1, n + 1))
        return total + face / ((1 + r) ** n)

    lo, hi = -0.99, 10.0
    f_lo = pv(lo) - price
    f_hi = pv(hi) - price
    if f_lo * f_hi > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        f_mid = pv(mid) - price
        if abs(f_mid) < 1e-8 or (hi - lo) < 1e-10:
            return mid
        if f_mid * f_lo < 0:
            hi = mid
        else:
            lo = mid
            f_lo = f_mid
    return (lo + hi) / 2


def _price_from_ytm(face, coupon_rate, ytm, years, frequency):
    if any(v is None for v in (face, coupon_rate, ytm, years, frequency)):
        return None
    if face <= 0 or years <= 0 or frequency <= 0:
        return None
    r = ytm / frequency
    if r <= -1:
        return None
    n = max(1, int(round(years * frequency)))
    coupon_per = face * coupon_rate / frequency
    pv = sum(coupon_per / ((1 + r) ** t) for t in range(1, n + 1))
    return pv + face / ((1 + r) ** n)


def _parse_bond_price(item, face):
    raw = item.get("price") or item.get("purchase_price") or item.get("current_price")
    if raw is None:
        return None
    s = str(raw).strip()
    if s.endswith("%"):
        pct = parse_percentage(raw)
        if pct is not None and face is not None:
            return face * pct
        return None
    p = safe_float(raw)
    if p is None:
        return None
    if face is not None and face >= 100 and 0 < p < face * 0.3:
        return p * face / 100.0
    return p


def _bond_accrued(item, face, coupon_rate, frequency, day_count_str):
    if face is None or coupon_rate is None or not frequency:
        return None, None
    last = parse_date(item.get("last_coupon_date")) or parse_date(item.get("issue_date"))
    settle = parse_date(item.get("valuation_date")) or parse_date(item.get("settlement_date"))
    if not last or not settle:
        return None, None
    days = (settle - last).days
    if days < 0:
        return None, None
    basis = 360.0 if "360" in day_count_str else 365.0
    days_in_period = basis / frequency
    coupon_per = face * coupon_rate / frequency
    return coupon_per * (days / days_in_period), days


_CAMEL_PAIRS = {
    "face_value": "faceValue", "current_price": "currentPrice",
    "coupon_rate": "couponRate", "years_to_maturity": "yearsToMaturity",
    "yield_to_maturity": "yieldToMaturity",
    "modified_duration": "modifiedDuration",
    "macaulay_duration": "macaulayDuration",
    "current_yield": "currentYield", "accrued_interest": "accruedInterest",
    "annual_coupon": "annualCoupon", "coupon_payment": "couponPayment",
    "coupon_per_period": "couponPerPeriod", "days_accrued": "daysAccrued",
    "price_per_100": "pricePer100",
    "bond_equivalent_yield": "bondEquivalentYield",
    "yield_curve_rate": "yieldCurveRate",
    "present_value": "presentValue", "fair_value": "fairValue",
    "carrying_value": "carryingValue", "discount_rate": "discountRate",
    "total_value": "totalValue", "term_days": "termDays",
    "interest_rate": "interestRate", "interest_earned": "interestEarned",
    "maturity_value": "maturityValue", "total_interest": "totalInterest",
    "discount_yield": "discountYield", "effective_yield": "effectiveYield",
    "effective_annual_rate": "effectiveAnnualRate",
    "effective_annual_yield": "effectiveAnnualYield",
    "money_market_yield": "moneyMarketYield",
    "holding_period_yield": "holdingPeriodYield",
    "discount_amount": "discountAmount",
    "purchase_price": "purchasePrice", "market_value": "marketValue",
    "valuation_date": "valuationDate",
    "maturity_date": "maturityDate",
    "issue_date": "issueDate",
    "settlement_date": "settlementDate",
    "last_coupon_date": "lastCouponDate",
    "ytm_input": "ytmInput",
    "ytm_source": "ytmSource",
}


def _add_camel_aliases(result):
    for snake, camel in _CAMEL_PAIRS.items():
        if snake in result and camel not in result:
            result[camel] = result[snake]
    return result


def calculate_treasury_bill(item: Dict[str, Any],
                            benchmark_yield: Optional[float] = None) -> Dict[str, Any]:
    item = normalize_row(item)
    face = safe_float(item.get("face_value")) or safe_float(item.get("principal"))
    purchase_price = (safe_float(item.get("purchase_price"))
                      or safe_float(item.get("current_price"))
                      or safe_float(item.get("price")))
    discount_rate = parse_percentage(item.get("discount_rate"))
    currency = item.get("currency") or item.get("ccy") or item.get("currency_code")

    day_count = str(item.get("day_count_convention") or item.get("day_count") or "ACT/360").upper()
    discount_basis = 365.0 if "365" in day_count else 360.0

    val_d = parse_date(item.get("valuation_date"))
    mat_d = parse_date(item.get("maturity_date"))
    days = safe_float(item.get("term_days")) or safe_float(item.get("days_to_maturity"))
    if days is None and val_d and mat_d:
        days = (mat_d - val_d).days if mat_d >= val_d else None
    if days is None:
        iss_d = parse_date(item.get("issue_date"))
        if iss_d and mat_d and mat_d >= iss_d:
            days = (mat_d - iss_d).days

    if (discount_rate is None and purchase_price is not None
            and face is not None and days is not None and days > 0):
        discount_rate = (face - purchase_price) / face * discount_basis / days

    bad = (face is None or days is None
           or (days is not None and days <= 0))

    result = {
        "status": "partial" if bad else "success",
        "instrument_type": "tbills",
        "face_value": round_money(face),
        "term_days": round_time(days) if days is not None and days > 0 else None,
        "discount_rate": _rate(discount_rate * 100) if discount_rate is not None else None,
        "day_count_convention": day_count,
        "currency": currency,
    }

    name = _extract_instrument_name(item)
    if name:
        result["instrument_name"] = name

    _add_input_dates(result, val_d, mat_d, item)

    derivations: Dict[str, Any] = {}

    days_deriv = _days_derivation(val_d, mat_d, days)
    if days_deriv:
        derivations["days_to_maturity"] = days_deriv

    if (face is not None and days is not None and days > 0
            and discount_rate is not None and purchase_price is None):
        derived_pp = face * (1.0 - discount_rate * days / discount_basis)
        derivations["purchase_price"] = _derivation(
            "face_value * (1 - discount_rate * days / discount_basis)",
            {"face_value": round_money(face),
             "discount_rate": _rate(discount_rate * 100),
             "days": round_time(days),
             "discount_basis": discount_basis},
            round_money(derived_pp),
            "currency",
        )
        purchase_price = derived_pp

    if purchase_price is not None and purchase_price > 0:
        result["purchase_price"] = round_money(purchase_price)

    carrying = safe_float(item.get("carrying_value")) or safe_float(item.get("book_value"))
    if carrying is not None:
        result["carrying_value"] = round_money(carrying)
    elif isinstance(item.get("carrying_value"), str):
        result["carrying_value"] = item.get("carrying_value")

    if (face is not None and purchase_price is not None and purchase_price > 0
            and days is not None and days > 0):
        discount_amount = face - purchase_price
        disc_yield = (discount_amount / face) * (discount_basis / days) * 100.0
        mm_yield = (discount_amount / purchase_price) * (discount_basis / days) * 100.0
        be_yield = (discount_amount / purchase_price) * (365.0 / days) * 100.0
        hp_yield = (discount_amount / purchase_price) * 100.0
        eff_yield = ((face / purchase_price) ** (365.0 / days) - 1.0) * 100.0

        derivations["discount_amount"] = _derivation(
            "face_value - purchase_price",
            {"face_value": round_money(face),
             "purchase_price": round_money(purchase_price)},
            round_money(discount_amount),
            "currency",
        )
        derivations["money_market_yield"] = _derivation(
            "((face_value - purchase_price) / purchase_price) * (basis / days) * 100",
            {"face_value": round_money(face),
             "purchase_price": round_money(purchase_price),
             "days": round_time(days),
             "basis": discount_basis},
            _rate(mm_yield),
            "percent",
        )
        derivations["bond_equivalent_yield"] = _derivation(
            "((face_value - purchase_price) / purchase_price) * (365 / days) * 100",
            {"face_value": round_money(face),
             "purchase_price": round_money(purchase_price),
             "days": round_time(days)},
            _rate(be_yield),
            "percent",
        )
        derivations["effective_annual_yield"] = _derivation(
            "((face_value / purchase_price) ** (365 / days) - 1) * 100",
            {"face_value": round_money(face),
             "purchase_price": round_money(purchase_price),
             "days": round_time(days)},
            _rate(eff_yield),
            "percent",
        )

        result.update({
            "discount_amount": round_money(discount_amount),
            "discount_yield": _rate(disc_yield),
            "money_market_yield": _rate(mm_yield),
            "bond_equivalent_yield": _rate(be_yield),
            "holding_period_yield": _rate(hp_yield),
            "effective_annual_yield": _rate(eff_yield),
            "yield_curve_rate": _rate(benchmark_yield * 100) if benchmark_yield is not None else None,
            "total_value": round_money(face),
            "status": "success",
        })

    if derivations:
        result["derivations"] = derivations

    return _add_camel_aliases(result)


def calculate_bond(item: Dict[str, Any],
                   benchmark_yield: Optional[float] = None) -> Dict[str, Any]:
    raw_freq = (item.get("Coupon Frequency") or item.get("coupon_frequency")
                or item.get("frequency"))
    item = normalize_row(item)

    face = safe_float(item.get("face_value")) or safe_float(item.get("principal"))
    coupon_rate = (parse_percentage(item.get("coupon_rate"))
                   or parse_percentage(item.get("interest_rate")))
    currency = item.get("currency") or item.get("ccy") or item.get("currency_code")

    price = _parse_bond_price(item, face)
    price_was_input = price is not None and price > 0
    day_count = str(item.get("day_count_convention") or item.get("day_count") or "ACT/365").upper()

    val_d = parse_date(item.get("valuation_date"))
    mat_d = parse_date(item.get("maturity_date"))

    years = safe_float(item.get("years_to_maturity"))
    years_derived_from_dates = False
    if years is None and val_d and mat_d:
        years = ((mat_d - val_d).days / 365.0) if mat_d >= val_d else None
        years_derived_from_dates = True
    if years is None:
        d2m = safe_float(item.get("days_to_maturity"))
        if d2m is not None and d2m > 0:
            years = d2m / 365.0
            years_derived_from_dates = True

    frequency = (
        parse_frequency(item.get("frequency"))
        or parse_frequency(item.get("coupon_frequency"))
        or parse_frequency(raw_freq)
    )
    defaulted_freq = False
    if frequency is None or frequency <= 0 or frequency > 365:
        frequency = 2
        defaulted_freq = True

    result = {
        "status": "partial",
        "instrument_type": "bonds",
        "face_value": round_money(face),
        "coupon_rate": _rate(coupon_rate * 100) if coupon_rate is not None else None,
        "years_to_maturity": round(years, 4) if years is not None else None,
        "frequency": frequency,
        "coupon_frequency": frequency,
        "day_count_convention": day_count,
        "currency": currency,
    }
    if defaulted_freq:
        result["warning"] = "Coupon frequency not specified — defaulted to semi-annual (2)."

    name = _extract_instrument_name(item)
    if name:
        result["instrument_name"] = name

    _add_input_dates(result, val_d, mat_d, item)

    derivations: Dict[str, Any] = {}

    if val_d and mat_d:
        d = days_between(val_d, mat_d)
        derivations["days_to_maturity"] = _days_derivation(val_d, mat_d, d)
    if years_derived_from_dates and years is not None:
        derivations["years_to_maturity"] = _derivation(
            "days_to_maturity / 365",
            {"days_to_maturity": round((years * 365), 2)},
            round(years, 4),
            "years",
        )

    if face is not None and coupon_rate is not None:
        annual_coupon = face * coupon_rate
        coupon_payment = annual_coupon / frequency
        result["annual_coupon"] = round_money(annual_coupon)
        result["coupon_payment"] = round_money(coupon_payment)
        result["coupon_per_period"] = result["coupon_payment"]
        derivations["annual_coupon"] = _derivation(
            "face_value * coupon_rate",
            {"face_value": round_money(face),
             "coupon_rate": _rate(coupon_rate * 100)},
            round_money(annual_coupon),
            "currency",
        )
        derivations["coupon_payment"] = _derivation(
            "annual_coupon / frequency",
            {"annual_coupon": round_money(annual_coupon),
             "frequency": frequency},
            round_money(coupon_payment),
            "currency",
        )

    if face is None or coupon_rate is None or years is None or years <= 0:
        result["error"] = "Missing required inputs (face_value, coupon_rate, or years_to_maturity)"
        if derivations:
            result["derivations"] = derivations
        return _add_camel_aliases(result)

    ytm_input = (parse_percentage(item.get("yield"))
                 or parse_percentage(item.get("yield_to_maturity")))
    if ytm_input is not None:
        result["ytm_input"] = _rate(ytm_input * 100)

    if price is None or price <= 0:
        if ytm_input is not None:
            price = _price_from_ytm(face, coupon_rate, ytm_input, years, frequency)
            if price is not None:
                derivations["current_price"] = _derivation(
                    "PV(coupons) + PV(face_value) discounted at yield_to_maturity",
                    {"face_value": round_money(face),
                     "coupon_rate": _rate(coupon_rate * 100),
                     "yield_to_maturity": _rate(ytm_input * 100),
                     "years_to_maturity": round(years, 4),
                     "frequency": frequency},
                    round_money(price),
                    "currency",
                )

    if price is not None and price > 0:
        result["current_price"] = round_money(price)
        result["total_value"] = round_money(price)

        ytm_was_solved = False
        ytm = _solve_ytm(price, face, coupon_rate, years, frequency)
        if ytm is not None:
            ytm_was_solved = True
        elif ytm_input is not None:
            ytm = ytm_input
        ytm_pct = ytm * 100 if ytm is not None else None

        if ytm_was_solved:
            result["ytm_source"] = "solved_from_price"
            derivations["yield_to_maturity"] = _derivation(
                "Solve r where current_price == PV(coupons) + PV(face_value)",
                {"current_price": round_money(price),
                 "face_value": round_money(face),
                 "coupon_rate": _rate(coupon_rate * 100),
                 "years_to_maturity": round(years, 4),
                 "frequency": frequency},
                _rate(ytm_pct),
                "percent",
            )
        elif ytm_input is not None:
            result["ytm_source"] = "input"

        macaulay = modified = convexity = None
        if ytm is not None and ytm > -0.99:
            r = ytm / frequency
            if r > -1:
                n = max(1, int(round(years * frequency)))
                coupon_per = face * coupon_rate / frequency
                pv_total = weighted = cx = 0.0
                for t in range(1, n + 1):
                    disc = (1 + r) ** t
                    pv_c = coupon_per / disc
                    pv_total += pv_c
                    weighted += t * pv_c
                    cx += t * (t + 1) * pv_c / ((1 + r) ** 2)
                pv_f = face / (1 + r) ** n
                pv_total += pv_f
                weighted += n * pv_f
                cx += n * (n + 1) * pv_f / ((1 + r) ** 2)
                if pv_total > 0:
                    macaulay = (weighted / pv_total) / frequency
                    modified = macaulay / (1 + r)
                    convexity = cx / pv_total / (frequency ** 2)

        annual_coupon = face * coupon_rate
        current_yield = annual_coupon / price * 100 if price > 0 else None
        accrued, days_accrued = _bond_accrued(item, face, coupon_rate, frequency, day_count)
        dv01 = price * modified * 0.0001 if (modified is not None and price > 0) else None

        if current_yield is not None:
            derivations["current_yield"] = _derivation(
                "(annual_coupon / current_price) * 100",
                {"annual_coupon": round_money(annual_coupon),
                 "current_price": round_money(price)},
                _rate(current_yield),
                "percent",
            )
        if accrued is not None and days_accrued is not None:
            basis = 360.0 if "360" in day_count else 365.0
            days_in_period = basis / frequency
            derivations["accrued_interest"] = _derivation(
                "coupon_payment * (days_accrued / days_in_coupon_period)",
                {"coupon_payment": round_money(face * coupon_rate / frequency),
                 "days_accrued": int(days_accrued),
                 "days_in_coupon_period": round(days_in_period, 4),
                 "day_count_convention": day_count},
                round_money(accrued),
                "currency",
            )
        if modified is not None:
            derivations["modified_duration"] = _derivation(
                "macaulay_duration / (1 + ytm / frequency)",
                {"macaulay_duration": _rate(macaulay),
                 "yield_to_maturity": _rate(ytm_pct),
                 "frequency": frequency},
                _rate(modified),
                "years",
            )
        if dv01 is not None:
            derivations["dv01"] = _derivation(
                "current_price * modified_duration * 0.0001",
                {"current_price": round_money(price),
                 "modified_duration": _rate(modified)},
                _rate(dv01),
                "currency",
            )

        result.update({
            "yield_to_maturity": _rate(ytm_pct),
            "duration": _rate(macaulay),
            "macaulay_duration": _rate(macaulay),
            "modified_duration": _rate(modified),
            "convexity": _rate(convexity),
            "dv01": _rate(dv01),
            "current_yield": _rate(current_yield),
            "accrued_interest": round_money(accrued),
            "days_accrued": round_time(days_accrued) if days_accrued is not None else None,
            "price_per_100": round(price / face * 100, 2) if face > 0 else None,
            "bond_equivalent_yield": _rate(ytm_pct),
            "yield_curve_rate": _rate(benchmark_yield * 100) if benchmark_yield is not None else None,
            "status": "partial" if defaulted_freq else "success",
        })
    else:
        result["error"] = "Need price or yield_to_maturity to value the bond"

    if derivations:
        result["derivations"] = derivations

    return _add_camel_aliases(result)


def calculate_money_market(item: Dict[str, Any],
                           benchmark_yield: Optional[float] = None) -> Dict[str, Any]:
    item = normalize_row(item)
    principal = (safe_float(item.get("principal"))
                 or safe_float(item.get("face_value"))
                 or safe_float(item.get("amount")))
    rate = (parse_percentage(item.get("interest_rate"))
            or parse_percentage(item.get("rate")))
    currency = item.get("currency") or item.get("ccy") or item.get("currency_code")

    day_count = str(item.get("day_count_convention") or item.get("day_count") or "ACT/360").upper()
    divisor = 365.0 if "365" in day_count else 360.0

    val_d = parse_date(item.get("valuation_date"))
    mat_d = parse_date(item.get("maturity_date"))
    days = safe_float(item.get("term_days")) or safe_float(item.get("days_to_maturity"))
    if days is None and val_d and mat_d:
        days = (mat_d - val_d).days if mat_d >= val_d else None
    if days is None:
        iss_d = parse_date(item.get("issue_date"))
        if iss_d and mat_d and mat_d >= iss_d:
            days = (mat_d - iss_d).days

    market_value = safe_float(item.get("market_value"))

    bad = (principal is None or rate is None or days is None
           or (days is not None and days <= 0))
    result = {
        "status": "partial" if bad else "success",
        "instrument_type": "money-market",
        "principal": round_money(principal),
        "interest_rate": _rate(rate * 100) if rate is not None else None,
        "term_days": round_time(days) if days is not None and days > 0 else None,
        "day_count_convention": day_count,
        "currency": currency,
    }

    name = _extract_instrument_name(item)
    if name:
        result["instrument_name"] = name

    _add_input_dates(result, val_d, mat_d, item)

    derivations: Dict[str, Any] = {}
    days_deriv = _days_derivation(val_d, mat_d, days)
    if days_deriv:
        derivations["days_to_maturity"] = days_deriv

    if market_value is not None:
        result["market_value"] = round_money(market_value)

    if principal is not None and principal > 0 and rate is not None and days is not None and days > 0:
        interest = principal * rate * (days / divisor)
        total_value = principal + interest
        disc_yield = (interest / total_value) * (divisor / days) * 100.0 if total_value else None
        eff_yield = (interest / principal) * (365.0 / days) * 100.0
        be_yield = (interest / principal) * (365.0 / days) * 100.0

        derivations["interest_earned"] = _derivation(
            "principal * interest_rate * (days / divisor)",
            {"principal": round_money(principal),
             "interest_rate": _rate(rate * 100),
             "days": round_time(days),
             "divisor": divisor},
            round_money(interest),
            "currency",
        )
        derivations["total_value"] = _derivation(
            "principal + interest_earned",
            {"principal": round_money(principal),
             "interest_earned": round_money(interest)},
            round_money(total_value),
            "currency",
        )
        derivations["effective_annual_rate"] = _derivation(
            "(interest_earned / principal) * (365 / days) * 100",
            {"interest_earned": round_money(interest),
             "principal": round_money(principal),
             "days": round_time(days)},
            _rate(eff_yield),
            "percent",
        )

        result.update({
            "interest_earned": round_money(interest),
            "total_value": round_money(total_value),
            "maturity_value": round_money(total_value),
            "total_interest": round_money(interest),
            "discount_yield": _rate(disc_yield),
            "effective_yield": _rate(eff_yield),
            "effective_annual_rate": _rate(eff_yield),
            "bond_equivalent_yield": _rate(be_yield),
            "yield_curve_rate": _rate(benchmark_yield * 100) if benchmark_yield is not None else None,
            "status": "success",
        })

    if derivations:
        result["derivations"] = derivations

    return _add_camel_aliases(result)


def calc_single(row: Dict[str, Any], instrument_type: str,
                valuation_date: Optional[str] = None,
                benchmark_yield: Optional[float] = None) -> Dict[str, Any]:
    if valuation_date:
        row = {**row, "valuation_date": valuation_date}

    validation = validate_row(row, instrument_type)
    norm = validation["normalized_row"]

    if instrument_type == "bonds":
        calc = calculate_bond(norm, benchmark_yield)
    elif instrument_type == "money-market":
        calc = calculate_money_market(norm, benchmark_yield)
    else:
        calc = calculate_treasury_bill(norm, benchmark_yield)

    name = (_extract_instrument_name(norm)
            or row.get("Instrument Name")
            or row.get("instrument_name")
            or "instrument-1")

    calc_status = calc.get("status", "error")
    status_out = "success" if calc_status == "success" else (
        "partial" if calc_status == "partial" else "error"
    )

    return {
        "status": status_out,
        "instrumentId": name,
        "instrumentType": instrument_type,
        "inputs": norm,
        "calculation": calc,
        "valuation": {
            "total_value": calc.get("total_value"),
            "principal": calc.get("principal"),
            "face_value": calc.get("face_value"),
            "interest_earned": calc.get("interest_earned"),
            "effective_yield": calc.get("effective_yield"),
            "yield_to_maturity": calc.get("yield_to_maturity"),
        },
        "sourceData": row,
        "missing_fields": validation["missing_fields"],
        "invalid_fields": validation["invalid_fields"],
        "errors": [] if status_out != "error" else [
            {"field": "calculation", "code": "failed",
             "message": calc.get("error", "Unknown error")}
        ],
    }


def _pick_name_column(first_row: Dict[str, Any]) -> Optional[str]:
    if not first_row:
        return None
    preferred = ["instrument name", "instrument", "security", "name",
                 "issuer", "description", "bond name", "tbill name"]
    keys_lower = {str(k).lower(): k for k in first_row.keys()}
    for p in preferred:
        for kl, k in keys_lower.items():
            if p == kl or p in kl:
                return k
    return next(iter(first_row.keys())) if first_row else None


def calculate_data(data: List[Dict],
                   instrument_type: str = "tbills",
                   valuation_date: Optional[str] = None,
                   benchmark_yield: Optional[float] = None) -> Dict[str, Any]:
    if not isinstance(data, list) or len(data) == 0:
        return {"status": "cannot_calculate", "mode": "unknown",
                "instrument_type": instrument_type, "instrument_count": 0,
                "instrument_results": [], "aggregates": {},
                "error": "No data provided"}

    instrument_results = []
    successful = []
    failed = []

    for row in data:
        if valuation_date:
            row = {**row, "valuation_date": valuation_date}
        row = normalize_row(row)

        name = _extract_instrument_name(row)

        if instrument_type == "bonds":
            calc = calculate_bond(row, benchmark_yield)
        elif instrument_type == "money-market":
            calc = calculate_money_market(row, benchmark_yield)
        else:
            calc = calculate_treasury_bill(row, benchmark_yield)

        if name:
            calc["instrument_name"] = name

        instrument_results.append(calc)

        if calc.get("status") == "success":
            successful.append(calc)
        elif calc.get("status") == "partial":
            has_data = (
                (calc.get("face_value") or 0) > 0
                or (calc.get("principal") or 0) > 0
                or (calc.get("current_price") or 0) > 0
                or (calc.get("total_value") or 0) > 0
            )
            (successful if has_data else failed).append(calc)
        else:
            failed.append(calc)

    unique_names = set()
    unnamed = 0
    for r in successful:
        nm = r.get("instrument_name")
        if nm and str(nm).strip():
            unique_names.add(str(nm).strip())
        else:
            unnamed += 1
    unique_instrument_count = len(unique_names) + unnamed

    aggregates: Dict[str, Any] = {
        "instrument_count": unique_instrument_count,
        "successful_rows": len(successful),
        "failed_count": len(failed),
        "total_rows": len(data),
        "unique_names": list(unique_names),
    }

    if successful:
        def _sum(field):
            return sum(r[field] for r in successful if r.get(field) is not None)

        def _mean(field):
            vals = [r[field] for r in successful if r.get(field) is not None]
            return sum(vals) / len(vals) if vals else None

        if instrument_type == "money-market":
            aggregates["total_principal"] = round_money(_sum("principal"))
            aggregates["total_interest"] = round_money(_sum("interest_earned"))
            aggregates["total_value"] = round_money(_sum("total_value"))
            principals = [r["principal"] for r in successful if r.get("principal") is not None]
            rates = [r["interest_rate"] for r in successful if r.get("interest_rate") is not None]
            if principals and sum(principals) > 0 and len(principals) == len(rates):
                aggregates["weighted_avg_rate"] = round(
                    sum(p * r for p, r in zip(principals, rates)) / sum(principals), 4)
            m = _mean("term_days")
            aggregates["avg_days_to_maturity"] = round(m, 2) if m is not None else None
            m = _mean("effective_yield")
            aggregates["effective_annual_rate"] = round(m, 4) if m is not None else None

        elif instrument_type == "tbills":
            aggregates["total_face_value"] = round_money(_sum("face_value"))
            aggregates["total_purchase_price"] = round_money(_sum("purchase_price"))
            aggregates["total_discount"] = round_money(_sum("discount_amount"))
            aggregates["total_value"] = round_money(_sum("face_value"))
            m = _mean("money_market_yield")
            aggregates["avg_discount_rate"] = round(m, 4) if m is not None else None
            m = _mean("term_days")
            aggregates["avg_days_to_maturity"] = round(m, 2) if m is not None else None
            faces = [r["face_value"] for r in successful if r.get("face_value") is not None]
            mm_ys = [r["money_market_yield"] for r in successful if r.get("money_market_yield") is not None]
            if faces and sum(faces) > 0 and len(faces) == len(mm_ys):
                aggregates["weighted_avg_discount"] = round(
                    sum(f * d for f, d in zip(faces, mm_ys)) / sum(faces), 4)
            m = _mean("purchase_price")
            aggregates["avg_investment"] = round(m, 2) if m is not None else None
            m = _mean("bond_equivalent_yield")
            aggregates["annualized_yield"] = round(m, 4) if m is not None else None

        elif instrument_type == "bonds":
            aggregates["total_face_value"] = round_money(_sum("face_value"))
            aggregates["total_market_value"] = round_money(_sum("current_price"))
            aggregates["total_coupon_income"] = round_money(_sum("annual_coupon"))
            aggregates["total_value"] = round_money(_sum("current_price"))
            m = _mean("yield_to_maturity")
            aggregates["avg_ytm"] = round(m, 4) if m is not None else None
            m = _mean("duration")
            aggregates["avg_duration"] = round(m, 4) if m is not None else None
            m = _mean("coupon_rate")
            aggregates["weighted_avg_coupon"] = round(m, 4) if m is not None else None

    camel_map = {
        "instrumentCount": "instrument_count",
        "totalValue": "total_value",
        "totalMarketValue": "total_market_value",
        "totalFaceValue": "total_face_value",
        "totalPrincipal": "total_principal",
        "totalInterest": "total_interest",
        "totalCouponIncome": "total_coupon_income",
        "totalAnnualIncome": "total_coupon_income",
        "weightedAvgRate": "weighted_avg_rate",
        "weightedAvgCoupon": "weighted_avg_coupon",
        "weightedAvgDiscount": "weighted_avg_discount",
        "avgYTM": "avg_ytm",
        "avgDiscountRate": "avg_discount_rate",
        "avgDaysToMaturity": "avg_days_to_maturity",
        "avgDuration": "avg_duration",
        "avgInvestment": "avg_investment",
        "annualizedYield": "annualized_yield",
        "duration": "avg_duration",
        "failedCount": "failed_count",
    }
    for camel, snake in camel_map.items():
        if snake in aggregates and camel not in aggregates:
            aggregates[camel] = aggregates[snake]

    if "avgRate" not in aggregates:
        if instrument_type == "bonds" and "weighted_avg_coupon" in aggregates:
            aggregates["avgRate"] = aggregates["weighted_avg_coupon"]
        elif "weighted_avg_rate" in aggregates:
            aggregates["avgRate"] = aggregates["weighted_avg_rate"]

    mode = "single" if unique_instrument_count == 1 else "multiple"

    return {
        "status": "success" if successful else "cannot_calculate",
        "mode": mode,
        "instrument_type": instrument_type,
        "instrument_count": unique_instrument_count,
        "successful_rows": len(successful),
        "instrument_results": instrument_results,
        "aggregates": aggregates,
        "calculations": instrument_results,
    }
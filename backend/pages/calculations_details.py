"""
Financial calculations for Money Market, Treasury Bills and Bonds.

RULES:
- The uploaded workbook is the ONLY source of truth.
- NO mock data, hardcoded values, or zero fallbacks.
- ExcelJS formula cells ({v, w, f}) are unwrapped before parsing.
- Missing inputs produce structured errors, never silent zeros.

Counts:
- instrument_count counts UNIQUE instrument names, not rows.
- Rows without an instrument name are counted individually.
"""

import math
import re
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional


# =============================================================================
# CELL UNWRAPPING
# =============================================================================

def _unwrap_cell(value):
    """Unwrap ExcelJS cell objects {v, w, f} and rich-text blocks to primitives."""
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


# =============================================================================
# SAFE CONVERSION HELPERS
# =============================================================================

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
    """Parse coupon frequency from text or numeric value to integer (1=annual, 2=semi-annual, 4=quarterly, 12=monthly)."""
    value = _unwrap_cell(value)
    if value is None or value == "":
        return None
    
    # If already numeric, return as int
    if isinstance(value, (int, float)):
        return int(value)
    
    if isinstance(value, str):
        v = value.strip().lower()
        
        # Map text values to numeric frequencies
        frequency_map = {
            # Annual
            'annual': 1,
            'annually': 1,
            'yearly': 1,
            '1': 1,
            'once per year': 1,
            
            # Semi-annual
            'semi-annual': 2,
            'semi-annually': 2,
            'semiannual': 2,
            'semi annul': 2,
            'semi annually': 2,
            'semiannually': 2,
            'bi-annual': 2,
            'biannual': 2,
            'bi annual': 2,
            'half-yearly': 2,
            'half yearly': 2,
            '2': 2,
            'twice per year': 2,
            
            # Quarterly
            'quarterly': 4,
            'quarter': 4,
            '4': 4,
            'four times per year': 4,
            
            # Monthly
            'monthly': 12,
            'month': 12,
            '12': 12,
            'twelve times per year': 12,
        }
        
        # Try direct match
        if v in frequency_map:
            return frequency_map[v]
        
        # Try to extract number if present
        import re
        num_match = re.search(r'\d+', v)
        if num_match:
            num = int(num_match.group())
            if num in [1, 2, 4, 12]:
                return num
    
    return None


_DATE_FORMATS = (
    "%Y-%m-%d",
    "%m/%d/%Y", "%m/%d/%y",
    "%d/%m/%Y", "%d/%m/%y",
    "%Y/%m/%d",
    "%d-%m-%Y", "%m-%d-%Y",
    "%d-%m-%y", "%m-%d-%y",
    "%d.%m.%Y", "%d %b %Y", "%d-%b-%Y",
    "%d-%b-%y", "%d %b %y",
    "%Y-%m-%dT%H:%M:%S",
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
                base = datetime(1899, 12, 30)
                return (base + timedelta(days=int(n))).date()
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
    return round(val, 2)


def round_time(value: Any) -> Optional[int]:
    val = safe_float(value)
    if val is None:
        return None
    return int(round(val))


def days_between(d1: date, d2: date) -> int:
    return abs((d2 - d1).days)


# =============================================================================
# SEMANTIC NORMALISATION
# =============================================================================

SPECIFIC_ALIASES: Dict[str, List[str]] = {
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
    "issue_date": [
        "issue date", "issuedate", "issue_date",
        "start date", "startdate", "start_date",
        "effective date", "effectivedate", "effective_date",
        "settlement date", "settlementdate", "settlement_date",
        "origination date", "value date", "valuedate", "value_date",
        "trade date", "tradedate", "trade_date",
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
    # ─── Extended name aliases ────────────────────────────────────────────────
    # Previously the engine only recognised 'instrument name' and a handful of
    # similar tokens. Adding 'name', 'bond name', 'tbill name' etc. fixes the
    # case where the workbook's identifier column is labelled simply "Name"
    # or "Bond Name", which caused the instrument_count to fall back to the
    # row count.
    "instrument_name": [
        "parent company name", "parent company",
        "issuer", "company", "entity",
        "short name", "shortname",
        "instrument name", "instrumentname", "instrument_name",
        "instrument", "description", "counterparty",
        "bond name", "bondname", "bond_name", "bond",
        "t-bill name", "tbill name", "tbillname", "tbill_name",
        "tbill", "t-bill", "treasury bill name",
        "security name", "securityname",
        "name", "ticker", "symbol",
    ],
    "classification": ["classification", "category", "asset class", "type"],
    "currency": ["currency", "ccy", "iso code", "currency code"],
    "country": ["country", "jurisdiction", "domicile"],
    "sector": ["sector", "industry", "industry group"],
    "rating": ["credit rating", "rating", "moody", "s&p", "fitch"],
    "face_value": [
        "face value", "facevalue", "face_value",
        "par value", "parvalue", "par_value",
        "redemption value", "redemptionvalue", "redemption_value",
        "maturity value", "maturityvalue", "maturity_value",
        "nominal value", "nominalvalue", "nominal_value",
    ],
    "discount_rate": [
        "discount rate", "discountrate", "discount_rate",
        "bank discount", "bankdiscount",
        "discount yield", "discountyield",
        "t-bill rate", "tbillrate",
        "auction rate", "auctionrate",
        "discount",
    ],
    "term_days": [
        "term days", "termdays", "term_days",
        "days to maturity", "daystomaturity",
        "maturity days", "maturitydays",
        "tenor", "term", "days",
    ],
    "auction_date": ["auction date", "auctiondate", "issue date", "settlement date"],
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
    """Map uploaded columns to canonical field names. Unwrap formula cells.
    Idempotent — safe to call more than once."""
    if not isinstance(row, dict):
        return {}
    normalized: Dict[str, Any] = {}
    consumed: set = set()

    # Pass 1: exact case-insensitive match
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

    # Pass 2: token-subset match
    for target, aliases in SPECIFIC_ALIASES.items():
        if target in normalized:
            continue
        for alias in aliases:
            alias_tokens = _tokenize(alias)
            if not alias_tokens:
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

    # Preserve unmatched, unwrapped
    for key, value in row.items():
        if key not in consumed and key not in normalized:
            unwrapped = _unwrap_cell(value)
            if unwrapped is not None:
                normalized[key] = unwrapped

    return normalized


# =============================================================================
# INSTRUMENT NAME EXTRACTION  (NEW — fixes instrument_count = rows bug)
# =============================================================================

def _extract_instrument_name(row: Dict[str, Any]) -> Optional[str]:
    """
    Pull the instrument name out of a NORMALIZED row.
    Falls back to common alternative keys so it works regardless of which
    column the user mapped as the identifier.
    """
    candidates = [
        "instrument_name",
        "BondName", "TBillName",
        "Instrument Name", "Instrument", "Security", "Name",
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


# =============================================================================
# VALIDATION
# =============================================================================

def validate_row(row: Dict[str, Any], instrument_type: str) -> Dict[str, Any]:
    if not isinstance(row, dict):
        return {"can_calculate": False,
                "missing_fields": ["row is not a dictionary"],
                "invalid_fields": [], "detected_fields": {},
                "normalized_row": {}, "all_source_keys": []}

    # Check for Coupon Frequency BEFORE normalization
    raw_coupon_frequency = row.get('Coupon Frequency') or row.get('coupon_frequency') or row.get('frequency') or row.get('instrument_type')
    
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
            if val_d and mat_d:
                years = days_between(val_d, mat_d) / 365.0
            else:
                d2m = safe_float(norm.get("days_to_maturity"))
                if d2m is not None:
                    years = d2m / 365.0
        if years is None or years <= 0:
            missing.append("years_to_maturity (or Valuation Date + Maturity Date)")

        freq = parse_frequency(norm.get("coupon_frequency")) or parse_frequency(norm.get("frequency")) or parse_frequency(norm.get("Coupon Frequency")) or parse_frequency(raw_coupon_frequency)
        note("coupon_frequency"); note("frequency"); note("Coupon Frequency")
        if freq is None or freq <= 0:
            missing.append("coupon_frequency (Annual=1, Semi-annual=2, Quarterly=4, Monthly=12)")

        if face is not None and face <= 0:
            invalid.append(("face_value", "must be > 0"))
        
        # Validate date consistency
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
            if val_d and mat_d:
                days = days_between(val_d, mat_d)
        if days is None:
            iss_d = parse_date(norm.get("issue_date"))
            mat_d = parse_date(norm.get("maturity_date"))
            if iss_d and mat_d:
                days = days_between(iss_d, mat_d)
        if days is None or days <= 0:
            missing.append("term_days (or Valuation Date + Maturity Date)")
        
        # Validate date consistency
        val_d = parse_date(norm.get("valuation_date"))
        mat_d = parse_date(norm.get("maturity_date"))
        iss_d = parse_date(norm.get("issue_date"))
        if val_d and mat_d and val_d > mat_d:
            invalid.append(("valuation_date", "must be on or before maturity_date"))
        if iss_d and mat_d and iss_d > mat_d:
            invalid.append(("issue_date", "must be on or before maturity_date"))

    else:  # tbills
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
            if val_d and mat_d:
                days = days_between(val_d, mat_d)
        if days is None:
            iss_d = parse_date(norm.get("issue_date"))
            mat_d = parse_date(norm.get("maturity_date"))
            if iss_d and mat_d:
                days = days_between(iss_d, mat_d)
        if days is None or days <= 0:
            missing.append("term_days (or Valuation Date + Maturity Date)")

        price = (safe_float(norm.get("purchase_price"))
                 or safe_float(norm.get("price"))
                 or safe_float(norm.get("current_price")))
        disc = parse_percentage(norm.get("discount_rate"))
        note("purchase_price"); note("price"); note("current_price"); note("discount_rate")
        if price is None and disc is None:
            missing.append("purchase_price or discount_rate")
        
        # Validate price consistency with face value
        if price is not None and face is not None and price > face:
            invalid.append(("purchase_price", "cannot exceed face value for discount instruments"))
        
        # Validate discount rate
        if disc is not None and disc < 0:
            invalid.append(("discount_rate", "must be >= 0"))
        
        # Validate date consistency
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


# =============================================================================
# YIELD SOLVER
# =============================================================================

def _solve_ytm(price: float, face: float, coupon_rate: float,
               years: float, frequency: int) -> Optional[float]:
    if price is None or face is None or coupon_rate is None:
        return None
    if price <= 0 or face <= 0 or years <= 0 or frequency <= 0:
        return None
    coupon = face * coupon_rate / frequency
    n = int(round(years * frequency))
    if n <= 0:
        return None
    annual_coupon = face * coupon_rate
    ytm = annual_coupon / price if price > 0 else 0.05
    for _ in range(200):
        r = ytm / frequency
        if r <= -1: r = 1e-6
        pv = 0.0
        dpv = 0.0
        for t in range(1, n + 1):
            disc = (1 + r) ** t
            pv += coupon / disc
            dpv += -t * coupon / (disc * (1 + r))
        disc_n = (1 + r) ** n
        pv += face / disc_n
        dpv += -n * face / (disc_n * (1 + r))
        diff = pv - price
        if abs(diff) < 1e-8: break
        if abs(dpv) < 1e-14: break
        ytm_new = ytm - (diff * frequency) / dpv
        if abs(ytm_new - ytm) < 1e-10:
            ytm = ytm_new
            break
        ytm = ytm_new
        if ytm < -0.99: ytm = 1e-6
    if ytm is None or math.isnan(ytm) or math.isinf(ytm):
        return None
    return ytm


def _price_from_ytm(face: float, coupon_rate: float, ytm: float,
                    years: float, frequency: int) -> Optional[float]:
    """
    Price a bond from its YTM using the standard discounted cash flow formula.
    Used when the uploaded workbook provides a YTM but no price column.
    """
    if (face is None or coupon_rate is None or ytm is None
            or years is None or frequency is None):
        return None
    if face <= 0 or years <= 0 or frequency <= 0:
        return None
    r = ytm / frequency
    if r <= -1:
        return None
    n = max(1, int(round(years * frequency)))
    coupon_per = face * coupon_rate / frequency
    try:
        pv = 0.0
        for t in range(1, n + 1):
            pv += coupon_per / ((1 + r) ** t)
        pv += face / ((1 + r) ** n)
        return pv
    except (ZeroDivisionError, OverflowError):
        return None


# =============================================================================
# TREASURY BILLS
# =============================================================================

def calculate_treasury_bill(item: Dict[str, Any], benchmark_yield: Optional[float] = None) -> Dict[str, Any]:
    item = normalize_row(item)
    face = safe_float(item.get("face_value")) or safe_float(item.get("principal"))
    purchase_price = (safe_float(item.get("purchase_price"))
                      or safe_float(item.get("current_price"))
                      or safe_float(item.get("price")))
    discount_rate = parse_percentage(item.get("discount_rate"))
    
    # Preserve currency from input
    currency = item.get("currency") or item.get("ccy") or item.get("currency_code")

    # Determine day count convention (default to ACT/360 for T-Bills)
    day_count = item.get("day_count_convention") or item.get("day_count") or "ACT/360"
    day_count_str = str(day_count).upper() if day_count else "ACT/360"
    
    # T-Bills typically use 360-day basis for discount calculations
    # But bond equivalent yield uses 365-day basis
    if "360" in day_count_str:
        discount_basis = 360.0
    elif "365" in day_count_str:
        discount_basis = 365.0
    else:
        discount_basis = 360.0  # Default to ACT/360 for T-Bills

    # Calculate days to maturity from valuation date if not provided
    days = safe_float(item.get("term_days")) or safe_float(item.get("days_to_maturity"))
    if days is None:
        val_d = parse_date(item.get("valuation_date"))
        mat_d = parse_date(item.get("maturity_date"))
        if val_d and mat_d:
            days = days_between(val_d, mat_d)
    if days is None:
        iss_d = parse_date(item.get("issue_date"))
        mat_d = parse_date(item.get("maturity_date"))
        if iss_d and mat_d:
            days = days_between(iss_d, mat_d)

    # Calculate partial results - don't fail completely if some fields are missing
    result = {
        "status": "partial" if (face is None or days is None) else "success",
        "instrument_type": "tbills",
        "face_value": round_money(face),
        "term_days": round_time(days) if days is not None and days > 0 else None,
        "discount_rate": round(discount_rate * 100.0, 4) if discount_rate is not None else None,
        "day_count_convention": day_count_str,
        "currency": currency,
    }

    # Calculate purchase price from discount rate using standard T-Bill formula
    # Price = Face * (1 - discount_rate * days / 360)
    if face is not None and days is not None and days > 0 and discount_rate is not None:
        if purchase_price is None:
            purchase_price = face * (1.0 - discount_rate * days / discount_basis)
        result["purchase_price"] = round_money(purchase_price) if purchase_price is not None and purchase_price > 0 else None

    # Carrying Value from cleaned data (book value, not calculated PV)
    carrying_value = safe_float(item.get("carrying_value")) or safe_float(item.get("book_value"))
    if carrying_value is not None:
        result["carrying_value"] = round_money(carrying_value)
    elif isinstance(item.get("carrying_value"), str):
        result["carrying_value"] = item.get("carrying_value")

    # Calculate yields if face, purchase_price, and days are available
    if face is not None and purchase_price is not None and purchase_price > 0 and days is not None and days > 0:
        discount_amount = face - purchase_price
        
        # Discount yield (bank discount rate) - uses discount basis (typically 360)
        discount_yield = (discount_amount / face) * (discount_basis / days) * 100.0
        
        # Money market yield (also called CD equivalent yield) - uses discount basis
        money_market_yield = (discount_amount / purchase_price) * (discount_basis / days) * 100.0
        
        # Bond equivalent yield (investment yield) - uses 365-day basis
        bond_equivalent_yield = (discount_amount / purchase_price) * (365.0 / days) * 100.0
        
        # Holding period yield
        holding_period_yield = (discount_amount / purchase_price) * 100.0
        
        # Effective annual yield (compounded)
        effective_annual_yield = ((face / purchase_price) ** (365.0 / days) - 1.0) * 100.0

        result["discount_amount"] = round_money(discount_amount)
        result["discount_yield"] = round(discount_yield, 4)
        result["money_market_yield"] = round(money_market_yield, 4)
        result["bond_equivalent_yield"] = round(bond_equivalent_yield, 4)
        result["holding_period_yield"] = round(holding_period_yield, 4)
        result["effective_annual_yield"] = round(effective_annual_yield, 4)
        result["yield_curve_rate"] = round(benchmark_yield * 100.0, 4) if benchmark_yield is not None else None
        result["total_value"] = round_money(face)  # T-Bill value at maturity
        result["status"] = "success"

    # Add camelCase aliases for frontend compatibility
    result["faceValue"] = result["face_value"]
    result["purchasePrice"] = result.get("purchase_price")
    result["termDays"] = result["term_days"]
    result["discountAmount"] = result.get("discount_amount")
    result["discountYield"] = result.get("discount_yield")
    result["moneyMarketYield"] = result.get("money_market_yield")
    result["bondEquivalentYield"] = result.get("bond_equivalent_yield")
    result["holdingPeriodYield"] = result.get("holding_period_yield")
    result["effectiveAnnualYield"] = result.get("effective_annual_yield")
    result["yieldCurveRate"] = result.get("yield_curve_rate")
    result["totalValue"] = result.get("total_value")
    result["carryingValue"] = result.get("carrying_value")

    return result


# =============================================================================
# BONDS
# =============================================================================

def calculate_bond(item: Dict[str, Any], benchmark_yield: Optional[float] = None) -> Dict[str, Any]:
    # Check for Coupon Frequency BEFORE normalization to catch the space-separated name
    raw_coupon_frequency = item.get('Coupon Frequency') or item.get('coupon_frequency') or item.get('frequency') or item.get('instrument_type')
    
    item = normalize_row(item)
    face = safe_float(item.get("face_value")) or safe_float(item.get("principal"))
    coupon_rate = (parse_percentage(item.get("coupon_rate"))
                   or parse_percentage(item.get("interest_rate")))
    
    # Preserve currency from input
    currency = item.get("currency") or item.get("ccy") or item.get("currency_code")
    
    # Handle price - check if it's a percentage and convert to monetary value
    price_input = item.get("price") or item.get("purchase_price") or item.get("current_price")
    price = None
    if price_input is not None:
        price_str = str(price_input).strip()
        if price_str.endswith('%'):
            # It's a percentage - convert to monetary value using face value
            price_pct = parse_percentage(price_input)
            if price_pct is not None and face is not None:
                price = face * price_pct
        else:
            # It's already a monetary value
            price = safe_float(price_input)
    
    # Determine day count convention for accrued interest
    day_count = item.get("day_count_convention") or item.get("day_count") or "ACT/365"
    day_count_str = str(day_count).upper() if day_count else "ACT/365"
    
    years = safe_float(item.get('years_to_maturity'))
    frequency = parse_frequency(item.get('frequency')) or parse_frequency(item.get('coupon_frequency')) or parse_frequency(item.get('instrument_type')) or parse_frequency(item.get('Coupon Frequency')) or parse_frequency(raw_coupon_frequency)
    
    # Validate frequency - if it's an unreasonable value, set to null and add error
    if frequency is not None and (frequency <= 0 or frequency > 365):
        frequency = None

    # Calculate years to maturity from valuation date if not provided
    if years is None:
        val_d = parse_date(item.get("valuation_date"))
        mat_d = parse_date(item.get("maturity_date"))
        if val_d and mat_d:
            years = days_between(val_d, mat_d) / 365.0
    if years is None:
        d2m = safe_float(item.get("days_to_maturity"))
        if d2m is not None and d2m > 0:
            years = d2m / 365.0

    # Calculate partial results - don't fail completely if some fields are missing
    result = {
        "status": "partial" if (face is None or coupon_rate is None or years is None or frequency is None or price is None) else "success",
        "instrument_type": "bonds",
        "face_value": round_money(face),
        "coupon_rate": round(coupon_rate * 100.0, 4) if coupon_rate is not None else None,
        "years_to_maturity": round(years, 4) if years is not None else None,
        "frequency": int(frequency) if frequency is not None and frequency > 0 else None,
        "day_count_convention": day_count_str,
        "currency": currency,
    }

    # Add error message if frequency is invalid
    if frequency is None:
        result["error"] = "Invalid or missing coupon frequency. Full calculations require valid frequency (1=annual, 2=semi-annual, 4=quarterly, 12=monthly)."
        result["missing_field"] = "coupon_frequency"

    # Calculate annual coupon if face and coupon_rate are available
    if face is not None and coupon_rate is not None:
        result["annual_coupon"] = round_money(face * coupon_rate)

    # Calculate Discount Rate from components if available
    discount_rate = None
    # Use FRED benchmark or explicitly provided risk-free rate
    risk_free_rate = None
    if benchmark_yield is not None and benchmark_yield > 0:
        risk_free_rate = benchmark_yield / 100.0  # Convert from percentage to decimal
    else:
        risk_free_rate = parse_percentage(item.get("risk_free_rate"))
    
    country_risk_premium = parse_percentage(item.get("country_risk_premium"))
    credit_spread = parse_percentage(item.get("credit_spread")) or parse_percentage(item.get("spread"))
    
    if risk_free_rate is not None:
        discount_rate = risk_free_rate
        if country_risk_premium is not None:
            discount_rate += country_risk_premium
        if credit_spread is not None:
            discount_rate += credit_spread
        result["discount_rate"] = round(discount_rate * 100.0, 4) if discount_rate is not None else None

    # Calculate YTM and price if enough data is available
    if face is not None and coupon_rate is not None and years is not None and years > 0 and frequency is not None and frequency > 0:
        frequency = int(frequency)
        
        # Validate yield input - if it's > 1 (100%), it's likely a monetary value, not a percentage
        ytm_input = (parse_percentage(item.get("yield"))
                     or parse_percentage(item.get("yield_to_maturity")))
        if ytm_input is not None and ytm_input > 1.0:
            # Yield > 100% is likely a monetary value, reject it
            ytm_input = None
            result["error"] = "Invalid yield value (appears to be monetary, not percentage). Full calculations require valid yield or price."
            result["missing_field"] = "yield_to_maturity"

        if price is None or price <= 0:
            if ytm_input is not None:
                price = _price_from_ytm(face, coupon_rate, ytm_input, years, frequency)

        if price is not None and price > 0:
            result["current_price"] = round_money(price)
            result["total_value"] = round_money(price)
            
            annual_coupon = coupon_rate * face
            coupon_per_period = annual_coupon / frequency
            periods = max(1, int(round(years * frequency)))

            # Calculate Present Value using discount rate if available
            present_value = None
            if discount_rate is not None and discount_rate > 0:
                r = discount_rate / frequency
                pv_total = 0.0
                for t in range(1, periods + 1):
                    disc = (1 + r) ** t
                    pv_total += coupon_per_period / disc
                disc_n = (1 + r) ** periods
                pv_total += face / disc_n
                present_value = pv_total
                result["present_value"] = round_money(present_value)
                
                # Calculate Fair Value = Present Value - Price
                if present_value is not None:
                    fair_value = present_value - price
                    result["fair_value"] = round_money(fair_value)

            # Calculate Carrying Value from cleaned data or accounting method
            carrying_value = safe_float(item.get("carrying_value")) or safe_float(item.get("book_value"))
            if carrying_value is not None:
                result["carrying_value"] = round_money(carrying_value)
            elif isinstance(item.get("carrying_value"), str):
                # Handle text values like "Reducing Balance"
                result["carrying_value"] = item.get("carrying_value")

            ytm = _solve_ytm(price, face, coupon_rate, years, frequency)
            if ytm is None and ytm_input is not None:
                ytm = ytm_input
            ytm_pct = ytm * 100.0 if ytm is not None else None

            macaulay = None
            modified = None
            if ytm is not None and ytm > -0.99:
                r = ytm / frequency
                if r > -1:
                    pv_total = 0.0
                    weighted = 0.0
                    for t in range(1, periods + 1):
                        disc = (1 + r) ** t
                        pv_c = coupon_per_period / disc
                        pv_total += pv_c
                        weighted += t * pv_c
                    disc_n = (1 + r) ** periods
                    pv_f = face / disc_n
                    pv_total += pv_f
                    weighted += periods * pv_f
                    if pv_total > 0:
                        macaulay = (weighted / pv_total) / frequency
                        modified = macaulay / (1 + r)

            current_yield = (annual_coupon / price) * 100.0 if price > 0 else None
            accrued = None
            days_accrued = None
            # Use last coupon date or issue date for accrued interest calculation
            last_coupon_d = parse_date(item.get("last_coupon_date")) or parse_date(item.get("issue_date"))
            val_d = parse_date(item.get("valuation_date")) or parse_date(item.get("settlement_date"))
            if last_coupon_d and val_d:
                days_accrued = days_between(last_coupon_d, val_d)
                # Determine days in period based on day count convention
                if "30" in day_count_str:
                    days_in_period = 360.0 / frequency
                elif "360" in day_count_str:
                    days_in_period = 360.0 / frequency
                elif "ACT" in day_count_str:
                    # ACT/ACT: actual days in the coupon period
                    # For simplicity, use 365/frequency as approximation
                    days_in_period = 365.0 / frequency
                else:
                    days_in_period = 365.0 / frequency  # Default to ACT/365
                accrued = coupon_per_period * (days_accrued / days_in_period)

            result["yield_to_maturity"] = round(ytm_pct, 4) if ytm_pct is not None else None
            result["duration"] = round(macaulay, 4) if macaulay is not None else None
            result["modified_duration"] = round(modified, 4) if modified is not None else None
            result["current_yield"] = round(current_yield, 4) if current_yield is not None else None
            result["accrued_interest"] = round_money(accrued)
            result["coupon_per_period"] = round_money(coupon_per_period) if coupon_per_period is not None else None
            result["days_accrued"] = round_time(days_accrued) if days_accrued is not None else None
            result["price_per_100"] = round((price / face) * 100.0, 2) if price is not None and face is not None and face > 0 else None
            result["bond_equivalent_yield"] = round(ytm_pct, 4) if ytm_pct is not None else None
            result["yield_curve_rate"] = round(benchmark_yield * 100.0, 4) if benchmark_yield is not None else None
            result["status"] = "success"

    # Add camelCase aliases for frontend compatibility
    result["faceValue"] = result["face_value"]
    result["currentPrice"] = result.get("current_price")
    result["couponRate"] = result["coupon_rate"]
    result["yearsToMaturity"] = result["years_to_maturity"]
    result["yieldToMaturity"] = result.get("yield_to_maturity")
    result["duration"] = result.get("duration")
    result["modifiedDuration"] = result.get("modified_duration")
    result["currentYield"] = result.get("current_yield")
    result["accruedInterest"] = result.get("accrued_interest")
    result["annualCoupon"] = result.get("annual_coupon")
    result["couponPerPeriod"] = result.get("coupon_per_period")
    result["daysAccrued"] = result.get("days_accrued")
    result["pricePer100"] = result.get("price_per_100")
    result["bondEquivalentYield"] = result.get("bond_equivalent_yield")
    result["yieldCurveRate"] = result.get("yield_curve_rate")
    result["presentValue"] = result.get("present_value")
    result["fairValue"] = result.get("fair_value")
    result["carryingValue"] = result.get("carrying_value")
    result["discountRate"] = result.get("discount_rate")

    return result


# =============================================================================
# MONEY MARKET
# =============================================================================

def calculate_money_market(item: Dict[str, Any], benchmark_yield: Optional[float] = None) -> Dict[str, Any]:
    item = normalize_row(item)
    principal = (safe_float(item.get("principal"))
                 or safe_float(item.get("face_value"))
                 or safe_float(item.get("amount")))
    rate = (parse_percentage(item.get("interest_rate"))
            or parse_percentage(item.get("rate")))
    
    # Preserve currency from input
    currency = item.get("currency") or item.get("ccy") or item.get("currency_code")

    # Determine day count convention (default to ACT/360 for money market)
    day_count = item.get("day_count_convention") or item.get("day_count") or "ACT/360"
    day_count_str = str(day_count).upper() if day_count else "ACT/360"
    
    # Determine day count divisor based on convention
    if "360" in day_count_str:
        day_count_divisor = 360.0
    elif "365" in day_count_str:
        day_count_divisor = 365.0
    else:
        day_count_divisor = 360.0  # Default to ACT/360 for money market

    # Calculate days to maturity from valuation date if not provided
    days = safe_float(item.get("term_days")) or safe_float(item.get("days_to_maturity"))
    if days is None:
        val_d = parse_date(item.get("valuation_date"))
        mat_d = parse_date(item.get("maturity_date"))
        if val_d and mat_d:
            days = days_between(val_d, mat_d)
    if days is None:
        iss_d = parse_date(item.get("issue_date"))
        mat_d = parse_date(item.get("maturity_date"))
        if iss_d and mat_d:
            days = days_between(iss_d, mat_d)

    market_value = safe_float(item.get("market_value"))

    # Calculate partial results - don't fail completely if some fields are missing
    result = {
        "status": "partial" if (principal is None or rate is None or days is None) else "success",
        "instrument_type": "money-market",
        "principal": round_money(principal),
        "interest_rate": round(rate * 100.0, 4) if rate is not None else None,
        "term_days": round_time(days) if days is not None and days > 0 else None,
        "day_count_convention": day_count_str,
        "currency": currency,
    }

    if market_value is not None:
        result["market_value"] = round_money(market_value)

    # Calculate interest and yields if principal, rate, and days are available
    if principal is not None and principal > 0 and rate is not None and days is not None and days > 0:
        # Simple interest calculation using the determined day count convention
        interest = principal * rate * (days / day_count_divisor)
        total_value = principal + interest
        
        # Money market yield (also called discount yield for some instruments)
        # Uses the same day count convention as the interest calculation
        discount_yield = (interest / total_value) * (day_count_divisor / days) * 100.0 if total_value else None
        
        # Effective annual yield (actual/actual for the year)
        effective_yield = (interest / principal) * (365.0 / days) * 100.0
        
        # Bond equivalent yield (365-day basis)
        bond_equivalent_yield = (interest / principal) * (365.0 / days) * 100.0

        result["interest_earned"] = round_money(interest)
        result["total_value"] = round_money(total_value)
        result["maturity_value"] = round_money(total_value)  # Alias for total_value
        result["total_interest"] = round_money(interest)  # Alias for interest_earned
        result["discount_yield"] = round(discount_yield, 4) if discount_yield is not None else None
        result["effective_yield"] = round(effective_yield, 4)
        result["effective_annual_rate"] = round(effective_yield, 4)  # Alias for effective_yield
        result["bond_equivalent_yield"] = round(bond_equivalent_yield, 4)
        result["yield_curve_rate"] = round(benchmark_yield * 100.0, 4) if benchmark_yield is not None else None
        result["status"] = "success"

    # Add camelCase aliases for frontend compatibility
    result["principal"] = result["principal"]
    result["interestRate"] = result["interest_rate"]
    result["termDays"] = result["term_days"]
    result["interestEarned"] = result.get("interest_earned")
    result["totalValue"] = result.get("total_value")
    result["maturityValue"] = result.get("maturity_value")
    result["totalInterest"] = result.get("total_interest")
    result["discountYield"] = result.get("discount_yield")
    result["effectiveYield"] = result.get("effective_yield")
    result["effectiveAnnualRate"] = result.get("effective_annual_rate")
    result["bondEquivalentYield"] = result.get("bond_equivalent_yield")
    result["yieldCurveRate"] = result.get("yield_curve_rate")
    if "market_value" in result:
        result["marketValue"] = result["market_value"]

    return result


# =============================================================================
# SINGLE INSTRUMENT DISPATCHER
# =============================================================================

def calc_single(row: Dict[str, Any], instrument_type: str,
                valuation_date: Optional[str] = None,
                benchmark_yield: Optional[float] = None) -> Dict[str, Any]:
    if valuation_date:
        row = {**row, "valuation_date": valuation_date}

    validation = validate_row(row, instrument_type)
    if not validation["can_calculate"]:
        return {
            "status": "error",
            "instrumentId": (row.get("Instrument Name") or row.get("instrument_name")
                             or "instrument-1"),
            "instrumentType": instrument_type,
            "inputs": validation["normalized_row"],
            "sourceData": row,
            "missing_fields": validation["missing_fields"],
            "invalid_fields": validation["invalid_fields"],
            "errors": [
                *[{"field": f, "code": "missing",
                   "message": f"Missing required field: {f}"}
                  for f in validation["missing_fields"]],
                *[{"field": iv["field"], "code": "invalid",
                   "message": f"{iv['field']}: {iv['reason']}"}
                  for iv in validation["invalid_fields"]],
            ],
        }

    norm = validation["normalized_row"]
    if instrument_type == "bonds":
        calc = calculate_bond(norm, benchmark_yield)
    elif instrument_type == "money-market":
        calc = calculate_money_market(norm, benchmark_yield)
    else:
        calc = calculate_treasury_bill(norm, benchmark_yield)

    name = _extract_instrument_name(norm) or (row.get("Instrument Name")
                                              or row.get("instrument_name")
                                              or "instrument-1")

    return {
        "status": "success" if calc.get("status") == "success" else "error",
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
        "missing_fields": [calc.get("missing_field")] if calc.get("missing_field") else [],
        "invalid_fields": [],
        "errors": [] if calc.get("status") == "success" else [
            {"field": "calculation", "code": "failed",
             "message": calc.get("error", "Unknown error")}
        ],
    }


# =============================================================================
# MAIN DISPATCHER
# =============================================================================

def _pick_name_column(first_row: Dict[str, Any]) -> Optional[str]:
    """Legacy helper — kept for backward compatibility. Prefer _extract_instrument_name."""
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

        # CRITICAL FIX: extract the instrument name from the NORMALIZED row,
        # not from the original column key. Previously the original column name
        # (e.g. "Instrument Name") was used to index into the normalized dict,
        # which had renamed that key to "instrument_name". The lookup always
        # returned None, so instrument_count fell back to the row count.
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
        # Include partial calculations in successful for aggregation if they have meaningful data
        if calc.get("status") == "success":
            successful.append(calc)
        elif calc.get("status") == "partial":
            # Include partial calculations if they have at least face_value or principal
            has_meaningful_data = (
                calc.get("face_value") is not None and calc.get("face_value") > 0
                or calc.get("principal") is not None and calc.get("principal") > 0
                or calc.get("current_price") is not None and calc.get("current_price") > 0
                or calc.get("total_value") is not None and calc.get("total_value") > 0
            )
            if has_meaningful_data:
                successful.append(calc)
            else:
                failed.append(calc)
        else:
            failed.append(calc)

    # -------------------------------------------------------------------------
    # AGGREGATES — instrument_count counts UNIQUE instruments, not rows.
    # -------------------------------------------------------------------------
    unique_names = set()
    unnamed_rows = 0
    for r in successful:
        nm = r.get("instrument_name")
        if nm and str(nm).strip():
            unique_names.add(str(nm).strip())
        else:
            unnamed_rows += 1

    unique_instrument_count = len(unique_names) + unnamed_rows

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
            # Effective annual rate is the same as effective yield
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
            # Calculate weighted average discount rate (by face value)
            face_values = [r["face_value"] for r in successful if r.get("face_value") is not None]
            discount_rates = [r["money_market_yield"] for r in successful if r.get("money_market_yield") is not None]
            if face_values and sum(face_values) > 0 and len(face_values) == len(discount_rates):
                aggregates["weighted_avg_discount"] = round(
                    sum(f * d for f, d in zip(face_values, discount_rates)) / sum(face_values), 4)
            # Calculate average investment (purchase price)
            m = _mean("purchase_price")
            aggregates["avg_investment"] = round(m, 2) if m is not None else None
            # Annualized yield is bond equivalent yield (365-day basis)
            m = _mean("bond_equivalent_yield")
            aggregates["annualized_yield"] = round(m, 4) if m is not None else None

        elif instrument_type == "bonds":
            aggregates["total_face_value"] = round_money(_sum("face_value"))
            aggregates["total_market_value"] = round_money(_sum("current_price"))
            # FIX: coupon income should come from annual_coupon, not accrued_interest.
            aggregates["total_coupon_income"] = round_money(_sum("annual_coupon"))
            # total_value is current_price (market value) - NO silent fallback to face_value
            # If current_price is missing, it will be None (not fabricated)
            aggregates["total_value"] = round_money(_sum("current_price"))
            m = _mean("yield_to_maturity")
            aggregates["avg_ytm"] = round(m, 4) if m is not None else None
            m = _mean("duration")
            aggregates["avg_duration"] = round(m, 4) if m is not None else None
            m = _mean("coupon_rate")
            aggregates["weighted_avg_coupon"] = round(m, 4) if m is not None else None

    # -------------------------------------------------------------------------
    # Camel-case aliases so the frontend's calculationFields can find them.
    # The frontend reads keys like 'weightedAvgCoupon', 'avgYTM',
    # 'totalAnnualIncome', 'duration', 'totalValue', 'instrumentCount', etc.
    # -------------------------------------------------------------------------
    camel_map = {
        "instrumentCount":    "instrument_count",
        "totalValue":         "total_value",
        "totalMarketValue":   "total_market_value",
        "totalFaceValue":     "total_face_value",
        "totalPrincipal":     "total_principal",
        "totalInterest":      "total_interest",
        "totalCouponIncome":  "total_coupon_income",
        "totalAnnualIncome":  "total_coupon_income",   # frontend label for bonds
        "weightedAvgRate":    "weighted_avg_rate",
        "weightedAvgCoupon":  "weighted_avg_coupon",
        "weightedAvgDiscount": "weighted_avg_discount",
        "avgYTM":             "avg_ytm",
        "avgDiscountRate":    "avg_discount_rate",
        "avgDaysToMaturity":  "avg_days_to_maturity",
        "avgDuration":        "avg_duration",
        "avgInvestment":      "avg_investment",
        "annualizedYield":    "annualized_yield",
        "duration":           "avg_duration",
        "failedCount":        "failed_count",
    }
    for camel, snake in camel_map.items():
        if snake in aggregates and camel not in aggregates:
            aggregates[camel] = aggregates[snake]
    
    # Special case: avgRate should map to weighted_avg_rate for money-market/tbills,
    # but to weighted_avg_coupon for bonds
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
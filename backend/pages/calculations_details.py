"""
Calculation engine for money-market, T-Bills and Bonds.

Architectural rules enforced here:

  1. Prerequisites are computed BEFORE their dependents (declarative chain).
  2. Every dependent step reads the *raw* (unrounded) prerequisite value.
  3. Only the final flat-field value is rounded, using consistent half-up
     rounding (financial standard). Days are rounded to whole numbers at
     the step boundary with ROUND_HALF_UP.
  4. Missing prerequisites SKIP the dependent step (they are not silently
     defaulted to None).
  5. Circular dependencies are detected at import time and surfaced as a
     warning (never silently accepted).
  6. Every step records: formula, dependencies, inputs, raw result,
     rounded result, unit and status. This is the full audit trail consumed
     by the frontend formula popup.

Public API is unchanged: validate_row, normalize_row, calc_single,
calculate_data, calculate_treasury_bill, calculate_bond,
calculate_money_market.
"""

import math
import re
import warnings
from dataclasses import dataclass, field as dc_field
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional, Callable


# ─────────────────────────────────────────────────────────────
# 1. Primitive parsers / formatters
# ─────────────────────────────────────────────────────────────
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


def _half_up(value: float, decimals: int) -> float:
    quantizer = Decimal(1).scaleb(-decimals)
    return float(Decimal(str(value)).quantize(quantizer, rounding=ROUND_HALF_UP))


def round_money(value: Any) -> Optional[float]:
    val = safe_float(value)
    if val is None:
        return None
    return _half_up(val, 2)


def round_time(value: Any) -> Optional[int]:
    """Whole-number day rounding using financial (half-up) rounding."""
    val = safe_float(value)
    if val is None:
        return None
    return int(Decimal(str(val)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _rate(value) -> Optional[float]:
    """Round a percentage (already in percent form, e.g. 5.0) to 4 dp."""
    if value is None:
        return None
    try:
        return float(Decimal(str(value)).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        ))
    except Exception:
        return None


def _benchmark_to_percent(benchmark_yield):
    """
    Normalise a benchmark rate to percent form (e.g. 4.41), regardless of
    whether the caller supplied a decimal fraction (0.0441) or an
    already-percent value (4.41). Prevents the 'Benchmark Rate: 441 %' bug
    caused by multiplying an already-percent input by 100.
    """
    if benchmark_yield is None:
        return None
    try:
        v = float(benchmark_yield)
    except (TypeError, ValueError):
        return None
    if v < 1.0:                       # fraction → percent
        return _rate(v * 100.0)
    return _rate(v)                   # already percent


def days_between(d1: date, d2: date) -> int:
    return abs((d2 - d1).days)


# ─────────────────────────────────────────────────────────────
# 2. Derivation record builders (legacy helpers kept for callers)
# ─────────────────────────────────────────────────────────────
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
    d = {
        "formula": formula,
        "inputs": inputs_dict,
        "result": result_val,
    }
    if unit is not None:
        d["unit"] = unit
    return d


def _add_input_dates(result, val_d, mat_d, item):
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


# ─────────────────────────────────────────────────────────────
# 3. DEPENDENCY CHAIN EXECUTOR
# ─────────────────────────────────────────────────────────────
class CalculationSkipped(Exception):
    """Raise inside a step compute() to skip a step (optional data absent)."""


@dataclass
class CalcStep:
    """
    One node in a calculation chain.

    - `dependencies` list may contain other *step names* or *raw input names*.
    - `compute(inputs)` receives a dict whose keys are exactly the resolved
      dependencies PLUS any `extra_inputs`. It must return the raw
      (unrounded) result.
    - `unit` determines the final rounding:
        "currency" → 2 dp half-up
        "percent"  → 4 dp half-up
        "days"     → whole number, half-up
        "number"   → left as returned
    """
    name: str
    formula: str
    dependencies: List[str]
    compute: Callable[[Dict[str, Any]], Any]
    unit: str = "number"
    extra_inputs: Dict[str, Any] = dc_field(default_factory=dict)


def _round_for_unit(value: Any, unit: str) -> Any:
    if value is None:
        return None
    if unit == "days":
        return round_time(value)
    if unit == "percent":
        return _rate(value)
    if unit == "currency":
        return round_money(value)
    return value


def _display_input(value: Any) -> Any:
    if isinstance(value, (int, float)):
        return float(value)
    return value


def _detect_cycles(steps: List[CalcStep]) -> List[str]:
    step_names = {s.name for s in steps}
    graph = {s.name: set(s.dependencies) & step_names for s in steps}

    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in graph}
    in_cycle: set = set()

    def dfs(node: str, stack: List[str]):
        color[node] = GRAY
        for nxt in graph[node]:
            if color[nxt] == GRAY:
                try:
                    idx = stack.index(nxt)
                    in_cycle.update(stack[idx:])
                except ValueError:
                    in_cycle.add(nxt)
                in_cycle.add(node)
            elif color[nxt] == WHITE:
                dfs(nxt, stack + [nxt])
        color[node] = BLACK

    for n in graph:
        if color[n] == WHITE:
            dfs(n, [n])
    return sorted(in_cycle)


def execute_chain(steps: List[CalcStep],
                  available_inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the chain in the order given (caller must supply a topologically
    ordered list). Returns:

    {
      "values":      {step_name: raw_unrounded_result, ...},
      "derivations": {step_name: {
                          formula, dependencies, inputs,
                          result_raw, result, unit, status, error?
                      }, ...},
      "errors":      [{step, reason, ...}, ...],
    }
    """
    cycle = _detect_cycles(steps)
    if cycle:
        return {
            "values": {},
            "derivations": {name: {
                "formula": "", "dependencies": [], "inputs": {},
                "result_raw": None, "result": None, "unit": "number",
                "status": "failed",
                "error": f"Circular dependency: {cycle}",
            } for name in cycle},
            "errors": [{"step": c, "reason": "circular_dependency"} for c in cycle],
        }

    values: Dict[str, Any] = {}
    derivations: Dict[str, Any] = {}
    errors: List[Dict[str, Any]] = []
    failed_steps: set = set()

    for step in steps:
        failed_deps = [d for d in step.dependencies if d in failed_steps]
        if failed_deps:
            derivations[step.name] = {
                "formula": step.formula,
                "dependencies": step.dependencies,
                "inputs": {},
                "result_raw": None,
                "result": None,
                "unit": step.unit,
                "status": "skipped",
                "error": f"Dependency failed or skipped: {failed_deps}",
            }
            errors.append({"step": step.name, "reason": "dependency_failed",
                           "failed": failed_deps})
            failed_steps.add(step.name)
            continue

        resolved: Dict[str, Any] = {}
        missing_deps: List[str] = []
        for dep in step.dependencies:
            if dep in values and values[dep] is not None:
                resolved[dep] = values[dep]
            elif (dep in available_inputs
                  and available_inputs[dep] is not None
                  and available_inputs[dep] != ""):
                resolved[dep] = available_inputs[dep]
            else:
                missing_deps.append(dep)

        if missing_deps:
            derivations[step.name] = {
                "formula": step.formula,
                "dependencies": step.dependencies,
                "inputs": {},
                "result_raw": None,
                "result": None,
                "unit": step.unit,
                "status": "skipped",
                "error": f"Missing prerequisites: {missing_deps}",
            }
            errors.append({"step": step.name, "reason": "missing_prerequisites",
                           "missing": missing_deps})
            failed_steps.add(step.name)
            continue

        inputs_for_compute = dict(resolved)
        for k, v in step.extra_inputs.items():
            inputs_for_compute[k] = v

        try:
            raw_result = step.compute(inputs_for_compute)
        except CalculationSkipped as e:
            derivations[step.name] = {
                "formula": step.formula,
                "dependencies": step.dependencies,
                "inputs": {k: _display_input(v) for k, v in inputs_for_compute.items()},
                "result_raw": None,
                "result": None,
                "unit": step.unit,
                "status": "skipped",
                "error": str(e) or "Optional data missing",
            }
            errors.append({"step": step.name, "reason": "skipped",
                           "detail": str(e)})
            failed_steps.add(step.name)
            continue
        except ZeroDivisionError as e:
            derivations[step.name] = {
                "formula": step.formula,
                "dependencies": step.dependencies,
                "inputs": {k: _display_input(v) for k, v in inputs_for_compute.items()},
                "result_raw": None,
                "result": None,
                "unit": step.unit,
                "status": "failed",
                "error": f"Division by zero: {e}",
            }
            errors.append({"step": step.name, "reason": "division_by_zero"})
            failed_steps.add(step.name)
            continue
        except Exception as e:
            derivations[step.name] = {
                "formula": step.formula,
                "dependencies": step.dependencies,
                "inputs": {k: _display_input(v) for k, v in inputs_for_compute.items()},
                "result_raw": None,
                "result": None,
                "unit": step.unit,
                "status": "failed",
                "error": str(e),
            }
            errors.append({"step": step.name, "reason": "compute_error",
                           "error": str(e)})
            failed_steps.add(step.name)
            continue

        # A compute() that silently returns None must be treated as a skip —
        # otherwise downstream sees values[dep] is None and cascades as
        # "missing" with no trail of *why* this step produced nothing.
        if raw_result is None:
            derivations[step.name] = {
                "formula": step.formula,
                "dependencies": step.dependencies,
                "inputs": {k: _display_input(v) for k, v in inputs_for_compute.items()},
                "result_raw": None,
                "result": None,
                "unit": step.unit,
                "status": "skipped",
                "error": "compute() returned None",
            }
            errors.append({"step": step.name, "reason": "skipped",
                           "detail": "compute() returned None"})
            failed_steps.add(step.name)
            continue

        values[step.name] = raw_result
        derivations[step.name] = {
            "formula": step.formula,
            "dependencies": step.dependencies,
            "inputs": {k: _display_input(v) for k, v in inputs_for_compute.items()},
            "result_raw": (float(raw_result)
                           if isinstance(raw_result, (int, float))
                           else raw_result),
            "result": _round_for_unit(raw_result, step.unit),
            "unit": step.unit,
            "status": "ok",
        }

    return {"values": values, "derivations": derivations, "errors": errors}


# ─────────────────────────────────────────────────────────────
# 4. Row alias normalisation
# ─────────────────────────────────────────────────────────────
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
        "tbillname", "TBillName",
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


# ─────────────────────────────────────────────────────────────
# 5. Row validation
# ─────────────────────────────────────────────────────────────
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
        note("years_to_maturity"); note("valuation_date"); note("maturity_date"); note("issue_date")
        if years is None:
            period_start = (parse_date(norm.get("valuation_date"))
                            or parse_date(norm.get("issue_date")))
            mat_d = parse_date(norm.get("maturity_date"))
            if period_start and mat_d and mat_d >= period_start:
                years = (mat_d - period_start).days / 365.0
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

    elif instrument_type == "money-market" or instrument_type == "money_market":
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


# ─────────────────────────────────────────────────────────────
# 6. YTM solver, price-from-YTM, bond accrued helper
# ─────────────────────────────────────────────────────────────
def _solve_ytm(price, face, coupon_rate, years, frequency):
    """Solve YTM (as a decimal fraction) from price. Inputs are fractions."""
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
    """price from YTM. Inputs are decimal fractions."""
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


# ─────────────────────────────────────────────────────────────
# 7. CamelCase aliasing for frontend compatibility
# ─────────────────────────────────────────────────────────────
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


# ─────────────────────────────────────────────────────────────
# 8. MONEY MARKET calculation
# ─────────────────────────────────────────────────────────────
def calculate_money_market(item: Dict[str, Any],
                           benchmark_yield: Optional[float] = None) -> Dict[str, Any]:
    item = normalize_row(item)

    principal = (safe_float(item.get("principal"))
                 or safe_float(item.get("face_value"))
                 or safe_float(item.get("amount")))
    rate_frac = (parse_percentage(item.get("interest_rate"))
                 or parse_percentage(item.get("rate")))
    currency = item.get("currency") or item.get("ccy") or item.get("currency_code")

    day_count = str(item.get("day_count_convention")
                    or item.get("day_count") or "ACT/360").upper()
    divisor = 365.0 if "365" in day_count else 360.0

    val_d = parse_date(item.get("valuation_date"))
    mat_d = parse_date(item.get("maturity_date"))
    period_start = val_d or parse_date(item.get("issue_date"))

    raw_days = (safe_float(item.get("term_days"))
                or safe_float(item.get("days_to_maturity")))

    # capture rate as percent (5.0) for both display and downstream division
    rate_pct = (rate_frac * 100.0) if rate_frac is not None else None

    result: Dict[str, Any] = {
        "instrument_type": "money-market",
        "principal": round_money(principal),
        "interest_rate": _rate(rate_pct) if rate_pct is not None else None,
        "day_count_convention": day_count,
        "currency": currency,
        "status": "success"
    }
    name = _extract_instrument_name(item)
    if name:
        result["instrument_name"] = name
    _add_input_dates(result, val_d, mat_d, item)

    # ── Step definitions ──
    if raw_days is not None:
        days_deps = []
        days_compute = (lambda inp, _raw=raw_days: round_time(_raw))
    else:
        days_deps = ["period_start", "maturity_date"]
        def days_compute(inp):
            v = parse_date(inp["period_start"])
            m = parse_date(inp["maturity_date"])
            d = (m - v).days
            if d <= 0:
                raise ValueError(f"Maturity date must be after period start (got {d} days)")
            return d

    def _calc_interest(inp):
        return (inp["principal"]
                * (inp["interest_rate"] / 100.0)
                * (inp["days_to_maturity"] / divisor))

    def _calc_total(inp):
        return inp["principal"] + inp["interest_earned"]

    def _calc_discount_yield(inp):
        return ((inp["interest_earned"] / inp["total_value"])
                * (divisor / inp["days_to_maturity"]) * 100.0)

    def _calc_eff_annual(inp):
        return ((inp["interest_earned"] / inp["principal"])
                * (365.0 / inp["days_to_maturity"]) * 100.0)

    steps = [
        CalcStep(
            name="days_to_maturity",
            formula="term_days input, else maturity_date − valuation_date",
            dependencies=days_deps,
            compute=days_compute,
            unit="days",
            extra_inputs={"day_count_convention": day_count},
        ),
        CalcStep(
            name="interest_earned",
            formula="principal × (interest_rate/100) × (days / divisor)",
            dependencies=["principal", "interest_rate", "days_to_maturity"],
            compute=_calc_interest,
            unit="currency",
            extra_inputs={"divisor": divisor, "day_count_convention": day_count},
        ),
        CalcStep(
            name="total_value",
            formula="principal + interest_earned",
            dependencies=["principal", "interest_earned"],
            compute=_calc_total,
            unit="currency",
        ),
        CalcStep(
            name="discount_yield",
            formula="(interest_earned / total_value) × (divisor / days) × 100",
            dependencies=["interest_earned", "total_value", "days_to_maturity"],
            compute=_calc_discount_yield,
            unit="percent",
            extra_inputs={"divisor": divisor},
        ),
        CalcStep(
            name="effective_annual_rate",
            formula="(interest_earned / principal) × (365 / days) × 100",
            dependencies=["interest_earned", "principal", "days_to_maturity"],
            compute=_calc_eff_annual,
            unit="percent",
        ),
        CalcStep(
            name="bond_equivalent_yield",
            formula="(interest_earned / principal) × (365 / days) × 100",
            dependencies=["interest_earned", "principal", "days_to_maturity"],
            compute=_calc_eff_annual,
            unit="percent",
        ),
        CalcStep(
            name="effective_yield",
            formula="(interest_earned / principal) × (365 / days) × 100",
            dependencies=["interest_earned", "principal", "days_to_maturity"],
            compute=_calc_eff_annual,
            unit="percent",
        ),
        CalcStep(
            name="present_value",
            formula="principal",
            dependencies=["principal"],
            compute=lambda inp: inp["principal"],
            unit="currency",
        ),
        CalcStep(
            name="fair_value",
            formula="principal + interest_earned",
            dependencies=["principal", "interest_earned"],
            compute=_calc_total,
            unit="currency",
        ),
    ]

    available = {
        "principal": principal,
        "interest_rate": rate_pct,
        "period_start": period_start,
        "maturity_date": mat_d,
    }

    chain = execute_chain(steps, available)
    values = chain["values"]
    hard_failures = [e for e in chain["errors"]
                     if e["reason"] in ("missing_prerequisites",
                                        "circular_dependency",
                                        "compute_error",
                                        "division_by_zero")]

    # ── Flat fields ──
    if "days_to_maturity" in values:
        result["term_days"] = round_time(values["days_to_maturity"])
    if "interest_earned" in values:
        result["interest_earned"] = round_money(values["interest_earned"])
        result["total_interest"] = result["interest_earned"]
    if "total_value" in values:
        result["total_value"] = round_money(values["total_value"])
        result["maturity_value"] = result["total_value"]
        result["fair_value"] = result["total_value"]
    for k in ("discount_yield", "effective_annual_rate",
              "bond_equivalent_yield", "effective_yield"):
        if k in values:
            result[k] = _rate(values[k])
    if "effective_annual_rate" in result:
        result["annual_yield"] = result["effective_annual_rate"]
    if "present_value" in values:
        result["present_value"] = round_money(values["present_value"])
    result["yield_curve_rate"] = _benchmark_to_percent(benchmark_yield)

    if hard_failures:
        result["status"] = "partial"
        result["missing_prerequisites"] = [
            e.get("missing") for e in hard_failures if e.get("missing")
        ]
    else:
        result["status"] = "success"

    result["derivations"] = chain["derivations"]
    if chain["errors"]:
        result["calculation_errors"] = chain["errors"]
    return _add_camel_aliases(result)


# ─────────────────────────────────────────────────────────────
# 9. T-BILL calculation
# ─────────────────────────────────────────────────────────────
def calculate_treasury_bill(item: Dict[str, Any],
                            benchmark_yield: Optional[float] = None) -> Dict[str, Any]:
    item = normalize_row(item)

    face = safe_float(item.get("face_value")) or safe_float(item.get("principal"))
    purchase_price_in = (safe_float(item.get("purchase_price"))
                         or safe_float(item.get("current_price"))
                         or safe_float(item.get("price")))
    discount_rate_in_frac = parse_percentage(item.get("discount_rate"))
    currency = item.get("currency") or item.get("ccy") or item.get("currency_code")
    day_count = str(item.get("day_count_convention")
                    or item.get("day_count") or "ACT/360").upper()
    discount_basis = 365.0 if "365" in day_count else 360.0

    val_d = parse_date(item.get("valuation_date"))
    mat_d = parse_date(item.get("maturity_date"))
    period_start = val_d or parse_date(item.get("issue_date"))
    raw_days = (safe_float(item.get("term_days"))
                or safe_float(item.get("days_to_maturity")))

    discount_rate_pct_in = (discount_rate_in_frac * 100.0
                            if discount_rate_in_frac is not None else None)

    result: Dict[str, Any] = {
        "instrument_type": "tbills",
        "face_value": round_money(face),
        "day_count_convention": day_count,
        "currency": currency,
        "status": "success"
    }
    name = _extract_instrument_name(item)
    if name:
        result["instrument_name"] = name
    _add_input_dates(result, val_d, mat_d, item)

    # Date validation
    if val_d and mat_d:
        if mat_d < val_d:
            result["error"] = f"Maturity date ({mat_d.isoformat()}) is before valuation date ({val_d.isoformat()}). Days calculation requires maturity after valuation."
            result["status"] = "validation_failed"
            result["invalid_fields"] = [{"field": "maturity_date", "reason": "must be after valuation_date"}]
            result["derivations"] = {}
            return _add_camel_aliases(result)

    # Conflicting-input detection (price wins)
    if (purchase_price_in is not None and discount_rate_in_frac is not None
            and face is not None and raw_days is not None and raw_days > 0):
        implied = ((face - purchase_price_in) / face
                   * discount_basis / raw_days)
        if abs(implied - discount_rate_in_frac) > 1e-6:
            result["warning"] = (
                f"Provided discount_rate={discount_rate_in_frac * 100:.4f}% and "
                f"purchase_price={purchase_price_in:.2f} are inconsistent "
                f"(price implies {implied * 100:.4f}%). "
                "purchase_price takes precedence."
            )

    # ── Chain ──
    if raw_days is not None:
        days_deps = []
        days_compute = (lambda inp, _raw=raw_days: round_time(_raw))
    else:
        days_deps = ["period_start", "maturity_date"]
        def days_compute(inp):
            v = parse_date(inp["period_start"])
            m = parse_date(inp["maturity_date"])
            if v is None or m is None:
                raise ValueError("Both period_start and maturity_date are required for days calculation")
            d = (m - v).days
            if d <= 0:
                raise ValueError(f"Maturity date must be after period start (got {d} days)")
            return d

    def _establish_price(inp):
        if purchase_price_in is not None:
            return purchase_price_in
        if discount_rate_in_frac is not None:
            return (inp["face_value"]
                    * (1.0 - discount_rate_in_frac
                       * inp["days_to_maturity"] / discount_basis))
        raise ValueError("Need purchase_price or discount_rate")

    def _discount_amount(inp):
        return inp["face_value"] - inp["purchase_price"]

    def _discount_rate_from_price(inp):
        return ((inp["face_value"] - inp["purchase_price"])
                / inp["face_value"]
                * (discount_basis / inp["days_to_maturity"]) * 100.0)

    def _discount_yield(inp):
        return ((inp["face_value"] - inp["purchase_price"])
                / inp["face_value"]
                * (discount_basis / inp["days_to_maturity"]) * 100.0)

    def _mm_yield(inp):
        return ((inp["face_value"] - inp["purchase_price"])
                / inp["purchase_price"]
                * (discount_basis / inp["days_to_maturity"]) * 100.0)

    def _be_yield(inp):
        return ((inp["face_value"] - inp["purchase_price"])
                / inp["purchase_price"]
                * (365.0 / inp["days_to_maturity"]) * 100.0)

    def _hp_yield(inp):
        return ((inp["face_value"] - inp["purchase_price"])
                / inp["purchase_price"] * 100.0)

    def _eff_annual_yield(inp):
        return ((inp["face_value"] / inp["purchase_price"])
                ** (365.0 / inp["days_to_maturity"]) - 1.0) * 100.0

    def _present_value(inp):
        dr = inp.get("discount_rate", discount_rate_in_frac * 100.0 if discount_rate_in_frac else 0)
        return (inp["face_value"]
                * (1.0 - (dr / 100.0)
                   * inp["days_to_maturity"] / discount_basis))

    steps = [
        CalcStep(
            name="days_to_maturity",
            formula="term_days input, else maturity_date − valuation_date",
            dependencies=days_deps,
            compute=days_compute,
            unit="days",
            extra_inputs={"day_count_convention": day_count},
        ),
        CalcStep(
            name="purchase_price",
            formula="input price, or face × (1 − discount_rate × days / basis)",
            dependencies=["face_value", "days_to_maturity"],
            compute=_establish_price,
            unit="currency",
            extra_inputs={
                "input_price": purchase_price_in,
                "input_discount_rate_pct": discount_rate_pct_in,
                "discount_basis": discount_basis,
            },
        ),
        CalcStep(
            name="discount_amount",
            formula="face_value − purchase_price",
            dependencies=["face_value", "purchase_price"],
            compute=_discount_amount,
            unit="currency",
        ),
        CalcStep(
            name="discount_rate",
            formula="((face_value − purchase_price) / face_value) × (basis / days) × 100",
            dependencies=["face_value", "purchase_price", "days_to_maturity"],
            compute=_discount_rate_from_price,
            unit="percent",
            extra_inputs={"discount_basis": discount_basis},
        ),
        CalcStep(
            name="discount_yield",
            formula="((face_value − purchase_price) / face_value) × (basis / days) × 100",
            dependencies=["face_value", "purchase_price", "days_to_maturity"],
            compute=_discount_yield,
            unit="percent",
            extra_inputs={"discount_basis": discount_basis},
        ),
        CalcStep(
            name="money_market_yield",
            formula="((face_value − purchase_price) / purchase_price) × (basis / days) × 100",
            dependencies=["face_value", "purchase_price", "days_to_maturity"],
            compute=_mm_yield,
            unit="percent",
            extra_inputs={"discount_basis": discount_basis},
        ),
        CalcStep(
            name="bond_equivalent_yield",
            formula="((face_value − purchase_price) / purchase_price) × (365 / days) × 100",
            dependencies=["face_value", "purchase_price", "days_to_maturity"],
            compute=_be_yield,
            unit="percent",
        ),
        CalcStep(
            name="holding_period_yield",
            formula="((face_value − purchase_price) / purchase_price) × 100",
            dependencies=["face_value", "purchase_price"],
            compute=_hp_yield,
            unit="percent",
        ),
        CalcStep(
            name="effective_annual_yield",
            formula="((face_value / purchase_price)^(365/days) − 1) × 100",
            dependencies=["face_value", "purchase_price", "days_to_maturity"],
            compute=_eff_annual_yield,
            unit="percent",
        ),
        CalcStep(
            name="present_value",
            formula="face × (1 − discount_rate/100 × days / basis)",
            dependencies=["face_value", "days_to_maturity"],
            compute=_present_value,
            unit="currency",
            extra_inputs={"discount_basis": discount_basis, "discount_rate": discount_rate_pct_in},
        ),
    ]

    available = {
        "face_value": face,
        "period_start": period_start,
        "maturity_date": mat_d,
        "discount_rate_input_frac": discount_rate_in_frac,
    }
    chain = execute_chain(steps, available)
    values = chain["values"]
    hard_failures = [e for e in chain["errors"]
                     if e["reason"] in ("missing_prerequisites",
                                        "circular_dependency",
                                        "compute_error",
                                        "division_by_zero")]

    # ── Flat fields ──
    if "days_to_maturity" in values:
        result["term_days"] = round_time(values["days_to_maturity"])
    for k in ("purchase_price", "discount_amount",
              "present_value"):
        if k in values:
            result[k] = round_money(values[k])
    if "discount_rate" in values:
        result["discount_rate"] = _rate(values["discount_rate"])
    for k in ("discount_yield", "money_market_yield",
              "bond_equivalent_yield", "holding_period_yield",
              "effective_annual_yield"):
        if k in values:
            result[k] = _rate(values[k])
    if face is not None:
        result["total_value"] = round_money(face)
        result["maturity_value"] = round_money(face)
    if "present_value" in result:
        result["fair_value"] = result["present_value"]
    if "bond_equivalent_yield" in result:
        result["annualized_yield"] = result["bond_equivalent_yield"]
    if "purchase_price" in result:
        result["avg_investment"] = result["purchase_price"]
    result["yield_curve_rate"] = _benchmark_to_percent(benchmark_yield)

    if hard_failures:
        result["status"] = "partial"
        result["missing_prerequisites"] = [
            e.get("missing") for e in hard_failures if e.get("missing")
        ]
    else:
        result["status"] = "success"

    result["derivations"] = chain["derivations"]
    if chain["errors"]:
        result["calculation_errors"] = chain["errors"]
    return _add_camel_aliases(result)


# ─────────────────────────────────────────────────────────────
# 10. BOND calculation
# ─────────────────────────────────────────────────────────────
def calculate_bond(item: Dict[str, Any],
                   benchmark_yield: Optional[float] = None) -> Dict[str, Any]:
    raw_freq = (item.get("Coupon Frequency") or item.get("coupon_frequency")
                or item.get("frequency"))
    item = normalize_row(item)

    face = safe_float(item.get("face_value")) or safe_float(item.get("principal"))
    coupon_rate_frac = (parse_percentage(item.get("coupon_rate"))
                        or parse_percentage(item.get("interest_rate")))
    currency = item.get("currency") or item.get("ccy") or item.get("currency_code")

    price_in = _parse_bond_price(item, face)
    ytm_input_frac = (parse_percentage(item.get("yield"))
                      or parse_percentage(item.get("yield_to_maturity")))

    day_count = str(item.get("day_count_convention")
                    or item.get("day_count") or "ACT/365").upper()

    val_d = parse_date(item.get("valuation_date"))
    mat_d = parse_date(item.get("maturity_date"))

    years = safe_float(item.get("years_to_maturity"))
    years_source = "input" if years is not None else None
    if years is None:
        period_start = val_d or parse_date(item.get("issue_date"))
        if period_start and mat_d and mat_d >= period_start:
            years = (mat_d - period_start).days / 365.0
            years_source = "derived_from_dates"
    if years is None:
        d2m = safe_float(item.get("days_to_maturity"))
        if d2m is not None and d2m > 0:
            years = d2m / 365.0
            years_source = "derived_from_days"

    frequency = (parse_frequency(item.get("frequency"))
                 or parse_frequency(item.get("coupon_frequency"))
                 or parse_frequency(raw_freq))
    defaulted_freq = False
    if frequency is None or frequency <= 0 or frequency > 365:
        frequency = 2
        defaulted_freq = True

    coupon_rate_pct = (coupon_rate_frac * 100.0
                       if coupon_rate_frac is not None else None)
    ytm_input_pct = (ytm_input_frac * 100.0
                     if ytm_input_frac is not None else None)

    result: Dict[str, Any] = {
        "instrument_type": "bonds",
        "face_value": round_money(face),
        "coupon_rate": _rate(coupon_rate_pct) if coupon_rate_pct is not None else None,
        "years_to_maturity": round(years, 4) if years is not None else None,
        "frequency": frequency,
        "coupon_frequency": frequency,
        "day_count_convention": day_count,
        "currency": currency,
        "status": "success"
    }
    name = _extract_instrument_name(item)
    if name:
        result["instrument_name"] = name
    _add_input_dates(result, val_d, mat_d, item)
    if defaulted_freq:
        result["warning"] = "Coupon frequency not specified — defaulted to semi-annual (2)."

    basis = 360.0 if "360" in day_count else 365.0

    def _n_periods(years_val: float, freq: int) -> int:
        return max(1, int(Decimal(str(years_val * freq)).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP)))

    # ── Step bodies ──
    def _annual_coupon(inp):
        return inp["face_value"] * (inp["coupon_rate"] / 100.0)

    def _coupon_payment(inp):
        return inp["annual_coupon"] / frequency

    def _current_price(inp):
        if price_in is not None and price_in > 0:
            return price_in
        if ytm_input_frac is None:
            raise ValueError("Need price or yield_to_maturity to value the bond")
        return _price_from_ytm(
            inp["face_value"], inp["coupon_rate"] / 100.0,
            ytm_input_frac, inp["years_to_maturity"], frequency,
        )

    def _yield_to_maturity(inp):
        if ytm_input_frac is not None:
            return ytm_input_pct
        solved = _solve_ytm(
            inp["current_price"], inp["face_value"],
            inp["coupon_rate"] / 100.0,
            inp["years_to_maturity"], frequency,
        )
        if solved is None:
            raise ValueError("Could not solve YTM from price")
        return solved * 100.0

    def _current_yield(inp):
        return (inp["annual_coupon"] / inp["current_price"]) * 100.0

    def _price_per_100(inp):
        return (inp["current_price"] / inp["face_value"]) * 100.0

    def _days_accrued(inp):
        v = parse_date(inp["valuation_date"])
        l = parse_date(inp["last_coupon_date"])
        if l is None:
            raise CalculationSkipped("last_coupon_date not provided")
        d = (v - l).days
        if d < 0:
            raise CalculationSkipped("valuation_date precedes last_coupon_date")
        return d

    def _accrued_interest(inp):
        days_per_period = basis / frequency
        return inp["coupon_payment"] * (inp["days_accrued"] / days_per_period)

    def _duration_block(inp):
        y_frac = inp["yield_to_maturity"] / 100.0
        if y_frac <= -0.99:
            raise ValueError("Yield out of range")
        n = _n_periods(inp["years_to_maturity"], frequency)
        r = y_frac / frequency
        coupon_per = (inp["face_value"]
                      * (inp["coupon_rate"] / 100.0) / frequency)
        pv_total = weighted = cx = 0.0
        for t in range(1, n + 1):
            disc = (1 + r) ** t
            pv_c = coupon_per / disc
            pv_total += pv_c
            weighted += t * pv_c
            cx += t * (t + 1) * pv_c / ((1 + r) ** 2)
        pv_f = inp["face_value"] / (1 + r) ** n
        pv_total += pv_f
        weighted += n * pv_f
        cx += n * (n + 1) * pv_f / ((1 + r) ** 2)
        if pv_total <= 0:
            raise ValueError("Non-positive PV — cannot compute duration")
        macaulay = (weighted / pv_total) / frequency
        modified = macaulay / (1 + r)
        convexity = cx / pv_total / (frequency ** 2)
        return {"macaulay": macaulay, "modified": modified, "convexity": convexity}

    def _macaulay(inp):
        return _duration_block(inp)["macaulay"]

    def _modified(inp):
        return _duration_block(inp)["modified"]

    def _convexity(inp):
        return _duration_block(inp)["convexity"]

    def _dv01(inp):
        return inp["current_price"] * (inp["modified_duration"]) * 0.0001

    steps = [
        CalcStep(
            name="annual_coupon",
            formula="face_value × (coupon_rate / 100)",
            dependencies=["face_value", "coupon_rate"],
            compute=_annual_coupon,
            unit="currency",
        ),
        CalcStep(
            name="coupon_payment",
            formula="annual_coupon / frequency",
            dependencies=["annual_coupon"],
            compute=_coupon_payment,
            unit="currency",
            extra_inputs={"frequency": frequency},
        ),
        CalcStep(
            name="current_price",
            formula="input price, or PV(coupons) + PV(face) discounted at YTM",
            dependencies=["face_value", "coupon_rate", "years_to_maturity"],
            compute=_current_price,
            unit="currency",
            extra_inputs={"input_price": price_in, "frequency": frequency},
        ),
        CalcStep(
            name="yield_to_maturity",
            formula="input YTM, or IRR solved from current_price",
            dependencies=["current_price", "face_value", "coupon_rate",
                          "years_to_maturity"],
            compute=_yield_to_maturity,
            unit="percent",
            extra_inputs={"frequency": frequency},
        ),
        CalcStep(
            name="current_yield",
            formula="(annual_coupon / current_price) × 100",
            dependencies=["annual_coupon", "current_price"],
            compute=_current_yield,
            unit="percent",
        ),
        CalcStep(
            name="price_per_100",
            formula="(current_price / face_value) × 100",
            dependencies=["current_price", "face_value"],
            compute=_price_per_100,
            unit="number",
        ),
        CalcStep(
            name="days_accrued",
            formula="valuation_date − last_coupon_date",
            dependencies=["valuation_date", "last_coupon_date"],
            compute=_days_accrued,
            unit="days",
        ),
        CalcStep(
            name="accrued_interest",
            formula="coupon_payment × (days_accrued / (basis/frequency))",
            dependencies=["coupon_payment", "days_accrued"],
            compute=_accrued_interest,
            unit="currency",
            extra_inputs={"basis": basis, "frequency": frequency},
        ),
        CalcStep(
            name="macaulay_duration",
            formula="Σ(t × PV(CF)) / (price × frequency)",
            dependencies=["current_price", "face_value", "coupon_rate",
                          "years_to_maturity", "yield_to_maturity"],
            compute=_macaulay,
            unit="number",
            extra_inputs={"frequency": frequency},
        ),
        CalcStep(
            name="modified_duration",
            formula="macaulay / (1 + ytm / (100 × frequency))",
            dependencies=["current_price", "face_value", "coupon_rate",
                          "years_to_maturity", "yield_to_maturity"],
            compute=_modified,
            unit="number",
            extra_inputs={"frequency": frequency},
        ),
        CalcStep(
            name="convexity",
            formula="Σ(t(t+1) × PV(CF)) / (price × (1+r)²)",
            dependencies=["current_price", "face_value", "coupon_rate",
                          "years_to_maturity", "yield_to_maturity"],
            compute=_convexity,
            unit="number",
            extra_inputs={"frequency": frequency},
        ),
        CalcStep(
            name="dv01",
            formula="current_price × modified_duration × 0.0001",
            dependencies=["current_price", "modified_duration"],
            compute=_dv01,
            unit="currency",
        ),
    ]

    available = {
        "face_value": face,
        "coupon_rate": coupon_rate_pct,
        "years_to_maturity": years,
        "valuation_date": val_d,
        "maturity_date": mat_d,
        "last_coupon_date": parse_date(item.get("last_coupon_date")),
        "yield_to_maturity_input_pct": ytm_input_pct,
    }
    chain = execute_chain(steps, available)
    values = chain["values"]
    hard_failures = [e for e in chain["errors"]
                     if e["reason"] in ("missing_prerequisites",
                                        "circular_dependency",
                                        "compute_error",
                                        "division_by_zero")]

    # ── Flat fields ──
    for k in ("annual_coupon", "coupon_payment", "current_price",
              "accrued_interest", "dv01"):
        if k in values:
            result[k] = round_money(values[k])
    if "coupon_payment" in values:
        result["coupon_per_period"] = result["coupon_payment"]
    for k in ("yield_to_maturity", "current_yield"):
        if k in values:
            result[k] = _rate(values[k])
    if "price_per_100" in values:
        result["price_per_100"] = round(values["price_per_100"], 2)
    for k in ("macaulay_duration", "modified_duration", "convexity"):
        if k in values:
            result[k] = _rate(values[k])
    if "macaulay_duration" in values:
        result["duration"] = result["macaulay_duration"]
    if "days_accrued" in values:
        result["days_accrued"] = round_time(values["days_accrued"])
    if "current_price" in values:
        result["total_value"] = result["current_price"]
        result["present_value"] = result["current_price"]
        result["fair_value"] = result["current_price"]

    result["ytm_input"] = _rate(ytm_input_pct) if ytm_input_pct is not None else None
    if "yield_to_maturity" not in values:
        result["ytm_source"] = None
    elif ytm_input_frac is not None:
        result["ytm_source"] = "input"
    else:
        result["ytm_source"] = "solved_from_price"
    result["yield_curve_rate"] = _benchmark_to_percent(benchmark_yield)

    # Warn if both provided and they diverge (input YTM wins, but flag it)
    if (ytm_input_frac is not None and price_in is not None
            and "yield_to_maturity" in values):
        solved_pct = _solve_ytm(price_in, face, coupon_rate_frac, years, frequency)
        if solved_pct is not None and abs(solved_pct - ytm_input_frac) > 1e-4:
            warn = (f"Provided yield_to_maturity={ytm_input_pct:.4f}% and "
                    f"price={price_in:.2f} imply different YTMs "
                    f"(price implies {solved_pct * 100:.4f}%). Input YTM wins.")
            result["warning"] = ((result.get("warning") or "") + " " + warn).strip()

    if hard_failures:
        result["status"] = "partial"
        result["missing_prerequisites"] = [
            e.get("missing") for e in hard_failures if e.get("missing")
        ]
    else:
        result["status"] = "partial" if defaulted_freq else "success"

    result["derivations"] = chain["derivations"]
    if chain["errors"]:
        result["calculation_errors"] = chain["errors"]
    return _add_camel_aliases(result)


# ─────────────────────────────────────────────────────────────
# 11. Single-row calc dispatcher
# ─────────────────────────────────────────────────────────────
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


# ─────────────────────────────────────────────────────────────
# 12. Multi-row dispatcher + aggregates
# ─────────────────────────────────────────────────────────────
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

        # Validate once before calculation
        validation = validate_row(row, instrument_type)
        if not validation["can_calculate"]:
            calc = {
                "instrument_type": instrument_type,
                "status": "validation_failed",
                "missing_fields": validation["missing_fields"],
                "invalid_fields": validation["invalid_fields"],
                "message": f"Cannot calculate: missing {len(validation['missing_fields'])} fields, {len(validation['invalid_fields'])} invalid",
                "derivations": {}
            }
            name = _extract_instrument_name(row)
            if name:
                calc["instrument_name"] = name
            instrument_results.append(calc)
            failed.append(calc)
            continue

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
            m = _mean("interest_rate")
            aggregates["avg_rate"] = round(m, 4) if m is not None else None
            m = _mean("term_days")
            aggregates["avg_days_to_maturity"] = round(m, 2) if m is not None else None
            m = _mean("effective_annual_rate")
            aggregates["effective_annual_rate"] = round(m, 4) if m is not None else None
            m = _mean("effective_yield")
            aggregates["effective_yield"] = round(m, 4) if m is not None else None
            m = _mean("bond_equivalent_yield")
            aggregates["bond_equivalent_yield"] = round(m, 4) if m is not None else None
            m = _mean("discount_yield")
            aggregates["discount_yield"] = round(m, 4) if m is not None else None
            m = _mean("term_days")
            aggregates["term_days"] = round(m, 2) if m is not None else None
            aggregates["days_to_maturity"] = aggregates["term_days"]
            aggregates["maturity_value"] = round_money(_sum("maturity_value"))
            aggregates["present_value"] = round_money(_sum("present_value"))
            aggregates["fair_value"] = round_money(_sum("fair_value"))
            aggregates["yield_curve_rate"] = (
                round(_mean("yield_curve_rate"), 4)
                if _mean("yield_curve_rate") is not None else None
            )
            m = _mean("annual_yield")
            aggregates["annual_yield"] = round(m, 4) if m is not None else None

        elif instrument_type == "tbills":
            aggregates["total_face_value"] = round_money(_sum("face_value"))
            aggregates["total_purchase_price"] = round_money(_sum("purchase_price"))
            aggregates["total_discount"] = round_money(_sum("discount_amount"))
            aggregates["total_value"] = round_money(_sum("face_value"))
            m = _mean("discount_rate")
            aggregates["avg_discount_rate"] = round(m, 4) if m is not None else None
            m = _mean("term_days")
            aggregates["avg_days_to_maturity"] = round(m, 2) if m is not None else None
            faces = [r["face_value"] for r in successful if r.get("face_value") is not None]
            disc_rates = [r["discount_rate"] for r in successful if r.get("discount_rate") is not None]
            if faces and sum(faces) > 0 and len(faces) == len(disc_rates):
                aggregates["weighted_avg_discount"] = round(
                    sum(f * d for f, d in zip(faces, disc_rates)) / sum(faces), 4)
            m = _mean("purchase_price")
            aggregates["avg_investment"] = round(m, 2) if m is not None else None
            m = _mean("bond_equivalent_yield")
            aggregates["annualized_yield"] = round(m, 4) if m is not None else None
            aggregates["discount_rate"] = (round(_mean("discount_rate"), 4)
                                            if _mean("discount_rate") is not None else None)
            aggregates["discount_yield"] = (round(_mean("discount_yield"), 4)
                                             if _mean("discount_yield") is not None else None)
            aggregates["money_market_yield"] = (round(_mean("money_market_yield"), 4)
                                                 if _mean("money_market_yield") is not None else None)
            aggregates["bond_equivalent_yield"] = (round(_mean("bond_equivalent_yield"), 4)
                                                    if _mean("bond_equivalent_yield") is not None else None)
            aggregates["holding_period_yield"] = (round(_mean("holding_period_yield"), 4)
                                                   if _mean("holding_period_yield") is not None else None)
            aggregates["effective_annual_yield"] = (round(_mean("effective_annual_yield"), 4)
                                                     if _mean("effective_annual_yield") is not None else None)
            m = _mean("term_days")
            aggregates["term_days"] = round(m, 2) if m is not None else None
            aggregates["days_to_maturity"] = aggregates["term_days"]
            aggregates["maturity_value"] = round_money(_sum("maturity_value"))
            aggregates["present_value"] = round_money(_sum("present_value"))
            aggregates["fair_value"] = round_money(_sum("fair_value"))
            aggregates["purchase_price"] = round_money(_mean("purchase_price"))
            aggregates["discount_amount"] = round_money(_mean("discount_amount"))
            aggregates["yield_curve_rate"] = (
                round(_mean("yield_curve_rate"), 4)
                if _mean("yield_curve_rate") is not None else None
            )

        elif instrument_type == "bonds":
            aggregates["total_face_value"] = round_money(_sum("face_value"))
            aggregates["total_market_value"] = round_money(_sum("current_price"))
            aggregates["total_coupon_income"] = round_money(_sum("annual_coupon"))
            aggregates["total_value"] = round_money(_sum("current_price"))
            m = _mean("yield_to_maturity")
            aggregates["avg_ytm"] = round(m, 4) if m is not None else None
            m = _mean("duration")
            aggregates["avg_duration"] = round(m, 4) if m is not None else None
            faces = [r["face_value"] for r in successful if r.get("face_value") is not None]
            coupon_rates = [r["coupon_rate"] for r in successful if r.get("coupon_rate") is not None]
            if faces and sum(faces) > 0 and len(faces) == len(coupon_rates):
                aggregates["weighted_avg_coupon"] = round(
                    sum(f * c for f, c in zip(faces, coupon_rates)) / sum(faces), 4)
            aggregates["avg_coupon_rate"] = (round(_mean("coupon_rate"), 4)
                                              if _mean("coupon_rate") is not None else None)
            aggregates["current_price"] = round_money(_mean("current_price"))
            aggregates["price_per_100"] = (round(_mean("price_per_100"), 2)
                                            if _mean("price_per_100") is not None else None)
            aggregates["coupon_rate"] = (round(_mean("coupon_rate"), 4)
                                          if _mean("coupon_rate") is not None else None)
            aggregates["annual_coupon"] = round_money(_mean("annual_coupon"))
            aggregates["coupon_per_period"] = round_money(_mean("coupon_payment"))
            aggregates["yield_to_maturity"] = (round(_mean("yield_to_maturity"), 4)
                                                if _mean("yield_to_maturity") is not None else None)
            aggregates["current_yield"] = (round(_mean("current_yield"), 4)
                                            if _mean("current_yield") is not None else None)
            aggregates["duration"] = (round(_mean("duration"), 4)
                                       if _mean("duration") is not None else None)
            aggregates["modified_duration"] = (round(_mean("modified_duration"), 4)
                                                if _mean("modified_duration") is not None else None)
            aggregates["accrued_interest"] = round_money(_sum("accrued_interest"))
            aggregates["years_to_maturity"] = (round(_mean("years_to_maturity"), 4)
                                                if _mean("years_to_maturity") is not None else None)
            aggregates["frequency"] = (round(_mean("frequency"), 2)
                                        if _mean("frequency") is not None else None)
            aggregates["days_accrued"] = (round(_mean("days_accrued"), 2)
                                           if _mean("days_accrued") is not None else None)
            aggregates["convexity"] = (round(_mean("convexity"), 4)
                                        if _mean("convexity") is not None else None)
            aggregates["dv01"] = (round(_mean("dv01"), 4)
                                   if _mean("dv01") is not None else None)
            aggregates["present_value"] = round_money(_sum("present_value"))
            aggregates["fair_value"] = round_money(_sum("fair_value"))
            aggregates["yield_curve_rate"] = (
                round(_mean("yield_curve_rate"), 4)
                if _mean("yield_curve_rate") is not None else None
            )

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


# ─────────────────────────────────────────────────────────────
# 13. Import-time cycle check (SAFE)
# ─────────────────────────────────────────────────────────────
try:
    from pages.calculation_dependencies import (
        create_calculation_dependency_engine as _mk_engine,
    )
    _engine = _mk_engine()
    if hasattr(_engine, "detect_cycles"):
        for _t in ("money-market", "tbills", "bonds"):
            _cyc = _engine.detect_cycles(_t)
            if _cyc:
                warnings.warn(
                    f"Circular dependencies detected for '{_t}': {_cyc}. "
                    "Calculation chains for this instrument will fail at runtime.",
                    RuntimeWarning, stacklevel=2,
                )
    else:
        warnings.warn(
            "calculation_dependencies.py does not define detect_cycles(); "
            "import-time cycle check skipped. Runtime cycle detection in "
            "execute_chain() is still active.",
            RuntimeWarning, stacklevel=2,
        )
except ImportError:
    pass
except Exception as _e:
    warnings.warn(
        f"Calculation dependency cycle check skipped: {_e}",
        RuntimeWarning, stacklevel=2,
    )
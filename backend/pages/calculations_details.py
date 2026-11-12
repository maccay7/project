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

Alias handling note (fix):
  normalize_row() is now idempotent AND non-destructive. A single source
  column such as "Face Value" satisfies BOTH `face_value` and `principal`
  so money-market never reports `principal` missing when the workbook
  only had a "Face Value" heading. Every calculator reads via _canonical()
  which returns the first non-empty candidate, never inventing values.
"""

import math
import re
import warnings
import calendar
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
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
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


def parse_day_count_convention(convention: Any) -> Dict[str, Any]:
    """
    Parse day-count convention string and return metadata for calculation.

    Returns:
        Dict with keys:
        - 'convention': The normalized convention name
        - 'basis': The divisor (360 or 365)
        - 'is_30_360': Whether to use 30/360 calculation logic
        - 'is_european': Whether to use 30E/360 European variant
    """
    if convention is None:
        return {
            'convention': 'ACT/360',
            'basis': 360.0,
            'is_30_360': False,
            'is_european': False,
            'is_actual_actual': False,
        }

    conv_str = str(convention).upper().strip()
    # Normalize separators
    conv_str = conv_str.replace('-', '/').replace('_', '/')

    # Check for 30/360 variants
    if '30' in conv_str and '360' in conv_str:
        is_european = 'E' in conv_str or 'EURO' in conv_str
        return {
            'convention': '30E/360' if is_european else '30/360',
            'basis': 360.0,
            'is_30_360': True,
            'is_european': is_european,
            'is_actual_actual': False,
        }

    if ('ACT/ACT' in conv_str or 'ACTUAL/ACTUAL' in conv_str
            or 'ISDA' in conv_str or 'ICMA' in conv_str):
        return {
            'convention': 'ACT/ACT',
            'basis': 365.0,
            'is_30_360': False,
            'is_european': False,
            'is_actual_actual': True,
        }

    # Check for ACT/365
    if '365' in conv_str:
        return {
            'convention': 'ACT/365',
            'basis': 365.0,
            'is_30_360': False,
            'is_european': False,
            'is_actual_actual': False,
        }

    # Default to ACT/360
    return {
        'convention': 'ACT/360',
        'basis': 360.0,
        'is_30_360': False,
        'is_european': False,
        'is_actual_actual': False,
    }


def _next_business_day(d: date) -> date:
    d = d + timedelta(days=1)
    while d.weekday() >= 5:
        d = d + timedelta(days=1)
    return d


def _prev_business_day(d: date) -> date:
    while d.weekday() >= 5:
        d = d - timedelta(days=1)
    return d


def _infer_settlement_t1(item: Dict[str, Any]) -> None:
    """T+1 settlement inference: SettlementDate = ValuationDate + 1 business
    day. Modified Following — if the roll crosses into the next month, fall
    back to the last business day of the valuation month. Records the
    assumption on the row so it is surfaced, never silent."""
    if _canonical(item, "settlement_date") is not None:
        return
    val = parse_date(_canonical(item, "valuation_date"))
    if val is None:
        return
    settle = _next_business_day(val)
    if settle.month != val.month:
        settle = _prev_business_day(val)
    item["settlement_date"] = settle.isoformat()
    assumptions = item.get("_assumptions_applied")
    if not isinstance(assumptions, list):
        assumptions = []
        item["_assumptions_applied"] = assumptions
    assumptions.append(
        f"SettlementDate: {settle.isoformat()} (T+1 inferred from ValuationDate {val.isoformat()})"
    )


def _resolve_day_count(item: Dict[str, Any], instrument_type: str) -> Dict[str, Any]:
    """Day-count convention with explicit, flagged defaults:
    Actual/360 for Money Market and T-Bills, 30/360 for Bonds.
    A missing convention is never applied silently — the inference is
    recorded on the row's _assumptions_applied list."""
    raw = _canonical(item, "day_count_convention", "day_count")
    if raw is None or str(raw).strip() == "":
        default = "30/360" if instrument_type == "bonds" else "Actual/360"
        meta = parse_day_count_convention(default)
        meta["is_inferred"] = True
        assumptions = item.get("_assumptions_applied")
        if not isinstance(assumptions, list):
            assumptions = []
            item["_assumptions_applied"] = assumptions
        assumptions.append(
            f"DayCountConvention: {default} (auto-inferred for {instrument_type})"
        )
        return meta
    return parse_day_count_convention(raw)


def calculate_days_30_360(start_date: date, end_date: date, european: bool = False) -> int:
    """
    Calculate days between two dates using 30/360 convention.

    Standard 30/360 (NASD):
    - If end_date day is 31 and start_date day is not 30 or 31, set end_day to 30
    - If start_date day is 31, set start_day to 30
    - If start_date day is 30 and end_date day is 31, set end_day to 30

    European 30E/360:
    - If any day is 31, set it to 30
    - No adjustment for end-of-month

    Returns: Integer number of days
    """
    if not start_date or not end_date:
        raise ValueError("Both start_date and end_date are required for 30/360 calculation")

    start_year = start_date.year
    start_month = start_date.month
    start_day = start_date.day

    end_year = end_date.year
    end_month = end_date.month
    end_day = end_date.day

    if european:
        # 30E/360: set any day of 31 to 30
        if start_day == 31:
            start_day = 30
        if end_day == 31:
            end_day = 30
    else:
        # Standard 30/360 (NASD)
        if start_day == 31:
            start_day = 30
        if start_day == 30 and end_day == 31:
            end_day = 30
        elif end_day == 31 and start_day != 30:
            end_day = 30

    days = ((end_year - start_year) * 360 +
            (end_month - start_month) * 30 +
            (end_day - start_day))

    return days


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    day = min(value.day, last_day)
    if value.day == calendar.monthrange(value.year, value.month)[1]:
        day = last_day
    return date(year, month, day)


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
    next_coupon_d = parse_date(item.get("next_coupon_date"))
    if next_coupon_d:
        result["next_coupon_date"] = next_coupon_d.isoformat()
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
    - `display_label` is the human-readable name shown in the breakdown popup.
    - `display_inputs` maps internal dep names to display labels.
    """
    name: str
    formula: str
    dependencies: List[str]
    compute: Callable[[Dict[str, Any]], Any]
    unit: str = "number"
    extra_inputs: Dict[str, Any] = dc_field(default_factory=dict)
    display_label: Optional[str] = None
    display_inputs: Optional[Dict[str, str]] = None


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


_INPUT_LABELS = {
    "principal": "Principal",
    "face_value": "Face Value",
    "interest_rate": "Interest Rate (%)",
    "coupon_rate": "Coupon Rate (%)",
    "discount_rate": "Discount Rate (%)",
    "current_price": "Current Price",
    "purchase_price": "Purchase Price",
    "annual_coupon": "Annual Coupon",
    "coupon_payment": "Coupon per Period",
    "days_to_maturity": "Days to Maturity",
    "term_days": "Term (days)",
    "total_value": "Total Value",
    "interest_earned": "Interest Earned",
    "discount_amount": "Discount Amount",
    "discount_yield": "Discount Yield (%)",
    "effective_annual_rate": "Effective Annual Rate (%)",
    "effective_yield": "Effective Yield (%)",
    "bond_equivalent_yield": "Bond Equivalent Yield (%)",
    "money_market_yield": "Money-Market Yield (%)",
    "holding_period_yield": "Holding Period Yield (%)",
    "effective_annual_yield": "Effective Annual Yield (%)",
    "yield_to_maturity": "Yield to Maturity (%)",
    "current_yield": "Current Yield (%)",
    "price_per_100": "Price per 100",
    "days_accrued": "Days Accrued",
    "accrued_interest": "Accrued Interest",
    "macaulay_duration": "Macaulay Duration",
    "modified_duration": "Modified Duration",
    "convexity": "Convexity",
    "dv01": "DV01",
    "present_value": "Present Value",
    "fair_value": "Fair Value",
    "yield_curve_rate": "Yield Curve Rate (%)",
    "divisor": "Day Count Divisor",
    "discount_basis": "Day Count Basis",
    "frequency": "Coupon Frequency",
    "basis": "Day Count Basis",
    "period_start": "Period Start",
    "maturity_date": "Maturity Date",
    "valuation_date": "Valuation Date",
    "last_coupon_date": "Last Coupon Date",
    "next_coupon_date": "Next Coupon Date",
    "day_count_convention": "Day Count Convention",
    "compounding_method": "Compounding Method",
    "compounding_frequency": "Compounding Frequency",
}


def _friendly_inputs(step: CalcStep,
                     inputs_for_compute: Dict[str, Any]) -> Dict[str, Any]:
    """Return {label: value} pairs for the breakdown popup."""
    overrides = step.display_inputs or {}
    out: Dict[str, Any] = {}
    for k, v in inputs_for_compute.items():
        label = overrides.get(k) or _INPUT_LABELS.get(k, k)
        out[label] = _display_input(v)
    return out


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
    ordered list). Every step produces:

    derivations[name] = {
      formula, dependencies, inputs (internal keys), display_inputs (labels),
      result_raw, result, unit, status, error?
    }

    Failures are LOCAL: a divide-by-zero in `discount_yield` does not poison
    `bond_equivalent_yield` if the latter doesn't depend on the former.
    """
    cycle = _detect_cycles(steps)
    if cycle:
        return {
            "values": {},
            "derivations": {name: {
                "formula": "", "dependencies": [], "inputs": {},
                "display_inputs": {}, "result_raw": None, "result": None,
                "unit": "number", "status": "failed",
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
                "display_inputs": {},
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
                "display_inputs": {},
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
                "display_inputs": _friendly_inputs(step, inputs_for_compute),
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
                "display_inputs": _friendly_inputs(step, inputs_for_compute),
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
                "display_inputs": _friendly_inputs(step, inputs_for_compute),
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

        if raw_result is None:
            derivations[step.name] = {
                "formula": step.formula,
                "dependencies": step.dependencies,
                "inputs": {k: _display_input(v) for k, v in inputs_for_compute.items()},
                "display_inputs": _friendly_inputs(step, inputs_for_compute),
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
            "display_inputs": _friendly_inputs(step, inputs_for_compute),
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
    "clean_price": [
        "clean price", "cleanprice", "clean_price",
        "flat price", "flatprice", "flat_price",
        "quoted price", "quotedprice",
    ],
    "dirty_price": [
        "dirty price", "dirtyprice", "dirty_price",
        "full price", "fullprice", "full_price",
        "invoice price", "invoiceprice",
    ],
    "price_basis": [
        "price basis", "pricebasis", "price_basis",
    ],
    "compounding_method": [
        "compounding method", "compoundingmethod", "compounding_method",
        "interest method", "interest calculation method",
    ],
    "compounding_frequency": [
        "compounding frequency", "compoundingfrequency",
        "compounding_frequency", "periods per year",
    ],
    "carrying_value": [
        "carrying value", "carryingvalue", "carrying_value",
        "book value", "bookvalue", "book_value",
        "amortized cost", "amortizedcost",
    ],
    "market_value": [
        "market value", "marketvalue", "market_value",
        "fair market value", "fairmarketvalue",
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
    "discount_rate": [
        "discount rate", "discountrate", "discount_rate",
        "bank discount", "discount yield", "discountyield",
        "t-bill rate", "tbill rate", "tbillrate",
        "auction rate", "auctionrate", "discount",
    ],
    "yield": [
        "yield", "investor yield", "investoryield", "investor_yield",
        "investor rate", "investorrate",
        "ytm", "yield to maturity", "yieldtomaturity",
        "expected yield", "expectedyield",
    ],
    "investor_yield": [
        "investor yield", "investoryield", "investor_yield",
        "yield", "ytm", "yield to maturity",
    ],
    "auction_date": [
        "auction date", "auctiondate", "auction_date",
        "issue date", "issuedate", "issue_date",
        "settlement date", "settlementdate", "settlement_date",
    ],
    "purchase_price": [
        "purchase price", "purchaseprice", "purchase_price",
        "buy price", "buyprice", "buy_price",
        "acquisition price", "entry price",
        "price paid", "pricepaid", "price_paid",
        "issue price", "issueprice", "issue_price",
        "price", "current price", "currentprice", "current_price",
        "market price", "marketprice", "market_price",
    ],
    "settlement_date": [
        "settlement date", "settlementdate", "settlement_date",
        "trade date", "tradedate", "trade_date",
        "effective date", "effectivedate", "effective_date",
        "value date", "valuedate", "value_date",
    ],
    "days_accrued": [
        "days accrued", "daysaccrued", "days_accrued",
        "accrued days", "accrueddays", "accrued_days",
        "days since issue", "dayssinceissue",
    ],
    "accrued_interest": [
        "accrued interest", "accruedinterest", "accrued_interest",
        "interest accrued", "interestaccrued",
    ],
    "discount_amount": [
        "discount amount", "discountamount", "discount_amount",
        "discount", "bank discount",
    ],
    "discount_yield": [
        "discount yield", "discountyield", "discount_yield",
        "money market yield", "moneymarketyield",
    ],
    "money_market_yield": [
        "money market yield", "moneymarketyield", "money_market_yield",
        "mm yield", "mmyield",
    ],
    "holding_period_yield": [
        "holding period yield", "holdingperiodyield", "holding_period_yield",
        "hpy", "holding yield",
    ],
    "carrying_value": [
        "carrying value", "carryingvalue", "carrying_value",
        "book value", "bookvalue", "book_value",
        "amortized cost", "amortizedcost",
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
        "origination date", "effective date", "effectivedate", "effective_date",
        "trade date", "tradedate", "trade_date",
    ],
    "last_coupon_date": [
        "last coupon date", "lastcoupondate", "last_coupon_date",
        "previous coupon date", "previouscoupondate", "previous_coupon_date",
    ],
    "next_coupon_date": [
        "next coupon date", "nextcoupondate", "next_coupon_date",
        "upcoming coupon date", "following coupon date",
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


_EXACT_ALIAS_LOOKUPS = {
    target: frozenset(alias.lower().strip() for alias in aliases)
    for target, aliases in SPECIFIC_ALIASES.items()
}
_TOKEN_ALIAS_LOOKUPS = {
    target: tuple(
        frozenset(tokens)
        for tokens in (_tokenize(alias) for alias in aliases)
        if len(tokens) >= 2
    )
    for target, aliases in SPECIFIC_ALIASES.items()
}


def normalize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Idempotent alias expansion.

    Every source key is mapped to ALL canonical targets it satisfies.
    No source key is 'consumed' — a single 'Face Value' column can
    legitimately satisfy both `face_value` and `principal`. This is the
    core fix: previously the first matching alias won and burned the
    column, so `principal` (required by money-market) was reported
    missing even though the data was present.
    """
    if not isinstance(row, dict):
        return {}
    normalized: Dict[str, Any] = {}
    source_entries = [
        (str(key), str(key).lower().strip(), _tokenize(key), value)
        for key, value in row.items()
    ]

    # First pass: exact (case-insensitive) matches.
    for target in SPECIFIC_ALIASES:
        for src_key, normalized_key, _, src_val in source_entries:
            if normalized_key in _EXACT_ALIAS_LOOKUPS[target]:
                unwrapped = _unwrap_cell(src_val)
                if unwrapped is not None:
                    normalized[target] = unwrapped
                break  # stop at first match per target; do not consume src_key

    # Second pass: token-subset matches for multi-token aliases.
    for target in SPECIFIC_ALIASES:
        if target in normalized:
            continue
        for alias_tokens in _TOKEN_ALIAS_LOOKUPS[target]:
            for src_key, _, source_tokens, src_val in source_entries:
                if alias_tokens.issubset(source_tokens):
                    unwrapped = _unwrap_cell(src_val)
                    if unwrapped is not None:
                        normalized[target] = unwrapped
                        break
            if target in normalized:
                break

    # Third pass: carry through unmapped originals (for display + source tracking).
    for key, value in row.items():
        unwrapped = _unwrap_cell(value)
        if unwrapped is not None and key not in normalized:
            normalized[key] = unwrapped
    return normalized


def _canonical(row: Dict[str, Any], *candidates, as_float=False):
    """Read the first non-empty value among *candidates* from an
    already-normalized row. Never invents a value; returns None if
    every candidate is truly absent/empty."""
    for key in candidates:
        if key not in row:
            continue
        raw = row.get(key)
        if raw is None or raw == "":
            continue
        if as_float:
            v = safe_float(raw)
            if v is not None:
                return v
            continue
        return raw
    return None


def _canonical_pct(row: Dict[str, Any], *candidates):
    for key in candidates:
        if key not in row:
            continue
        raw = row.get(key)
        if raw is None or raw == "":
            continue
        v = parse_percentage(raw)
        if v is not None:
            return v
    return None


def _normalize_currency(value: Any) -> Optional[str]:
    if value is None:
        return None
    currency = str(value).strip().upper()
    return currency or None


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
def validate_row(
    row: Dict[str, Any],
    instrument_type: str,
    *,
    normalized: bool = False,
) -> Dict[str, Any]:
    if not isinstance(row, dict):
        return {"can_calculate": False,
                "missing_fields": ["row is not a dictionary"],
                "invalid_fields": [], "detected_fields": {},
                "normalized_row": {}, "all_source_keys": []}

    norm = row if normalized else normalize_row(row)
    missing: List[str] = []
    invalid: List[tuple] = []
    detected: Dict[str, Any] = {}

    def note(field):
        if norm.get(field) is not None:
            detected[field] = norm.get(field)

    if instrument_type == "bonds":
        face = _canonical(norm, "face_value", "principal", as_float=True)
        note("face_value"); note("principal")
        if face is None:
            missing.append("face_value (aliases: Face Value, Principal, Par Value, Notional, Amount)")

        cr = _canonical_pct(norm, "coupon_rate", "interest_rate")
        note("coupon_rate"); note("interest_rate")
        if cr is None:
            missing.append("coupon_rate (aliases: Coupon Rate, Coupon, Interest Rate, Rate)")

        price = _canonical(
            norm, "price", "purchase_price", "current_price", "market_value",
            "present_value", "fair_value", as_float=True,
        )
        ytm = _canonical_pct(norm, "yield", "yield_to_maturity")
        note("price"); note("purchase_price"); note("current_price")
        note("yield"); note("yield_to_maturity")
        if price is None and ytm is None:
            missing.append("price or yield_to_maturity")

        years = None
        note("years_to_maturity"); note("valuation_date"); note("maturity_date"); note("issue_date")
        period_start = (parse_date(_canonical(norm, "valuation_date"))
                        or parse_date(_canonical(norm, "issue_date")))
        mat_d = parse_date(_canonical(norm, "maturity_date"))
        if period_start and mat_d and mat_d >= period_start:
            years = (mat_d - period_start).days / 365.0
        elif not (period_start and mat_d):
            years = _canonical(norm, "years_to_maturity", as_float=True)
            if years is None:
                d2m = _canonical(norm, "days_to_maturity", "term_days", as_float=True)
                if d2m is not None:
                    years = d2m / 365.0
        if years is None or years <= 0:
            missing.append("years_to_maturity (or Valuation Date + Maturity Date)")

        note("coupon_frequency"); note("frequency")
        coupon_frequency = parse_frequency(
            _canonical(norm, "coupon_frequency", "frequency")
        )
        if coupon_frequency is None:
            missing.append(
                "coupon_frequency (required for coupon-period and yield calculations)"
            )
        elif coupon_frequency <= 0 or coupon_frequency > 365:
            invalid.append(("coupon_frequency", "must be between 1 and 365"))

        if face is not None and face <= 0:
            invalid.append(("face_value", "must be > 0"))

        val_d = parse_date(_canonical(norm, "valuation_date"))
        mat_d = parse_date(_canonical(norm, "maturity_date"))
        iss_d = parse_date(_canonical(norm, "issue_date"))
        if val_d and mat_d and val_d > mat_d:
            invalid.append(("valuation_date", "must be on or before maturity_date"))
        if iss_d and mat_d and iss_d > mat_d:
            invalid.append(("issue_date", "must be on or before maturity_date"))
        last_coupon_d = (
            parse_date(_canonical(norm, "last_coupon_date")) or iss_d
        )
        accrual_date = val_d or parse_date(
            _canonical(norm, "settlement_date")
        )
        if (last_coupon_d and accrual_date
                and _canonical(norm, "day_count_convention", "day_count") is None):
            missing.append(
                "day_count_convention (required for accrued interest)"
            )

    elif instrument_type == "money-market":
        principal = _canonical(norm, "principal", "face_value", "amount", as_float=True)
        note("principal"); note("face_value"); note("amount")
        if principal is None:
            missing.append("principal (aliases: Principal, Principle, Face Value, Amount, Notional)")
        elif principal <= 0:
            invalid.append(("principal", "must be > 0"))

        # A supplied price can also determine the discount.
        rate = _canonical_pct(norm, "interest_rate", "rate", "coupon_rate")
        discount_rate = _canonical_pct(norm, "discount_rate")
        note("interest_rate"); note("rate"); note("discount_rate")
        purchase_price = _canonical(
            norm, "purchase_price", "current_price", "price", as_float=True
        )
        if rate is None and discount_rate is None and purchase_price is None:
            missing.append("interest_rate OR discount_rate (aliases: Interest Rate, Rate, Coupon, Discount Rate)")

        note("purchase_price"); note("price")
        if purchase_price is not None and purchase_price <= 0:
            invalid.append(("purchase_price", "must be > 0"))

        val_d = parse_date(_canonical(norm, "valuation_date"))
        set_d = parse_date(_canonical(norm, "settlement_date"))
        iss_d = parse_date(_canonical(norm, "issue_date"))
        mat_d = parse_date(_canonical(norm, "maturity_date"))
        period_start = val_d or set_d or iss_d
        days = None
        if period_start and mat_d and mat_d >= period_start:
            days = (mat_d - period_start).days
        if days is None:
            days = _canonical(norm, "term_days", "days_to_maturity", as_float=True)
        note("term_days"); note("days_to_maturity")
        note("valuation_date"); note("maturity_date"); note("issue_date"); note("settlement_date")
        if days is None or days <= 0:
            missing.append("term_days (or Valuation Date + Maturity Date)")

        if val_d and mat_d and val_d > mat_d:
            invalid.append(("valuation_date", "must be on or before maturity_date"))
        if iss_d and mat_d and iss_d > mat_d:
            invalid.append(("issue_date", "must be on or before maturity_date"))
        if set_d and mat_d and set_d > mat_d:
            invalid.append(("settlement_date", "must be on or before maturity_date"))

    else:  # tbills
        face = _canonical(norm, "face_value", "principal", as_float=True)
        note("face_value"); note("principal")
        if face is None:
            missing.append("face_value (aliases: Face Value, Principal, Par Value, Amount, Notional)")
        elif face <= 0:
            invalid.append(("face_value", "must be > 0"))

        # Accept either discount_rate (discount-based) OR yield (yield-based) OR purchase_price
        discount_rate = _canonical_pct(norm, "discount_rate")
        yield_rate = _canonical_pct(norm, "yield", "yield_to_maturity", "investor_yield")
        purchase_price = _canonical(norm, "purchase_price", "current_price", "price", as_float=True)
        note("discount_rate"); note("yield"); note("yield_to_maturity"); note("investor_yield")
        note("purchase_price"); note("price")

        if discount_rate is None and yield_rate is None and purchase_price is None:
            missing.append("discount_rate OR yield (investor yield) OR purchase_price (aliases: Discount Rate, Yield, YTM, Investor Yield, Price)")
        if purchase_price is not None and purchase_price <= 0:
            invalid.append(("purchase_price", "must be > 0"))

        val_d = parse_date(_canonical(norm, "valuation_date"))
        set_d = parse_date(_canonical(norm, "settlement_date"))
        auc_d = parse_date(_canonical(norm, "auction_date", "issue_date"))
        iss_d = parse_date(_canonical(norm, "issue_date"))
        mat_d = parse_date(_canonical(norm, "maturity_date"))
        period_start = val_d or set_d or auc_d
        days = None
        if period_start and mat_d and mat_d >= period_start:
            days = (mat_d - period_start).days
        if days is None:
            days = _canonical(norm, "term_days", "days_to_maturity", as_float=True)
        note("term_days"); note("days_to_maturity")
        note("valuation_date"); note("maturity_date"); note("issue_date"); note("auction_date"); note("settlement_date")
        if days is None or days <= 0:
            missing.append("term_days (or Valuation Date + Maturity Date)")

        if val_d and mat_d and val_d > mat_d:
            invalid.append(("valuation_date", "must be on or before maturity_date"))
        if iss_d and mat_d and iss_d > mat_d:
            invalid.append(("issue_date", "must be on or before maturity_date"))
        if auc_d and mat_d and auc_d > mat_d:
            invalid.append(("auction_date", "must be on or before maturity_date"))
        if set_d and mat_d and set_d > mat_d:
            invalid.append(("settlement_date", "must be on or before maturity_date"))

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
    raw = None
    price_basis = None
    for key, basis in (
        ("clean_price", "clean"),
        ("dirty_price", "dirty"),
        ("price", None),
        ("purchase_price", None),
        ("current_price", None),
        ("present_value", None),
        ("fair_value", "dirty"),
        ("market_value", "dirty"),
    ):
        value = item.get(key)
        if value is not None and value != "":
            raw = value
            price_basis = basis
            break
    if raw is None:
        return None, None

    explicit_basis = _canonical(item, "price_basis")
    if explicit_basis is not None:
        normalized_basis = str(explicit_basis).strip().lower()
        if normalized_basis in ("clean", "dirty"):
            price_basis = normalized_basis

    value = str(raw).strip()
    if value.endswith("%"):
        percentage = parse_percentage(raw)
        if percentage is not None and face is not None:
            return face * percentage, price_basis or "dirty"
        return None, price_basis
    price = safe_float(raw)
    if price is None:
        return None, price_basis
    if face is not None and face >= 100 and 0 < price < face * 0.3:
        price *= face / 100.0
    return price, price_basis or "dirty"


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
    _infer_settlement_t1(item)

    principal = _canonical(item, "principal", "face_value", "amount", as_float=True)
    rate_frac = _canonical_pct(item, "interest_rate", "rate", "coupon_rate")
    discount_rate_frac = _canonical_pct(item, "discount_rate")
    purchase_price_in = _canonical(item, "purchase_price", "current_price", "price", as_float=True)
    currency = _normalize_currency(
        _canonical(item, "currency", "ccy", "currency_code")
    )

    day_count_meta = _resolve_day_count(item, "money-market")
    day_count = day_count_meta['convention']
    divisor = day_count_meta['basis']
    is_30_360 = day_count_meta['is_30_360']
    is_european = day_count_meta['is_european']
    raw_compounding_method = _canonical(item, "compounding_method")
    raw_compounding_frequency = _canonical(item, "compounding_frequency")
    frequency_aliases = {
        "daily": 365, "weekly": 52, "monthly": 12, "quarterly": 4,
        "semiannual": 2, "semi annual": 2,
        "annual": 1, "annually": 1, "yearly": 1,
    }

    def _parse_compounding_frequency(value):
        if value is None:
            return None
        text = str(value).strip().lower().replace("-", " ")
        if text in frequency_aliases:
            return frequency_aliases[text]
        parsed = safe_float(value)
        if parsed is not None and parsed.is_integer() and parsed > 0:
            return int(parsed)
        return None

    compounding_frequency = _parse_compounding_frequency(
        raw_compounding_frequency
    )
    method_text = str(raw_compounding_method or "").strip().lower()
    normalized_method = method_text.replace("-", " ").replace("_", " ")
    compounding_error = None
    if not method_text and compounding_frequency is None:
        compounding_method = "simple"
    elif "continuous" in normalized_method:
        compounding_method = "continuous"
    elif "effective" in normalized_method and (
        "annual" in normalized_method or "year" in normalized_method
    ):
        compounding_method = "effective_annual"
    elif "simple" in normalized_method or "add on" in normalized_method:
        compounding_method = "simple"
    elif (
        "compound" in normalized_method
        or compounding_frequency is not None
        or normalized_method in frequency_aliases
    ):
        compounding_method = "compound"
        if compounding_frequency is None:
            compounding_frequency = next(
                (
                    frequency for alias, frequency in frequency_aliases.items()
                    if alias in normalized_method
                ),
                None,
            )
        if compounding_frequency is None:
            compounding_error = "compounding_frequency is required"
    else:
        compounding_method = "invalid"
        compounding_error = "unsupported compounding_method"
    if rate_frac is None:
        compounding_error = None

    val_d = parse_date(_canonical(item, "valuation_date"))
    mat_d = parse_date(_canonical(item, "maturity_date"))
    set_d = parse_date(_canonical(item, "settlement_date"))
    period_start = val_d or set_d or parse_date(_canonical(item, "issue_date"))

    has_date_range = bool(period_start and mat_d)
    raw_days = None
    if has_date_range and mat_d >= period_start:
        if is_30_360:
            raw_days = float(calculate_days_30_360(period_start, mat_d, is_european))
        else:
            raw_days = float((mat_d - period_start).days)
    elif not has_date_range:
        raw_days = _canonical(item, "term_days", "days_to_maturity", as_float=True)

    # Calculate days from issue to settlement for accrued interest
    raw_days_accrued = None
    issue_d = parse_date(_canonical(item, "issue_date"))
    if issue_d and set_d and set_d >= issue_d:
        if is_30_360:
            raw_days_accrued = float(calculate_days_30_360(issue_d, set_d, is_european))
        else:
            raw_days_accrued = float((set_d - issue_d).days)

    rate_pct = (rate_frac * 100.0) if rate_frac is not None else None
    discount_rate_pct = (discount_rate_frac * 100.0) if discount_rate_frac is not None else None

    result: Dict[str, Any] = {
        "instrument_type": "money-market",
        "principal": round_money(principal),
        "interest_rate": _rate(rate_pct) if rate_pct is not None else None,
        "discount_rate": _rate(discount_rate_pct) if discount_rate_pct is not None else None,
        "day_count_convention": day_count,
        "compounding_method": (
            compounding_method if compounding_method != "invalid" else None
        ),
        "compounding_frequency": compounding_frequency,
        "currency": currency,
    }
    name = _extract_instrument_name(item)
    if name:
        result["instrument_name"] = name
    _add_input_dates(result, val_d, mat_d, item)

    # Conflicting-input detection (purchase price wins if both provided)
    if (purchase_price_in is not None and discount_rate_frac is not None
            and principal is not None and raw_days is not None and raw_days > 0):
        implied = ((principal - purchase_price_in) / principal
                   * divisor / raw_days)
        if abs(implied - discount_rate_frac) > 1e-6:
            result["warning"] = (
                f"Provided discount_rate={discount_rate_frac * 100:.4f}% and "
                f"purchase_price={purchase_price_in:.2f} are inconsistent "
                f"(price implies {implied * 100:.4f}%). "
                "purchase_price takes precedence."
            )

    if raw_days is not None:
        days_deps = []
        days_compute = (lambda inp, _raw=raw_days: round_time(_raw))
    else:
        days_deps = ["period_start", "maturity_date"]
        def days_compute(inp):
            v = parse_date(inp["period_start"])
            m = parse_date(inp["maturity_date"])
            d = (calculate_days_30_360(v, m, is_european)
                 if is_30_360 else (m - v).days)
            if d <= 0:
                raise ValueError(f"Maturity date must be after period start (got {d} days)")
            return d

    if raw_days_accrued is not None:
        accrued_days_deps = []
        accrued_days_compute = (lambda inp, _raw=raw_days_accrued: round_time(_raw))
    else:
        # Skip accrued interest calculation if dates not provided
        accrued_days_deps = []
        accrued_days_compute = (lambda inp: None)

    def _calc_interest(inp):
        if rate_pct is not None:
            if compounding_error:
                raise CalculationSkipped(compounding_error)
            rate = rate_frac
            year_fraction = inp["days_to_maturity"] / divisor
            if compounding_method == "simple":
                growth = rate * year_fraction
            elif compounding_method == "effective_annual":
                growth = (1 + rate) ** year_fraction - 1
            elif compounding_method == "continuous":
                growth = math.exp(rate * year_fraction) - 1
            else:
                if compounding_frequency is None:
                    raise CalculationSkipped(
                        "compounding_frequency is required"
                    )
                period_rate = rate / compounding_frequency
                if period_rate <= -1:
                    raise ValueError("compounding rate is out of range")
                growth = (
                    (1 + period_rate)
                    ** (compounding_frequency * year_fraction) - 1
                )
            return inp["principal"] * growth
        if discount_rate_frac is not None or purchase_price_in is not None:
            return inp["principal"] - inp["purchase_price"]
        raise CalculationSkipped("interest_rate or discount_rate is required")

    def _calc_accrued_interest(inp):
        # Accrued interest from issue to settlement
        if inp.get("days_accrued") is None:
            raise CalculationSkipped("issue_date and settlement_date are required")
        if inp.get("interest_rate") is None:
            raise CalculationSkipped("interest_rate is required for accrued interest")
        if compounding_error:
            raise CalculationSkipped(compounding_error)
        year_fraction = inp["days_accrued"] / divisor
        if compounding_method == "simple":
            growth = rate_frac * year_fraction
        elif compounding_method == "effective_annual":
            growth = (1 + rate_frac) ** year_fraction - 1
        elif compounding_method == "continuous":
            growth = math.exp(rate_frac * year_fraction) - 1
        elif compounding_frequency:
            growth = (
                (1 + rate_frac / compounding_frequency)
                ** (compounding_frequency * year_fraction) - 1
            )
        else:
            raise CalculationSkipped("compounding_frequency is required")
        return inp["principal"] * growth

    def _calc_total(inp):
        if rate_pct is not None:
            return inp["principal"] + inp["interest_earned"]
        if discount_rate_frac is not None or purchase_price_in is not None:
            return inp["principal"]
        raise CalculationSkipped("an applicable rate or purchase price is required")

    def _calc_purchase_price(inp):
        if purchase_price_in is not None:
            return purchase_price_in
        if discount_rate_frac is not None:
            return (inp["principal"]
                    * (1.0 - discount_rate_frac
                       * inp["days_to_maturity"] / divisor))
        if rate_frac is not None:
            return inp["principal"]
        raise CalculationSkipped("purchase_price or an applicable rate is required")

    def _calc_discount_amount(inp):
        # Discount amount = principal - purchase price
        return inp["principal"] - inp["purchase_price"]

    def _calc_discount_rate_from_price(inp):
        if discount_rate_frac is None and purchase_price_in is None:
            raise CalculationSkipped(
                "discount_rate or an observed purchase_price is required"
            )
        if inp["purchase_price"] == 0:
            raise ValueError("purchase_price is zero")
        return ((inp["principal"] - inp["purchase_price"])
                / inp["principal"]
                * (divisor / inp["days_to_maturity"]) * 100.0)

    def _calc_discount_yield(inp):
        if discount_rate_frac is None and purchase_price_in is None:
            raise CalculationSkipped(
                "discount_rate or an observed purchase_price is required"
            )
        return ((inp["discount_amount"] / inp["principal"])
                * (divisor / inp["days_to_maturity"]) * 100.0)

    def _calc_money_market_yield(inp):
        # Annualize earned interest over the invested amount.
        if inp["purchase_price"] == 0:
            raise ValueError("purchase_price is zero")
        return ((inp["interest_earned"] / inp["purchase_price"])
                * (divisor / inp["days_to_maturity"]) * 100.0)

    def _calc_bond_equivalent_yield(inp):
        if inp["purchase_price"] <= 0:
            raise ValueError("purchase_price must be > 0")
        return ((inp["interest_earned"] / inp["purchase_price"])
                * (365.0 / inp["days_to_maturity"]) * 100.0)

    def _calc_holding_period_yield(inp):
        # Holding period yield = (maturity_value - purchase_price) / purchase_price × 100
        if inp["purchase_price"] == 0:
            raise ValueError("purchase_price is zero")
        return ((inp["total_value"] - inp["purchase_price"])
                / inp["purchase_price"] * 100.0)

    def _calc_eff_annual(inp):
        if inp["purchase_price"] <= 0:
            raise ValueError("purchase_price must be > 0")
        if inp["total_value"] < 0:
            raise ValueError("total_value cannot be negative")
        return ((inp["total_value"] / inp["purchase_price"])
                ** (365.0 / inp["days_to_maturity"]) - 1.0) * 100.0

    def _calc_present_value(inp):
        return inp["purchase_price"]

    def _calc_carrying_value(inp):
        # Carrying value = purchase price + accrued interest
        return inp["purchase_price"] + inp["accrued_interest"]

    purchase_price_dependencies = (
        [] if purchase_price_in is not None else
        ["principal", "days_to_maturity"] if discount_rate_frac is not None else
        ["principal"]
    )
    steps = [
        CalcStep(
            name="days_to_maturity",
            formula="term_days input, else maturity_date − valuation_date",
            dependencies=days_deps,
            compute=days_compute,
            unit="days",
            extra_inputs={"day_count_convention": day_count},
            display_label="Days to Maturity",
        ),
        CalcStep(
            name="days_accrued",
            formula="settlement_date − issue_date",
            dependencies=accrued_days_deps,
            compute=accrued_days_compute,
            unit="days",
            extra_inputs={"day_count_convention": day_count},
            display_label="Days Accrued",
        ),
        CalcStep(
            name="purchase_price",
            formula="input price, or principal × (1 − discount_rate × days/divisor)",
            dependencies=purchase_price_dependencies,
            compute=_calc_purchase_price,
            unit="currency",
            extra_inputs={"divisor": divisor},
            display_label="Purchase Price",
        ),
        CalcStep(
            name="discount_amount",
            formula="principal − purchase_price",
            dependencies=["principal", "purchase_price"],
            compute=_calc_discount_amount,
            unit="currency",
            display_label="Discount Amount",
        ),
        CalcStep(
            name="interest_earned",
            formula=(
                "interest accrual using stated method, rate, term, and day count"
            ),
            dependencies=["principal", "days_to_maturity", "purchase_price"],
            compute=_calc_interest,
            unit="currency",
            extra_inputs={
                "divisor": divisor,
                "interest_rate": rate_pct,
                "compounding_method": compounding_method,
                "compounding_frequency": compounding_frequency,
            },
            display_label="Interest Earned",
        ),
        CalcStep(
            name="accrued_interest",
            formula="principal × (interest_rate/100) × (days_accrued / divisor)",
            dependencies=["principal", "interest_rate", "days_accrued"],
            compute=_calc_accrued_interest,
            unit="currency",
            extra_inputs={
                "divisor": divisor,
                "compounding_method": compounding_method,
                "compounding_frequency": compounding_frequency,
            },
            display_label="Accrued Interest",
        ),
        CalcStep(
            name="total_value",
            formula="principal + interest_earned",
            dependencies=["principal", "interest_earned"],
            compute=_calc_total,
            unit="currency",
            display_label="Total Value / Maturity Value",
        ),
        CalcStep(
            name="discount_rate",
            formula="(principal − purchase_price) / principal × (divisor/days) × 100",
            dependencies=["principal", "purchase_price", "days_to_maturity"],
            compute=_calc_discount_rate_from_price,
            unit="percent",
            extra_inputs={"divisor": divisor},
            display_label="Discount Rate",
        ),
        CalcStep(
            name="discount_yield",
            formula="(discount_amount / principal) × (divisor / days) × 100",
            dependencies=["discount_amount", "principal", "days_to_maturity"],
            compute=_calc_discount_yield,
            unit="percent",
            extra_inputs={"divisor": divisor},
            display_label="Discount Yield",
        ),
        CalcStep(
            name="money_market_yield",
            formula="(interest_earned / purchase_price) × (divisor / days) × 100",
            dependencies=["interest_earned", "purchase_price", "days_to_maturity"],
            compute=_calc_money_market_yield,
            unit="percent",
            extra_inputs={"divisor": divisor},
            display_label="Money Market Yield",
        ),
        CalcStep(
            name="holding_period_yield",
            formula="(total_value − purchase_price) / purchase_price × 100",
            dependencies=["total_value", "purchase_price"],
            compute=_calc_holding_period_yield,
            unit="percent",
            display_label="Holding Period Yield",
        ),
        CalcStep(
            name="effective_annual_rate",
            formula="((total_value / purchase_price)^(365/days) − 1) × 100",
            dependencies=["total_value", "purchase_price", "days_to_maturity"],
            compute=_calc_eff_annual,
            unit="percent",
            display_label="Effective Annual Rate",
        ),
        CalcStep(
            name="bond_equivalent_yield",
            formula="(interest_earned / purchase_price) × (365 / days) × 100",
            dependencies=["interest_earned", "purchase_price", "days_to_maturity"],
            compute=_calc_bond_equivalent_yield,
            unit="percent",
            display_label="Bond Equivalent Yield",
        ),
        CalcStep(
            name="effective_yield",
            formula="((total_value / purchase_price)^(365/days) − 1) × 100",
            dependencies=["total_value", "purchase_price", "days_to_maturity"],
            compute=_calc_eff_annual,
            unit="percent",
            display_label="Effective Yield",
        ),
        CalcStep(
            name="present_value",
            formula="purchase_price (or principal if add-on rate)",
            dependencies=["purchase_price"],
            compute=_calc_present_value,
            unit="currency",
            display_label="Present Value",
        ),
        CalcStep(
            name="carrying_value",
            formula="purchase_price + accrued_interest",
            dependencies=["purchase_price", "accrued_interest"],
            compute=_calc_carrying_value,
            unit="currency",
            display_label="Carrying Value",
        ),
        CalcStep(
            name="fair_value",
            formula="principal + interest_earned",
            dependencies=["principal", "interest_earned"],
            compute=_calc_total,
            unit="currency",
            display_label="Fair Value",
        ),
    ]

    available = {
        "principal": principal,
        "interest_rate": rate_pct,
        "discount_rate": discount_rate_pct,
        "period_start": period_start,
        "maturity_date": mat_d,
        "issue_date": issue_d,
        "settlement_date": set_d,
    }

    chain = execute_chain(steps, available)
    values = chain["values"]
    hard_failures = [e for e in chain["errors"]
                     if e["reason"] in ("missing_prerequisites",
                                        "circular_dependency",
                                        "compute_error",
                                        "division_by_zero")]
    if "days_to_maturity" in values:
        result["term_days"] = round_time(values["days_to_maturity"])
    if "days_accrued" in values:
        result["days_accrued"] = round_time(values["days_accrued"])
    if "purchase_price" in values:
        result["purchase_price"] = round_money(values["purchase_price"])
    if "discount_amount" in values:
        result["discount_amount"] = round_money(values["discount_amount"])
    if "interest_earned" in values:
        result["interest_earned"] = round_money(values["interest_earned"])
        result["total_interest"] = result["interest_earned"]
    if "accrued_interest" in values:
        result["accrued_interest"] = round_money(values["accrued_interest"])
    if "total_value" in values:
        result["total_value"] = round_money(values["total_value"])
        result["maturity_value"] = result["total_value"]
        result["fair_value"] = result["total_value"]
    for k in ("discount_rate", "discount_yield", "money_market_yield",
              "holding_period_yield", "effective_annual_rate",
              "bond_equivalent_yield", "effective_yield"):
        if k in values:
            result[k] = _rate(values[k])
    if "effective_annual_rate" in result:
        result["annual_yield"] = result["effective_annual_rate"]
    if "present_value" in values:
        result["present_value"] = round_money(values["present_value"])
    if "carrying_value" in values:
        result["carrying_value"] = round_money(values["carrying_value"])
    result["yield_curve_rate"] = _benchmark_to_percent(benchmark_yield)

    # Expose avg_rate on single rows so the KPI card always finds one.
    if result.get("interest_rate") is not None:
        result["avg_rate"] = result["interest_rate"]
    elif result.get("discount_rate") is not None:
        result["avg_rate"] = result["discount_rate"]

    validation = validate_row(item, "money-market", normalized=True)
    if validation["missing_fields"]:
        result["missing_fields"] = list(validation["missing_fields"])
    if compounding_error == "compounding_frequency is required":
        result.setdefault("missing_fields", []).append("compounding_frequency")
    if validation["invalid_fields"]:
        result["invalid_fields"] = list(validation["invalid_fields"])
    if compounding_error == "unsupported compounding_method":
        result.setdefault("invalid_fields", []).append("compounding_method")

    if (hard_failures or validation["missing_fields"]
            or validation["invalid_fields"] or compounding_error):
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
    _infer_settlement_t1(item)

    face = _canonical(item, "face_value", "principal", as_float=True)
    purchase_price_in = _canonical(item, "purchase_price", "current_price", "price", as_float=True)
    discount_rate_in_frac = _canonical_pct(item, "discount_rate")
    # Support yield-based pricing (investor yield) as distinct from discount rate
    yield_rate_in_frac = _canonical_pct(item, "yield", "yield_to_maturity", "investor_yield")
    currency = _normalize_currency(
        _canonical(item, "currency", "ccy", "currency_code")
    )
    day_count_meta = _resolve_day_count(item, "tbills")
    day_count = day_count_meta['convention']
    discount_basis = day_count_meta['basis']
    is_30_360 = day_count_meta['is_30_360']
    is_european = day_count_meta['is_european']

    val_d = parse_date(_canonical(item, "valuation_date"))
    mat_d = parse_date(_canonical(item, "maturity_date"))
    set_d = parse_date(_canonical(item, "settlement_date"))
    auction_d = parse_date(_canonical(item, "auction_date", "issue_date"))
    period_start = val_d or set_d or auction_d
    has_date_range = bool(period_start and mat_d)
    raw_days = None
    if has_date_range and mat_d >= period_start:
        if is_30_360:
            raw_days = float(calculate_days_30_360(period_start, mat_d, is_european))
        else:
            raw_days = float((mat_d - period_start).days)
    elif not has_date_range:
        raw_days = _canonical(item, "term_days", "days_to_maturity", as_float=True)

    discount_rate_pct_in = (discount_rate_in_frac * 100.0
                            if discount_rate_in_frac is not None else None)
    yield_rate_pct_in = (yield_rate_in_frac * 100.0
                         if yield_rate_in_frac is not None else None)

    result: Dict[str, Any] = {
        "instrument_type": "tbills",
        "face_value": round_money(face),
        "day_count_convention": day_count,
        "currency": currency,
    }
    name = _extract_instrument_name(item)
    if name:
        result["instrument_name"] = name
    _add_input_dates(result, val_d, mat_d, item)

    # Conflicting-input detection (price wins for discount-rate pricing)
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

    # Conflicting-input detection for yield-based pricing
    if (purchase_price_in is not None and yield_rate_in_frac is not None
            and face is not None and raw_days is not None and raw_days > 0):
        # For yield-based pricing: price = face / (1 + yield * days / 365)
        implied_price = face / (1.0 + yield_rate_in_frac * raw_days / 365.0)
        if abs(implied_price - purchase_price_in) > 0.01:
            result["warning"] = (
                f"Provided yield={yield_rate_in_frac * 100:.4f}% and "
                f"purchase_price={purchase_price_in:.2f} are inconsistent "
                f"(yield implies price={implied_price:.2f}). "
                "purchase_price takes precedence."
            )

    if raw_days is not None:
        days_deps = []
        days_compute = (lambda inp, _raw=raw_days: round_time(_raw))
    else:
        days_deps = ["period_start", "maturity_date"]
        def days_compute(inp):
            v = parse_date(inp["period_start"])
            m = parse_date(inp["maturity_date"])
            d = (calculate_days_30_360(v, m, is_european)
                 if is_30_360 else (m - v).days)
            if d <= 0:
                raise ValueError(f"Maturity date must be after period start (got {d} days)")
            return d

    def _establish_price_from_discount(inp):
        """Calculate price from discount rate (discount-based pricing)."""
        if purchase_price_in is not None:
            return purchase_price_in
        if discount_rate_in_frac is not None:
            return (inp["face_value"]
                    * (1.0 - discount_rate_in_frac
                       * inp["days_to_maturity"] / discount_basis))
        raise ValueError("Need purchase_price or discount_rate for discount-based pricing")

    def _establish_price_from_yield(inp):
        """Calculate price from yield rate (yield-based pricing)."""
        if purchase_price_in is not None:
            return purchase_price_in
        if yield_rate_in_frac is not None:
            # Yield-based pricing: price = face / (1 + yield * days / 365)
            return inp["face_value"] / (1.0 + yield_rate_in_frac * inp["days_to_maturity"] / 365.0)
        # Fall back to discount-based if yield not provided
        return _establish_price_from_discount(inp)

    def _discount_amount(inp):
        return inp["face_value"] - inp["purchase_price"]

    def _discount_rate_from_price(inp):
        """Calculate discount rate from price (discount-based)."""
        return ((inp["face_value"] - inp["purchase_price"])
                / inp["face_value"]
                * (discount_basis / inp["days_to_maturity"]) * 100.0)

    def _yield_from_price(inp):
        """Calculate investor yield from price (yield-based)."""
        if inp["purchase_price"] == 0:
            raise ValueError("purchase_price is zero")
        return ((inp["face_value"] / inp["purchase_price"] - 1.0)
                * (365.0 / inp["days_to_maturity"]) * 100.0)

    def _mm_yield(inp):
        """Money market yield = (discount / price) × (basis / days) × 100."""
        if inp["purchase_price"] == 0:
            raise ValueError("purchase_price is zero")
        return ((inp["face_value"] - inp["purchase_price"])
                / inp["purchase_price"]
                * (discount_basis / inp["days_to_maturity"]) * 100.0)

    def _be_yield(inp):
        """Bond equivalent yield = (discount / price) × (365 / days) × 100."""
        if inp["purchase_price"] == 0:
            raise ValueError("purchase_price is zero")
        return ((inp["face_value"] - inp["purchase_price"])
                / inp["purchase_price"]
                * (365.0 / inp["days_to_maturity"]) * 100.0)

    def _hp_yield(inp):
        """Holding period yield = (face - price) / price × 100."""
        if inp["purchase_price"] == 0:
            raise ValueError("purchase_price is zero")
        return ((inp["face_value"] - inp["purchase_price"])
                / inp["purchase_price"] * 100.0)

    def _eff_annual_yield(inp):
        """Effective annual yield = (face / price)^(365/days) - 1 × 100."""
        if inp["purchase_price"] <= 0:
            raise ValueError("purchase_price must be > 0")
        return ((inp["face_value"] / inp["purchase_price"])
                ** (365.0 / inp["days_to_maturity"]) - 1.0) * 100.0

    def _present_value(inp):
        """Present value equals purchase price for T-Bills."""
        return inp["purchase_price"]

    def _carrying_value(inp):
        """Carrying value = purchase price (T-Bills don't accrue interest)."""
        return inp["purchase_price"]

    def _accrued_interest(inp):
        """T-Bills are discount instruments; accrued interest is typically zero."""
        return 0.0

    steps = [
        CalcStep(
            name="days_to_maturity",
            formula="term_days input, else maturity_date − valuation_date",
            dependencies=days_deps,
            compute=days_compute,
            unit="days",
            display_label="Days to Maturity",
        ),
        CalcStep(
            name="purchase_price",
            formula="input price, or yield-based: face/(1+yield×days/365), or discount-based: face×(1−discount×days/basis)",
            dependencies=["face_value", "days_to_maturity"],
            compute=_establish_price_from_yield,
            unit="currency",
            display_label="Purchase Price",
        ),
        CalcStep(
            name="discount_amount",
            formula="face_value − purchase_price",
            dependencies=["face_value", "purchase_price"],
            compute=_discount_amount,
            unit="currency",
            display_label="Discount Amount",
        ),
        CalcStep(
            name="discount_rate",
            formula="((face_value − purchase_price) / face_value) × (basis / days) × 100",
            dependencies=["face_value", "purchase_price", "days_to_maturity"],
            compute=_discount_rate_from_price,
            unit="percent",
            extra_inputs={"discount_basis": discount_basis},
            display_label="Discount Rate",
        ),
        CalcStep(
            name="discount_yield",
            formula="((face_value − purchase_price) / face_value) × (basis / days) × 100",
            dependencies=["face_value", "purchase_price", "days_to_maturity"],
            compute=_discount_rate_from_price,
            unit="percent",
            extra_inputs={"discount_basis": discount_basis},
            display_label="Discount Yield",
        ),
        CalcStep(
            name="investor_yield",
            formula="((face_value / purchase_price) − 1) × (365 / days) × 100",
            dependencies=["face_value", "purchase_price", "days_to_maturity"],
            compute=_yield_from_price,
            unit="percent",
            display_label="Investor Yield",
        ),
        CalcStep(
            name="money_market_yield",
            formula="((face_value − purchase_price) / purchase_price) × (basis / days) × 100",
            dependencies=["face_value", "purchase_price", "days_to_maturity"],
            compute=_mm_yield,
            unit="percent",
            extra_inputs={"discount_basis": discount_basis},
            display_label="Money-Market Yield",
        ),
        CalcStep(
            name="bond_equivalent_yield",
            formula="((face_value − purchase_price) / purchase_price) × (365 / days) × 100",
            dependencies=["face_value", "purchase_price", "days_to_maturity"],
            compute=_be_yield,
            unit="percent",
            display_label="Bond Equivalent Yield",
        ),
        CalcStep(
            name="holding_period_yield",
            formula="((face_value − purchase_price) / purchase_price) × 100",
            dependencies=["face_value", "purchase_price"],
            compute=_hp_yield,
            unit="percent",
            display_label="Holding Period Yield",
        ),
        CalcStep(
            name="effective_annual_yield",
            formula="((face_value / purchase_price)^(365/days) − 1) × 100",
            dependencies=["face_value", "purchase_price", "days_to_maturity"],
            compute=_eff_annual_yield,
            unit="percent",
            display_label="Effective Annual Yield",
        ),
        CalcStep(
            name="present_value",
            formula="purchase_price",
            dependencies=["purchase_price"],
            compute=_present_value,
            unit="currency",
            display_label="Present Value",
        ),
        CalcStep(
            name="carrying_value",
            formula="purchase_price (T-Bills don't accrue interest)",
            dependencies=["purchase_price"],
            compute=_carrying_value,
            unit="currency",
            display_label="Carrying Value",
        ),
        CalcStep(
            name="accrued_interest",
            formula="0 (T-Bills are discount instruments)",
            dependencies=[],
            compute=lambda inp: 0.0,
            unit="currency",
            display_label="Accrued Interest",
        ),
    ]

    available = {
        "face_value": face,
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

    if "days_to_maturity" in values:
        result["term_days"] = round_time(values["days_to_maturity"])
    for k in ("purchase_price", "discount_amount", "present_value", "carrying_value"):
        if k in values:
            result[k] = round_money(values[k])
    if "accrued_interest" in values:
        result["accrued_interest"] = round_money(values["accrued_interest"])
    if "discount_rate" in values:
        result["discount_rate"] = _rate(values["discount_rate"])
    if "investor_yield" in values:
        result["investor_yield"] = _rate(values["investor_yield"])
    for k in ("discount_yield", "money_market_yield",
              "bond_equivalent_yield", "holding_period_yield",
              "effective_annual_yield"):
        if k in values:
            result[k] = _rate(values[k])

    # Yield gating by days to maturity:
    #   <=365d -> money-market yield only (suppress BEY)
    #   >365d  -> bond-equivalent yield only (suppress MMY) + classification
    #             warning: a bill beyond 1y is Note/Bond territory.
    d_days = values.get("days_to_maturity")
    if d_days is not None:
        if d_days > 365:
            result.pop("money_market_yield", None)
            result["classification_warning"] = (
                f"days_to_maturity={d_days:.0f} exceeds 365 — a T-Bill is a "
                "discount instrument; consider Note/Bond classification."
            )
        else:
            result.pop("bond_equivalent_yield", None)
            # annualized_yield was aliased from BEY — drop the stale alias.
            if result.get("annualized_yield") == values.get("bond_equivalent_yield"):
                result.pop("annualized_yield", None)
    if face is not None:
        result["maturity_value"] = round_money(face)
    if "present_value" in result:
        result["total_value"] = result["present_value"]
    if "present_value" in result:
        result["fair_value"] = result["present_value"]
    if "bond_equivalent_yield" in result:
        result["annualized_yield"] = result["bond_equivalent_yield"]
    if "purchase_price" in result:
        result["avg_investment"] = result["purchase_price"]
    result["yield_curve_rate"] = _benchmark_to_percent(benchmark_yield)

    # KPI fallback: expose avg_rate from discount, investor yield, or BEY.
    if result.get("discount_rate") is not None:
        result["avg_rate"] = result["discount_rate"]
    elif result.get("investor_yield") is not None:
        result["avg_rate"] = result["investor_yield"]
    elif result.get("bond_equivalent_yield") is not None:
        result["avg_rate"] = result["bond_equivalent_yield"]

    validation = validate_row(item, "tbills", normalized=True)
    if validation["missing_fields"]:
        result["missing_fields"] = validation["missing_fields"]
    if validation["invalid_fields"]:
        result["invalid_fields"] = validation["invalid_fields"]

    # T-Bills are discount instruments: price above face is invalid.
    price_over_face = (
        purchase_price_in is not None and face is not None
        and face > 0 and purchase_price_in > face
    )
    if price_over_face:
        result.setdefault("invalid_fields", []).append({
            "field": "purchase_price",
            "code": "price_exceeds_face_value",
            "message": "Purchase price exceeds face value",
        })
        result["warning"] = (
            f"purchase_price={purchase_price_in:.2f} exceeds "
            f"face_value={face:.2f}; a discount instrument cannot be "
            "priced above par."
        )

    if (hard_failures or validation["missing_fields"]
            or validation["invalid_fields"] or price_over_face):
        result["status"] = "partial"
        result["missing_prerequisites"] = [
            e.get("missing") for e in hard_failures if e.get("missing")
        ]
    else:
        result["status"] = "success"

    result["derivations"] = chain["derivations"]
    if period_start and mat_d and "days_to_maturity" in result["derivations"]:
        result["derivations"]["days_to_maturity"]["from"] = period_start.isoformat()
        result["derivations"]["days_to_maturity"]["to"] = mat_d.isoformat()
    if chain["errors"]:
        result["calculation_errors"] = chain["errors"]
    return _add_camel_aliases(result)


# ─────────────────────────────────────────────────────────────
# 10. BOND calculation
# ─────────────────────────────────────────────────────────────
def calculate_bond(item: Dict[str, Any],
                   benchmark_yield: Optional[float] = None) -> Dict[str, Any]:
    raw_freq = _canonical(item, "Coupon Frequency", "coupon_frequency", "frequency")
    item = normalize_row(item)
    _infer_settlement_t1(item)

    face = _canonical(item, "face_value", "principal", as_float=True)
    coupon_rate_frac = _canonical_pct(item, "coupon_rate", "interest_rate")
    currency = _normalize_currency(
        _canonical(item, "currency", "ccy", "currency_code")
    )

    price_in, price_basis = _parse_bond_price(item, face)
    ytm_input_frac = _canonical_pct(item, "yield", "yield_to_maturity")

    day_count_meta = _resolve_day_count(item, "bonds")
    day_count = day_count_meta['convention']
    basis = day_count_meta['basis']
    is_30_360 = day_count_meta['is_30_360']
    is_european = day_count_meta['is_european']
    is_actual_actual = day_count_meta['is_actual_actual']
    has_day_count_convention = (
        _canonical(item, "day_count_convention", "day_count") is not None
    )

    val_d = parse_date(_canonical(item, "valuation_date"))
    mat_d = parse_date(_canonical(item, "maturity_date"))

    period_start = val_d or parse_date(_canonical(item, "issue_date"))
    has_date_range = bool(period_start and mat_d)
    years = None
    years_source = None
    if has_date_range and mat_d >= period_start:
        years = (mat_d - period_start).days / 365.0
        years_source = "derived_from_dates"
    elif not has_date_range:
        years = _canonical(item, "years_to_maturity", as_float=True)
        if years is not None:
            years_source = "input"
    if years is None and not has_date_range:
        d2m = _canonical(item, "days_to_maturity", "term_days", as_float=True)
        if d2m is not None and d2m > 0:
            years = d2m / 365.0
            years_source = "derived_from_days"

    frequency = (parse_frequency(_canonical(item, "frequency"))
                 or parse_frequency(_canonical(item, "coupon_frequency"))
                 or parse_frequency(raw_freq))
    if frequency is not None and (frequency <= 0 or frequency > 365):
        frequency = None
    last_coupon_d = (
        parse_date(_canonical(item, "last_coupon_date"))
        or parse_date(_canonical(item, "issue_date"))
    )
    next_coupon_d = parse_date(_canonical(item, "next_coupon_date"))
    if next_coupon_d is None and last_coupon_d and frequency:
        next_coupon_d = _add_months(last_coupon_d, 12 // frequency)

    coupon_rate_pct = (coupon_rate_frac * 100.0
                       if coupon_rate_frac is not None else None)
    ytm_input_pct = (ytm_input_frac * 100.0
                     if ytm_input_frac is not None else None)

    days_to_maturity = None
    if has_date_range and mat_d >= period_start:
        days_to_maturity = (mat_d - period_start).days
    if days_to_maturity is None:
        d2m_in = _canonical(item, "days_to_maturity", "term_days", as_float=True)
        if d2m_in is not None and d2m_in > 0:
            days_to_maturity = int(d2m_in)
        elif years is not None:
            days_to_maturity = round(years * 365)

    result: Dict[str, Any] = {
        "instrument_type": "bonds",
        "face_value": round_money(face),
        "coupon_rate": _rate(coupon_rate_pct) if coupon_rate_pct is not None else None,
        "years_to_maturity": round(years, 4) if years is not None else None,
        "days_to_maturity": days_to_maturity,
        "frequency": frequency,
        "coupon_frequency": frequency,
        "day_count_convention": day_count,
        "currency": currency,
    }
    name = _extract_instrument_name(item)
    if name:
        result["instrument_name"] = name
    _add_input_dates(result, val_d, mat_d, item)
    if next_coupon_d:
        result["next_coupon_date"] = next_coupon_d.isoformat()
    if frequency is None:
        result["warning"] = (
            "Coupon frequency is missing or invalid; frequency-dependent "
            "calculations are unavailable."
        )

    def _n_periods(years_val: float, freq: int) -> int:
        return max(1, int(Decimal(str(years_val * freq)).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP)))

    # ── Step bodies ──
    def _annual_coupon(inp):
        return inp["face_value"] * (inp["coupon_rate"] / 100.0)

    def _coupon_payment(inp):
        if frequency is None:
            raise CalculationSkipped("coupon_frequency is required")
        return inp["annual_coupon"] / frequency

    def _current_price(inp):
        if price_in is not None and price_in > 0:
            if price_basis == "clean":
                accrued_interest = inp.get("accrued_interest")
                if accrued_interest is None:
                    raise CalculationSkipped(
                        "accrued_interest is required to value a clean price"
                    )
                return price_in + accrued_interest
            return price_in
        if ytm_input_frac is None:
            raise ValueError("Need price or yield_to_maturity to value the bond")
        if frequency is None:
            raise CalculationSkipped(
                "coupon_frequency is required to price a bond from yield"
            )
        return _price_from_ytm(
            inp["face_value"], inp["coupon_rate"] / 100.0,
            ytm_input_frac, inp["years_to_maturity"], frequency,
        )

    def _yield_to_maturity(inp):
        if ytm_input_frac is not None:
            return ytm_input_pct
        if frequency is None:
            raise CalculationSkipped(
                "coupon_frequency is required to solve yield from price"
            )
        solved = _solve_ytm(
            inp["current_price"], inp["face_value"],
            inp["coupon_rate"] / 100.0,
            inp["years_to_maturity"], frequency,
        )
        if solved is None:
            raise ValueError("Could not solve YTM from price")
        return solved * 100.0

    def _current_yield(inp):
        if inp["current_price"] == 0:
            raise ValueError("current_price is zero")
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
        if is_30_360:
            d = calculate_days_30_360(l, v, is_european)
        return d

    def _accrued_interest(inp):
        if not has_day_count_convention:
            raise CalculationSkipped(
                "day_count_convention is required for accrued interest"
            )
        if frequency is None:
            raise CalculationSkipped("coupon_frequency is required")
        if inp.get("days_accrued") is None:
            raise CalculationSkipped("last_coupon_date is required")
        if is_actual_actual:
            if next_coupon_d is None or last_coupon_d is None:
                raise CalculationSkipped(
                    "next_coupon_date or a derivable coupon schedule is required"
                )
            period_days = (next_coupon_d - last_coupon_d).days
            if period_days <= 0 or inp["days_accrued"] > period_days:
                raise CalculationSkipped(
                    "coupon dates do not define the current accrual period"
                )
            return inp["coupon_payment"] * (
                inp["days_accrued"] / period_days
            )
        days_per_period = basis / frequency
        return inp["coupon_payment"] * (
            inp["days_accrued"] / days_per_period
        )

    def _clean_price(inp):
        """Clean price = current price - accrued interest."""
        if price_basis == "clean" and price_in is not None:
            return price_in
        if inp.get("accrued_interest") is None:
            raise CalculationSkipped("accrued interest is unavailable")
        return inp["current_price"] - inp["accrued_interest"]

    def _dirty_price(inp):
        """Dirty price = clean price + accrued interest = current price."""
        return inp["current_price"]

    def _carrying_value(inp):
        """Carrying value = clean price + accrued interest = dirty price."""
        return inp["current_price"]

    def _market_value(inp):
        """Market value = dirty price = current price."""
        return inp["current_price"]

    def _duration_block(inp):
        if frequency is None:
            raise CalculationSkipped("coupon_frequency is required")
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
            display_label="Annual Coupon",
        ),
        CalcStep(
            name="coupon_payment",
            formula="annual_coupon / frequency",
            dependencies=["annual_coupon"],
            compute=_coupon_payment,
            unit="currency",
            extra_inputs={"frequency": frequency},
            display_label="Coupon per Period",
        ),
        CalcStep(
            name="days_accrued",
            formula="valuation_date − last_coupon_date",
            dependencies=["valuation_date", "last_coupon_date"],
            compute=_days_accrued,
            unit="days",
            display_label="Days Accrued",
        ),
        CalcStep(
            name="accrued_interest",
            formula=(
                "coupon_payment × accrued_coupon_fraction "
                "(day-count convention)"
            ),
            dependencies=["coupon_payment", "days_accrued"],
            compute=_accrued_interest,
            unit="currency",
            extra_inputs={
                "basis": basis,
                "frequency": frequency,
                "next_coupon_date": next_coupon_d,
            },
            display_label="Accrued Interest",
        ),
        CalcStep(
            name="current_price",
            formula="input price, or PV(coupons) + PV(face) discounted at YTM",
            dependencies=(
                ["face_value", "coupon_rate", "years_to_maturity",
                 "accrued_interest"]
                if price_in is not None and price_basis == "clean"
                else ["face_value", "coupon_rate", "years_to_maturity"]
            ),
            compute=_current_price,
            unit="currency",
            extra_inputs={"input_price": price_in, "frequency": frequency},
            display_label="Current Price",
        ),
        CalcStep(
            name="yield_to_maturity",
            formula="input YTM, or IRR solved from current_price",
            dependencies=["current_price", "face_value", "coupon_rate",
                          "years_to_maturity"],
            compute=_yield_to_maturity,
            unit="percent",
            extra_inputs={"frequency": frequency},
            display_label="Yield to Maturity",
        ),
        CalcStep(
            name="current_yield",
            formula="(annual_coupon / current_price) × 100",
            dependencies=["annual_coupon", "current_price"],
            compute=_current_yield,
            unit="percent",
            display_label="Current Yield",
        ),
        CalcStep(
            name="price_per_100",
            formula="(current_price / face_value) × 100",
            dependencies=["current_price", "face_value"],
            compute=_price_per_100,
            unit="number",
            display_label="Price per 100",
        ),
        CalcStep(
            name="clean_price",
            formula="current_price - accrued_interest",
            dependencies=(
                [] if price_in is not None and price_basis == "clean"
                else ["current_price", "accrued_interest"]
            ),
            compute=_clean_price,
            unit="currency",
            display_label="Clean Price",
        ),
        CalcStep(
            name="dirty_price",
            formula="clean_price + accrued_interest = current_price",
            dependencies=["current_price", "accrued_interest"],
            compute=_dirty_price,
            unit="currency",
            display_label="Dirty Price",
        ),
        CalcStep(
            name="carrying_value",
            formula="clean_price + accrued_interest = dirty_price",
            dependencies=["current_price", "accrued_interest"],
            compute=_carrying_value,
            unit="currency",
            display_label="Carrying Value",
        ),
        CalcStep(
            name="market_value",
            formula="dirty_price = current_price",
            dependencies=["current_price"],
            compute=_market_value,
            unit="currency",
            display_label="Market Value",
        ),
        CalcStep(
            name="macaulay_duration",
            formula="Σ(t × PV(CF)) / (price × frequency)",
            dependencies=["current_price", "face_value", "coupon_rate",
                          "years_to_maturity", "yield_to_maturity"],
            compute=_macaulay,
            unit="number",
            extra_inputs={"frequency": frequency},
            display_label="Macaulay Duration",
        ),
        CalcStep(
            name="modified_duration",
            formula="macaulay / (1 + ytm / (100 × frequency))",
            dependencies=["current_price", "face_value", "coupon_rate",
                          "years_to_maturity", "yield_to_maturity"],
            compute=_modified,
            unit="number",
            extra_inputs={"frequency": frequency},
            display_label="Modified Duration",
        ),
        CalcStep(
            name="convexity",
            formula="Σ(t(t+1) × PV(CF)) / (price × (1+r)²)",
            dependencies=["current_price", "face_value", "coupon_rate",
                          "years_to_maturity", "yield_to_maturity"],
            compute=_convexity,
            unit="number",
            extra_inputs={"frequency": frequency},
            display_label="Convexity",
        ),
        CalcStep(
            name="dv01",
            formula="current_price × modified_duration × 0.0001",
            dependencies=["current_price", "modified_duration"],
            compute=_dv01,
            unit="currency",
            display_label="DV01",
        ),
    ]

    available = {
        "face_value": face,
        "coupon_rate": coupon_rate_pct,
        "years_to_maturity": years,
        "valuation_date": val_d,
        "maturity_date": mat_d,
        "last_coupon_date": last_coupon_d,
        "next_coupon_date": next_coupon_d,
    }
    chain = execute_chain(steps, available)
    values = chain["values"]
    hard_failures = [e for e in chain["errors"]
                     if e["reason"] in ("missing_prerequisites",
                                        "circular_dependency",
                                        "compute_error",
                                        "division_by_zero")
                     and not (
                         e["reason"] == "missing_prerequisites"
                         and e.get("step") == "days_accrued"
                     )]
    validation = validate_row(item, "bonds", normalized=True)
    if validation["missing_fields"]:
        result["missing_fields"] = validation["missing_fields"]
    if validation["invalid_fields"]:
        result["invalid_fields"] = validation["invalid_fields"]

    # ── Flat fields ──
    for k in ("annual_coupon", "coupon_payment", "current_price",
              "accrued_interest", "dv01", "clean_price", "dirty_price",
              "carrying_value", "market_value"):
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

    # Expose avg_rate for the primary KPI card.
    if result.get("yield_to_maturity") is not None:
        result["avg_rate"] = result["yield_to_maturity"]
    elif result.get("coupon_rate") is not None:
        result["avg_rate"] = result["coupon_rate"]

    if hard_failures or validation["missing_fields"] or validation["invalid_fields"]:
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
# 11. Single-row calc dispatcher
# ─────────────────────────────────────────────────────────────
def calc_single(row: Dict[str, Any], instrument_type: str,
                valuation_date: Optional[str] = None,
                benchmark_yield: Optional[float] = None) -> Dict[str, Any]:
    if valuation_date and parse_date(
        _canonical(normalize_row(row), "valuation_date")
    ) is None:
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


def _resolve_row_instrument_type(row: Dict[str, Any], default: str) -> str:
    """Per-row instrument type from the row's own instrument_type field.
    Only explicit type names override the payload type — ambiguous values
    (e.g. 'US$ CP', 'US$ MM' currency classes) fall back to `default`."""
    if not isinstance(row, dict):
        return default
    raw = str(
        row.get("instrument_type") or row.get("Instrument Type")
        or row.get("type") or row.get("Type") or ""
    ).lower()
    if not raw:
        return default
    if "t-bill" in raw or "tbill" in raw or "treasury" in raw:
        return "tbills"
    if "money market" in raw or "money-market" in raw:
        return "money-market"
    if "bond" in raw:
        return "bonds"
    return default


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
            existing_date = parse_date(
                _canonical(normalize_row(row), "valuation_date")
            )
            if existing_date is None:
                row = {**row, "valuation_date": valuation_date}

        row_type = _resolve_row_instrument_type(row, instrument_type)
        # Rate-source trace: show exactly which discount/yield inputs the
        # row carries and which benchmark the route supplied, so curve
        # fallbacks (e.g. an unexpected 8.94%) can be diagnosed.
        print(f"[RATE-TRACE] row={row.get('instrument_name') or row.get('name') or '?'} "
              f"type={row_type} benchmark_yield={benchmark_yield} "
              f"discount_rate={row.get('discount_rate') or row.get('Discount Rate')} "
              f"yield={row.get('yield') or row.get('yield_to_maturity') or row.get('Yield')} "
              f"coupon_rate={row.get('coupon_rate') or row.get('Coupon Rate')} "
              f"price={row.get('price') or row.get('Price') or row.get('purchase_price')}")
        # Surface inferred inputs (T+1 settlement, day-count default) on
        # the result metadata — never applied silently.
        _infer_settlement_t1(row)
        _resolve_day_count(row, row_type)
        row_assumptions = list(row.get("_assumptions_applied") or [])
        if row_type == "bonds":
            calc = calculate_bond(row, benchmark_yield)
        elif row_type == "money-market":
            calc = calculate_money_market(row, benchmark_yield)
        else:
            calc = calculate_treasury_bill(row, benchmark_yield)
        if row_assumptions:
            calc["assumptions_applied"] = list(
                dict.fromkeys(
                    (calc.get("assumptions_applied") or []) + row_assumptions
                )
            )

        instrument_results.append(calc)

        if calc.get("status") == "success":
            successful.append(calc)
        elif calc.get("status") == "partial":
            # A partial calculation is only "successful" for aggregate
            # purposes if it produced at least one MONETARY output. A
            # bond with only a face value and coupon rate (no price, no
            # YTM) has no valuation — counting it as successful made the
            # KPI card show total market value = 0.00 for a portfolio
            # that simply could not be valued.
            monetary_outputs = (
                calc.get("current_price"),
                calc.get("total_value"),
                calc.get("interest_earned"),
                calc.get("purchase_price"),
                calc.get("discount_amount"),
                calc.get("accrued_interest"),
                calc.get("present_value"),
                calc.get("maturity_value"),
            )
            has_monetary = any(
                v is not None and v != 0 and v != 0.0
                for v in monetary_outputs
            )
            (successful if has_monetary else failed).append(calc)
        else:
            failed.append(calc)

    unique_names = set()
    unique_instrument_keys = set()
    unnamed = 0
    for r in successful:
        nm = r.get("instrument_name")
        if nm and str(nm).strip():
            unique_names.add(str(nm).strip())
            unique_instrument_keys.add("name:" + str(nm).strip().lower())
        else:
            fingerprint = tuple(
                (key, str(r[key]).strip().lower())
                for key in (
                    "face_value", "principal", "interest_rate", "coupon_rate",
                    "discount_rate", "term_days", "days_to_maturity",
                    "maturity_date", "currency",
                )
                if r.get(key) is not None and str(r[key]).strip() != ""
            )
            if fingerprint:
                unique_instrument_keys.add(
                    "fingerprint:" + "|".join(f"{key}:{value}" for key, value in fingerprint)
                )
            else:
                unnamed += 1
    unique_instrument_count = len(unique_instrument_keys) + unnamed

    aggregates: Dict[str, Any] = {
        "instrument_count": unique_instrument_count,
        "successful_rows": len(successful),
        "failed_count": len(failed),
        "total_rows": len(data),
        "unique_names": list(unique_names),
    }

    # Overall payload status for UI banners:
    #   complete — every row calculated successfully
    #   partial  — some rows calculated, some have missing_fields
    #   failed   — no rows produced a calculation
    status_counts = {"success": 0, "partial": 0, "failed": 0}
    for r in instrument_results:
        st = str(r.get("status") or "failed").lower()
        status_counts[st if st in status_counts else "failed"] += 1
    aggregates["status_counts"] = status_counts
    if not instrument_results or status_counts["success"] + status_counts["partial"] == 0:
        aggregates["overall_status"] = "failed"
    elif status_counts["failed"] == 0 and status_counts["partial"] == 0:
        aggregates["overall_status"] = "complete"
    else:
        aggregates["overall_status"] = "partial"

    if successful:
        # Check for currency consistency - only aggregate same-currency instruments
        currencies = {
            str(r.get("currency")).strip().upper()
            if r.get("currency") else None
            for r in successful
        }
        requires_currency_separation = (
            len(currencies) > 1 or None in currencies
        )

        def _sum(field, rows=successful):
            values = [r[field] for r in rows if r.get(field) is not None]
            return sum(values) if values else None

        def _mean(field, rows=successful):
            vals = [r[field] for r in rows if r.get(field) is not None]
            return sum(vals) / len(vals) if vals else None

        if requires_currency_separation:
            currency_groups = {}
            for r in successful:
                currency = (
                    str(r.get("currency")).strip().upper()
                    if r.get("currency") else "UNSPECIFIED"
                )
                if currency not in currency_groups:
                    currency_groups[currency] = []
                currency_groups[currency].append(r)

            currency_labels = sorted(currency or "UNSPECIFIED" for currency in currencies)
            aggregates["warning"] = (
                "Portfolio totals are not combined because instruments have "
                f"different or unspecified currencies: {', '.join(currency_labels)}."
            )
            aggregates["currency_groups"] = {}
        elif currencies:
            aggregates["currency"] = next(iter(currencies))

        if requires_currency_separation:
            for currency, group in currency_groups.items():
                currency_agg = {"currency": currency, "instrument_count": len(group)}
                if instrument_type == "money-market":
                    currency_agg["total_principal"] = round_money(_sum("principal", group))
                    currency_agg["total_interest"] = round_money(_sum("interest_earned", group))
                    currency_agg["total_value"] = round_money(_sum("total_value", group))
                elif instrument_type == "tbills":
                    currency_agg["total_face_value"] = round_money(_sum("face_value", group))
                    currency_agg["total_purchase_price"] = round_money(_sum("purchase_price", group))
                    currency_agg["total_value"] = round_money(_sum("total_value", group))
                    currency_agg["total_discount"] = round_money(_sum("discount_amount", group))
                elif instrument_type == "bonds":
                    currency_agg["total_face_value"] = round_money(_sum("face_value", group))
                    currency_agg["total_market_value"] = round_money(_sum("current_price", group))
                    currency_agg["total_coupon_income"] = round_money(_sum("annual_coupon", group))
                    currency_agg["total_value"] = round_money(_sum("current_price", group))

                aggregates["currency_groups"][currency] = currency_agg

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
            aggregates["total_value"] = round_money(_sum("total_value"))
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
            # KPI fallback: if avg_rate never set, derive from discount.
            if aggregates.get("avg_rate") is None and aggregates.get("discount_rate") is not None:
                aggregates["avg_rate"] = aggregates["discount_rate"]
            elif aggregates.get("avg_rate") is None and aggregates.get("bond_equivalent_yield") is not None:
                aggregates["avg_rate"] = aggregates["bond_equivalent_yield"]

        elif instrument_type == "bonds":
            aggregates["total_face_value"] = round_money(_sum("face_value"))
            aggregates["total_market_value"] = round_money(_sum("current_price"))
            aggregates["total_coupon_income"] = round_money(_sum("annual_coupon"))
            aggregates["total_value"] = round_money(_sum("current_price"))
            m = _mean("yield_to_maturity")
            aggregates["avg_ytm"] = round(m, 4) if m is not None else None
            m = _mean("duration")
            aggregates["avg_duration"] = round(m, 4) if m is not None else None
            m = _mean("days_to_maturity")
            aggregates["avg_days_to_maturity"] = round(m, 1) if m is not None else None
            aggregates["days_to_maturity"] = aggregates["avg_days_to_maturity"]
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
            # KPI fallback for bonds.
            if aggregates.get("avg_rate") is None:
                if aggregates.get("weighted_avg_coupon") is not None:
                    aggregates["avg_rate"] = aggregates["weighted_avg_coupon"]
                elif aggregates.get("avg_ytm") is not None:
                    aggregates["avg_rate"] = aggregates["avg_ytm"]
                elif aggregates.get("avg_coupon_rate") is not None:
                    aggregates["avg_rate"] = aggregates["avg_coupon_rate"]

        if requires_currency_separation:
            for key in (
                "total_value", "total_principal", "total_interest",
                "total_face_value", "total_purchase_price", "total_discount",
                "total_market_value", "total_coupon_income", "maturity_value",
                "present_value", "fair_value",
            ):
                if key in aggregates:
                    aggregates[key] = None

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
        elif "avg_rate" in aggregates:
            aggregates["avgRate"] = aggregates["avg_rate"]

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
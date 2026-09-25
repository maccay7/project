"""
Enhanced Field Detector
=======================

Detects the canonical financial fields present in an uploaded workbook.

For each row we look at the columns present and try to map them to a
canonical field name for the selected instrument type
(money-market / tbills / bonds). The detector then reads the value in
that column for the first row where it appears and reports:

    - value       : the actual value found in the uploaded data
    - value_type  : NUMBER / DATE / PERCENTAGE / TEXT / MISSING
    - source      : the original column name in the workbook
    - confidence  : 0.0 .. 1.0 match confidence
    - row / col   : zero-based location of the first successful hit

HARD RULES enforced by this module:

*  NEVER returns a fabricated value. If a field is not found the
   value_type is MISSING and value is None.
*  NEVER rounds, converts, or reformats the value. That is the
   calculation layer's job.
*  NEVER adds a field that is not backed by a real column.

The calculation pipeline can therefore trust every FieldDetection
object as a genuine observation from the uploaded workbook.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from datetime import datetime, date
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple
import re


# =============================================================================
#  VALUE TYPE ENUM
# =============================================================================

class FieldValueType(Enum):
    """The physical shape of a detected value."""
    MISSING    = "missing"
    NUMBER     = "number"
    PERCENTAGE = "percentage"
    DATE       = "date"
    TEXT       = "text"


# =============================================================================
#  DETECTION RESULT
# =============================================================================

@dataclass
class FieldDetection:
    """The result of trying to locate one canonical field in the data."""
    field_name: str
    value: Any = None
    value_type: FieldValueType = FieldValueType.MISSING
    source: Optional[str] = None           # original column name
    confidence: float = 0.0                # 0.0 – 1.0
    row: Optional[int] = None              # zero-based row index of the hit
    col: Optional[int] = None              # zero-based column index of the hit
    raw_label: Optional[str] = None        # the original header text

    # ---------------------------------------------------------------
    # Convenience predicates used by the caller
    # ---------------------------------------------------------------
    @property
    def found(self) -> bool:
        return self.value_type is not FieldValueType.MISSING


# =============================================================================
#  ALIAS TABLE  —  canonical field  →  list of source-column names
# =============================================================================

# These aliases are conservative on purpose: we match column names, we
# do NOT substring-guess. Ordering matters only for confidence scoring.

_MONEY_MARKET_ALIASES: Dict[str, List[str]] = {
    "principal":       ["principal", "investment amount", "initial investment",
                        "starting balance", "deposit amount", "amount",
                        "total cost", "purchase cost", "notional",
                        "nominal", "face value", "par value"],
    "interest_rate":   ["interest rate", "rate", "annual rate", "nominal rate",
                        "stated rate", "effective rate", "apr", "coupon",
                        "rate %", "rate%"],
    "term_days":       ["term days", "term_days", "days to maturity",
                        "maturity days", "duration days", "contract days",
                        "tenor", "term", "days", "period"],
    "issue_date":      ["issue date", "start date", "effective date",
                        "trade date", "settlement date", "origination date",
                        "value date"],
    "maturity_date":   ["maturity date", "end date", "due date",
                        "redemption date", "expiry date", "termination date"],
    "valuation_date":  ["valuation date", "portfolio date", "report date",
                        "as of date", "date pfolio", "date"],
    "purchase_price":  ["purchase price", "buy price", "acquisition price",
                        "entry price", "price paid"],
    "market_value":    ["market value", "current value", "fair value",
                        "present value", "total value"],
    "instrument_name": ["instrument name", "instrument", "issuer", "company",
                        "entity", "security", "short name"],
    "currency":        ["currency", "ccy", "iso code", "currency code"],
    "country":         ["country", "jurisdiction", "domicile"],
    "classification":  ["classification", "category", "asset class", "type"],
}

_TBILLS_ALIASES: Dict[str, List[str]] = {
    "face_value":      ["face value", "par value", "redemption value",
                        "maturity value", "nominal value", "principal",
                        "amount"],
    "discount_rate":   ["discount rate", "bank discount", "discount yield",
                        "t-bill rate", "auction rate", "discount"],
    "term_days":       ["term days", "term_days", "days to maturity",
                        "maturity days", "tenor", "term", "days", "period"],
    "issue_date":      ["issue date", "start date", "settlement date",
                        "trade date", "auction date"],
    "maturity_date":   ["maturity date", "end date", "due date",
                        "redemption date", "expiry date"],
    "valuation_date":  ["valuation date", "portfolio date", "report date",
                        "as of date", "date"],
    "purchase_price":  ["purchase price", "buy price", "price paid", "price",
                        "clean price"],
    "instrument_name": ["instrument name", "instrument", "issuer", "security",
                        "short name"],
    "currency":        ["currency", "ccy", "iso code"],
    "country":         ["country", "jurisdiction", "domicile"],
}

_BONDS_ALIASES: Dict[str, List[str]] = {
    "face_value":        ["face value", "par value", "principal", "nominal",
                          "redemption value", "maturity value"],
    "coupon_rate":       ["coupon rate", "coupon", "annual coupon",
                          "fixed rate", "stated rate", "interest rate"],
    "coupon_frequency":  ["coupon frequency", "payment frequency", "frequency",
                          "coupon period", "payments per year"],
    "years_to_maturity": ["years to maturity", "maturity years", "term years",
                          "duration years", "time to maturity", "years",
                          "term"],
    "yield_to_maturity": ["yield to maturity", "ytm", "market yield",
                          "required return", "redemption yield", "yield"],
    "market_price":      ["market price", "clean price", "dirty price",
                          "current price", "flat price", "quoted price",
                          "price"],
    "issue_date":        ["issue date", "start date", "effective date",
                          "settlement date", "trade date"],
    "maturity_date":     ["maturity date", "end date", "due date",
                          "redemption date", "expiry date"],
    "valuation_date":    ["valuation date", "portfolio date", "report date",
                          "as of date", "date"],
    "call_date":         ["call date", "first call date",
                          "early redemption date"],
    "call_price":        ["call price", "call premium", "redemption price"],
    "put_date":          ["put date", "puttable date"],
    "put_price":         ["put price", "put premium"],
    "instrument_name":   ["instrument name", "instrument", "issuer", "bond name",
                          "security", "short name"],
    "currency":          ["currency", "ccy", "iso code"],
    "country":           ["country", "jurisdiction", "domicile"],
    "sector":            ["sector", "industry", "industry group"],
    "rating":            ["credit rating", "rating", "moody", "s&p", "fitch"],
}


_ALIAS_TABLE: Dict[str, Dict[str, List[str]]] = {
    "money-market": _MONEY_MARKET_ALIASES,
    "money_market": _MONEY_MARKET_ALIASES,
    "mm":           _MONEY_MARKET_ALIASES,
    "tbills":       _TBILLS_ALIASES,
    "t-bills":      _TBILLS_ALIASES,
    "treasury-bills": _TBILLS_ALIASES,
    "bonds":        _BONDS_ALIASES,
    "bond":         _BONDS_ALIASES,
}


# =============================================================================
#  VALUE-TYPE DETECTION
# =============================================================================

# A relaxed date regexp — the string parsers downstream handle many formats.
_DATE_RE = re.compile(
    r"""^\s*
        (?:
            \d{4}[-/]\d{1,2}[-/]\d{1,2}          # 2024-01-15, 2024/1/15
          | \d{1,2}[-/]\d{1,2}[-/]\d{2,4}        # 15/01/2024, 1/15/24
        )
        (?:\s+\d{1,2}:\d{2}(?::\d{2})?)?         # optional time
        \s*$""",
    re.VERBOSE,
)


def _classify_value(value: Any) -> FieldValueType:
    """Determine the physical shape of one cell."""
    if value is None or value == "":
        return FieldValueType.MISSING
    if isinstance(value, bool):
        return FieldValueType.TEXT
    if isinstance(value, datetime):
        return FieldValueType.DATE
    if isinstance(value, date):
        return FieldValueType.DATE
    if isinstance(value, (int, float)):
        # We cannot tell percentage from number at this stage.
        # The type will be refined by the field-level expectation below.
        return FieldValueType.NUMBER
    if isinstance(value, str):
        s = value.strip()
        if s == "":
            return FieldValueType.MISSING
        if s.endswith("%"):
            return FieldValueType.PERCENTAGE
        if _DATE_RE.match(s):
            return FieldValueType.DATE
        # Numeric-with-commas string
        try:
            float(s.replace(",", ""))
            return FieldValueType.NUMBER
        except (TypeError, ValueError):
            pass
        return FieldValueType.TEXT
    return FieldValueType.TEXT


# Percentage-expected canonical fields — if such a field is found as
# a NUMBER we upgrade its type to PERCENTAGE only when its magnitude
# is consistent with a percentage (i.e. value > 1). Values 0..1 are
# treated as decimal-rate inputs.
_PERCENTAGE_FIELDS = {
    "interest_rate", "discount_rate", "coupon_rate",
    "yield_to_maturity", "yield", "inflation_rate",
}


def _refine_value_type(field_name: str, value: Any,
                       base: FieldValueType) -> FieldValueType:
    """Upgrade NUMBER → PERCENTAGE for percentage-shaped fields."""
    if base is not FieldValueType.NUMBER:
        return base
    if field_name not in _PERCENTAGE_FIELDS:
        return base
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return base
    if numeric > 1:
        return FieldValueType.PERCENTAGE
    # 0..1 decimals are left as NUMBER — the parser knows they are decimals.
    return base


# =============================================================================
#  COLUMN-NAME MATCHING  —  confidence scoring
# =============================================================================

def _normalise_header(text: str) -> str:
    """Lower-case, collapse whitespace, strip punctuation we don't care about."""
    if text is None:
        return ""
    return re.sub(r"\s+", " ", str(text).strip().lower())


def _tokens(text: str) -> List[str]:
    """Split a header into lower-case word tokens."""
    if not text:
        return []
    return [t for t in re.split(r"[\s_\-\(\)\[\]/]+", text.lower().strip()) if t]


def _confidence(header: str, alias: str) -> float:
    """
    Score a match between a workbook header and an alias.

    *  1.00 — exact case-insensitive string match
    *  0.90 — all alias tokens appear in the header, in the same order
    *  0.75 — all alias tokens appear in the header, any order
    *  0.50 — the header is a single token that equals a single alias token
    *  0.00 — no match (caller must reject these)
    """
    if not header or not alias:
        return 0.0
    h = _normalise_header(header)
    a = _normalise_header(alias)
    if h == a:
        return 1.00

    h_tokens = _tokens(h)
    a_tokens = _tokens(a)
    if not a_tokens or not h_tokens:
        return 0.0

    a_set = set(a_tokens)
    h_set = set(h_tokens)

    if a_set.issubset(h_set):
        # Same order?  Compare the sequence of alias tokens in the header.
        indices = [h_tokens.index(t) for t in a_tokens if t in h_tokens]
        if indices == sorted(indices):
            return 0.90
        return 0.75

    if len(a_tokens) == 1 and a_tokens[0] in h_set:
        return 0.50

    return 0.0


# =============================================================================
#  THE DETECTOR
# =============================================================================

class EnhancedFieldDetector:
    """
    Locates canonical fields in an uploaded workbook.

    Usage (matches the existing call-site in calculations.py):

        detector = create_enhanced_field_detector()
        detected = detector.detect_fields(data, "tbills")
        summary  = detector.get_detection_summary(detected)
    """

    #: Minimum confidence required for a hit to be reported.
    MIN_CONFIDENCE = 0.50

    def __init__(self) -> None:
        # Public counters we expose in the summary; reset per detect_fields call.
        self._last_rows_scanned = 0
        self._last_columns_scanned = 0

    # ------------------------------------------------------------------ public

    def detect_fields(self, data: List[Dict[str, Any]],
                      instrument_type: str) -> Dict[str, FieldDetection]:
        """
        Return one FieldDetection per canonical field for the instrument type.

        Fields that could not be located are included in the result with
        value_type=MISSING — this makes the summary deterministic and
        lets the caller iterate safely.
        """
        aliases = self._aliases_for(instrument_type)
        if not aliases:
            # Unknown instrument type — return everything MISSING.
            return {}

        if not data or not isinstance(data, list):
            self._last_rows_scanned = 0
            self._last_columns_scanned = 0
            return {
                name: FieldDetection(field_name=name,
                                     value_type=FieldValueType.MISSING)
                for name in aliases
            }

        # Discover the union of column headers across all rows.
        headers: List[str] = []
        seen = set()
        for row in data:
            if not isinstance(row, dict):
                continue
            for key in row.keys():
                if key not in seen:
                    seen.add(key)
                    headers.append(key)

        self._last_rows_scanned = len(data)
        self._last_columns_scanned = len(headers)

        detected: Dict[str, FieldDetection] = {}
        for canonical, alias_list in aliases.items():
            detected[canonical] = self._detect_one(
                canonical, alias_list, headers, data
            )
        return detected

    def get_detection_summary(self,
                              detected_fields: Dict[str, FieldDetection]) -> Dict[str, Any]:
        """
        Return a compact summary suitable for logging or API responses.
        """
        found = []
        missing = []
        by_type: Dict[str, int] = {}

        for name, det in detected_fields.items():
            if det.found:
                found.append({
                    "field": name,
                    "value": det.value,
                    "value_type": det.value_type.value,
                    "source_column": det.source,
                    "confidence": det.confidence,
                })
                by_type[det.value_type.value] = by_type.get(det.value_type.value, 0) + 1
            else:
                missing.append(name)

        return {
            "rows_scanned": self._last_rows_scanned,
            "columns_scanned": self._last_columns_scanned,
            "found_count": len(found),
            "missing_count": len(missing),
            "found": found,
            "missing": missing,
            "by_value_type": by_type,
        }

    # ----------------------------------------------------------------- internal

    @staticmethod
    def _aliases_for(instrument_type: Optional[str]) -> Dict[str, List[str]]:
        if not instrument_type:
            return {}
        key = instrument_type.lower().replace("_", "-").strip()
        return _ALIAS_TABLE.get(key, {})

    def _detect_one(self,
                    canonical: str,
                    alias_list: Sequence[str],
                    headers: Sequence[str],
                    data: Sequence[Dict[str, Any]]) -> FieldDetection:
        """
        Find the best matching column for `canonical`, then read the first
        non-empty value from that column across the rows.
        """
        # 1. Score every header against every alias and keep the best (header, alias).
        best_header: Optional[str] = None
        best_alias: Optional[str] = None
        best_score = 0.0

        for header in headers:
            for alias in alias_list:
                score = _confidence(header, alias)
                if score > best_score:
                    best_score = score
                    best_header = header
                    best_alias = alias

        if best_header is None or best_score < self.MIN_CONFIDENCE:
            return FieldDetection(field_name=canonical,
                                  value_type=FieldValueType.MISSING)

        # 2. Read the first non-empty value in that column.
        value, row_idx, col_idx = self._first_non_empty(best_header, headers, data)

        if value is None:
            return FieldDetection(
                field_name=canonical,
                value_type=FieldValueType.MISSING,
                source=best_header,
                raw_label=best_header,
                confidence=best_score,
            )

        # 3. Classify and (for percentage-shaped fields) refine the type.
        base_type = _classify_value(value)
        value_type = _refine_value_type(canonical, value, base_type)

        return FieldDetection(
            field_name=canonical,
            value=value,
            value_type=value_type,
            source=best_header,
            raw_label=best_header,
            confidence=best_score,
            row=row_idx,
            col=col_idx,
        )

    @staticmethod
    def _first_non_empty(column: str,
                         headers: Sequence[str],
                         data: Sequence[Dict[str, Any]]
                         ) -> Tuple[Any, Optional[int], Optional[int]]:
        """
        Return the first non-empty cell in `column`, plus its (row, col)
        indices. If the column never has a value we return (None, None, None).
        """
        try:
            col_idx: Optional[int] = list(headers).index(column)
        except ValueError:
            col_idx = None

        for row_idx, row in enumerate(data):
            if not isinstance(row, dict):
                continue
            if column not in row:
                continue
            v = row[column]
            if v is None:
                continue
            if isinstance(v, str) and v.strip() == "":
                continue
            return v, row_idx, col_idx

        return None, None, col_idx


# =============================================================================
#  FACTORY
# =============================================================================

def create_enhanced_field_detector() -> EnhancedFieldDetector:
    """Factory used by the calculation pipeline."""
    return EnhancedFieldDetector()
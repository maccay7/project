from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from datetime import datetime, date
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple
import re


class FieldValueType(Enum):
    MISSING    = "missing"
    NUMBER     = "number"
    PERCENTAGE = "percentage"
    DATE       = "date"
    TEXT       = "text"


@dataclass
class FieldDetection:
    field_name: str
    value: Any = None
    value_type: FieldValueType = FieldValueType.MISSING
    source: Optional[str] = None
    confidence: float = 0.0
    row: Optional[int] = None
    col: Optional[int] = None
    raw_label: Optional[str] = None

    @property
    def found(self) -> bool:
        return self.value_type is not FieldValueType.MISSING


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


_DATE_RE = re.compile(
    r"""^\s*
        (?:
            \d{4}[-/]\d{1,2}[-/]\d{1,2}
          | \d{1,2}[-/]\d{1,2}[-/]\d{2,4}
        )
        (?:\s+\d{1,2}:\d{2}(?::\d{2})?)?
        \s*$""",
    re.VERBOSE,
)


def _classify_value(value: Any) -> FieldValueType:
    if value is None or value == "":
        return FieldValueType.MISSING
    if isinstance(value, bool):
        return FieldValueType.TEXT
    if isinstance(value, datetime):
        return FieldValueType.DATE
    if isinstance(value, date):
        return FieldValueType.DATE
    if isinstance(value, (int, float)):
        return FieldValueType.NUMBER
    if isinstance(value, str):
        s = value.strip()
        if s == "":
            return FieldValueType.MISSING
        if s.endswith("%"):
            return FieldValueType.PERCENTAGE
        if _DATE_RE.match(s):
            return FieldValueType.DATE
        try:
            float(s.replace(",", ""))
            return FieldValueType.NUMBER
        except (TypeError, ValueError):
            pass
        return FieldValueType.TEXT
    return FieldValueType.TEXT


_PERCENTAGE_FIELDS = {
    "interest_rate", "discount_rate", "coupon_rate",
    "yield_to_maturity", "yield", "inflation_rate",
}


def _refine_value_type(field_name: str, value: Any,
                       base: FieldValueType) -> FieldValueType:
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
    return base


def _normalise_header(text: str) -> str:
    if text is None:
        return ""
    return re.sub(r"\s+", " ", str(text).strip().lower())


def _tokens(text: str) -> List[str]:
    if not text:
        return []
    return [t for t in re.split(r"[\s_\-\(\)\[\]/]+", text.lower().strip()) if t]


def _confidence(header: str, alias: str) -> float:
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
        indices = [h_tokens.index(t) for t in a_tokens if t in h_tokens]
        if indices == sorted(indices):
            return 0.90
        return 0.75

    if len(a_tokens) == 1 and a_tokens[0] in h_set:
        return 0.50

    return 0.0


class EnhancedFieldDetector:

    MIN_CONFIDENCE = 0.50

    def __init__(self) -> None:
        self._last_rows_scanned = 0
        self._last_columns_scanned = 0

    def detect_fields(self, data: List[Dict[str, Any]],
                      instrument_type: str) -> Dict[str, FieldDetection]:
        aliases = self._aliases_for(instrument_type)
        if not aliases:
            return {}

        if not data or not isinstance(data, list):
            self._last_rows_scanned = 0
            self._last_columns_scanned = 0
            return {
                name: FieldDetection(field_name=name,
                                     value_type=FieldValueType.MISSING)
                for name in aliases
            }

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

        value, row_idx, col_idx = self._first_non_empty(best_header, headers, data)

        if value is None:
            return FieldDetection(
                field_name=canonical,
                value_type=FieldValueType.MISSING,
                source=best_header,
                raw_label=best_header,
                confidence=best_score,
            )

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


def create_enhanced_field_detector() -> EnhancedFieldDetector:
    return EnhancedFieldDetector()
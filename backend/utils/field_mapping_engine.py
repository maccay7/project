from typing import Dict, List, Optional, Tuple, Set
import re
from dataclasses import dataclass
from enum import Enum


class InstrumentType(Enum):
    MONEY_MARKET = "money-market"
    TBILLS = "tbills"
    BONDS = "bonds"


@dataclass
class FieldMapping:
    target_field: str
    source_field: str
    confidence: float
    aliases: List[str]
    semantic_category: str


class FieldMappingEngine:

    def __init__(self):
        self.field_aliases = {
            'principal': [
                'principal', 'face value', 'face', 'face amount', 'par value', 'par',
                'nominal', 'nominal value', 'investment amount', 'amount invested',
                'purchase amount', 'issue price', 'notional', 'notional amount'
            ],
            'face_value': [
                'face value', 'face', 'face amount', 'par value', 'par',
                'principal', 'nominal', 'nominal value', 'maturity value'
            ],
            'purchase_price': [
                'purchase price', 'purchase', 'price', 'clean price', 'dirty price',
                'issue price', 'investment amount', 'amount invested'
            ],

            'interest_rate': [
                'interest rate', 'rate', 'coupon rate', 'coupon', 'yield',
                'annual rate', 'nominal rate', 'stated rate'
            ],
            'coupon_rate': [
                'coupon rate', 'coupon', 'interest rate', 'rate', 'annual coupon'
            ],
            'discount_rate': [
                'discount rate', 'discount', 'bank discount', 'discount yield'
            ],
            'yield': [
                'yield', 'ytm', 'yield to maturity', 'investment yield',
                'money market yield', 'bond equivalent yield', 'bey'
            ],

            'maturity_date': [
                'maturity date', 'maturity', 'due date', 'expiration date',
                'redemption date'
            ],
            'settlement_date': [
                'settlement date', 'settlement', 'trade date', 'value date',
                'effective date'
            ],
            'issue_date': [
                'issue date', 'issuance date', 'origination date', 'start date'
            ],

            'days_to_maturity': [
                'days to maturity', 'maturity days', 'term', 'tenor', 'days',
                'remaining days', 'days remaining'
            ],
            'term': [
                'term', 'tenor', 'duration', 'maturity', 'period'
            ],

            'coupon_frequency': [
                'coupon frequency', 'frequency', 'payment frequency',
                'payments per year', 'compounding frequency'
            ],

            'instrument_name': [
                'parent company name', 'parent company',
                'issuer', 'company', 'entity',
                'short name', 'shortname',
                'instrument name', 'instrumentname', 'instrument_name',
                'instrument', 'description',
                'bond name', 'bondname', 'bond_name', 'bond',
                't-bill name', 'tbill name', 'tbillname', 'tbill_name',
                'tbill', 't-bill', 'treasury bill name',
                'security name', 'securityname',
                'name', 'ticker', 'symbol',
            ],
            # Kept separate from instrument_name so counterparty stays
            # visible but never replaces the real instrument name.
            'counterparty': [
                'counterparty', 'counter party', 'counter-party', 'cp',
                'account name', 'client name',
            ],
            'instrument_type': [
                'instrument type', 'type', 'category', 'class', 'asset class'
            ],
            'quantity': [
                'quantity', 'amount', 'number of units', 'units',
                'face quantity'
            ],
            'accrued_interest': [
                'accrued interest', 'accrued', 'interest accrued'
            ],
            'day_count_convention': [
                'day count', 'day count convention', 'day basis',
                'basis', 'day basis'
            ]
        }

        self.instrument_requirements = {
            InstrumentType.MONEY_MARKET: {
                'required': ['principal', 'interest_rate'],
                'optional': ['maturity_date', 'settlement_date', 'days_to_maturity',
                             'day_count_convention', 'compounding_frequency'],
                'calculations': {
                    'simple_interest': ['principal', 'interest_rate', 'days_to_maturity', 'day_count_convention'],
                    'present_value': ['principal', 'interest_rate', 'days_to_maturity', 'day_count_convention'],
                    'effective_yield': ['interest_rate', 'compounding_frequency'],
                    'investment_yield': ['face_value', 'purchase_price', 'days_to_maturity', 'day_count_convention'],
                    'discount_yield': ['face_value', 'purchase_price', 'days_to_maturity', 'day_count_convention']
                }
            },
            InstrumentType.TBILLS: {
                'required': ['face_value', 'discount_rate'],
                'optional': ['maturity_date', 'settlement_date', 'days_to_maturity', 'day_count_convention'],
                'calculations': {
                    'purchase_price': ['face_value', 'discount_rate', 'days_to_maturity', 'day_count_convention'],
                    'discount_amount': ['face_value', 'discount_rate', 'days_to_maturity', 'day_count_convention'],
                    'bond_equivalent_yield': ['face_value', 'purchase_price', 'days_to_maturity'],
                    'investment_yield': ['face_value', 'purchase_price', 'days_to_maturity'],
                    'effective_annual_yield': ['bond_equivalent_yield', 'days_to_maturity']
                }
            },
            InstrumentType.BONDS: {
                'required': ['face_value', 'coupon_rate', 'yield_to_maturity'],
                'optional': ['maturity_date', 'settlement_date', 'years_to_maturity',
                             'coupon_frequency', 'call_date', 'call_price',
                             'put_date', 'put_price'],
                'calculations': {
                    'coupon_payment': ['face_value', 'coupon_rate', 'coupon_frequency'],
                    'clean_price': ['face_value', 'coupon_rate', 'yield_to_maturity',
                                    'years_to_maturity', 'coupon_frequency'],
                    'dirty_price': ['clean_price', 'accrued_interest'],
                    'accrued_interest': ['coupon_payment', 'coupon_frequency',
                                         'settlement_date', 'issue_date'],
                    'macaulay_duration': ['face_value', 'coupon_rate', 'yield_to_maturity',
                                          'years_to_maturity', 'coupon_frequency'],
                    'modified_duration': ['macaulay_duration', 'yield_to_maturity',
                                          'coupon_frequency'],
                    'convexity': ['face_value', 'coupon_rate', 'yield_to_maturity',
                                  'years_to_maturity', 'coupon_frequency'],
                    'current_yield': ['coupon_payment', 'clean_price', 'coupon_frequency']
                }
            }
        }

    def normalize_field_name(self, field_name: str) -> str:
        if not field_name:
            return ''
        normalized = field_name.lower().strip()
        normalized = re.sub(r'[^\w\s]', '_', normalized)
        normalized = re.sub(r'\s+', '_', normalized)
        normalized = re.sub(r'_+', '_', normalized)
        normalized = normalized.strip('_')
        return normalized

    def calculate_semantic_similarity(self, source_field: str, target_field: str) -> float:
        source_norm = self.normalize_field_name(source_field)
        target_norm = self.normalize_field_name(target_field)

        if not source_norm or not target_norm:
            return 0.0

        if source_norm == target_norm:
            return 1.0

        source_padded = f"_{source_norm}_"
        target_padded = f"_{target_norm}_"
        if target_padded in source_padded or source_padded in target_padded:
            return 0.8

        for target_key, aliases in self.field_aliases.items():
            alias_norms = [self.normalize_field_name(a) for a in aliases]
            if target_norm in alias_norms:
                if source_norm in alias_norms:
                    return 0.9

        source_words = set(source_norm.split('_'))
        target_words = set(target_norm.split('_'))

        if source_words & target_words:
            overlap = len(source_words & target_words)
            total = len(source_words | target_words)
            return overlap / total if total > 0 else 0

        return 0.0

    def detect_fields(self, data: List[Dict]) -> List[str]:
        if not data:
            return []
        fields = set()
        for row in data:
            if isinstance(row, dict):
                fields.update(row.keys())
        return sorted(list(fields))

    def suggest_mapping(self, source_fields: List[str],
                        instrument_type: InstrumentType) -> Dict[str, FieldMapping]:
        requirements = self.instrument_requirements.get(instrument_type, {})
        required_fields = requirements.get('required', [])
        optional_fields = requirements.get('optional', [])
        all_target_fields = required_fields + optional_fields

        mappings = {}

        for target_field in all_target_fields:
            best_match = None
            best_confidence = 0.0

            for source_field in source_fields:
                confidence = self.calculate_semantic_similarity(source_field, target_field)

                aliases = self.field_aliases.get(target_field, [])
                for alias in aliases:
                    alias_confidence = self.calculate_semantic_similarity(source_field, alias)
                    if alias_confidence > confidence:
                        confidence = alias_confidence

                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = source_field

            if best_match and best_confidence > 0.5:
                mappings[target_field] = FieldMapping(
                    target_field=target_field,
                    source_field=best_match,
                    confidence=best_confidence,
                    aliases=self.field_aliases.get(target_field, []),
                    semantic_category=self._get_semantic_category(target_field)
                )

        return mappings

    def _get_semantic_category(self, field_name: str) -> str:
        categories = {
            'principal': 'amount',
            'face_value': 'amount',
            'purchase_price': 'amount',
            'interest_rate': 'rate',
            'coupon_rate': 'rate',
            'discount_rate': 'rate',
            'yield': 'rate',
            'maturity_date': 'date',
            'settlement_date': 'date',
            'issue_date': 'date',
            'days_to_maturity': 'duration',
            'term': 'duration',
            'coupon_frequency': 'frequency',
            'instrument_name': 'identifier',
            'counterparty': 'identifier',
            'instrument_type': 'type',
            'quantity': 'quantity'
        }
        norm_name = self.normalize_field_name(field_name)
        return categories.get(norm_name, 'other')

    def validate_mapping(self, mapping: Dict[str, FieldMapping],
                         instrument_type: InstrumentType) -> Tuple[bool, List[str], List[str]]:
        requirements = self.instrument_requirements.get(instrument_type, {})
        required_fields = requirements.get('required', [])

        mapped_fields = set(mapping.keys())
        missing_fields = [f for f in required_fields if f not in mapped_fields]

        warnings = []
        for field_mapping in mapping.values():
            if field_mapping.confidence < 0.7:
                warnings.append(
                    f"Low confidence mapping: {field_mapping.source_field} -> "
                    f"{field_mapping.target_field} "
                    f"(confidence: {field_mapping.confidence:.2f})"
                )

        return (len(missing_fields) == 0, missing_fields, warnings)

    def apply_mapping(self, data: List[Dict],
                      mapping: Dict[str, FieldMapping]) -> List[Dict]:
        if not data or not mapping:
            return data

        consumed_sources = {fm.source_field for fm in mapping.values()}

        transformed = []
        for row in data:
            transformed_row = {}
            for target_field, field_mapping in mapping.items():
                source_field = field_mapping.source_field
                if source_field in row:
                    transformed_row[target_field] = row[source_field]
            for key, value in row.items():
                if key not in consumed_sources:
                    transformed_row[key] = value
            transformed.append(transformed_row)

        return transformed


def create_field_mapping_engine() -> FieldMappingEngine:
    return FieldMappingEngine()
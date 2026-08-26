"""
Dynamic Field Detection and Semantic Mapping Engine

This module provides intelligent field detection and semantic mapping
for financial instrument data, supporting various naming conventions
and field aliases across different datasets.
"""

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
    """Represents a mapping from a source field to a target field."""
    target_field: str
    source_field: str
    confidence: float
    aliases: List[str]
    semantic_category: str


class FieldMappingEngine:
    """
    Dynamic field detection and semantic mapping engine.
    
    This engine:
    - Detects fields from uploaded datasets
    - Performs semantic matching to identify equivalent fields
    - Supports field aliases and naming variations
    - Provides confidence scores for mappings
    - Allows user confirmation/override of mappings
    """
    
    def __init__(self):
        # Comprehensive field alias database
        self.field_aliases = {
            # Principal/Face Value concepts
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
            
            # Interest Rate concepts
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
            
            # Date concepts
            'maturity_date': [
                'maturity date', 'maturity', 'due date', 'expiration date',
                'redemption date', 'maturity'
            ],
            'settlement_date': [
                'settlement date', 'settlement', 'trade date', 'value date',
                'effective date'
            ],
            'issue_date': [
                'issue date', 'issuance date', 'origination date', 'start date'
            ],
            
            # Term/Duration concepts
            'days_to_maturity': [
                'days to maturity', 'maturity days', 'term', 'tenor', 'days',
                'remaining days', 'days remaining'
            ],
            'term': [
                'term', 'tenor', 'duration', 'maturity', 'period'
            ],
            
            # Frequency concepts
            'coupon_frequency': [
                'coupon frequency', 'frequency', 'payment frequency',
                'payments per year', 'compounding frequency'
            ],
            
            # Other financial concepts
            'instrument_name': [
                'instrument name', 'name', 'security', 'security name',
                'bond name', 'tbill name', 'description', 'ticker', 'symbol'
            ],
            'instrument_type': [
                'instrument type', 'type', 'category', 'class', 'asset class'
            ],
            'quantity': [
                'quantity', 'quantity', 'amount', 'number of units', 'units',
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
        
        # Instrument-specific required fields
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
                            'coupon_frequency', 'call_date', 'call_price', 'put_date', 'put_price'],
                'calculations': {
                    'coupon_payment': ['face_value', 'coupon_rate', 'coupon_frequency'],
                    'clean_price': ['face_value', 'coupon_rate', 'yield_to_maturity', 
                                  'years_to_maturity', 'coupon_frequency'],
                    'dirty_price': ['clean_price', 'accrued_interest'],
                    'accrued_interest': ['coupon_payment', 'coupon_frequency', 'settlement_date', 'issue_date'],
                    'macaulay_duration': ['face_value', 'coupon_rate', 'yield_to_maturity', 
                                         'years_to_maturity', 'coupon_frequency'],
                    'modified_duration': ['macaulay_duration', 'yield_to_maturity', 'coupon_frequency'],
                    'convexity': ['face_value', 'coupon_rate', 'yield_to_maturity', 
                                'years_to_maturity', 'coupon_frequency'],
                    'current_yield': ['coupon_payment', 'clean_price', 'coupon_frequency']
                }
            }
        }
    
    def normalize_field_name(self, field_name: str) -> str:
        """
        Normalize a field name for comparison.
        
        Args:
            field_name: Raw field name from dataset
            
        Returns:
            Normalized field name (lowercase, underscores, no special chars)
        """
        if not field_name:
            return ''
        
        # Convert to lowercase
        normalized = field_name.lower().strip()
        
        # Replace special characters with underscores
        normalized = re.sub(r'[^\w\s]', '_', normalized)
        
        # Replace spaces with underscores
        normalized = re.sub(r'\s+', '_', normalized)
        
        # Remove multiple consecutive underscores
        normalized = re.sub(r'_+', '_', normalized)
        
        # Strip leading/trailing underscores
        normalized = normalized.strip('_')
        
        return normalized
    
    def calculate_semantic_similarity(self, source_field: str, target_field: str) -> float:
        """
        Calculate semantic similarity between two field names.
        
        Args:
            source_field: Field name from dataset
            target_field: Target field name to match against
            
        Returns:
            Similarity score between 0 and 1
        """
        source_norm = self.normalize_field_name(source_field)
        target_norm = self.normalize_field_name(target_field)
        
        # Exact match
        if source_norm == target_norm:
            return 1.0
        
        # Check if source contains target or vice versa
        if target_norm in source_norm or source_norm in target_norm:
            return 0.8
        
        # Check aliases
        for target_key, aliases in self.field_aliases.items():
            if target_norm in [self.normalize_field_name(a) for a in aliases]:
                if source_norm in [self.normalize_field_name(a) for a in aliases]:
                    return 0.9
        
        # Word overlap
        source_words = set(source_norm.split('_'))
        target_words = set(target_norm.split('_'))
        
        if source_words & target_words:
            overlap = len(source_words & target_words)
            total = len(source_words | target_words)
            return overlap / total if total > 0 else 0
        
        return 0.0
    
    def detect_fields(self, data: List[Dict]) -> List[str]:
        """
        Detect all unique field names from dataset.
        
        Args:
            data: List of data rows (dictionaries)
            
        Returns:
            List of unique field names
        """
        if not data:
            return []
        
        fields = set()
        for row in data:
            if isinstance(row, dict):
                fields.update(row.keys())
        
        return sorted(list(fields))
    
    def suggest_mapping(self, source_fields: List[str], 
                      instrument_type: InstrumentType) -> Dict[str, FieldMapping]:
        """
        Suggest field mappings for a given instrument type.
        
        Args:
            source_fields: List of field names from dataset
            instrument_type: Type of instrument
            
        Returns:
            Dictionary mapping target fields to FieldMapping objects
        """
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
                
                # Also check against aliases
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
        """Get semantic category for a field."""
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
            'instrument_type': 'type',
            'quantity': 'quantity'
        }
        
        norm_name = self.normalize_field_name(field_name)
        return categories.get(norm_name, 'other')
    
    def validate_mapping(self, mapping: Dict[str, FieldMapping],
                        instrument_type: InstrumentType) -> Tuple[bool, List[str], List[str]]:
        """
        Validate a mapping against instrument requirements.
        
        Args:
            mapping: Dictionary of field mappings
            instrument_type: Type of instrument
            
        Returns:
            Tuple of (is_valid, missing_fields, warnings)
        """
        requirements = self.instrument_requirements.get(instrument_type, {})
        required_fields = requirements.get('required', [])
        
        mapped_fields = set(mapping.keys())
        missing_fields = [f for f in required_fields if f not in mapped_fields]
        
        warnings = []
        
        # Check for unmapped source fields that might be important
        for field_mapping in mapping.values():
            if field_mapping.confidence < 0.7:
                warnings.append(
                    f"Low confidence mapping: {field_mapping.source_field} -> {field_mapping.target_field} "
                    f"(confidence: {field_mapping.confidence:.2f})"
                )
        
        return (len(missing_fields) == 0, missing_fields, warnings)
    
    def apply_mapping(self, data: List[Dict], 
                     mapping: Dict[str, FieldMapping]) -> List[Dict]:
        """
        Apply field mappings to transform data.
        
        Args:
            data: Original data rows
            mapping: Field mappings
            
        Returns:
            Transformed data with mapped field names
        """
        if not data or not mapping:
            return data
        
        transformed = []
        for row in data:
            transformed_row = {}
            
            # Apply mappings
            for target_field, field_mapping in mapping.items():
                source_field = field_mapping.source_field
                if source_field in row:
                    transformed_row[target_field] = row[source_field]
            
            # Preserve unmapped fields
            for key, value in row.items():
                if key not in [fm.source_field for fm in mapping.values()]:
                    transformed_row[key] = value
            
            transformed.append(transformed_row)
        
        return transformed


def create_field_mapping_engine() -> FieldMappingEngine:
    """Factory function to create a field mapping engine."""
    return FieldMappingEngine()

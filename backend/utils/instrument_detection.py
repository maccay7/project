"""
Instrument Detection Logic

This module provides logic to detect whether a dataset contains a single instrument
or multiple instruments, and determines the appropriate workflow for each case.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class InstrumentCount(Enum):
    """Number of instruments in dataset."""
    SINGLE = "single"
    MULTIPLE = "multiple"
    UNKNOWN = "unknown"


@dataclass
class InstrumentDetectionResult:
    """Result of instrument detection."""
    count_type: InstrumentCount
    instrument_count: int
    instrument_type: Optional[str]
    confidence: float
    reasoning: str
    recommended_workflow: str


class InstrumentDetector:
    """
    Detects whether a dataset contains single or multiple instruments.
    
    This detector:
    - Analyzes data structure to determine instrument count
    - Identifies instrument type based on available fields
    - Provides confidence scores for detection
    - Recommends appropriate workflow
    """
    
    def __init__(self):
        # Field patterns that indicate specific instrument types
        self.instrument_field_patterns = {
            'money-market': [
                'principal', 'interest_rate', 'investment_amount', 'days_to_maturity',
                'term', 'tenor', 'money market', 'deposit', 'certificate of deposit'
            ],
            'tbills': [
                'discount_rate', 'face_value', 'tbill', 'treasury bill', 'discount',
                'bill', 't-bill', 'treasury'
            ],
            'bonds': [
                'coupon_rate', 'bond', 'coupon', 'yield_to_maturity', 'ytm',
                'maturity_date', 'face_value', 'par_value', 'bond_name'
            ]
        }
        
        # Fields that typically indicate multiple instruments
        self.multi_instrument_indicators = [
            'instrument_name', 'security', 'ticker', 'symbol',
            'isin', 'cusip', 'bond_name', 'tbill_name', 'instrument_id'
        ]
    
    def detect_from_data(self, data: List[Dict]) -> InstrumentDetectionResult:
        """
        Detect instrument count and type from data rows.
        
        Args:
            data: List of data rows (dictionaries)
            
        Returns:
            InstrumentDetectionResult with detection details
        """
        if not data or not isinstance(data, list):
            return InstrumentDetectionResult(
                count_type=InstrumentCount.UNKNOWN,
                instrument_count=0,
                instrument_type=None,
                confidence=0.0,
                reasoning="No data provided",
                recommended_workflow="error"
            )
        
        instrument_count = len(data)
        
        # Check for instrument identifier fields
        has_identifier = self._has_instrument_identifier(data)
        
        # Detect instrument type from field names
        detected_type = self._detect_instrument_type(data)
        
        # Determine if single or multiple
        if instrument_count == 1:
            count_type = InstrumentCount.SINGLE
            confidence = 0.95
            reasoning = "Single data row detected"
            recommended_workflow = "single_instrument"
        elif instrument_count > 1 and has_identifier:
            count_type = InstrumentCount.MULTIPLE
            confidence = 0.90
            reasoning = f"Multiple data rows ({instrument_count}) with instrument identifiers detected"
            recommended_workflow = "multiple_instruments"
        elif instrument_count > 1:
            # Could be multiple instruments without explicit identifiers
            count_type = InstrumentCount.MULTIPLE
            confidence = 0.70
            reasoning = f"Multiple data rows ({instrument_count}) detected, treating as multiple instruments"
            recommended_workflow = "multiple_instruments"
        else:
            count_type = InstrumentCount.UNKNOWN
            confidence = 0.0
            reasoning = "Unable to determine instrument count"
            recommended_workflow = "error"
        
        return InstrumentDetectionResult(
            count_type=count_type,
            instrument_count=instrument_count,
            instrument_type=detected_type,
            confidence=confidence,
            reasoning=reasoning,
            recommended_workflow=recommended_workflow
        )
    
    def detect_from_fields(self, fields: List[str]) -> InstrumentDetectionResult:
        """
        Detect instrument type from available field names.
        
        Args:
            fields: List of field names
            
        Returns:
            InstrumentDetectionResult with detection details
        """
        if not fields:
            return InstrumentDetectionResult(
                count_type=InstrumentCount.UNKNOWN,
                instrument_count=0,
                instrument_type=None,
                confidence=0.0,
                reasoning="No fields provided",
                recommended_workflow="error"
            )
        
        # Detect instrument type
        detected_type = self._detect_instrument_type_from_fields(fields)
        
        # Check for identifier fields
        has_identifier = any(
            any(indicator in field.lower() for indicator in self.multi_instrument_indicators)
            for field in fields
        )
        
        if has_identifier:
            return InstrumentDetectionResult(
                count_type=InstrumentCount.MULTIPLE,
                instrument_count=0,  # Unknown count from fields only
                instrument_type=detected_type,
                confidence=0.75,
                reasoning="Instrument identifier fields detected, likely multiple instruments",
                recommended_workflow="multiple_instruments"
            )
        else:
            return InstrumentDetectionResult(
                count_type=InstrumentCount.SINGLE,
                instrument_count=1,
                instrument_type=detected_type,
                confidence=0.60,
                reasoning="No instrument identifiers detected, assuming single instrument",
                recommended_workflow="single_instrument"
            )
    
    def _has_instrument_identifier(self, data: List[Dict]) -> bool:
        """Check if data has instrument identifier fields."""
        if not data:
            return False
        
        first_row = data[0]
        fields = list(first_row.keys())
        
        for field in fields:
            field_lower = field.lower()
            for indicator in self.multi_instrument_indicators:
                if indicator in field_lower:
                    return True
        
        return False
    
    def _detect_instrument_type(self, data: List[Dict]) -> Optional[str]:
        """Detect instrument type from data fields and values."""
        if not data:
            return None
        
        first_row = data[0]
        fields = list(first_row.keys())
        
        return self._detect_instrument_type_from_fields(fields)
    
    def _detect_instrument_type_from_fields(self, fields: List[str]) -> Optional[str]:
        """Detect instrument type from field names only."""
        scores = {
            'money-market': 0,
            'tbills': 0,
            'bonds': 0
        }
        
        for field in fields:
            field_lower = field.lower()
            
            for inst_type, patterns in self.instrument_field_patterns.items():
                for pattern in patterns:
                    if pattern in field_lower:
                        scores[inst_type] += 1
        
        # Return type with highest score
        max_score = max(scores.values())
        if max_score > 0:
            for inst_type, score in scores.items():
                if score == max_score:
                    return inst_type
        
        return None
    
    def get_workflow_requirements(self, detection_result: InstrumentDetectionResult) -> Dict:
        """
        Get workflow requirements based on detection result.
        
        Args:
            detection_result: Result from instrument detection
            
        Returns:
            Dictionary with workflow requirements
        """
        if detection_result.recommended_workflow == "single_instrument":
            return {
                'workflow': 'single_instrument',
                'show_mapping': True,
                'show_preview': True,
                'show_calculations': True,
                'show_summary': True,
                'show_portfolio_summary': False,
                'display_mode': 'detailed',
                'require_confirmation': True
            }
        elif detection_result.recommended_workflow == "multiple_instruments":
            return {
                'workflow': 'multiple_instruments',
                'show_mapping': True,
                'show_preview': True,
                'show_calculations': True,
                'show_summary': True,
                'show_portfolio_summary': True,
                'display_mode': 'summary',
                'require_confirmation': True,
                'show_individual_details': False  # Show only on "Show Excel" click
            }
        else:
            return {
                'workflow': 'error',
                'show_mapping': False,
                'show_preview': False,
                'show_calculations': False,
                'show_summary': False,
                'show_portfolio_summary': False,
                'display_mode': 'error',
                'require_confirmation': False,
                'error_message': 'Unable to determine instrument type or count'
            }


def create_instrument_detector() -> InstrumentDetector:
    """Factory function to create an instrument detector."""
    return InstrumentDetector()

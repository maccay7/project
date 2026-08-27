"""
Enhanced Field Detection Engine

This module provides comprehensive field detection for financial instrument data,
scanning the entire dataset (not just headers) to detect:
- Column headers
- Label/value pairs
- Nearby labels and values
- Synonyms and spelling variations
- Dates, percentages, currencies and numeric values
- Existing formulas/calculated values

It classifies each detected value as:
- Input (raw user-provided data)
- Existing Worksheet Value (pre-calculated in the sheet)
- Derived Calculation (can be calculated from other inputs)
- Unavailable/Missing Required Input (not found)
"""

from typing import Dict, List, Optional, Tuple, Set, Any
from dataclasses import dataclass
from enum import Enum
import re
from datetime import datetime


class ValueType(Enum):
    """Classification of detected field values."""
    INPUT = "input"  # Raw user-provided data
    EXISTING = "existing"  # Pre-calculated value in worksheet
    DERIVED = "derived"  # Can be calculated from other inputs
    MISSING = "missing"  # Not found or unavailable


@dataclass
class DetectedField:
    """Represents a detected field with its value and classification."""
    field_name: str
    value: Any
    value_type: ValueType
    source: str  # Where it was found (header, label_value, nearby, etc.)
    confidence: float  # 0-1 confidence score
    row: int  # Row index where found
    col: int  # Column index where found
    raw_label: Optional[str] = None  # Original label if from label/value pair


class EnhancedFieldDetector:
    """
    Enhanced field detection engine that scans entire data comprehensively.
    
    This detector:
    - Scans entire dataset, not just headers
    - Detects label/value pairs in various orientations
    - Matches synonyms and spelling variations
    - Identifies numeric, date, percentage, currency patterns
    - Recognizes existing calculated values
    - Classifies values by type (input, existing, derived, missing)
    - Provides confidence scores for detections
    """
    
    def __init__(self):
        # Comprehensive field synonym database
        self.field_synonyms = self._build_field_synonyms()
        
        # Patterns for value type detection
        self.numeric_pattern = re.compile(r'^[\d\,\.\-\$€£¥%]+$')
        self.percentage_pattern = re.compile(r'^[\d\,\.\-\%]+\%?$')
        self.currency_pattern = re.compile(r'^[\$\€\£\¥]?[\d\,\.\-]+[\$\€\£\¥]?$')
        self.date_pattern = re.compile(
            r'^\d{4}[-/]\d{1,2}[-/]\d{1,2}$|'  # YYYY-MM-DD or YYYY/MM/DD
            r'^\d{1,2}[-/]\d{1,2}[-/]\d{4}$|'  # DD-MM-YYYY or DD/MM/YYYY
            r'^\d{1,2}\s+[A-Za-z]{3}\s+\d{4}$|'  # DD Mon YYYY
            r'^[A-Za-z]{3}\s+\d{1,2},\s+\d{4}$'  # Mon DD, YYYY
        )
        
        # Fields that typically indicate calculated values
        self.calculated_field_patterns = [
            'calculated', 'computed', 'derived', 'formula', 'result',
            'total', 'sum', 'average', 'avg', 'present value', 'pv',
            'future value', 'fv', 'dirty price', 'clean price', 'yield',
            'duration', 'convexity', 'accrued', 'discount'
        ]
    
    def _build_field_synonyms(self) -> Dict[str, List[str]]:
        """Build comprehensive synonym database for all financial fields."""
        return {
            # Principal/Face Value
            'principal': ['principal', 'face value', 'face', 'face amount', 'par value', 'par',
                        'nominal', 'nominal value', 'investment amount', 'amount invested',
                        'purchase amount', 'issue price', 'notional', 'notional amount',
                        'capital', 'investment'],
            'face_value': ['face value', 'face', 'face amount', 'par value', 'par',
                         'principal', 'nominal', 'nominal value', 'maturity value'],
            'par_value': ['par value', 'face value', 'principal', 'par'],
            'nominal_value': ['nominal value', 'face value', 'par value', 'notional'],
            'notional': ['notional', 'nominal value', 'face value', 'principal'],
            
            # Interest Rate / Coupon
            'interest_rate': ['interest rate', 'rate', 'coupon rate', 'coupon', 'yield',
                           'annual rate', 'nominal rate', 'stated rate', 'fixed rate',
                           'floating rate', 'apr', 'annual percentage rate'],
            'coupon_rate': ['coupon rate', 'coupon', 'interest rate', 'rate', 'annual coupon'],
            'discount_rate': ['discount rate', 'discount', 'bank discount', 'discount yield'],
            'yield': ['yield', 'ytm', 'yield to maturity', 'investment yield',
                     'money market yield', 'bond equivalent yield', 'bey', 'return'],
            'yield_to_maturity': ['yield to maturity', 'ytm', 'yield'],
            
            # Dates
            'maturity_date': ['maturity date', 'maturity', 'due date', 'expiration date',
                            'redemption date', 'expiry date', 'end date'],
            'settlement_date': ['settlement date', 'settlement', 'trade date', 'value date',
                              'effective date', 'purchase date'],
            'issue_date': ['issue date', 'issuance date', 'origination date', 'start date',
                         'commencement date', 'auction date'],
            'valuation_date': ['valuation date', 'pricing date', 'as of date', 'value date'],
            
            # Duration/Term
            'days_to_maturity': ['days to maturity', 'maturity days', 'term', 'tenor', 'days',
                               'remaining days', 'days remaining', 'term in days'],
            'term': ['term', 'tenor', 'duration', 'maturity', 'period'],
            'tenor': ['tenor', 'term', 'duration', 'maturity'],
            'years_to_maturity': ['years to maturity', 'term in years', 'remaining years'],
            
            # Frequency
            'coupon_frequency': ['coupon frequency', 'frequency', 'payment frequency',
                              'payments per year', 'compounding frequency', 'pmt frequency'],
            'compounding_frequency': ['compounding frequency', 'frequency'],
            
            # Prices
            'purchase_price': ['purchase price', 'purchase', 'price', 'clean price', 'dirty price',
                             'issue price', 'investment amount', 'amount invested', 'cost'],
            'clean_price': ['clean price', 'price', 'quoted price'],
            'dirty_price': ['dirty price', 'full price', 'gross price'],
            'market_price': ['market price', 'current price', 'trading price'],
            
            # Values
            'present_value': ['present value', 'pv', 'current value', 'discounted value'],
            'future_value': ['future value', 'fv', 'maturity value'],
            'fair_value': ['fair value', 'fv', 'market value', 'current value'],
            'market_value': ['market value', 'fair value', 'current value'],
            'carrying_value': ['carrying value', 'book value', 'amortised cost'],
            'book_value': ['book value', 'carrying value', 'amortised cost'],
            
            # Interest
            'accrued_interest': ['accrued interest', 'accrued', 'interest accrued', 'accrued coupon'],
            'interest_earned': ['interest earned', 'interest income', 'interest amount'],
            'interest_amount': ['interest amount', 'interest earned'],
            
            # Identification
            'instrument_name': ['instrument name', 'name', 'security', 'security name',
                              'bond name', 'tbill name', 'description', 'ticker', 'symbol',
                              'counterparty', 'issuer', 'borrower', 'entity', 'company'],
            'instrument_id': ['instrument id', 'id', 'security id', 'bond id', 'tbill id'],
            'isin': ['isin', 'isin code'],
            'cusip': ['cusip', 'cusip code'],
            
            # Currency
            'currency': ['currency', 'denomination', 'ccy', 'currency code', 'curr',
                       'base currency', 'local currency', 'reporting currency'],
            'exchange_rate': ['exchange rate', 'exch rate', 'fx rate', 'forex rate',
                            'conversion rate', 'spot rate', 'forward rate'],
            
            # Country/Region
            'country': ['country', 'jurisdiction', 'nation', 'region'],
            'issuer_country': ['issuer country', 'country of issue', 'issuing country'],
            
            # T-Bill specific
            'price_per_100': ['price per 100', 'clean price', 'price'],
            'bond_equivalent_yield': ['bond equivalent yield', 'investment yield', 'bey'],
            'effective_annual_yield': ['effective annual yield', 'eay', 'effective yield'],
            
            # Bond specific
            'call_date': ['call date', 'optional redemption date'],
            'call_price': ['call price', 'redemption price'],
            'put_date': ['put date', 'optional put date'],
            'put_price': ['put price'],
            'next_coupon_date': ['next coupon date', 'upcoming coupon date'],
            
            # Day count
            'day_count_convention': ['day count', 'day count convention', 'day basis',
                                   'basis', 'day count basis'],
            'days_in_year': ['days in year', 'day count basis']
        }
    
    def detect_fields(self, data: List[Dict], instrument_type: str = 'money-market') -> Dict[str, DetectedField]:
        """
        Detect all financial fields from the entire dataset.
        
        Args:
            data: List of data rows (dictionaries)
            instrument_type: Type of instrument ('money-market', 'tbills', 'bonds')
            
        Returns:
            Dictionary mapping field names to DetectedField objects
        """
        if not data or not isinstance(data, list):
            return {}
        
        detected_fields = {}
        
        # Step 0: Analyze worksheet structure to understand data organization
        structure_analysis = self._analyze_worksheet_structure(data)
        
        # Step 1: Detect from column headers (traditional approach)
        header_detections = self._detect_from_headers(data, structure_analysis)
        detected_fields.update(header_detections)
        
        # Step 2: Detect from label/value pairs (vertical orientation)
        label_value_detections = self._detect_from_label_value_pairs(data, structure_analysis)
        # Merge with existing, keeping higher confidence
        for field_name, detection in label_value_detections.items():
            if field_name not in detected_fields or detection.confidence > detected_fields[field_name].confidence:
                detected_fields[field_name] = detection
        
        # Step 3: Detect from nearby labels and values
        nearby_detections = self._detect_from_nearby_labels(data, structure_analysis)
        for field_name, detection in nearby_detections.items():
            if field_name not in detected_fields or detection.confidence > detected_fields[field_name].confidence:
                detected_fields[field_name] = detection
        
        # Step 4: Detect from value patterns (numeric, date, percentage)
        pattern_detections = self._detect_from_value_patterns(data, detected_fields)
        for field_name, detection in pattern_detections.items():
            if field_name not in detected_fields or detection.confidence > detected_fields[field_name].confidence:
                detected_fields[field_name] = detection
        
        # Step 5: Classify detected values
        detected_fields = self._classify_values(detected_fields, data)
        
        # Step 6: Identify missing required fields
        required_fields = self._get_required_fields(instrument_type)
        for field in required_fields:
            if field not in detected_fields:
                detected_fields[field] = DetectedField(
                    field_name=field,
                    value=None,
                    value_type=ValueType.MISSING,
                    source='not_detected',
                    confidence=0.0,
                    row=-1,
                    col=-1
                )
        
        return required_fields.get(instrument_type, [])
    
    def _analyze_worksheet_structure(self, data: List[Dict]) -> Dict[str, Any]:
        """
        Analyze worksheet structure to understand data organization.
        
        This method identifies:
        - Cell content types (empty, numeric, date, text, header, label, data)
        - Potential header rows
        - Label-value pair patterns
        - Table structures
        - Section boundaries
        
        Returns:
            Dictionary containing structure analysis results
        """
        if not data:
            return {}
        
        structure = {
            'cell_types': [],
            'potential_header_rows': [],
            'label_value_pairs': [],
            'table_regions': [],
            'section_boundaries': []
        }
        
        # Analyze each cell's content type
        for row_idx, row in enumerate(data):
            row_types = {}
            for col_idx, (key, value) in enumerate(row.items()):
                cell_type = self._classify_cell_content(value)
                row_types[key] = cell_type
            structure['cell_types'].append(row_types)
        
        # Identify potential header rows
        for row_idx, row_types in enumerate(structure['cell_types']):
            header_count = 0
            total_cells = 0
            
            for key, cell_type in row_types.items():
                if cell_type['type'] != 'empty':
                    total_cells += 1
                    if cell_type['is_header']:
                        header_count += 1
            
            # If more than 50% of non-empty cells look like headers
            if total_cells >= 2 and header_count / total_cells >= 0.5:
                structure['potential_header_rows'].append(row_idx)
        
        # Identify label-value pairs
        for row_idx in range(len(data) - 1):
            current_row = data[row_idx]
            next_row = data[row_idx + 1]
            
            for key, label_cell in current_row.items():
                label_str = str(label_cell).strip() if label_cell else ''
                if not label_str:
                    continue
                
                label_type = structure['cell_types'][row_idx].get(key, {})
                if label_type.get('is_label', False):
                    value_cell = next_row.get(key)
                    if value_cell is not None and str(value_cell).strip() not in ['', ' ', 'N/A', 'n/a', '-']:
                        structure['label_value_pairs'].append({
                            'row': row_idx,
                            'col': key,
                            'label': label_str,
                            'value': value_cell,
                            'orientation': 'vertical'
                        })
        
        # Horizontal label-value pairs
        for row_idx, row in enumerate(data):
            keys = list(row.keys())
            for col_idx in range(len(keys) - 1):
                label_cell = row[keys[col_idx]]
                value_cell = row[keys[col_idx + 1]]
                
                label_str = str(label_cell).strip() if label_cell else ''
                if not label_str:
                    continue
                
                label_type = structure['cell_types'][row_idx].get(keys[col_idx], {})
                if label_type.get('is_label', False):
                    if value_cell is not None and str(value_cell).strip() not in ['', ' ', 'N/A', 'n/a', '-']:
                        structure['label_value_pairs'].append({
                            'row': row_idx,
                            'col': keys[col_idx],
                            'label': label_str,
                            'value': value_cell,
                            'orientation': 'horizontal'
                        })
        
        # Identify table regions (header row + data rows)
        for header_row in structure['potential_header_rows']:
            start_col = None
            end_col = None
            
            # Find column range
            for key in data[header_row].keys():
                if structure['cell_types'][header_row][key]['type'] != 'empty':
                    if start_col is None:
                        start_col = key
                    end_col = key
            
            if start_col is None:
                continue
            
            # Find end of table
            end_row = header_row
            consecutive_empty = 0
            
            for row_idx in range(header_row + 1, len(data)):
                has_data = False
                for key in data[row_idx].keys():
                    if structure['cell_types'][row_idx][key]['type'] != 'empty':
                        has_data = True
                        break
                
                if has_data:
                    end_row = row_idx
                    consecutive_empty = 0
                else:
                    consecutive_empty += 1
                    if consecutive_empty >= 2:
                        break
            
            if end_row > header_row:
                structure['table_regions'].append({
                    'start_row': header_row,
                    'end_row': end_row,
                    'start_col': start_col,
                    'end_col': end_col
                })
        
        # Identify section boundaries (empty rows)
        for row_idx, row in enumerate(data):
            is_empty = all(
                structure['cell_types'][row_idx][key]['type'] == 'empty'
                for key in row.keys()
            )
            if is_empty:
                structure['section_boundaries'].append(row_idx)
        
        return structure
    
    def _classify_cell_content(self, value: Any) -> Dict[str, Any]:
        """
        Classify cell content type.
        
        Returns:
            Dictionary with type classification and flags
        """
        if value is None or value == '':
            return {'type': 'empty', 'is_header': False, 'is_label': False, 'is_data': False}
        
        text = str(value).strip()
        is_numeric = self.numeric_pattern.match(text)
        is_date = self.date_pattern.match(text)
        is_percentage = self.percentage_pattern.match(text)
        
        # Header keywords
        header_keywords = ['name', 'date', 'rate', 'value', 'amount', 'price', 'yield', 
                          'coupon', 'maturity', 'issue', 'principal', 'face', 'discount', 
                          'interest', 'term', 'tenor', 'frequency', 'currency', 'country', 
                          'instrument', 'bond', 'bill', 'security']
        
        is_header_keyword = any(keyword in text.lower() for keyword in header_keywords)
        is_short_text = len(text) < 50 and not is_numeric and not is_date
        is_header = is_short_text and (is_header_keyword or (text and text[0].isupper()))
        
        # Label detection
        label_patterns = [r'^(.+?)\s*[:=]\s*$', r'^(.+?)\s*$']
        is_label = is_short_text and (
            any(re.match(pattern, text) for pattern in label_patterns) or is_header_keyword
        )
        
        # Data detection
        is_data = is_numeric or is_date or is_percentage or (not is_header and not is_label and text)
        
        cell_type = 'numeric' if is_numeric else 'date' if is_date else 'percentage' if is_percentage else 'text'
        
        return {
            'type': cell_type,
            'is_header': is_header,
            'is_label': is_label,
            'is_data': is_data,
            'text': text,
            'length': len(text)
        }
    
    def _detect_from_headers(self, data: List[Dict], structure_analysis: Dict[str, Any]) -> Dict[str, DetectedField]:
        """Detect fields from column headers."""
        detections = {}
        
        if not data:
            return detections
        
        # Check all rows for headers, not just first row
        for row_idx, row in enumerate(data):
            headers = list(row.keys())
            
            for col_idx, header in enumerate(headers):
                if not header:
                    continue
                
                matched_field = self._match_field_to_synonym(header)
                
                if matched_field:
                    # Get the first non-empty value for this column
                    value = None
                    for check_row in data:
                        if header in check_row and check_row[header] not in [None, '', ' ']:
                            value = check_row[header]
                            break
                    
                    if value is not None:
                        # Only add if not already detected with higher confidence
                        if matched_field not in detections or 0.9 > detections[matched_field].confidence:
                            detections[matched_field] = DetectedField(
                                field_name=matched_field,
                                value=value,
                                value_type=ValueType.INPUT,  # Will be reclassified later
                                source='header',
                                confidence=0.9,
                                row=row_idx,
                                col=col_idx,
                                raw_label=header
                            )
        
        return detections
    
    def _detect_from_label_value_pairs(self, data: List[Dict], structure_analysis: Dict[str, Any]) -> Dict[str, DetectedField]:
        """Detect fields from label/value pairs (vertical orientation)."""
        detections = {}
        
        if not data:
            return detections
        
        # Scan all rows for label/value pairs
        for row_idx, row in enumerate(data):
            keys = list(row.keys())
            
            for col_idx in range(len(keys) - 1):
                label_cell = row[keys[col_idx]]
                value_cell = row[keys[col_idx + 1]]
                
                if not label_cell:
                    continue
                
                label_str = str(label_cell).strip()
                
                matched_field = self._match_field_to_synonym(label_str)
                
                if matched_field and value_cell is not None and str(value_cell).strip() not in ['', ' ', 'N/A', 'n/a', '-']:
                    # Try to parse the value
                    parsed_value = self._parse_value(str(value_cell).strip())
                    
                    # Only add if not already detected with higher confidence
                    if matched_field not in detections or 0.85 > detections[matched_field].confidence:
                        detections[matched_field] = DetectedField(
                            field_name=matched_field,
                            value=parsed_value,
                            value_type=ValueType.INPUT,  # Will be reclassified later
                            source='label_value_pair',
                            confidence=0.85,
                            row=row_idx,
                            col=col_idx + 1,
                            raw_label=label_str
                        )
        
        return detections
    
    def _detect_from_nearby_labels(self, data: List[Dict], structure_analysis: Dict[str, Any]) -> Dict[str, DetectedField]:
        """Detect fields from nearby labels and values (horizontal scanning)."""
        detections = {}
        
        if not data or len(data) < 2:
            return detections
        
        # Scan all adjacent row pairs
        for row_idx in range(len(data) - 1):
            current_row = data[row_idx]
            next_row = data[row_idx + 1]
            
            for col_idx, (key, label_cell) in enumerate(current_row.items()):
                if not label_cell:
                    continue
                
                label_str = str(label_cell).strip()
                matched_field = self._match_field_to_synonym(label_str)
                
                if matched_field:
                    # Look for value in same column in next row
                    value_cell = next_row.get(key)
                    if value_cell is not None and str(value_cell).strip() not in ['', ' ', 'N/A', 'n/a', '-']:
                        parsed_value = self._parse_value(str(value_cell).strip())
                        
                        # Only add if not already detected with higher confidence
                        if matched_field not in detections or 0.75 > detections[matched_field].confidence:
                            detections[matched_field] = DetectedField(
                                field_name=matched_field,
                                value=parsed_value,
                                value_type=ValueType.INPUT,  # Will be reclassified later
                                source='nearby_label',
                                confidence=0.75,
                                row=row_idx + 1,
                                col=col_idx,
                                raw_label=label_str
                            )
        
        return detections
    
    def _detect_from_value_patterns(self, data: List[Dict], 
                                   existing_detections: Dict[str, DetectedField]) -> Dict[str, DetectedField]:
        """Detect fields based on value patterns (numeric, date, percentage)."""
        detections = {}
        
        if not data:
            return detections
        
        # Only detect fields not already found
        already_detected = set(existing_detections.keys())
        
        for row_idx, row in enumerate(data):
            for col_idx, (key, value) in enumerate(row.items()):
                if key in already_detected:
                    continue
                
                if value is None or value == '':
                    continue
                
                value_str = str(value).strip()
                
                # Check for percentage values (likely interest/discount rates)
                if self.percentage_pattern.match(value_str):
                    if 'interest_rate' not in already_detected:
                        detections['interest_rate'] = DetectedField(
                            field_name='interest_rate',
                            value=self._parse_value(value_str),
                            value_type=ValueType.INPUT,
                            source='percentage_pattern',
                            confidence=0.6,
                            row=row_idx,
                            col=col_idx
                        )
                    elif 'discount_rate' not in already_detected:
                        detections['discount_rate'] = DetectedField(
                            field_name='discount_rate',
                            value=self._parse_value(value_str),
                            value_type=ValueType.INPUT,
                            source='percentage_pattern',
                            confidence=0.6,
                            row=row_idx,
                            col=col_idx
                        )
                    elif 'coupon_rate' not in already_detected:
                        detections['coupon_rate'] = DetectedField(
                            field_name='coupon_rate',
                            value=self._parse_value(value_str),
                            value_type=ValueType.INPUT,
                            source='percentage_pattern',
                            confidence=0.6,
                            row=row_idx,
                            col=col_idx
                        )
                
                # Check for currency values (likely principal/face value)
                elif self.currency_pattern.match(value_str):
                    if 'principal' not in already_detected:
                        detections['principal'] = DetectedField(
                            field_name='principal',
                            value=self._parse_value(value_str),
                            value_type=ValueType.INPUT,
                            source='currency_pattern',
                            confidence=0.6,
                            row=row_idx,
                            col=col_idx
                        )
                    elif 'face_value' not in already_detected:
                        detections['face_value'] = DetectedField(
                            field_name='face_value',
                            value=self._parse_value(value_str),
                            value_type=ValueType.INPUT,
                            source='currency_pattern',
                            confidence=0.6,
                            row=row_idx,
                            col=col_idx
                        )
                
                # Check for date values
                elif self.date_pattern.match(value_str):
                    # Try to match to date fields
                    for date_field in ['maturity_date', 'settlement_date', 'issue_date', 'valuation_date']:
                        if date_field not in already_detected:
                            detections[date_field] = DetectedField(
                                field_name=date_field,
                                value=self._parse_date(value_str),
                                value_type=ValueType.INPUT,
                                source='date_pattern',
                                confidence=0.5,
                                row=row_idx,
                                col=col_idx
                            )
                            break  # Only assign to first matching date field
        
        return detections
    
    def _classify_values(self, detections: Dict[str, DetectedField], data: List[Dict]) -> Dict[str, DetectedField]:
        """Classify detected values as input, existing, derived, or missing."""
        
        for field_name, detection in detections.items():
            if detection.value_type == ValueType.MISSING:
                continue
            
            # Check if field name suggests it's a calculated value
            if any(pattern in field_name.lower() for pattern in self.calculated_field_patterns):
                detection.value_type = ValueType.EXISTING
                continue
            
            # Check if the source suggests it's calculated
            if detection.source in ['existing_formula', 'calculated_cell']:
                detection.value_type = ValueType.EXISTING
                continue
            
            # Check if it can be derived from other fields
            if self._can_be_derived(field_name, detections):
                detection.value_type = ValueType.DERIVED
            else:
                detection.value_type = ValueType.INPUT
        
        return detections
    
    def _can_be_derived(self, field_name: str, detections: Dict[str, DetectedField]) -> bool:
        """Check if a field can be derived from other detected fields."""
        
        # Define derivation rules
        derivation_rules = {
            'days_to_maturity': ['settlement_date', 'maturity_date'],
            'term': ['settlement_date', 'maturity_date'],
            'years_to_maturity': ['settlement_date', 'maturity_date'],
            'annual_coupon': ['face_value', 'coupon_rate'],
            'coupon_payment': ['face_value', 'coupon_rate', 'coupon_frequency'],
            'discount_amount': ['face_value', 'purchase_price'],
            'investment_yield': ['face_value', 'purchase_price', 'days_to_maturity'],
            'simple_interest': ['principal', 'interest_rate', 'days_to_maturity'],
            'present_value': ['future_value', 'interest_rate', 'days_to_maturity']
        }
        
        required_fields = derivation_rules.get(field_name, [])
        
        # Check if all required fields are available as INPUT or EXISTING
        for req_field in required_fields:
            if req_field not in detections:
                return False
            if detections[req_field].value_type in [ValueType.MISSING]:
                return False
        
        return len(required_fields) > 0
    
    def _match_field_to_synonym(self, text: str) -> Optional[str]:
        """Match a text string to a field name using synonyms."""
        if not text:
            return None
        
        text_lower = text.lower().strip()
        
        # Direct match
        for field_name, synonyms in self.field_synonyms.items():
            if text_lower == field_name.lower():
                return field_name
            for synonym in synonyms:
                if text_lower == synonym.lower():
                    return field_name
        
        # Contains match
        for field_name, synonyms in self.field_synonyms.items():
            if field_name.lower() in text_lower or text_lower in field_name.lower():
                return field_name
            for synonym in synonyms:
                if synonym.lower() in text_lower or text_lower in synonym.lower():
                    return field_name
        
        return None
    
    def _parse_value(self, value_str: str) -> Any:
        """Parse a string value to appropriate type."""
        if not value_str:
            return None
        
        value_str = value_str.strip()
        
        # Try to parse as number
        try:
            # Remove currency symbols, commas, percentage signs
            cleaned = value_str.replace('$', '').replace('€', '').replace('£', '').replace('¥', '')
            cleaned = cleaned.replace(',', '').replace('%', '')
            
            # Check if it's a decimal
            if '.' in cleaned:
                return float(cleaned)
            else:
                return int(cleaned)
        except (ValueError, TypeError):
            pass
        
        # Return as string if not numeric
        return value_str
    
    def _parse_date(self, date_str: str) -> str:
        """Parse a date string to ISO format (YYYY-MM-DD)."""
        if not date_str:
            return None
        
        date_str = date_str.strip()
        
        # Try common date formats
        date_formats = [
            '%Y-%m-%d',
            '%Y/%m/%d',
            '%d-%m-%Y',
            '%d/%m/%Y',
            '%m-%d-%Y',
            '%m/%d/%Y',
            '%d %b %Y',
            '%b %d, %Y'
        ]
        
        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                return parsed_date.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        # Return original if parsing fails
        return date_str
    
    def _looks_like_label(self, text: str) -> bool:
        """Check if text looks like a label rather than a value."""
        if not text:
            return False
        
        text_lower = text.lower().strip()
        
        # If it contains letters and is relatively short, it's likely a label
        if len(text_lower) > 2 and len(text_lower) < 50:
            # Check if it contains alphabetic characters
            if any(c.isalpha() for c in text_lower):
                # Check if it's not purely numeric
                if not self.numeric_pattern.match(text_lower):
                    return True
        
        return False
    
    def _get_required_fields(self, instrument_type: str) -> List[str]:
        """Get required fields for a given instrument type."""
        required_fields = {
            'money-market': ['principal', 'interest_rate'],
            'tbills': ['face_value', 'discount_rate'],
            'bonds': ['face_value', 'coupon_rate', 'yield_to_maturity']
        }
        
        return required_fields.get(instrument_type, [])
    
    def get_detection_summary(self, detections: Dict[str, DetectedField]) -> Dict[str, Any]:
        """Generate a summary of detection results."""
        summary = {
            'total_fields_detected': len(detections),
            'input_fields': 0,
            'existing_fields': 0,
            'derived_fields': 0,
            'missing_fields': 0,
            'fields_by_type': {},
            'confidence_scores': {}
        }
        
        for field_name, detection in detections.items():
            # Count by type
            if detection.value_type == ValueType.INPUT:
                summary['input_fields'] += 1
            elif detection.value_type == ValueType.EXISTING:
                summary['existing_fields'] += 1
            elif detection.value_type == ValueType.DERIVED:
                summary['derived_fields'] += 1
            elif detection.value_type == ValueType.MISSING:
                summary['missing_fields'] += 1
            
            # Track confidence
            summary['confidence_scores'][field_name] = detection.confidence
        
        return summary


def create_enhanced_field_detector() -> EnhancedFieldDetector:
    """Factory function to create an enhanced field detector."""
    return EnhancedFieldDetector()

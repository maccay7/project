import json
from flask import request, jsonify
from utils.db import get_db
import pandas as pd
import numpy as np
from datetime import datetime


def create_processed_data_table():
    """Create the processed_data table if it doesn't exist."""
    conn = get_db()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processed_data (
                id INT AUTO_INCREMENT PRIMARY KEY,
                dataset_id INT NOT NULL,
                instrument_type VARCHAR(50) NOT NULL,
                original_data JSON,
                cleaned_data JSON,
                cleaning_options JSON,
                processing_stats JSON,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error creating processed_data table: {e}")
        conn.close()
        return False


def clean_data(data, cleaning_options):
    """
    Clean data based on provided options.
    Returns: { cleaned_data: [], stats: {} }
    """
    if not data or not isinstance(data, list):
        return {'cleaned_data': [], 'stats': {}}
    
    df = pd.DataFrame(data)
    original_rows = len(df)
    
    stats = {
        'original_rows': original_rows,
        'removed_duplicates': 0,
        'filled_missing_text': 0,
        'removed_missing_rows': 0,
        'trimmed_whitespace': 0,
        'final_rows': original_rows
    }
    
    # Remove duplicates
    if cleaning_options.get('removeDuplicates', True):
        before_dedup = len(df)
        df = df.drop_duplicates()
        stats['removed_duplicates'] = before_dedup - len(df)
    
    # Fill missing text values
    if cleaning_options.get('fillMissingText', True):
        text_columns = df.select_dtypes(include=['object']).columns
        for col in text_columns:
            filled_count = df[col].fillna('').count()
            stats['filled_missing_text'] += filled_count
    
    # Drop rows with missing values
    if cleaning_options.get('dropRowsWithMissing', False):
        before_drop = len(df)
        df = df.dropna()
        stats['removed_missing_rows'] = before_drop - len(df)
    
    # Trim whitespace
    if cleaning_options.get('trimWhitespace', True):
        text_columns = df.select_dtypes(include=['object']).columns
        for col in text_columns:
            df[col] = df[col].astype(str).str.strip()
            stats['trimmed_whitespace'] = len(df)
    
    # Convert back to list of dicts
    cleaned_data = df.to_dict('records')
    stats['final_rows'] = len(cleaned_data)
    
    return {
        'cleaned_data': cleaned_data,
        'stats': stats
    }


def validate_row(row, required_fields):
    """
    Validate a row against required fields.
    Returns: { valid: bool, missing: [], invalid: [] }
    """
    missing = []
    invalid = []
    
    for field in required_fields:
        value = row.get(field)
        if value is None or value == '' or value == 0:
            missing.append(field)
    
    # Type validation for numeric fields
    numeric_fields = ['Principal', 'FaceValue', 'InterestRate', 'CouponRate', 'DiscountRate', 'DaysToMaturity', 'Yield', 'Price']
    for field in numeric_fields:
        if field in row:
            try:
                float(row[field])
            except (ValueError, TypeError):
                invalid.append({'field': field, 'error': 'Must be a number'})
    
    return {
        'valid': len(missing) == 0 and len(invalid) == 0,
        'missing': missing,
        'invalid': invalid
    }


def apply_mapping(data, column_mapping):
    """
    Apply column mapping to data.
    column_mapping: { system_column: file_column }
    """
    if not data or not column_mapping:
        return data
    
    mapped_data = []
    for row in data:
        mapped_row = {}
        for system_col, file_col in column_mapping.items():
            if file_col and file_col in row:
                mapped_row[system_col] = row[file_col]
            else:
                mapped_row[system_col] = ''
        mapped_data.append(mapped_row)
    
    return mapped_data


def auto_match_columns(file_columns, required_columns):
    """
    Automatically match file columns to required system columns using keywords.
    Returns: { system_column: file_column }
    """
    # Keywords for each system column
    keywords = {
        'Principal': ['principal', 'principal amount', 'investment', 'amount', 'notional'],
        'InterestRate': ['interest rate', 'rate', 'interest', 'coupon'],
        'InvestmentAmount': ['investment amount', 'investment', 'amount'],
        'DaysToMaturity': ['days to maturity', 'maturity days', 'term', 'tenor'],
        'CouponRate': ['coupon rate', 'coupon', 'rate'],
        'CouponFrequency': ['coupon frequency', 'frequency', 'payment frequency'],
        'FaceValue': ['face value', 'face', 'par value', 'par', 'amount'],
        'Yield': ['yield', 'ytm', 'yield to maturity'],
        'SettlementDate': ['settlement date', 'settlement', 'trade date'],
        'MaturityDate': ['maturity date', 'maturity', 'due date'],
        'DiscountRate': ['discount rate', 'discount'],
        'PurchasePrice': ['purchase price', 'purchase', 'price'],
        'RedemptionValue': ['redemption value', 'redemption']
    }
    
    mapping = {}
    
    for system_col in required_columns:
        system_keywords = keywords.get(system_col, [])
        for file_col in file_columns:
            file_col_lower = str(file_col).lower()
            if any(kw in file_col_lower for kw in system_keywords):
                mapping[system_col] = file_col
                break
    
    return mapping


def data_processing_routes(app):
    """Register all data processing routes."""
    
    # Create table on module load
    create_processed_data_table()
    
    @app.route('/api/data/clean', methods=['POST', 'OPTIONS'])
    def clean_dataset():
        if request.method == 'OPTIONS':
            return '', 200
        
        payload = request.get_json() or {}
        data = payload.get('data', [])
        cleaning_options = payload.get('cleaning_options', {
            'removeDuplicates': True,
            'fillMissingText': True,
            'dropRowsWithMissing': False,
            'trimWhitespace': True
        })
        
        result = clean_data(data, cleaning_options)
        
        return jsonify({
            'success': True,
            'data': result
        })
    
    @app.route('/api/data/validate', methods=['POST', 'OPTIONS'])
    def validate_dataset():
        if request.method == 'OPTIONS':
            return '', 200
        
        payload = request.get_json() or {}
        data = payload.get('data', [])
        required_fields = payload.get('required_fields', [])
        
        validation_results = []
        for idx, row in enumerate(data):
            validation = validate_row(row, required_fields)
            validation_results.append({
                'row_index': idx,
                'valid': validation['valid'],
                'missing': validation['missing'],
                'invalid': validation['invalid']
            })
        
        valid_count = sum(1 for r in validation_results if r['valid'])
        
        return jsonify({
            'success': True,
            'data': {
                'total_rows': len(validation_results),
                'valid_rows': valid_count,
                'invalid_rows': len(validation_results) - valid_count,
                'results': validation_results
            }
        })
    
    @app.route('/api/data/apply-mapping', methods=['POST', 'OPTIONS'])
    def apply_column_mapping():
        if request.method == 'OPTIONS':
            return '', 200
        
        payload = request.get_json() or {}
        data = payload.get('data', [])
        column_mapping = payload.get('column_mapping', {})
        
        mapped_data = apply_mapping(data, column_mapping)
        
        return jsonify({
            'success': True,
            'data': mapped_data
        })
    
    @app.route('/api/data/auto-match', methods=['POST', 'OPTIONS'])
    def auto_match_columns_endpoint():
        if request.method == 'OPTIONS':
            return '', 200
        
        payload = request.get_json() or {}
        file_columns = payload.get('file_columns', [])
        required_columns = payload.get('required_columns', [])
        
        mapping = auto_match_columns(file_columns, required_columns)
        
        return jsonify({
            'success': True,
            'data': mapping
        })
    
    @app.route('/api/data/process', methods=['POST', 'OPTIONS'])
    def process_dataset():
        if request.method == 'OPTIONS':
            return '', 200
        
        payload = request.get_json() or {}
        dataset_id = payload.get('dataset_id')
        data = payload.get('data', [])
        column_mapping = payload.get('column_mapping', {})
        cleaning_options = payload.get('cleaning_options', {})
        required_fields = payload.get('required_fields', [])
        instrument_type = payload.get('instrument_type', 'money-market')
        
        # Apply mapping
        mapped_data = apply_mapping(data, column_mapping)
        
        # Clean data
        cleaning_result = clean_data(mapped_data, cleaning_options)
        cleaned_data = cleaning_result['cleaned_data']
        
        # Validate data
        validation_results = []
        for idx, row in enumerate(cleaned_data):
            validation = validate_row(row, required_fields)
            validation_results.append({
                'row_index': idx,
                'valid': validation['valid'],
                'missing': validation['missing'],
                'invalid': validation['invalid']
            })
        
        valid_count = sum(1 for r in validation_results if r['valid'])
        
        # Save to database
        conn = get_db()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO processed_data 
                       (dataset_id, instrument_type, original_data, cleaned_data, cleaning_options, processing_stats) 
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (dataset_id, instrument_type, json.dumps(data), json.dumps(cleaned_data), 
                     json.dumps(cleaning_options), json.dumps(cleaning_result['stats']))
                )
                conn.commit()
                processed_id = cursor.lastrowid
                cursor.close()
                conn.close()
            except Exception as e:
                print(f"Error saving processed data: {e}")
                conn.close()
                processed_id = None
        
        return jsonify({
            'success': True,
            'data': {
                'processed_id': processed_id,
                'cleaned_data': cleaned_data,
                'stats': cleaning_result['stats'],
                'validation': {
                    'total_rows': len(validation_results),
                    'valid_rows': valid_count,
                    'invalid_rows': len(validation_results) - valid_count,
                    'results': validation_results
                }
            }
        })

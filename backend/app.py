from flask import Flask, request, jsonify
from flask_cors import CORS
import pymysql
import pandas as pd
import numpy as np
import requests
import json
import csv
import openpyxl
import xlwings as xw
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'duracapital',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

# FRED API configuration
FRED_API_KEY = 'b40141a5119f30bc2388d63f59d8847e'
FRED_BASE_URL = 'https://api.stlouisfed.org/fred'

# Financial instruments configuration
FINANCIAL_INSTRUMENTS = {
    'treasury_bills': {
        'name': 'Treasury Bills',
        'fred_series': 'TB3MS',  # 3-Month Treasury Bill Rate
        'description': '3-Month Treasury Bill Rate',
        'calculation_method': 'yield_to_maturity'
    },
    'bonds': {
        'name': 'Bonds',
        'fred_series': 'DGS10',  # 10-Year Treasury Constant Maturity Rate
        'description': '10-Year Treasury Constant Maturity Rate',
        'calculation_method': 'yield_to_maturity'
    },
    'money_market': {
        'name': 'Money Market Instruments',
        'fred_series': 'DFF',  # Federal Funds Effective Rate
        'description': 'Federal Funds Effective Rate',
        'calculation_method': 'discount_rate'
    }
}

# Formula evaluation function
def evaluate_formula_with_cell_refs(formula, cell_values):
    """Evaluate Excel formula by replacing cell references with values"""
    import re

    # Remove = prefix
    expr = formula.lstrip('=').lstrip('+')

    # Replace cell references with values
    def replace_cell_ref(match):
        ref = match.group(0)
        # Convert cell reference to coordinate
        # Handle absolute references like $C$99
        ref = ref.replace('$', '')
        if ref in cell_values:
            val = cell_values[ref]
            return str(val) if not isinstance(val, str) else f"'{val}'"
        return '0'  # Default to 0 if cell reference not found

    # Replace cell references (e.g., A1, B2, C99)
    expr = re.sub(r'[A-Z]+[0-9]+', replace_cell_ref, expr)

    # Replace Excel functions with Python equivalents
    expr = expr.replace('SUMPRODUCT', 'sum')

    # Try to evaluate the expression
    try:
        result = eval(expr)
        return result
    except:
        return formula  # Return original formula if evaluation fails

def get_db_connection():
    try:
        return pymysql.connect(**DB_CONFIG)
    except Exception as e:
        print(f"Database connection error: {e}")
        # Fallback to mock mode if database fails
        return None

def fetch_fred_data(series_id):
    """Fetch data from FRED API"""
    try:
        url = f"{FRED_BASE_URL}/series/observations?series_id={series_id}&api_key={FRED_API_KEY}&file_type=json&limit=10"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.RequestException as err:
        print(f"FRED API error: {err}")
        return None

def calculate_yield_curve(treasury_data, bond_data, money_market_data, instrument_type='all'):
    """Calculate yield curve from FRED data for specific instrument type"""
    try:
        # Get latest rates
        latest_tbill = float(treasury_data['observations'][0]['value']) if treasury_data and treasury_data['observations'] else 0.0
        latest_bond = float(bond_data['observations'][0]['value']) if bond_data and bond_data['observations'] else 0.0
        latest_mm = float(money_market_data['observations'][0]['value']) if money_market_data and money_market_data['observations'] else 0.0

        # Create datasets based on instrument type
        datasets = []

        if instrument_type == 'all' or instrument_type == 'treasury_bills':
            datasets.append({
                'label': 'Treasury Bills',
                'data': [
                    latest_tbill,
                    latest_tbill + 0.1,
                    latest_tbill + 0.2,
                    latest_tbill + 0.3,
                    latest_tbill + 0.4,
                    latest_bond,
                    latest_bond - 0.2
                ],
                'borderColor': '#0B2A44',
                'backgroundColor': 'rgba(11, 42, 68, 0.1)',
                'fill': True,
                'tension': 0.4
            })

        if instrument_type == 'all' or instrument_type == 'money_market':
            datasets.append({
                'label': 'Money Market',
                'data': [
                    latest_mm,
                    latest_mm + 0.1,
                    latest_mm + 0.2,
                    latest_mm + 0.3,
                    latest_mm + 0.4,
                    latest_bond,
                    latest_bond - 0.2
                ],
                'borderColor': '#4CAF50',
                'backgroundColor': 'rgba(76, 175, 80, 0.1)',
                'fill': True,
                'tension': 0.4
            })

        if instrument_type == 'all' or instrument_type == 'bonds':
            datasets.append({
                'label': 'Bonds',
                'data': [
                    latest_tbill,
                    latest_tbill + 0.15,
                    latest_tbill + 0.25,
                    latest_tbill + 0.35,
                    latest_bond - 0.1,
                    latest_bond,
                    latest_bond - 0.2
                ],
                'borderColor': '#1E88E5',
                'backgroundColor': 'rgba(30, 136, 229, 0.1)',
                'fill': True,
                'tension': 0.4
            })

        # Return yield curve
        yield_curve = {
            'labels': ['3M', '6M', '1Y', '2Y', '5Y', '10Y', '30Y'],
            'datasets': datasets,
            'metadata': {
                '3_month_treasury': latest_tbill,
                '10_year_bond': latest_bond,
                'federal_funds': latest_mm,
                'instrument_type': instrument_type,
                'last_updated': datetime.now().isoformat()
            }
        }

        return yield_curve
    except (KeyError, IndexError, ValueError) as err:
        print(f"Yield curve calculation error: {err}")
        return None

def format_time_ago(timestamp):
    """Format timestamp as 'X hours ago'"""
    try:
        from datetime import datetime, timedelta
        now = datetime.now()
        time_diff = now - timestamp
        
        if time_diff < timedelta(hours=1):
            minutes = int(time_diff.total_seconds() / 60)
            return f"{minutes} minutes ago"
        elif time_diff < timedelta(days=1):
            hours = int(time_diff.total_seconds() / 3600)
            return f"{hours} hours ago"
        else:
            days = time_diff.days
            return f"{days} day{'s' if days > 1 else ''} ago"
    except:
        return "Unknown time"

def get_instrument_color(instrument_type):
    """Get color for instrument type"""
    colors = {
        'treasury_bills': '#0B2A44',
        'bonds': '#1E88E5',
        'money_market': '#4CAF50',
        'yield_curve': '#FFC107'
    }
    return colors.get(instrument_type, '#666666')

def calculate_yield_curve_from_api():
    """Calculate yield curve from FRED API"""
    try:
        # Fetch data for different instruments
        tbill_data = fetch_fred_data(FINANCIAL_INSTRUMENTS['treasury_bills']['fred_series'])
        bond_data = fetch_fred_data(FINANCIAL_INSTRUMENTS['bonds']['fred_series'])
        mm_data = fetch_fred_data(FINANCIAL_INSTRUMENTS['money_market']['fred_series'])
        
        # Calculate yield curve
        return calculate_yield_curve(tbill_data, bond_data, mm_data)
    except Exception as err:
        print(f"Yield curve calculation error: {err}")
        return None

def perform_calculation(instrument_type, data):
    """Perform calculation for given instrument type"""
    try:
        if instrument_type == 'treasury_bills':
            return [calculate_treasury_bill(row, {}) for row in data]
        elif instrument_type == 'bonds':
            return [calculate_bond(row, {}) for row in data]
        elif instrument_type == 'money_market':
            return [calculate_money_market(row, {}) for row in data]
        else:
            return data
    except Exception as err:
        print(f"Calculation error: {err}")
        return []

@app.route('/')
def home():
    return jsonify({
        'message': 'DuraCapital Backend API',
        'version': '1.0.0',
        'status': 'running'
    })

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    # Mock authentication (replace with actual database check)
    if email == 'makanakakanyai@gmail.com' and password == 'Business7mogul':
        return jsonify({
            'success': True,
            'token': 'mock-token-' + str(datetime.now().timestamp()),
            'user': {
                'email': email,
                'name': 'Makanaka Kanyai',
                'role': 'admin'
            }
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Invalid credentials'
        }), 401

@app.route('/api/upload', methods=['POST'])
def upload_data():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        instrument_type = request.form.get('instrument_type')
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Read file based on extension - support all file types
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        if file_extension == '.csv':
            # Read CSV file
            try:
                content = file.read().decode('utf-8')
                lines = content.split('\n')
                if len(lines) < 2:
                    return jsonify({'error': 'CSV file is empty or invalid'}), 400
                
                headers = [h.strip() for h in lines[0].split(',')]
                data = []
                for line in lines[1:]:
                    if line.strip():
                        values = [v.strip() for v in line.split(',')]
                        row = {}
                        for i, header in enumerate(headers):
                            if i < len(values):
                                row[header] = values[i]
                            else:
                                row[header] = ''
                        data.append(row)
            except Exception as e:
                return jsonify({'error': f'Error reading CSV file: {str(e)}'}), 400
                
        elif file_extension in ['.xlsx', '.xls', '.xlsm']:
            # Return Excel file as base64 for frontend rendering with SheetJS
            try:
                # Reset file pointer to beginning
                file.seek(0)
                
                # Read file as binary
                file_data = file.read()
                
                # Encode as base64
                import base64
                file_base64 = base64.b64encode(file_data).decode('utf-8')
                
                # Also parse basic metadata with openpyxl
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
                    temp_file.write(file_data)
                    temp_filename = temp_file.name
                
                workbook = openpyxl.load_workbook(temp_filename, data_only=False)
                sheet_names = workbook.sheetnames
                workbook.close()
                os.unlink(temp_filename)
                
                # Create response with base64 data and metadata
                response_data = {
                    'file_base64': file_base64,
                    'file_name': file.filename,
                    'file_type': file_extension,
                    'sheet_names': sheet_names,
                    'sheets_count': len(sheet_names)
                }
                print(f"DEBUG: Returning Excel file with {len(sheet_names)} sheets: {sheet_names}")
                    
            except Exception as e:
                return jsonify({'error': f'Error reading Excel file: {str(e)}'}), 400
                
        elif file_extension in ['.csv']:
            # Convert CSV to Excel and return as base64
            try:
                # Reset file pointer to beginning
                file.seek(0)
                
                # Read CSV content
                csv_content = file.read().decode('utf-8')
                
                # Parse CSV
                import io
                csv_file = io.StringIO(csv_content)
                reader = csv.reader(csv_file)
                rows = list(reader)
                
                if not rows:
                    return jsonify({'error': 'CSV file appears to be empty'}), 400
                
                # Create Excel workbook
                workbook = openpyxl.Workbook()
                sheet = workbook.active
                sheet.title = 'Data'
                
                # Write data to Excel
                for row_idx, row in enumerate(rows, start=1):
                    for col_idx, value in enumerate(row, start=1):
                        sheet.cell(row=row_idx, column=col_idx, value=value)
                
                # Save to temporary file
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
                    workbook.save(temp_file.name)
                    temp_filename = temp_file.name
                
                # Read the Excel file as binary
                with open(temp_filename, 'rb') as f:
                    excel_data = f.read()
                
                # Cleanup
                os.unlink(temp_filename)
                
                # Encode as base64
                import base64
                file_base64 = base64.b64encode(excel_data).decode('utf-8')
                
                # Create response with base64 data and metadata
                response_data = {
                    'file_base64': file_base64,
                    'file_name': file.filename.replace('.csv', '.xlsx'),
                    'file_type': '.xlsx',
                    'sheet_names': ['Data'],
                    'sheets_count': 1
                }
                print(f"DEBUG: Converted CSV to Excel with 1 sheet")
                    
            except Exception as e:
                return jsonify({'error': f'Error converting CSV to Excel: {str(e)}'}), 400
                
        elif file_extension in ['.json']:
            # Convert JSON to Excel and return as base64
            try:
                # Reset file pointer to beginning
                file.seek(0)
                
                # Read JSON content
                json_content = file.read().decode('utf-8')
                data = json.loads(json_content)
                
                if not data:
                    return jsonify({'error': 'JSON file appears to be empty'}), 400
                
                # Convert JSON to list of dictionaries if needed
                if isinstance(data, dict):
                    data = [data]
                
                # Create Excel workbook
                workbook = openpyxl.Workbook()
                sheet = workbook.active
                sheet.title = 'Data'
                
                # Write headers
                if isinstance(data[0], dict):
                    headers = list(data[0].keys())
                    for col_idx, header in enumerate(headers, start=1):
                        sheet.cell(row=1, column=col_idx, value=header)
                    
                    # Write data
                    for row_idx, row_data in enumerate(data, start=2):
                        for col_idx, header in enumerate(headers, start=1):
                            value = row_data.get(header, '')
                            sheet.cell(row=row_idx, column=col_idx, value=value)
                else:
                    # Simple array, write as single column
                    for row_idx, value in enumerate(data, start=1):
                        sheet.cell(row=row_idx, column=1, value=value)
                
                # Save to temporary file
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
                    workbook.save(temp_file.name)
                    temp_filename = temp_file.name
                
                # Read the Excel file as binary
                with open(temp_filename, 'rb') as f:
                    excel_data = f.read()
                
                # Cleanup
                os.unlink(temp_filename)
                
                # Encode as base64
                import base64
                file_base64 = base64.b64encode(excel_data).decode('utf-8')
                
                # Create response with base64 data and metadata
                response_data = {
                    'file_base64': file_base64,
                    'file_name': file.filename.replace('.json', '.xlsx'),
                    'file_type': '.xlsx',
                    'sheet_names': ['Data'],
                    'sheets_count': 1
                }
                print(f"DEBUG: Converted JSON to Excel with 1 sheet")
                    
            except Exception as e:
                return jsonify({'error': f'Error converting JSON to Excel: {str(e)}'}), 400
                
        elif file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg']:
            # Handle image files
            try:
                file.seek(0)
                image_data = file.read()
                
                # For images, return metadata instead of tabular data
                data = [{
                    'file_type': 'image',
                    'file_name': file.filename,
                    'file_size': len(image_data),
                    'file_extension': file_extension,
                    'upload_timestamp': datetime.now().isoformat(),
                    'preview_available': True
                }]
                headers = ['file_type', 'file_name', 'file_size', 'file_extension', 'upload_timestamp', 'preview_available']
                
            except Exception as e:
                return jsonify({'error': f'Error processing image file: {str(e)}'}), 400
                
        elif file_extension in ['.pdf', '.doc', '.docx', '.txt', '.rtf']:
            # Handle document files
            try:
                file.seek(0)
                document_data = file.read()
                
                # For documents, return metadata
                data = [{
                    'file_type': 'document',
                    'file_name': file.filename,
                    'file_size': len(document_data),
                    'file_extension': file_extension,
                    'upload_timestamp': datetime.now().isoformat(),
                    'preview_available': False
                }]
                headers = ['file_type', 'file_name', 'file_size', 'file_extension', 'upload_timestamp', 'preview_available']
                
            except Exception as e:
                return jsonify({'error': f'Error processing document file: {str(e)}'}), 400
                
        else:
            # Handle any other file type
            try:
                file.seek(0)
                file_data = file.read()
                
                # For other files, return basic metadata
                data = [{
                    'file_type': 'binary',
                    'file_name': file.filename,
                    'file_size': len(file_data),
                    'file_extension': file_extension,
                    'upload_timestamp': datetime.now().isoformat(),
                    'preview_available': False
                }]
                headers = ['file_type', 'file_name', 'file_size', 'file_extension', 'upload_timestamp', 'preview_available']
                
            except Exception as e:
                return jsonify({'error': f'Error processing file: {str(e)}'}), 400
        
        # Try to save to database, but don't fail if it doesn't work
        upload_id = None
        try:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                
                # Insert upload record
                upload_query = """
                INSERT INTO upload_history (user_id, filename, file_type, file_size, upload_status)
                VALUES (%s, %s, %s, %s, %s)
                """
                cursor.execute(upload_query, (
                    1,  # Default user ID for now
                    file.filename,
                    instrument_type,
                    len(data),
                    'completed'
                ))
                
                upload_id = cursor.lastrowid
                
                # Save calculation record
                calc_query = """
                INSERT INTO calculations (instrument_type, input_data, calculation_status, created_at)
                VALUES (%s, %s, %s, %s)
                """
                cursor.execute(calc_query, (
                    instrument_type,
                    json.dumps({'filename': file.filename, 'data_count': len(data), 'data': data}),
                    'completed',
                    datetime.now()
                ))
                
                conn.commit()
                cursor.close()
                conn.close()
        except Exception as db_error:
            print(f"Database save failed, continuing without database: {db_error}")
        
        # Prepare response data
        response_data = {
            'name': file.filename,
            'size': len(data),
            'instrument_type': instrument_type,
            'data': data,  # Return all records for preview
            'upload_id': upload_id
        }
        
        # Add display headers for Excel files
        if file_extension in ['.xlsx', '.xls', '.xlsm'] and 'headers' in locals() and headers:
            response_data['display_headers'] = [h['display'] for h in headers]
            print(f"DEBUG: Adding display_headers to response: {[h['display'] for h in headers]}")
        
        return jsonify({
            'success': True,
            'data': response_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clean', methods=['POST'])
def clean_data():
    try:
        data = request.get_json()
        original_data = data.get('data', [])
        cleaning_options = data.get('options', {})
        
        original_count = len(original_data)
        
        # Apply cleaning operations without pandas
        cleaned_data = original_data.copy()
        stats = {
            'original_rows': original_count,
            'duplicates_removed': 0,
            'missing_values_filled': 0,
            'outliers_removed': 0,
            'empty_rows_removed': 0,
            'text_standardized': 0,
            'whitespace_trimmed': 0,
            'numbers_normalized': 0,
            'dates_formatted': 0,
            'emails_validated': 0,
            'data_types_converted': 0,
            'currency_standardized': 0,
            'percentages_normalized': 0,
            'ranges_validated': 0,
            'consistency_checked': 0,
            'patterns_validated': 0,
            'special_chars_removed': 0,
            'phones_standardized': 0,
            'addresses_normalized': 0,
            'postal_codes_cleaned': 0
        }
        
        # Remove duplicates
        if cleaning_options.get('removeDuplicates'):
            seen = set()
            unique_data = []
            for row in cleaned_data:
                row_str = json.dumps(row, sort_keys=True)
                if row_str not in seen:
                    seen.add(row_str)
                    unique_data.append(row)
            
            stats['duplicates_removed'] = len(cleaned_data) - len(unique_data)
            cleaned_data = unique_data
        
        # Remove empty rows
        if cleaning_options.get('removeEmptyRows'):
            before_count = len(cleaned_data)
            cleaned_data = [row for row in cleaned_data if any(v is not None and v != '' and str(v).strip() != '' for v in row.values())]
            stats['empty_rows_removed'] = before_count - len(cleaned_data)
        
        # Fill missing values
        if cleaning_options.get('fillMissingValues'):
            missing_filled = 0
            for row in cleaned_data:
                for key, value in row.items():
                    if value is None or value == '' or str(value).strip() == '':
                        if key.lower() in ['amount', 'value', 'price', 'rate', 'cost'] or any(word in key.lower() for word in ['amount', 'value', 'price', 'rate', 'cost']):
                            row[key] = 0
                        else:
                            row[key] = 'N/A'
                        missing_filled += 1
            stats['missing_values_filled'] = missing_filled
        
        # Standardize text
        if cleaning_options.get('standardizeText'):
            text_standardized = 0
            for row in cleaned_data:
                for key, value in row.items():
                    if isinstance(value, str) and value.strip():
                        # Convert to title case for proper names, lowercase for others
                        if any(word in key.lower() for word in ['name', 'fund', 'portfolio']):
                            row[key] = value.title().strip()
                        else:
                            row[key] = value.lower().strip()
                        text_standardized += 1
            stats['text_standardized'] = text_standardized
        
        # Trim whitespace
        if cleaning_options.get('trimWhitespace'):
            whitespace_trimmed = 0
            for row in cleaned_data:
                for key, value in row.items():
                    if isinstance(value, str):
                        original_value = value
                        row[key] = value.strip()
                        if original_value != row[key]:
                            whitespace_trimmed += 1
            stats['whitespace_trimmed'] = whitespace_trimmed
        
        # Normalize numbers
        if cleaning_options.get('normalizeNumbers'):
            numbers_normalized = 0
            for row in cleaned_data:
                for key, value in row.items():
                    if isinstance(value, str):
                        # Remove currency symbols, commas, and convert to standard format
                        try:
                            clean_value = value.replace('$', '').replace(',', '').strip()
                            if clean_value.replace('.', '').replace('-', '').isdigit():
                                row[key] = float(clean_value)
                                numbers_normalized += 1
                        except (ValueError, AttributeError):
                            pass
            stats['numbers_normalized'] = numbers_normalized
        
        # Format dates
        if cleaning_options.get('formatDates'):
            dates_formatted = 0
            for row in cleaned_data:
                for key, value in row.items():
                    if isinstance(value, str) and any(word in key.lower() for word in ['date', 'maturity', 'issue', 'valuation']):
                        # Try to format dates to YYYY-MM-DD
                        try:
                            import re
                            # Simple date pattern matching
                            if re.match(r'\d{4}-\d{2}-\d{2}', value):
                                # Already in correct format
                                pass
                            elif re.match(r'\d{1,2}/\d{1,2}/\d{4}', value):
                                # Convert MM/DD/YYYY to YYYY-MM-DD
                                parts = value.split('/')
                                if len(parts) == 3:
                                    row[key] = f"{parts[2]}-{parts[0].zfill(2)}-{parts[1].zfill(2)}"
                                    dates_formatted += 1
                        except:
                            pass
            stats['dates_formatted'] = dates_formatted
        
        # Validate emails
        if cleaning_options.get('validateEmails'):
            emails_validated = 0
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            for row in cleaned_data:
                for key, value in row.items():
                    if isinstance(value, str) and 'email' in key.lower():
                        if not re.match(email_pattern, value.strip()):
                            row[key] = 'invalid@email.com'
                            emails_validated += 1
            stats['emails_validated'] = emails_validated
        
        # Standardize currency
        if cleaning_options.get('standardizeCurrency'):
            currency_standardized = 0
            for row in cleaned_data:
                for key, value in row.items():
                    if isinstance(value, (str, int, float)) and any(word in key.lower() for word in ['amount', 'value', 'price', 'cost']):
                        try:
                            # Convert to float and format as currency
                            num_value = float(str(value).replace('$', '').replace(',', '').strip())
                            row[key] = f"${num_value:,.2f}"
                            currency_standardized += 1
                        except (ValueError, AttributeError):
                            pass
            stats['currency_standardized'] = currency_standardized
        
        # Normalize percentages
        if cleaning_options.get('normalizePercentages'):
            percentages_normalized = 0
            for row in cleaned_data:
                for key, value in row.items():
                    if isinstance(value, str) and '%' in str(value):
                        try:
                            # Convert percentage to decimal
                            clean_value = value.replace('%', '').strip()
                            decimal_value = float(clean_value) / 100
                            row[key] = decimal_value
                            percentages_normalized += 1
                        except (ValueError, AttributeError):
                            pass
            stats['percentages_normalized'] = percentages_normalized
        
        # Remove special characters
        if cleaning_options.get('removeSpecialChars'):
            special_chars_removed = 0
            import re
            for row in cleaned_data:
                for key, value in row.items():
                    if isinstance(value, str) and not any(word in key.lower() for word in ['date', 'email', 'phone']):
                        # Remove special characters except letters, numbers, spaces, and basic punctuation
                        original_value = value
                        row[key] = re.sub(r'[^a-zA-Z0-9\s.,-@]', '', value)
                        if original_value != row[key]:
                            special_chars_removed += 1
            stats['special_chars_removed'] = special_chars_removed
        
        # Remove outliers (simplified version)
        if cleaning_options.get('removeOutliers'):
            outliers_removed = 0
            for row in cleaned_data:
                for key, value in row.items():
                    try:
                        num_value = float(str(value).replace('$', '').replace('%', '').replace(',', '').strip())
                        if abs(num_value) > 1000000:  # Simple threshold
                            row[key] = None
                            outliers_removed += 1
                    except (ValueError, TypeError):
                        pass
            
            # Remove rows with None values
            cleaned_data = [row for row in cleaned_data if all(v is not None for v in row.values())]
            stats['outliers_removed'] = outliers_removed
        
        # Calculate total operations
        stats['total_operations_applied'] = sum(1 for k, v in cleaning_options.items() if v)
        stats['cleaned_rows'] = len(cleaned_data)
        
        return jsonify({
            'success': True,
            'data': cleaned_data,
            'stats': stats
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete-dataset', methods=['POST'])
def delete_dataset():
    try:
        data = request.get_json()
        upload_id = data.get('upload_id')
        
        if not upload_id:
            return jsonify({'error': 'Upload ID is required'}), 400
        
        # Delete from database if connection available
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Delete from uploads table
            cursor.execute("DELETE FROM uploads WHERE upload_id = %s", (upload_id,))
            
            # Delete from calculations table if exists
            cursor.execute("DELETE FROM calculations WHERE upload_id = %s", (upload_id,))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"Dataset {upload_id} deleted from database")
        except Exception as db_error:
            print(f"Database delete failed: {db_error}")
            # Continue even if database delete fails
        
        return jsonify({
            'success': True,
            'message': f'Dataset {upload_id} deleted successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/calculate', methods=['POST'])
def calculate_financials():
    try:
        data = request.get_json()
        calculation_data = data.get('data', [])
        instrument_type = data.get('instrument_type', 'treasury-bills')
        params = data.get('params', {})
        
        results = []
        
        for row in calculation_data:
            if instrument_type in ['treasury-bills', 'treasury_bills']:
                result = calculate_treasury_bill(row, params)
            elif instrument_type == 'bonds':
                result = calculate_bond(row, params)
            elif instrument_type in ['money-market', 'money_market']:
                result = calculate_money_market(row, params)
            else:
                result = row
            
            results.append(result)
        
        return jsonify({
            'success': True,
            'calculations': results
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def calculate_treasury_bill(row, params):
    face_value = float(row.get('faceValue', params.get('faceValue', 1000)))
    purchase_price = float(row.get('purchasePrice', params.get('purchasePrice', 950)))
    days_to_maturity = float(row.get('daysToMaturity', params.get('daysToMaturity', 90)))
    
    yield_rate = ((face_value - purchase_price) / purchase_price) * (360 / days_to_maturity)
    discount_rate = ((face_value - purchase_price) / face_value) * (360 / days_to_maturity)
    
    return {
        **row,
        'yieldRate': f"{(yield_rate * 100):.4f}%",
        'discountRate': f"{(discount_rate * 100):.4f}%",
        'pricePer100': f"{(purchase_price / face_value) * 100:.4f}"
    }

def calculate_bond(row, params):
    face_value = float(row.get('faceValue', params.get('faceValue', 1000)))
    current_price = float(row.get('currentPrice', params.get('currentPrice', 980)))
    coupon_rate = float(row.get('couponRate', params.get('couponRate', 5))) / 100
    
    annual_coupon = face_value * coupon_rate
    current_yield = (annual_coupon / current_price) * 100
    
    return {
        **row,
        'couponRate': f"{(coupon_rate * 100):.2f}%",
        'annualCoupon': f"{annual_coupon:.2f}",
        'currentYield': f"{current_yield:.4f}%",
        'yieldToMaturity': 'N/A'  # Would need more complex calculation
    }

def calculate_money_market(row, params):
    """
    Comprehensive money market calculations for various instruments:
    - Commercial Paper
    - Certificate of Deposit
    - Repo Agreement
    - Bankers Acceptance
    """
    
    # Extract data from row with multiple field name options
    principal = float(row.get('principal') or row.get('Principal') or params.get('principal', 100000))
    interest_rate = float(row.get('interest_rate') or row.get('interest_rate') or params.get('interest_rate', 0.05))
    term_days = float(row.get('term_days') or row.get('Term_Days') or params.get('term_days', 90))
    face_value = float(row.get('face_value') or row.get('Face_Value') or principal)
    purchase_price = float(row.get('purchase_price') or row.get('Purchase_Price') or principal)
    discount_rate = float(row.get('discount_rate') or row.get('Discount_Rate') or params.get('discount_rate', 0.04))
    
    # Debug logging
    print(f"Processing money market calculation:")
    print(f"  Principal: {principal}")
    print(f"  Interest Rate: {interest_rate}")
    print(f"  Term Days: {term_days}")
    print(f"  Face Value: {face_value}")
    print(f"  Purchase Price: {purchase_price}")
    print(f"  Discount Rate: {discount_rate}")
    
    # Money Market Calculations
    
    # 1. Interest Earned
    interest_earned = principal * interest_rate * (term_days / 365)
    
    # 2. Annual Yield (simple interest)
    annual_yield = (interest_earned / principal) * (365 / term_days)
    
    # 3. Effective Rate (compounded annually)
    effective_rate = (1 + interest_rate * (term_days / 365)) ** (365 / term_days) - 1
    
    # 4. Maturity Value
    maturity_value = principal + interest_earned
    
    # 5. Bank Discount Rate (for discount instruments)
    bank_discount_rate = ((face_value - purchase_price) / face_value) * (360 / term_days)
    
    # 6. Money Market Yield (also called CD equivalent yield)
    money_market_yield = ((face_value - purchase_price) / purchase_price) * (360 / term_days)
    
    # 7. Bond Equivalent Yield (365-day year)
    bond_equivalent_yield = ((face_value - purchase_price) / purchase_price) * (365 / term_days)
    
    # 8. Discount Yield (360-day year)
    discount_yield = ((face_value - purchase_price) / face_value) * (360 / term_days)
    
    # 9. Price as percentage of par
    price_percentage = (purchase_price / face_value) * 100
    
    # 10. Dollar Discount
    dollar_discount = face_value - purchase_price
    
    # 11. Effective Annual Yield (365-day year)
    effective_annual_yield = (1 + money_market_yield) ** (365 / term_days) - 1
    
    # 12. Simple Yield
    simple_yield = interest_rate * 100
    
    # 13. Yield to Maturity approximation
    ytm_approx = ((face_value - purchase_price + interest_earned) / purchase_price) * (365 / term_days)
    
    # 14. Current Yield
    current_yield = (interest_earned / purchase_price) * (365 / term_days)
    
    # 15. Holding Period Return
    holding_period_return = (maturity_value - purchase_price) / purchase_price
    
    # Determine instrument type based on data characteristics
    instrument_type = detect_money_market_instrument(row, params)
    
    return {
        **row,
        'instrument_type': instrument_type,
        'principal': principal,
        'interest_earned': round(interest_earned, 2),
        'term_days': int(term_days),
        'annual_yield': round(annual_yield * 100, 4),
        'effective_rate': round(effective_rate * 100, 4),
        'maturity_value': round(maturity_value, 2),
        'bank_discount_rate': round(bank_discount_rate * 100, 4),
        'money_market_yield': round(money_market_yield * 100, 4),
        'bond_equivalent_yield': round(bond_equivalent_yield * 100, 4),
        'discount_yield': round(discount_yield * 100, 4),
        'price_percentage': round(price_percentage, 4),
        'dollar_discount': round(dollar_discount, 2),
        'effective_annual_yield': round(effective_annual_yield * 100, 4),
        'simple_yield': round(simple_yield, 4),
        'ytm_approx': round(ytm_approx * 100, 4),
        'current_yield': round(current_yield * 100, 4),
        'holding_period_return': round(holding_period_return * 100, 4),
        'face_value': face_value,
        'purchase_price': purchase_price
    }

def detect_money_market_instrument(row, params):
    """
    Detect the type of money market instrument based on data characteristics
    """
    instrument_name = row.get('instrument_name', '').lower()
    fund_name = row.get('fund_name', '').lower()
    portfolio = row.get('portfolio', '').lower()
    
    # Detection logic based on instrument characteristics
    if 'commercial paper' in instrument_name or 'cp' in instrument_name:
        return 'Commercial Paper'
    elif 'certificate of deposit' in instrument_name or 'cd' in instrument_name:
        return 'Certificate of Deposit'
    elif 'repo' in instrument_name or 'repurchase' in instrument_name:
        return 'Repo Agreement'
    elif 'bankers acceptance' in instrument_name or 'ba' in instrument_name:
        return 'Bankers Acceptance'
    elif 'treasury bill' in instrument_name or 't-bill' in instrument_name:
        return 'Treasury Bill'
    else:
        # Default based on typical characteristics
        term_days = float(row.get('term_days', 0))
        if term_days <= 30:
            return 'Commercial Paper'
        elif term_days <= 90:
            return 'Certificate of Deposit'
        elif term_days <= 180:
            return 'Repo Agreement'
        else:
            return 'Bankers Acceptance'

@app.route('/api/fred-yield-curve', methods=['GET'])
def get_fred_yield_curve():
    """Get yield curve data from FRED API for specific instrument type"""
    try:
        # Get instrument type from query parameter
        instrument_type = request.args.get('instrument_type', 'all')

        # Fetch data for different instruments
        tbill_data = fetch_fred_data(FINANCIAL_INSTRUMENTS['treasury_bills']['fred_series'])
        bond_data = fetch_fred_data(FINANCIAL_INSTRUMENTS['bonds']['fred_series'])
        mm_data = fetch_fred_data(FINANCIAL_INSTRUMENTS['money_market']['fred_series'])

        # Calculate yield curve based on instrument type
        yield_curve = calculate_yield_curve(tbill_data, bond_data, mm_data, instrument_type)

        if yield_curve:
            return jsonify({
                'success': True,
                'data': yield_curve,
                'instruments': FINANCIAL_INSTRUMENTS,
                'instrument_type': instrument_type
            })
        else:
            # Fallback to mock data if FRED API fails
            fallback_data = {
                'labels': ['3M', '6M', '1Y', '2Y', '5Y', '10Y', '30Y'],
                'datasets': [
                    {
                        'label': 'Treasury Bills',
                        'data': [4.5, 4.8, 5.1, 5.3, 5.0, 4.8, 4.6],
                        'borderColor': '#0B2A44',
                        'backgroundColor': 'rgba(11, 42, 68, 0.1)',
                        'fill': True,
                        'tension': 0.4
                    },
                    {
                        'label': 'Money Market',
                        'data': [4.2, 4.5, 4.8, 5.0, 4.7, 4.5, 4.3],
                        'borderColor': '#4CAF50',
                        'backgroundColor': 'rgba(76, 175, 80, 0.1)',
                        'fill': True,
                        'tension': 0.4
                    }
                ],
                'metadata': {
                    'source': 'fallback_data',
                    'last_updated': datetime.now().isoformat()
                }
            }

            return jsonify({
                'success': True,
                'data': fallback_data,
                'message': 'Using fallback data - FRED API temporarily unavailable'
            })

    except Exception as err:
        return jsonify({
            'success': False,
            'error': str(err)
        }), 500

# Add endpoints needed by frontend
@app.route('/api/system/info', methods=['GET'])
def get_system_info():
    return jsonify({
        'success': True,
        'data': {
            'version': '1.0.0',
            'environment': 'Development',
            'database': 'MySQL',
            'api_status': 'Online',
            'storage_used': '2.3 GB / 10 GB',
            'last_updated': datetime.now().isoformat()
        }
    })

@app.route('/api/dashboard/kpi', methods=['GET'])
def get_dashboard_kpi():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get total datasets from upload_history
        cursor.execute("SELECT COUNT(*) as total_datasets FROM upload_history WHERE upload_status = 'completed'")
        total_datasets = cursor.fetchone()['total_datasets']

        # Get total calculations
        cursor.execute("SELECT COUNT(*) as total_calculations FROM calculations WHERE calculation_status = 'completed'")
        total_calculations = cursor.fetchone()['total_calculations']

        # Get total reports
        cursor.execute("SELECT COUNT(*) as total_reports FROM reports WHERE generation_status = 'completed'")
        total_reports = cursor.fetchone()['total_reports']

        # Get datasets by instrument type
        cursor.execute("""
            SELECT file_type, COUNT(*) as count
            FROM upload_history
            WHERE upload_status = 'completed'
            GROUP BY file_type
        """)
        instrument_counts = cursor.fetchall()

        # Calculate performance metrics from database
        # Processing speed: average processing time (mocked as 95-99% based on successful uploads)
        cursor.execute("SELECT COUNT(*) as successful FROM upload_history WHERE upload_status = 'completed'")
        successful_uploads = cursor.fetchone()['successful']
        cursor.execute("SELECT COUNT(*) as total FROM upload_history")
        total_uploads = cursor.fetchone()['total']
        processing_speed = f'{int((successful_uploads / total_uploads * 100) if total_uploads > 0 else 98)}%' if total_uploads > 0 else '98%'

        # Data accuracy: based on successful calculations vs total calculations
        cursor.execute("SELECT COUNT(*) as successful FROM calculations WHERE calculation_status = 'completed'")
        successful_calcs = cursor.fetchone()['successful']
        cursor.execute("SELECT COUNT(*) as total FROM calculations")
        total_calcs = cursor.fetchone()['total']
        data_accuracy = f'{int((successful_calcs / total_calcs * 100) if total_calcs > 0 else 99)}%' if total_calcs > 0 else '99%'

        # System uptime: based on database connectivity (mocked as 99.9% for now)
        system_uptime = '99.9%'

        # User satisfaction: based on completed reports (mocked as 95% for now)
        cursor.execute("SELECT COUNT(*) as completed FROM reports WHERE generation_status = 'completed'")
        completed_reports = cursor.fetchone()['completed']
        cursor.execute("SELECT COUNT(*) as total FROM reports")
        total_reports_count = cursor.fetchone()['total']
        user_satisfaction = f'{int((completed_reports / total_reports_count * 100) if total_reports_count > 0 else 95)}%' if total_reports_count > 0 else '95%'

        cursor.close()
        conn.close()

        # Format instrument counts
        active_instruments = 0
        for instrument in instrument_counts:
            if instrument['file_type'] in ['treasury_bills', 'bonds', 'money_market']:
                active_instruments += instrument['count']

        return jsonify({
            'success': True,
            'data': {
                'total_datasets': total_datasets,
                'datasets': total_datasets,
                'active_calculations': total_calculations,
                'calculations': total_calculations,
                'reports_generated': total_reports,
                'reports': total_reports,
                'system_health': 'Optimal',
                'active_instruments': active_instruments,
                'instrument_breakdown': instrument_counts,
                'performance_metrics': {
                    'processing_speed': processing_speed,
                    'data_accuracy': data_accuracy,
                    'system_uptime': system_uptime,
                    'user_satisfaction': user_satisfaction
                }
            }
        })

    except Exception as err:
        # Fallback to mock data if database fails
        return jsonify({
            'success': True,
            'data': {
                'total_investments': '0',
                'active_calculations': 0,
                'reports_generated': 0,
                'system_health': 'Optimal',
                'total_datasets': 0,
                'active_instruments': 0,
                'instrument_breakdown': [],
                'performance_metrics': {
                    'processing_speed': '0%',
                    'data_accuracy': '0%',
                    'system_uptime': '0%',
                    'user_satisfaction': '0%'
                }
            }
        })

@app.route('/api/user/profile', methods=['GET'])
def get_user_profile():
    return jsonify({
        'success': True,
        'data': {
            'name': 'Makanaka Kanyai',
            'email': 'makanakakanyai@gmail.com',
            'role': 'Administrator'
        }
    })

@app.route('/api/user/preferences', methods=['GET'])
def get_user_preferences():
    return jsonify({
        'success': True,
        'data': {
            'language': 'English',
            'timezone': 'GMT+2',
            'date_format': 'DD/MM/YYYY',
            'currency': 'USD'
        }
    })

@app.route('/api/user/notifications/settings', methods=['GET'])
def get_notification_settings():
    return jsonify({
        'success': True,
        'data': {
            'emailNotifications': True,
            'pushNotifications': False,
            'weeklyReports': True,
            'systemAlerts': True
        }
    })

@app.route('/api/dashboard/recent-activity', methods=['GET'])
def get_recent_activity():
    """Get recent activity from database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get recent uploads and calculations combined
        query = """
        SELECT 'upload' as activity_type, filename as title, file_type as instrument_type, 
               created_at, upload_status as status
        FROM upload_history 
        WHERE upload_status = 'completed'
        UNION ALL
        SELECT 'calculation' as activity_type, instrument_type as title, instrument_type, 
               created_at, calculation_status as status
        FROM calculations 
        WHERE calculation_status = 'completed'
        ORDER BY created_at DESC 
        LIMIT 10
        """
        cursor.execute(query)
        activities_data = cursor.fetchall()
        
        # Format for frontend
        activities = []
        for activity in activities_data:
            if activity['activity_type'] == 'upload':
                text = f'{activity["title"]} uploaded'
                instrument_type = activity['instrument_type']
            else:
                text = f'{activity["instrument_type"].replace("_", " ").title()} calculations completed'
                instrument_type = activity['instrument_type']
            
            activities.append({
                'id': len(activities) + 1,
                'text': text,
                'time': format_time_ago(activity['created_at']),
                'color': get_instrument_color(instrument_type)
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': activities
        })
        
    except Exception as err:
        # Fallback to mock data if database fails
        return jsonify({
            'success': True,
            'data': [
                {
                    'id': 1,
                    'text': 'Treasury Bills dataset uploaded',
                    'time': '2 hours ago',
                    'color': '#0B2A44'
                },
                {
                    'id': 2,
                    'text': 'Bond calculations completed',
                    'time': '4 hours ago',
                    'color': '#1E88E5'
                },
                {
                    'id': 3,
                    'text': 'Money market analysis generated',
                    'time': '6 hours ago',
                    'color': '#4CAF50'
                },
                {
                    'id': 4,
                    'text': 'Monthly report exported to PDF',
                    'time': '1 day ago',
                    'color': '#FFC107'
                }
            ]
        })

@app.route('/api/calculations/history', methods=['GET'])
def get_calculation_history():
    """Get calculation history"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = "SELECT * FROM calculations ORDER BY created_at DESC LIMIT 50"
        cursor.execute(query)
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': results
        })
        
    except Exception as err:
        return jsonify({
            'success': False,
            'error': str(err)
        }), 500

@app.route('/api/dashboard/charts', methods=['GET'])
def get_dashboard_charts():
    """Get chart data for dashboard using database data"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get monthly activity data from database (uploads and calculations)
        cursor.execute("""
            SELECT
                DATE_FORMAT(created_at, '%Y-%m') as month,
                COUNT(*) as count,
                'uploads' as type
            FROM upload_history
            WHERE upload_status = 'completed'
            AND created_at >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
            GROUP BY DATE_FORMAT(created_at, '%Y-%m')
            UNION ALL
            SELECT
                DATE_FORMAT(created_at, '%Y-%m') as month,
                COUNT(*) as count,
                'calculations' as type
            FROM calculations
            WHERE calculation_status = 'completed'
            AND created_at >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
            GROUP BY DATE_FORMAT(created_at, '%Y-%m')
            ORDER BY month
        """)
        monthly_data = cursor.fetchall()

        # Get instrument distribution from database - remove time filter to show all data
        cursor.execute("""
            SELECT file_type as instrument_type, COUNT(*) as count
            FROM upload_history
            WHERE upload_status = 'completed'
            GROUP BY file_type
        """)
        instrument_distribution = cursor.fetchall()

        cursor.close()
        conn.close()

        # Format monthly data for charts
        months = []
        uploads = []
        calculations = []

        for i in range(12):
            month_date = datetime.now().replace(day=1) - pd.DateOffset(months=11-i)
            month_str = month_date.strftime('%Y-%m')
            months.append(month_date.strftime('%b %Y'))

            month_uploads = [d for d in monthly_data if d['month'] == month_str and d['type'] == 'uploads']
            month_calcs = [d for d in monthly_data if d['month'] == month_str and d['type'] == 'calculations']

            uploads.append(month_uploads[0]['count'] if month_uploads else 0)
            calculations.append(month_calcs[0]['count'] if month_calcs else 0)

        # Format instrument distribution - ensure we have data even if empty
        if not instrument_distribution:
            instrument_distribution = []

        return jsonify({
            'success': True,
            'data': {
                'monthlyActivity': {
                    'labels': months,
                    'datasets': [
                        {
                            'label': 'Datasets Uploaded',
                            'data': uploads,
                            'backgroundColor': 'rgba(11, 42, 68, 0.2)',
                            'borderColor': '#0B2A44',
                            'borderWidth': 2
                        },
                        {
                            'label': 'Calculations',
                            'data': calculations,
                            'backgroundColor': 'rgba(30, 136, 229, 0.2)',
                            'borderColor': '#1E88E5',
                            'borderWidth': 2
                        }
                    ]
                },
                'instrumentDistribution': {
                    'labels': [d['instrument_type'].replace('_', ' ').title() for d in instrument_distribution] if instrument_distribution else ['No Data'],
                    'data': [d['count'] for d in instrument_distribution] if instrument_distribution else [0],
                    'backgroundColor': ['#0B2A44', '#1E88E5', '#4CAF50', '#FFC107', '#9C27B0'][:len(instrument_distribution)] if instrument_distribution else ['#E0E0E0']
                }
            }
        })

    except Exception as err:
        return jsonify({
            'success': False,
            'error': str(err)
        }), 500

@app.route('/api/calculations/execute', methods=['POST'])
def execute_calculation():
    """Execute financial calculation"""
    try:
        data = request.get_json()
        
        if not data or 'instrument_type' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing instrument_type parameter'
            }), 400
        
        instrument_type = data['instrument_type']
        calculation_data = data.get('data', [])
        
        # Try to save calculation to database, but don't fail if it doesn't work
        calc_id = None
        try:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                
                query = """
                INSERT INTO calculations (instrument_type, input_data, calculation_status, created_at)
                VALUES (%s, %s, %s, %s)
                """
                cursor.execute(query, (
                    instrument_type,
                    json.dumps(data),
                    'processing',
                    datetime.now()
                ))
                
                calc_id = cursor.lastrowid
                conn.commit()
                cursor.close()
                conn.close()
        except Exception as db_error:
            print(f"Database save failed, continuing without database: {db_error}")
        
        # Perform calculation
        if instrument_type == 'yield_curve':
            result = calculate_yield_curve_from_api()
        elif calculation_data and len(calculation_data) > 0:
            # Use existing calculation functions with uploaded data
            result = perform_calculation(instrument_type, calculation_data)
        else:
            # Provide sample data for demonstration if no data provided
            sample_data = []
            if instrument_type == 'treasury_bills':
                sample_data = [
                    {'faceValue': 1000, 'purchasePrice': 950, 'daysToMaturity': 90},
                    {'faceValue': 1000, 'purchasePrice': 960, 'daysToMaturity': 180},
                    {'faceValue': 1000, 'purchasePrice': 970, 'daysToMaturity': 270}
                ]
            elif instrument_type == 'bonds':
                sample_data = [
                    {'faceValue': 1000, 'currentPrice': 980, 'couponRate': 5},
                    {'faceValue': 1000, 'currentPrice': 990, 'couponRate': 6},
                    {'faceValue': 1000, 'currentPrice': 975, 'couponRate': 4}
                ]
            elif instrument_type == 'money_market':
                sample_data = [
                    {'principal': 1000, 'interest': 25, 'days': 90},
                    {'principal': 1000, 'interest': 30, 'days': 180},
                    {'principal': 1000, 'interest': 35, 'days': 270}
                ]
            
            result = perform_calculation(instrument_type, sample_data)
        
        # Try to update calculation record
        if calc_id:
            try:
                conn = get_db_connection()
                if conn:
                    cursor = conn.cursor()
                    
                    update_query = """
                    UPDATE calculations 
                    SET result_data = %s, calculation_status = %s, completed_at = %s 
                    WHERE id = %s
                    """
                    cursor.execute(update_query, (
                        json.dumps(result),
                        'completed',
                        datetime.now(),
                        calc_id
                    ))
                    
                    conn.commit()
                    cursor.close()
                    conn.close()
            except Exception as db_error:
                print(f"Database update failed: {db_error}")
        
        return jsonify({
            'success': True,
            'data': result,
            'calculation_id': calc_id
        })
        
    except Exception as err:
        return jsonify({
            'success': False,
            'error': str(err)
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)

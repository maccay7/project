from flask import Flask, request, jsonify
from flask_cors import CORS
import pymysql
import pandas as pd
import numpy as np
import requests
import json
import csv
import openpyxl
import os
import base64
import tempfile
import uuid
from datetime import datetime
from io import BytesIO
import re

app = Flask(__name__)
CORS(app)

# ==================== CONFIGURATION (from environment) ====================
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', 'businessmogul'),
    'database': os.environ.get('DB_NAME', 'duracapital'),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

FRED_API_KEY = os.environ.get('FRED_API_KEY', '')
FRED_BASE_URL = 'https://api.stlouisfed.org/fred'

# ==================== DATABASE FUNCTIONS ====================

def get_db_connection():
    try:
        return pymysql.connect(**DB_CONFIG)
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def init_database():
    conn = get_db_connection()
    if not conn:
        return
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS upload_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                file_name VARCHAR(255) NOT NULL,
                upload_date DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS datasets (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE,
                file_base64 TEXT,
                sheet_names TEXT,
                upload_id VARCHAR(255),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS calculations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                instrument_type VARCHAR(50),
                input_data TEXT,
                result_data TEXT,
                calculation_status VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Database init error: {e}")

init_database()

# ==================== HELPER FUNCTIONS ====================

def fetch_fred_data(series_id):
    if not FRED_API_KEY:
        return None
    try:
        url = f"{FRED_BASE_URL}/series/observations?series_id={series_id}&api_key={FRED_API_KEY}&file_type=json&limit=10"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"FRED API error: {e}")
        return None

def get_value_from_row_or_params(row, params, key, alternatives=None):
    """Get value from row or params, no hardcoded defaults"""
    if alternatives is None:
        alternatives = [key, key.lower(), key.replace('_', ''), key.replace('_', '').lower()]
    
    for alt in [key] + alternatives:
        if alt in row and row[alt] is not None and row[alt] != '':
            return float(row[alt])
    
    for alt in [key] + alternatives:
        if alt in params and params[alt] is not None and params[alt] != '':
            return float(params[alt])
    
    return None

def calculate_treasury_bill(row, params):
    face_value = get_value_from_row_or_params(row, params, 'faceValue', ['face_value', 'FaceValue'])
    purchase_price = get_value_from_row_or_params(row, params, 'purchasePrice', ['purchase_price', 'PurchasePrice'])
    days_to_maturity = get_value_from_row_or_params(row, params, 'daysToMaturity', ['days_to_maturity', 'DaysToMaturity'])
    
    if face_value is None:
        return {**row, 'error': 'Missing faceValue'}
    if purchase_price is None:
        return {**row, 'error': 'Missing purchasePrice'}
    if days_to_maturity is None:
        return {**row, 'error': 'Missing daysToMaturity'}
    
    day_convention = get_value_from_row_or_params(row, params, 'day_convention', ['dayConvention'])
    if day_convention is None:
        day_convention = 360
    
    yield_rate = ((face_value - purchase_price) / purchase_price) * (day_convention / days_to_maturity)
    discount_rate = ((face_value - purchase_price) / face_value) * (day_convention / days_to_maturity)
    
    return {
        **row,
        'yieldRate': round(yield_rate * 100, 4),
        'discountRate': round(discount_rate * 100, 4),
        'pricePer100': round((purchase_price / face_value) * 100, 4)
    }

def calculate_bond(row, params):
    face_value = get_value_from_row_or_params(row, params, 'faceValue', ['face_value', 'FaceValue'])
    current_price = get_value_from_row_or_params(row, params, 'currentPrice', ['current_price', 'CurrentPrice'])
    coupon_rate = get_value_from_row_or_params(row, params, 'couponRate', ['coupon_rate', 'CouponRate'])
    
    if face_value is None:
        return {**row, 'error': 'Missing faceValue'}
    if current_price is None:
        return {**row, 'error': 'Missing currentPrice'}
    if coupon_rate is None:
        return {**row, 'error': 'Missing couponRate'}
    
    coupon_rate = coupon_rate / 100 if coupon_rate > 1 else coupon_rate
    annual_coupon = face_value * coupon_rate
    current_yield = (annual_coupon / current_price) * 100 if current_price > 0 else 0
    
    return {
        **row,
        'couponRate': round(coupon_rate * 100, 2),
        'annualCoupon': round(annual_coupon, 2),
        'currentYield': round(current_yield, 4)
    }

def calculate_money_market(row, params):
    principal = get_value_from_row_or_params(row, params, 'principal', ['Principal', 'amount'])
    interest_rate = get_value_from_row_or_params(row, params, 'interest_rate', ['interestRate', 'rate'])
    term_days = get_value_from_row_or_params(row, params, 'term_days', ['termDays', 'days', 'tenor'])
    
    if principal is None:
        return {**row, 'error': 'Missing principal'}
    if interest_rate is None:
        return {**row, 'error': 'Missing interest_rate'}
    if term_days is None:
        return {**row, 'error': 'Missing term_days'}
    
    year_days = get_value_from_row_or_params(row, params, 'year_days', ['yearDays'])
    if year_days is None:
        year_days = 365
    
    interest_earned = principal * interest_rate * (term_days / year_days)
    annual_yield = (interest_earned / principal) * (year_days / term_days) if term_days > 0 else 0
    maturity_value = principal + interest_earned
    
    return {
        **row,
        'principal': principal,
        'interest_earned': round(interest_earned, 2),
        'term_days': int(term_days),
        'annual_yield': round(annual_yield * 100, 4),
        'maturity_value': round(maturity_value, 2)
    }

def perform_calculation(instrument_type, data):
    results = []
    for row in data:
        if instrument_type in ['treasury_bills', 'treasury-bills']:
            results.append(calculate_treasury_bill(row, {}))
        elif instrument_type == 'bonds':
            results.append(calculate_bond(row, {}))
        elif instrument_type in ['money_market', 'money-market']:
            results.append(calculate_money_market(row, {}))
        else:
            results.append(row)
    return results

# ==================== API ENDPOINTS ====================

@app.route('/')
def home():
    return jsonify({
        'message': 'DuraCapital Backend API',
        'version': '1.0.0',
        'status': 'running',
        'fred_configured': bool(FRED_API_KEY)
    })

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    admin_email = os.environ.get('ADMIN_EMAIL')
    admin_password = os.environ.get('ADMIN_PASSWORD')
    
    if admin_email and admin_password and email == admin_email and password == admin_password:
        return jsonify({
            'success': True,
            'token': str(uuid.uuid4()),
            'user': {
                'email': email,
                'name': os.environ.get('ADMIN_NAME', ''),
                'role': os.environ.get('ADMIN_ROLE', 'user')
            }
        })
    else:
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

@app.route('/api/upload', methods=['POST'])
def upload_data():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        instrument_type = request.form.get('instrument_type', 'treasury_bills')
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        file_extension = os.path.splitext(file.filename)[1].lower()
        file.seek(0)
        file_data = file.read()
        
        if file_extension in ['.xlsx', '.xls', '.xlsm']:
            file_base64 = base64.b64encode(file_data).decode('utf-8')
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
                temp_file.write(file_data)
                temp_filename = temp_file.name
            
            workbook = openpyxl.load_workbook(temp_filename, data_only=True)
            sheet = workbook.active
            
            headers = []
            for col in range(1, sheet.max_column + 1):
                val = sheet.cell(1, col).value
                if val:
                    headers.append(str(val))
            
            data = []
            for row in range(2, sheet.max_row + 1):
                row_data = {}
                for col, header in enumerate(headers, 1):
                    val = sheet.cell(row, col).value
                    row_data[header] = val if val is not None else ''
                if any(row_data.values()):
                    data.append(row_data)
            
            sheet_names = workbook.sheetnames
            workbook.close()
            os.unlink(temp_filename)
            
            conn = get_db_connection()
            upload_id = None
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO upload_history (filename, file_type, upload_status, instrument_type, file_base64)
                    VALUES (%s, %s, %s, %s, %s)
                """, (file.filename, file_extension, 'completed', instrument_type, file_base64))
                upload_id = cursor.lastrowid
                conn.commit()
                cursor.close()
                conn.close()
            
            return jsonify({
                'success': True,
                'data': {
                    'file_base64': file_base64,
                    'file_name': file.filename,
                    'file_type': file_extension,
                    'sheet_names': sheet_names,
                    'data': data[:100],
                    'headers': headers,
                    'total_rows': len(data),
                    'upload_id': upload_id
                }
            })
        
        elif file_extension == '.csv':
            content = file_data.decode('utf-8')
            lines = content.split('\n')
            headers = [h.strip() for h in lines[0].split(',')]
            data = []
            for line in lines[1:]:
                if line.strip():
                    values = [v.strip() for v in line.split(',')]
                    row = {}
                    for i, header in enumerate(headers):
                        if i < len(values):
                            row[header] = values[i]
                    if any(row.values()):
                        data.append(row)
            
            return jsonify({
                'success': True,
                'data': {
                    'data': data[:100],
                    'headers': headers,
                    'file_name': file.filename,
                    'total_rows': len(data)
                }
            })
        
        else:
            return jsonify({'error': f'Unsupported file type: {file_extension}'}), 400
            
    except Exception as e:
        print(f"Upload error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/calculate', methods=['POST'])
def calculate_financials():
    try:
        data = request.get_json()
        calculation_data = data.get('data', [])
        instrument_type = data.get('instrument_type', 'treasury_bills')
        params = data.get('params', {})
        
        if not calculation_data:
            return jsonify({'error': 'No data provided'}), 400
        
        results = perform_calculation(instrument_type, calculation_data)
        
        return jsonify({
            'success': True,
            'calculations': results
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clean', methods=['POST'])
def clean_data():
    try:
        data = request.get_json()
        original_data = data.get('data', [])
        options = data.get('options', {})
        
        cleaned = []
        for row in original_data:
            if options.get('removeEmptyRows', True):
                if not any(v for v in row.values() if v and str(v).strip()):
                    continue
            
            clean_row = {}
            for k, v in row.items():
                if isinstance(v, str):
                    clean_row[k] = v.strip()
                else:
                    clean_row[k] = v
            cleaned.append(clean_row)
        
        return jsonify({
            'success': True,
            'data': cleaned,
            'stats': {
                'original_rows': len(original_data),
                'cleaned_rows': len(cleaned)
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/fred-yield-curve', methods=['GET'])
def get_fred_yield_curve():
    if not FRED_API_KEY:
        return jsonify({'success': False, 'error': 'FRED_API_KEY not configured'}), 503
    
    instrument_type = request.args.get('instrument_type', 'all')
    
    series_map = {
        'treasury_bills': os.environ.get('TBILL_SERIES', 'TB3MS'),
        'bonds': os.environ.get('BOND_SERIES', 'DGS10'),
        'money_market': os.environ.get('MM_SERIES', 'DFF')
    }
    
    datasets = []
    instruments = ['treasury_bills', 'bonds', 'money_market'] if instrument_type == 'all' else [instrument_type]
    
    for inst in instruments:
        if inst not in series_map:
            continue
        fred_data = fetch_fred_data(series_map[inst])
        if fred_data and fred_data.get('observations'):
            rate = float(fred_data['observations'][0]['value'])
            datasets.append({
                'label': inst.replace('_', ' ').title(),
                'data': [rate, rate + 0.3, rate + 0.6, rate + 0.8, rate + 0.5, rate + 0.2, rate - 0.1],
                'borderColor': '#0B2A44' if inst == 'treasury_bills' else '#1E88E5' if inst == 'bonds' else '#4CAF50',
                'fill': True
            })
    
    return jsonify({
        'success': True,
        'data': {
            'labels': ['3M', '6M', '1Y', '2Y', '5Y', '10Y', '30Y'],
            'datasets': datasets
        }
    })

@app.route('/api/save-dataset', methods=['POST'])
def save_dataset():
    try:
        data = request.get_json()
        name = data.get('name')
        file_base64 = data.get('file_base64')
        sheet_names = data.get('sheet_names', [])
        upload_id = data.get('upload_id')
        
        print(f"Save dataset request: name={name}, sheet_names={sheet_names}, upload_id={upload_id}")
        
        conn = get_db_connection()
        if not conn:
            print("ERROR: get_db_connection returned None")
            return jsonify({'success': False, 'error': 'Database connection failed'})
        
        cursor = conn.cursor()
        
        # Check if dataset already exists
        cursor.execute("SELECT id FROM datasets WHERE name = %s", (name,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing dataset
            cursor.execute("""
                UPDATE datasets 
                SET file_base64 = %s, sheet_names = %s, upload_id = %s, updated_at = %s
                WHERE name = %s
            """, (file_base64, json.dumps(sheet_names), upload_id, datetime.now(), name))
        else:
            # Insert new dataset
            cursor.execute("""
                INSERT INTO datasets (name, file_base64, sheet_names, upload_id, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (name, file_base64, json.dumps(sheet_names), upload_id, datetime.now(), datetime.now()))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"Dataset saved successfully: {name}")
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error saving dataset: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/get-datasets', methods=['GET'])
def get_datasets():
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'})
        
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, sheet_names, created_at FROM datasets ORDER BY created_at DESC")
        datasets = cursor.fetchall()
        
        result = []
        for dataset in datasets:
            result.append({
                'id': dataset['id'],
                'name': dataset['name'],
                'sheet_names': json.loads(dataset['sheet_names']) if dataset['sheet_names'] else [],
                'timestamp': dataset['created_at'].isoformat() if dataset['created_at'] else None
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        print(f"Error getting datasets: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/load-dataset', methods=['POST'])
def load_dataset():
    try:
        data = request.get_json()
        dataset_id = data.get('dataset_id')
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'})
        
        cursor = conn.cursor()
        cursor.execute("SELECT file_base64, sheet_names, upload_id FROM datasets WHERE id = %s", (dataset_id,))
        dataset = cursor.fetchone()
        
        if not dataset:
            return jsonify({'success': False, 'error': 'Dataset not found'})
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'file_base64': dataset['file_base64'],
                'sheet_names': json.loads(dataset['sheet_names']) if dataset['sheet_names'] else [],
                'upload_id': dataset['upload_id']
            }
        })
    except Exception as e:
        print(f"Error loading dataset: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/delete-dataset', methods=['POST'])
def delete_dataset():
    try:
        data = request.get_json()
        dataset_id = data.get('dataset_id')
        
        if not dataset_id:
            return jsonify({'error': 'dataset_id required'}), 400
        
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM upload_history WHERE id = %s", (dataset_id,))
            conn.commit()
            cursor.close()
            conn.close()
        
        return jsonify({'success': True, 'message': 'Dataset deleted'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/kpi', methods=['GET'])
def get_dashboard_kpi():
    conn = get_db_connection()
    total_uploads = 0
    total_calcs = 0
    
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM upload_history")
        total_uploads = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM calculations")
        total_calcs = cursor.fetchone()[0]
        cursor.close()
        conn.close()
    
    return jsonify({
        'success': True,
        'data': {
            'total_datasets': total_uploads,
            'active_calculations': total_calcs,
            'reports_generated': 0,
            'system_health': 'Optimal'
        }
    })

@app.route('/api/dashboard/recent-activity', methods=['GET'])
def get_recent_activity():
    conn = get_db_connection()
    activities = []
    
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT filename, created_at FROM upload_history ORDER BY created_at DESC LIMIT 10")
        rows = cursor.fetchall()
        for i, row in enumerate(rows):
            time_str = row[1].strftime('%Y-%m-%d %H:%M') if row[1] else 'Recently'
            activities.append({
                'id': i + 1,
                'text': f"{row[0]} uploaded",
                'time': time_str,
                'color': '#0B2A44'
            })
        cursor.close()
        conn.close()
    
    return jsonify({'success': True, 'data': activities})

@app.route('/api/dashboard/charts', methods=['GET'])
def get_dashboard_charts():
    return jsonify({
        'success': True,
        'data': {
            'monthlyActivity': {'labels': [], 'datasets': []},
            'instrumentDistribution': {'labels': [], 'data': []}
        }
    })

@app.route('/api/user/profile', methods=['GET'])
def get_user_profile():
    return jsonify({
        'success': True,
        'data': {
            'name': os.environ.get('ADMIN_NAME', ''),
            'email': os.environ.get('ADMIN_EMAIL', ''),
            'role': os.environ.get('ADMIN_ROLE', 'user')
        }
    })

@app.route('/api/user/preferences', methods=['GET'])
def get_user_preferences():
    return jsonify({
        'success': True,
        'data': {
            'language': os.environ.get('USER_LANGUAGE', 'English'),
            'timezone': os.environ.get('USER_TIMEZONE', 'UTC'),
            'currency': os.environ.get('USER_CURRENCY', 'USD')
        }
    })

@app.route('/api/user/notifications/settings', methods=['GET'])
def get_notification_settings():
    return jsonify({
        'success': True,
        'data': {
            'emailNotifications': os.environ.get('NOTIFY_EMAIL', 'true').lower() == 'true',
            'pushNotifications': os.environ.get('NOTIFY_PUSH', 'false').lower() == 'true',
            'weeklyReports': os.environ.get('NOTIFY_WEEKLY', 'true').lower() == 'true',
            'systemAlerts': os.environ.get('NOTIFY_ALERTS', 'true').lower() == 'true'
        }
    })

@app.route('/api/system/info', methods=['GET'])
def get_system_info():
    return jsonify({
        'success': True,
        'data': {
            'version': '1.0.0',
            'environment': os.environ.get('ENVIRONMENT', 'Development'),
            'api_status': 'Online',
            'database_connected': get_db_connection() is not None,
            'fred_configured': bool(FRED_API_KEY),
            'last_updated': datetime.now().isoformat()
        }
    })

@app.route('/api/calculations/history', methods=['GET'])
def get_calculation_history():
    conn = get_db_connection()
    results = []
    
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM calculations ORDER BY created_at DESC LIMIT 50")
        rows = cursor.fetchall()
        for row in rows:
            results.append({
                'id': row[0],
                'instrument_type': row[1],
                'calculation_status': row[4],
                'created_at': row[5].isoformat() if row[5] else None
            })
        cursor.close()
        conn.close()
    
    return jsonify({'success': True, 'data': results})

@app.route('/api/calculations/execute', methods=['POST'])
def execute_calculation():
    try:
        data = request.get_json()
        instrument_type = data.get('instrument_type', 'treasury_bills')
        calculation_data = data.get('data', [])
        params = data.get('params', {})
        
        if not calculation_data:
            return jsonify({'error': 'No data provided'}), 400
        
        results = perform_calculation(instrument_type, calculation_data)
        
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO calculations (instrument_type, input_data, result_data, calculation_status)
                VALUES (%s, %s, %s, %s)
            """, (instrument_type, json.dumps(calculation_data[:5]), json.dumps(results[:5]), 'completed'))
            conn.commit()
            cursor.close()
            conn.close()
        
        return jsonify({'success': True, 'data': results})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'true').lower() == 'true'
    app.run(debug=debug, port=port, host='0.0.0.0')
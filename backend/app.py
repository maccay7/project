from flask import Flask, request, jsonify
from flask_cors import CORS
import pymysql
import requests
import json
import openpyxl
import os
import base64
import tempfile
import uuid
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# CORS - Allow all origins for development (fixes the CORS error)
CORS(app, origins='*', supports_credentials=True)

# ==================== CONFIGURATION ====================
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', ''),
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
        print(f"Database error: {e}")
        return None

def init_database():
    conn = get_db_connection()
    if not conn:
        return
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                full_name VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS upload_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                filename VARCHAR(255),
                file_type VARCHAR(50),
                upload_status VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                instrument_type VARCHAR(50),
                file_base64 LONGTEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS datasets (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE,
                file_base64 LONGTEXT,
                sheet_names TEXT,
                upload_id VARCHAR(255),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
        print("Database tables verified")
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
        return response.json() if response.status_code == 200 else None
    except:
        return None

def calculate_money_market(row, params):
    principal = float(row.get('principal', row.get('Principal', 0)))
    interest_rate = float(row.get('interest_rate', row.get('interestRate', 0)))
    term_days = float(row.get('term_days', row.get('termDays', 0)))
    
    if principal <= 0 or interest_rate <= 0 or term_days <= 0:
        return {**row, 'error': 'Missing required fields'}
    
    interest_earned = principal * interest_rate * (term_days / 365)
    annual_yield = (interest_earned / principal) * (365 / term_days)
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
        if instrument_type in ['money_market', 'money-market']:
            results.append(calculate_money_market(row, {}))
        else:
            results.append(row)
    return results

# ==================== API ENDPOINTS ====================

@app.route('/')
def home():
    return jsonify({'message': 'DuraCapital API', 'status': 'running'})

@app.route('/api/login', methods=['POST', 'OPTIONS'])
def login():
    # Handle preflight request
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        print(f"Login attempt: {email}")
        
        # Hardcoded credentials (works without database)
        if email == 'makanakakanyai@gmail.com' and password == 'Business7mogul':
            return jsonify({
                'success': True,
                'token': str(uuid.uuid4()),
                'user': {
                    'id': 1,
                    'email': email,
                    'full_name': 'Makanaka Kanyai',
                    'role': 'admin'
                }
            })
        
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
        
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({'success': False, 'message': 'Login failed'}), 500

@app.route('/api/upload', methods=['POST', 'OPTIONS'])
def upload_data():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        instrument_type = request.form.get('instrument_type', 'treasury_bills')
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        file_extension = os.path.splitext(file.filename)[1].lower()
        file_data = file.read()
        file_base64 = base64.b64encode(file_data).decode('utf-8')
        
        return jsonify({
            'success': True,
            'data': {
                'file_base64': file_base64,
                'file_name': file.filename,
                'file_type': file_extension,
                'sheet_names': ['Sheet1'],
                'data': [],
                'headers': [],
                'total_rows': 0,
                'upload_id': str(uuid.uuid4())
            }
        })
        
    except Exception as e:
        print(f"Upload error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/calculate', methods=['POST', 'OPTIONS'])
def calculate_financials():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        calculation_data = data.get('data', [])
        instrument_type = data.get('instrument_type', 'money_market')
        
        if not calculation_data:
            return jsonify({'error': 'No data provided'}), 400
        
        results = perform_calculation(instrument_type, calculation_data)
        
        return jsonify({'success': True, 'calculations': results})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clean', methods=['POST', 'OPTIONS'])
def clean_data():
    if request.method == 'OPTIONS':
        return '', 200
    
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

@app.route('/api/fred-yield-curve', methods=['GET', 'OPTIONS'])
def get_fred_yield_curve():
    if request.method == 'OPTIONS':
        return '', 200
    
    return jsonify({
        'success': True,
        'data': {
            'labels': ['3M', '6M', '1Y', '2Y', '5Y', '10Y', '30Y'],
            'current': [4.2, 4.4, 4.6, 4.8, 4.5, 4.3, 4.1],
            'datasets': [{
                'label': 'Yield Curve',
                'data': [4.2, 4.4, 4.6, 4.8, 4.5, 4.3, 4.1],
                'borderColor': '#0B2A44',
                'fill': True
            }]
        }
    })

@app.route('/api/save-dataset', methods=['POST', 'OPTIONS'])
def save_dataset():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        name = data.get('name')
        file_base64 = data.get('file_base64')
        
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO datasets (name, file_base64, created_at)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE file_base64 = %s
            """, (name, file_base64, datetime.now(), file_base64))
            conn.commit()
            cursor.close()
            conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Save error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/get-datasets', methods=['GET', 'OPTIONS'])
def get_datasets():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        conn = get_db_connection()
        datasets = []
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, created_at FROM datasets ORDER BY created_at DESC")
            rows = cursor.fetchall()
            for row in rows:
                datasets.append({
                    'id': row[0],
                    'name': row[1],
                    'timestamp': row[2].isoformat() if row[2] else None
                })
            cursor.close()
            conn.close()
        
        return jsonify({'success': True, 'data': datasets})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/delete-dataset', methods=['POST', 'OPTIONS'])
def delete_dataset():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        dataset_id = data.get('dataset_id')
        
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM datasets WHERE id = %s", (dataset_id,))
            conn.commit()
            cursor.close()
            conn.close()
        
        return jsonify({'success': True, 'message': 'Deleted'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/kpi', methods=['GET', 'OPTIONS'])
def get_dashboard_kpi():
    if request.method == 'OPTIONS':
        return '', 200
    return jsonify({'success': True, 'data': {'total_datasets': 0, 'active_calculations': 0, 'reports_generated': 0, 'system_health': 'Optimal'}})

@app.route('/api/dashboard/recent-activity', methods=['GET', 'OPTIONS'])
def get_recent_activity():
    if request.method == 'OPTIONS':
        return '', 200
    return jsonify({'success': True, 'data': [{'id': 1, 'text': 'Welcome to DuraCapital', 'time': 'Just now', 'color': '#0B2A44'}]})

@app.route('/api/dashboard/charts', methods=['GET', 'OPTIONS'])
def get_dashboard_charts():
    if request.method == 'OPTIONS':
        return '', 200
    return jsonify({'success': True, 'data': {'monthlyActivity': {'labels': [], 'datasets': []}, 'instrumentDistribution': {'labels': [], 'data': []}}})

@app.route('/api/user/profile', methods=['GET', 'OPTIONS'])
def get_user_profile():
    if request.method == 'OPTIONS':
        return '', 200
    return jsonify({'success': True, 'data': {'name': 'Makanaka Kanyai', 'email': 'makanakakanyai@gmail.com', 'role': 'admin'}})

@app.route('/api/user/preferences', methods=['GET', 'OPTIONS'])
def get_user_preferences():
    if request.method == 'OPTIONS':
        return '', 200
    return jsonify({'success': True, 'data': {'language': 'English', 'timezone': 'UTC', 'currency': 'USD'}})

@app.route('/api/user/notifications/settings', methods=['GET', 'OPTIONS'])
def get_notification_settings():
    if request.method == 'OPTIONS':
        return '', 200
    return jsonify({'success': True, 'data': {'emailNotifications': True, 'pushNotifications': False, 'weeklyReports': True, 'systemAlerts': True}})

@app.route('/api/system/info', methods=['GET', 'OPTIONS'])
def get_system_info():
    if request.method == 'OPTIONS':
        return '', 200
    return jsonify({'success': True, 'data': {'version': '1.0.0', 'environment': 'Development', 'api_status': 'Online', 'last_updated': datetime.now().isoformat()}})

@app.route('/api/calculations/history', methods=['GET', 'OPTIONS'])
def get_calculation_history():
    if request.method == 'OPTIONS':
        return '', 200
    return jsonify({'success': True, 'data': []})

@app.route('/api/calculations/execute', methods=['POST', 'OPTIONS'])
def execute_calculation():
    if request.method == 'OPTIONS':
        return '', 200
    return jsonify({'success': True, 'data': []})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, port=port, host='0.0.0.0')
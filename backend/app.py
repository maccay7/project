from flask import Flask, request, jsonify
from flask_cors import CORS
import pymysql
import pandas as pd
import numpy as np
import requests
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'duracapital',
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

def get_db_connection():
    return pymysql.connect(**DB_CONFIG)

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

def calculate_yield_curve(treasury_data, bond_data, money_market_data):
    """Calculate yield curve from FRED data"""
    try:
        # Get latest rates
        latest_tbill = float(treasury_data['observations'][0]['value']) if treasury_data and treasury_data['observations'] else 0.0
        latest_bond = float(bond_data['observations'][0]['value']) if bond_data and bond_data['observations'] else 0.0
        latest_mm = float(money_market_data['observations'][0]['value']) if money_market_data and money_market_data['observations'] else 0.0
        
        # Create yield curve points
        yield_curve = {
            'labels': ['3M', '6M', '1Y', '2Y', '5Y', '10Y', '30Y'],
            'current': [
                latest_tbill,  # 3M
                latest_tbill + 0.1,  # 6M (estimated)
                latest_tbill + 0.2,  # 1Y (estimated)
                latest_tbill + 0.3,  # 2Y (estimated)
                latest_tbill + 0.4,  # 5Y (estimated)
                latest_bond,  # 10Y
                latest_bond - 0.2   # 30Y (estimated)
            ],
            'previous': [
                latest_tbill - 0.1,  # 3M previous
                latest_tbill,        # 6M previous
                latest_tbill + 0.1,  # 1Y previous
                latest_tbill + 0.2,  # 2Y previous
                latest_tbill + 0.3,  # 5Y previous
                latest_bond - 0.1,   # 10Y previous
                latest_bond - 0.3    # 30Y previous
            ],
            'metadata': {
                '3_month_treasury': latest_tbill,
                '10_year_bond': latest_bond,
                'federal_funds': latest_mm,
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
        
        # Read file based on extension
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file)
        elif file.filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file)
        else:
            return jsonify({'error': 'Unsupported file format'}), 400
        
        # Convert to JSON for frontend
        data = df.to_dict('records')
        
        return jsonify({
            'success': True,
            'data': {
                'name': file.filename,
                'size': len(data),
                'instrument_type': instrument_type,
                'data': data[:10]  # Return first 10 records for preview
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clean', methods=['POST'])
def clean_data():
    try:
        data = request.get_json()
        original_data = data.get('data', [])
        cleaning_options = data.get('options', {})
        
        df = pd.DataFrame(original_data)
        original_count = len(df)
        
        # Apply cleaning operations
        cleaned_df = df.copy()
        stats = {
            'original_rows': original_count,
            'duplicates_removed': 0,
            'missing_values_filled': 0,
            'outliers_removed': 0
        }
        
        if cleaning_options.get('remove_duplicates'):
            before_count = len(cleaned_df)
            cleaned_df = cleaned_df.drop_duplicates()
            stats['duplicates_removed'] = before_count - len(cleaned_df)
        
        if cleaning_options.get('fill_missing_values'):
            # Fill missing values with 0 for numeric, 'N/A' for text
            for col in cleaned_df.columns:
                if cleaned_df[col].dtype in ['int64', 'float64']:
                    cleaned_df[col] = cleaned_df[col].fillna(0)
                    stats['missing_values_filled'] += cleaned_df[col].isnull().sum()
                else:
                    cleaned_df[col] = cleaned_df[col].fillna('N/A')
        
        if cleaning_options.get('remove_outliers'):
            # Simple outlier removal using IQR method
            numeric_cols = cleaned_df.select_dtypes(include=[np.number]).columns
            for col in numeric_cols:
                Q1 = cleaned_df[col].quantile(0.25)
                Q3 = cleaned_df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                before_count = len(cleaned_df)
                cleaned_df = cleaned_df[(cleaned_df[col] >= lower_bound) & (cleaned_df[col] <= upper_bound)]
                stats['outliers_removed'] += before_count - len(cleaned_df)
        
        stats['cleaned_rows'] = len(cleaned_df)
        
        return jsonify({
            'success': True,
            'data': cleaned_df.to_dict('records'),
            'stats': stats
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
            if instrument_type == 'treasury-bills':
                result = calculate_treasury_bill(row, params)
            elif instrument_type == 'bonds':
                result = calculate_bond(row, params)
            elif instrument_type == 'money-market':
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
    principal = float(row.get('principal', params.get('principal', 1000)))
    interest = float(row.get('interest', params.get('interest', 25)))
    days = float(row.get('days', params.get('days', 90)))
    
    annual_rate = (interest / principal) * (365 / days)
    effective_rate = (1 + annual_rate) ** (365 / days) - 1
    
    return {
        **row,
        'annualRate': f"{(annual_rate * 100):.4f}%",
        'effectiveRate': f"{(effective_rate * 100):.4f}%"
    }

@app.route('/api/fred-yield-curve')
def get_fred_yield_curve():
    """Get yield curve data from FRED API"""
    try:
        # Fetch data for different instruments
        tbill_data = fetch_fred_data(FINANCIAL_INSTRUMENTS['treasury_bills']['fred_series'])
        bond_data = fetch_fred_data(FINANCIAL_INSTRUMENTS['bonds']['fred_series'])
        mm_data = fetch_fred_data(FINANCIAL_INSTRUMENTS['money_market']['fred_series'])
        
        # Calculate yield curve
        yield_curve = calculate_yield_curve(tbill_data, bond_data, mm_data)
        
        if yield_curve:
            return jsonify({
                'success': True,
                'data': yield_curve,
                'instruments': FINANCIAL_INSTRUMENTS
            })
        else:
            # Fallback to mock data if FRED API fails
            fallback_data = {
                'labels': ['3M', '6M', '1Y', '2Y', '5Y', '10Y', '30Y'],
                'current': [4.5, 4.8, 5.1, 5.3, 5.0, 4.8, 4.6, 4.4],
                'previous': [4.2, 4.5, 4.8, 5.0, 4.7, 4.5, 4.3, 4.1],
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
    return jsonify({
        'success': True,
        'data': {
            'total_investments': '$1,250,000',
            'active_calculations': 12,
            'reports_generated': 24,
            'system_health': 'Optimal'
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
        
        # Get recent calculations
        query = """
        SELECT id, instrument_type, calculation_status, created_at 
        FROM calculations 
        ORDER BY created_at DESC 
        LIMIT 10
        """
        cursor.execute(query)
        calculations = cursor.fetchall()
        
        # Format for frontend
        activities = []
        for calc in calculations:
            activities.append({
                'id': calc['id'],
                'text': f'{calc["instrument_type"].replace("_", " ").title()} {"completed" if calc["calculation_status"] == "completed" else "processed"}',
                'time': format_time_ago(calc['created_at']),
                'color': get_instrument_color(calc['instrument_type'])
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
        
        # Save calculation to database
        conn = get_db_connection()
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
        
        # Perform calculation
        if instrument_type == 'yield_curve':
            result = calculate_yield_curve_from_api()
        else:
            # Use existing calculation functions
            result = perform_calculation(instrument_type, calculation_data)
        
        # Update calculation record
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

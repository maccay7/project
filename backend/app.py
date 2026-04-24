from flask import Flask, request, jsonify
from flask_cors import CORS
import pymysql
import pandas as pd
import numpy as np
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'dura_capital',
    'cursorclass': pymysql.cursors.DictCursor
}

def get_db_connection():
    return pymysql.connect(**DB_CONFIG)

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
    # Mock FRED API data (replace with actual API call)
    mock_data = {
        'labels': ['1M', '3M', '6M', '1Y', '2Y', '5Y', '10Y', '30Y'],
        'current': [4.5, 4.8, 5.1, 5.3, 5.0, 4.8, 4.6, 4.4],
        'previous': [4.2, 4.5, 4.8, 5.0, 4.7, 4.5, 4.3, 4.1]
    }
    
    return jsonify({
        'success': True,
        'data': mock_data
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)

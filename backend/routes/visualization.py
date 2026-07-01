import json
from flask import request, jsonify
from utils.db import get_db
from datetime import datetime, timedelta
from utils.fred_config import series_for_country
import requests
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

FRED_API_KEY = os.environ.get('FRED_API_KEY')
FRED_BASE_URL = 'https://api.stlouisfed.org/fred'

def create_visualization_cache_table():
    conn = get_db()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS visualization_cache (
                id INT AUTO_INCREMENT PRIMARY KEY,
                cache_key VARCHAR(255) UNIQUE,
                instrument_type VARCHAR(50),
                country VARCHAR(50),
                currency VARCHAR(50),
                maturity VARCHAR(50),
                chart_data JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error creating cache table: {e}")
        return False

def get_cached_visualization(cache_key):
    conn = get_db()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM visualization_cache WHERE cache_key = %s AND expires_at > NOW()",
            (cache_key,)
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if not row:
            return None
        return {
            'chart_data': json.loads(row[6]) if row[6] else {}
        }
    except Exception as e:
        print(f"Cache get error: {e}")
        return None

def cache_visualization(cache_key, instrument_type, country, currency, maturity, chart_data, cache_duration_minutes=5):
    conn = get_db()
    if not conn:
        return False
    try:
        expires_at = datetime.now() + timedelta(minutes=cache_duration_minutes)
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO visualization_cache 
               (cache_key, instrument_type, country, currency, maturity, chart_data, expires_at) 
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
               chart_data = VALUES(chart_data),
               created_at = CURRENT_TIMESTAMP,
               expires_at = VALUES(expires_at)""",
            (cache_key, instrument_type, country, currency, maturity, json.dumps(chart_data), expires_at)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Cache save error: {e}")
        return False

def fetch_fred_rate(series_id):
    if not FRED_API_KEY:
        return None
    try:
        params = {
            'series_id': series_id,
            'api_key': FRED_API_KEY,
            'file_type': 'json',
            'sort_order': 'desc',
            'limit': 1
        }
        resp = requests.get(f'{FRED_BASE_URL}/series/observations', params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        if 'error_code' in data:
            return None
        obs = data.get('observations', [])
        if not obs:
            return None
        val = obs[0].get('value')
        if val == '.' or val is None:
            return None
        return float(val)
    except Exception as e:
        print(f"Error fetching {series_id}: {e}")
        return None

def get_maturities_for_instrument(inst_type):
    if inst_type == 'money-market':
        return ['1M','3M','6M','1Y']
    elif inst_type == 'bonds':
        return ['2Y','5Y','10Y','30Y']
    elif inst_type == 'tbills':
        return ['4W','8W','13W','26W','52W']
    else:
        return ['1M','3M','6M','1Y','2Y','5Y','10Y','30Y']

def parse_maturity_to_years(mat):
    num = float(mat[:-1])
    unit = mat[-1].upper()
    if unit == 'M':
        return num / 12
    elif unit == 'W':
        return num / 52
    elif unit == 'Y':
        return num
    else:
        return num

def prepare_yield_curve_data(instrument_type, country, currency, maturity):
    cache_key = f"yield_curve_{instrument_type}_{country}_{currency}_{maturity}"
    cached = get_cached_visualization(cache_key)
    if cached:
        return cached['chart_data']

    maturities = get_maturities_for_instrument(instrument_type)
    points = []

    def fetch_one(mat, fallback_country=None):
        if fallback_country:
            series_id, label, used_mat, _, _, note = series_for_country(fallback_country, mat)
        else:
            series_id, label, used_mat, _, _, note = series_for_country(country, mat)
        if not series_id:
            return None, None, None
        rate = fetch_fred_rate(series_id)
        if rate is None:
            return None, None, None
        return parse_maturity_to_years(used_mat), rate, used_mat

    # Try primary country
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_one, m) for m in maturities]
        for future in as_completed(futures):
            result = future.result()
            if result[0] is not None:
                points.append({'maturity': result[0], 'rate': result[1], 'code': result[2]})

    # If no points and country is not USA, fallback to USA
    if not points and country.upper() != 'USA':
        print(f"⚠️ No data for {country}, falling back to USA for {instrument_type} {maturity}")
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(fetch_one, m, 'USA') for m in maturities]
            for future in as_completed(futures):
                result = future.result()
                if result[0] is not None:
                    points.append({'maturity': result[0], 'rate': result[1], 'code': result[2]})

    if not points:
        return {'error': 'No data available from FRED for this country/maturity. Try selecting a different country or maturity.'}

    points.sort(key=lambda x: x['maturity'])
    chart_data = {
        'maturities': [p['code'] for p in points],
        'rates': [p['rate'] for p in points],
        'labels': [p['code'] for p in points]
    }
    cache_visualization(cache_key, instrument_type, country, currency, maturity, chart_data)
    return chart_data

def visualization_routes(app):
    create_visualization_cache_table()

    @app.route('/api/visualization/yield-curve', methods=['POST', 'OPTIONS'])
    def yield_curve_endpoint():
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        instrument_type = payload.get('instrument_type', 'money-market')
        country = payload.get('country', 'US')
        currency = payload.get('currency', 'USD')
        maturity = payload.get('maturity', '1Y')
        chart_data = prepare_yield_curve_data(instrument_type, country, currency, maturity)
        if 'error' in chart_data:
            return jsonify({'success': False, 'error': chart_data['error']}), 400
        return jsonify({'success': True, 'data': chart_data})

    @app.route('/api/visualization/cache/clear', methods=['DELETE', 'OPTIONS'])
    def clear_cache_endpoint():
        if request.method == 'OPTIONS':
            return '', 200
        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'DB error'}), 500
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM visualization_cache WHERE expires_at < NOW()")
            deleted = cursor.rowcount
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'success': True, 'data': {'deleted_count': deleted}})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
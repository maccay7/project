import os
import requests
from flask import request, jsonify
from dotenv import load_dotenv
from utils.fred_config import (
    build_filter_options,
    get_market_benchmark,
    series_for_country,
)

load_dotenv()

FRED_API_KEY = os.environ.get('FRED_API_KEY')
FRED_BASE_URL = 'https://api.stlouisfed.org/fred'

def fred_routes(app):

    @app.route('/api/fred/series/<series_id>', methods=['GET', 'OPTIONS'])
    def get_fred_series(series_id):
        if request.method == 'OPTIONS':
            return '', 200
        if not FRED_API_KEY:
            return jsonify({'success': False, 'error': 'FRED API key not configured'}), 500
        limit = request.args.get('limit', 200)
        sort_order = request.args.get('sort_order', 'desc')
        params = {
            'series_id': series_id,
            'api_key': FRED_API_KEY,
            'file_type': 'json',
            'sort_order': sort_order,
            'limit': limit
        }
        print(f"🔍 FRED API request: series={series_id}, limit={limit}, sort_order={sort_order}")
        try:
            response = requests.get(f'{FRED_BASE_URL}/series/observations', params=params, timeout=10)
            print(f"📊 FRED response status: {response.status_code}")
            response.raise_for_status()
            data = response.json()
            if 'error_code' in data:
                print(f"❌ FRED API error: {data.get('error_message')}")
                return jsonify({'success': False, 'error': data.get('error_message', 'FRED API error')}), 400
            observations = data.get('observations', [])
            print(f"📈 FRED returned {len(observations)} observations")
            result = []
            for obs in observations:
                if obs['value'] != '.':
                    result.append({
                        'date': obs['date'],
                        'value': float(obs['value'])
                    })
            print(f"✅ Filtered to {len(result)} valid observations")
            return jsonify({'success': True, 'series_id': series_id, 'data': result})
        except Exception as e:
            print(f"❌ FRED series error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/fred/categories', methods=['GET', 'OPTIONS'])
    def get_fred_categories():
        if request.method == 'OPTIONS':
            return '', 200
        categories = {
            'interest_rates': {
                'DTB3': '3-Month Treasury Bill',
                'DTB6': '6-Month Treasury Bill',
                'DGS1': '1-Year Treasury Rate',
                'DGS2': '2-Year Treasury Rate',
                'DGS5': '5-Year Treasury Rate',
                'DGS10': '10-Year Treasury Rate',
                'DGS30': '30-Year Treasury Rate',
                'T10Y2Y': '10Y-2Y Treasury Spread',
                'T10YIE': '10-Year Breakeven Inflation Rate'
            }
        }
        return jsonify({'success': True, 'categories': categories})

    @app.route('/api/fred/filters', methods=['GET', 'OPTIONS'])
    def fred_filters():
        if request.method == 'OPTIONS':
            return '', 200
        return jsonify({'success': True, 'data': build_filter_options()})

    @app.route('/api/fred/benchmark', methods=['GET', 'OPTIONS'])
    def fred_benchmark():
        if request.method == 'OPTIONS':
            return '', 200
        if not FRED_API_KEY:
            return jsonify({'success': False, 'error': 'FRED API key not configured'}), 500
        try:
            inst = request.args.get('instrument_type', 'money_market')
            maturity = request.args.get('maturity', '1Y')
            country = request.args.get('country', 'US')
            currency = request.args.get('currency', 'USD')
            data = get_market_benchmark(inst, maturity, country, currency)
            if data.get('error'):
                return jsonify({'success': False, 'error': data['error'], 'data': None}), 400
            return jsonify({'success': True, 'data': data})
        except Exception as e:
            print(f"Benchmark error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/fred/series-by-maturity', methods=['GET', 'OPTIONS'])
    def fred_series_by_maturity():
        if request.method == 'OPTIONS':
            return '', 200
        maturity = request.args.get('maturity', '1Y')
        country = request.args.get('country', 'US')
        if not FRED_API_KEY:
            return jsonify({'success': False, 'error': 'FRED API key not configured'}), 500
        series_id, label, used_mat, _, _, note = series_for_country(country, maturity)
        if not series_id:
            return jsonify({'success': False, 'error': f'No series found for {country} {maturity}'}), 404
        return jsonify({
            'success': True,
            'series_id': series_id,
            'label': label,
            'maturity': used_mat,
            'country': country.upper(),
            'note': note,
        })
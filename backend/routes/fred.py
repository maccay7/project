import os
import requests
from flask import request, jsonify
from dotenv import load_dotenv

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
        
        try:
            response = requests.get(f'{FRED_BASE_URL}/series/observations', params=params)
            response.raise_for_status()
            data = response.json()
            
            if 'error_code' in data:
                return jsonify({'success': False, 'error': data.get('error_message', 'FRED API error')}), 400
            
            observations = data.get('observations', [])
            result = []
            for obs in observations:
                if obs['value'] != '.':
                    result.append({
                        'date': obs['date'],
                        'value': float(obs['value'])
                    })
            
            return jsonify({'success': True, 'series_id': series_id, 'data': result})
        except Exception as e:
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
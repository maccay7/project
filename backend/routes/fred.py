import os
import requests
from flask import request, jsonify
from dotenv import load_dotenv
from utils.fred_config import (
    build_filter_options,
    get_market_benchmark,
    series_for_country,
    generate_synthetic_benchmark,
    get_yield_curve,
    logger
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
            return jsonify({
                'success': True,
                'series_id': series_id,
                'data': [{'date': '2024-01-01', 'value': 4.0}],
                'note': 'Synthetic fallback (no key)'
            }), 200
        params = {
            'series_id': series_id,
            'api_key': FRED_API_KEY,
            'file_type': 'json',
            'sort_order': 'desc',
            'limit': request.args.get('limit', 200)
        }
        try:
            resp = requests.get(f'{FRED_BASE_URL}/series/observations', params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if 'error_code' in data:
                return jsonify({'success': True, 'data': [], 'note': 'FRED error'}), 200
            observations = data.get('observations', [])
            result = [{'date': obs['date'], 'value': float(obs['value'])} 
                      for obs in observations if obs.get('value') and obs['value'] != '.']
            return jsonify({'success': True, 'series_id': series_id, 'data': result})
        except Exception as e:
            return jsonify({'success': True, 'data': [], 'note': str(e)}), 200

    @app.route('/api/fred/categories', methods=['GET', 'OPTIONS'])
    def get_fred_categories():
        if request.method == 'OPTIONS':
            return '', 200
        return jsonify({
            'success': True,
            'categories': {
                'DTB3': '3-Month T-Bill',
                'DGS10': '10-Year Treasury',
                'DGS2': '2-Year Treasury',
                'DGS5': '5-Year Treasury',
                'DGS30': '30-Year Treasury'
            }
        })

    @app.route('/api/fred/filters', methods=['GET', 'OPTIONS'])
    def fred_filters():
        if request.method == 'OPTIONS':
            return '', 200
        try:
            data = build_filter_options()
            return jsonify({'success': True, 'data': data})
        except Exception as e:
            logger.error(f"Filters error: {e}")
            return jsonify({
                'success': True,
                'data': {
                    'countries': [
                        {'code': 'US', 'name': 'United States', 'currency': 'USD', 'maturities': [
                            {'code': '1M', 'name': '1 Month'},
                            {'code': '3M', 'name': '3 Months'},
                            {'code': '6M', 'name': '6 Months'},
                            {'code': '1Y', 'name': '1 Year'},
                            {'code': '2Y', 'name': '2 Years'},
                            {'code': '5Y', 'name': '5 Years'},
                            {'code': '10Y', 'name': '10 Years'},
                            {'code': '30Y', 'name': '30 Years'}
                        ]}
                    ],
                    'currencies': [{'code': 'USD', 'name': 'USD'}]
                }
            }), 200

    @app.route('/api/fred/benchmark', methods=['GET', 'OPTIONS'])
    def fred_benchmark():
        if request.method == 'OPTIONS':
            return '', 200
        inst = request.args.get('instrument_type', 'money_market')
        maturity = request.args.get('maturity', '1Y')
        country = request.args.get('country', 'US')
        currency = request.args.get('currency', 'USD')
        data = get_market_benchmark(inst, maturity, country, currency)
        return jsonify({'success': True, 'data': data})

    @app.route('/api/fred/series-by-maturity', methods=['GET', 'OPTIONS'])
    def fred_series_by_maturity():
        if request.method == 'OPTIONS':
            return '', 200
        maturity = request.args.get('maturity', '1Y')
        country = request.args.get('country', 'US')
        series_id, label, used_mat, _, _, note = series_for_country(country, maturity)
        return jsonify({
            'success': True,
            'series_id': series_id,
            'label': label,
            'maturity': used_mat,
            'country': country.upper(),
            'note': note
        })

    # ===== YIELD CURVE – using app.add_url_rule with unique endpoint names =====
    def _fred_yield_curve_handler():
        if request.method == 'OPTIONS':
            return '', 200
        if request.method == 'POST':
            payload = request.get_json() or {}
            country = payload.get('country', 'US')
            maturities = payload.get('maturities')
        else:
            country = request.args.get('country', 'US')
            maturities = request.args.get('maturities')
            if maturities:
                maturities = maturities.split(',')

        points = get_yield_curve(country, maturities)
        if points:
            note = f'Yield curve from FRED (real data only). Retrieved {len(points)} maturities.'
        else:
            note = 'No yield curve data could be fetched from FRED for the selected country and maturities. Please try different filters.'

        return jsonify({
            'success': True,
            'data': {
                'maturities': [p['maturity'] for p in points],
                'labels': [p['maturityLabel'] for p in points],
                'rates': [p['rate'] for p in points],
                'country': country,
                'note': note
            }
        }), 200

    app.add_url_rule(
        '/api/fred/yield-curve',
        endpoint='fred_yield_curve_main',
        view_func=_fred_yield_curve_handler,
        methods=['GET', 'POST', 'OPTIONS']
    )

    def _legacy_fred_yield_curve_handler():
        return _fred_yield_curve_handler()

    app.add_url_rule(
        '/api/fred-yield-curve',
        endpoint='fred_yield_curve_legacy',
        view_func=_legacy_fred_yield_curve_handler,
        methods=['GET', 'OPTIONS']
    )

    print("✅ FRED routes registered (unique endpoints, no conflict)")
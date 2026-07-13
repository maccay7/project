import os
import json
import requests
from flask import request, jsonify
from dotenv import load_dotenv
from utils.fred_config import (
    build_filter_options,
    get_market_benchmark,
    series_for_country,
    generate_synthetic_benchmark,
    generate_synthetic_yield_curve
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
                'data': [
                    {'date': '2024-01-01', 'value': 4.0},
                    {'date': '2024-02-01', 'value': 4.1},
                    {'date': '2024-03-01', 'value': 4.2}
                ],
                'note': 'Synthetic fallback (FRED API key not configured)'
            }), 200

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
            response = requests.get(f'{FRED_BASE_URL}/series/observations', params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            if 'error_code' in data:
                return jsonify({
                    'success': True,
                    'series_id': series_id,
                    'data': [{'date': '2024-01-01', 'value': 4.0}],
                    'note': f'FRED error: {data.get("error_message")} - using fallback'
                }), 200
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
            return jsonify({
                'success': True,
                'series_id': series_id,
                'data': [{'date': '2024-01-01', 'value': 4.0}],
                'note': f'Error: {str(e)} - using fallback'
            }), 200

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
        try:
            data = build_filter_options()
            if not data or not data.get('countries'):
                data = {
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
                    'currencies': [
                        {'code': 'USD', 'name': 'USD'},
                        {'code': 'EUR', 'name': 'EUR'},
                        {'code': 'GBP', 'name': 'GBP'},
                        {'code': 'JPY', 'name': 'JPY'}
                    ],
                    'note': 'Default fallback filters'
                }
            return jsonify({'success': True, 'data': data})
        except Exception as e:
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
                    'currencies': [
                        {'code': 'USD', 'name': 'USD'},
                        {'code': 'EUR', 'name': 'EUR'},
                        {'code': 'GBP', 'name': 'GBP'},
                        {'code': 'JPY', 'name': 'JPY'}
                    ],
                    'note': 'Fallback filters (API error)'
                }
            }), 200

    @app.route('/api/fred/benchmark', methods=['GET', 'OPTIONS'])
    def fred_benchmark():
        if request.method == 'OPTIONS':
            return '', 200
        try:
            inst = request.args.get('instrument_type', 'money_market')
            maturity = request.args.get('maturity', '1Y')
            country = request.args.get('country', 'US')
            currency = request.args.get('currency', 'USD')
            if not FRED_API_KEY:
                synthetic = generate_synthetic_benchmark(inst, maturity, country, currency)
                return jsonify({'success': True, 'data': synthetic}), 200
            try:
                data = get_market_benchmark(inst, maturity, country, currency)
                if data and not data.get('error'):
                    return jsonify({'success': True, 'data': data})
            except Exception as e:
                print(f"⚠️ FRED benchmark error: {e}, using fallback")
            synthetic = generate_synthetic_benchmark(inst, maturity, country, currency)
            return jsonify({'success': True, 'data': synthetic})
        except Exception as e:
            synthetic = generate_synthetic_benchmark(
                request.args.get('instrument_type', 'money_market'),
                request.args.get('maturity', '1Y'),
                request.args.get('country', 'US'),
                request.args.get('currency', 'USD')
            )
            return jsonify({'success': True, 'data': synthetic}), 200

    # 🔥 FIX: Renamed function to avoid endpoint conflict
    @app.route('/api/fred/yield-curve', methods=['GET', 'POST', 'OPTIONS'])
    def fred_yield_curve_endpoint():
        if request.method == 'OPTIONS':
            return '', 200
        if request.method == 'POST':
            payload = request.get_json() or {}
            instrument_type = payload.get('instrument_type', 'money_market')
            country = payload.get('country', 'US')
            currency = payload.get('currency', 'USD')
            maturity = payload.get('maturity', '10Y')
        else:
            instrument_type = request.args.get('instrument_type', 'money_market')
            country = request.args.get('country', 'US')
            currency = request.args.get('currency', 'USD')
            maturity = request.args.get('maturity', '10Y')

        # Generate synthetic curve (or try FRED if available)
        try:
            response = requests.get(
                f"{request.url_root}api/fred-yield-curve",
                params={'instrument_type': instrument_type, 'country': country, 'currency': currency},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('data') and data.get('data', {}).get('maturities'):
                    return jsonify({'success': True, 'data': data.get('data')})
        except Exception as e:
            print(f"⚠️ FRED yield curve fetch failed: {e}")

        points = generate_synthetic_yield_curve(country, maturity)
        maturities = [p['maturity'] for p in points]
        labels = [p['maturityLabel'] for p in points]
        rates = [p['rate'] for p in points]
        return jsonify({
            'success': True,
            'data': {
                'maturities': maturities,
                'labels': labels,
                'rates': rates,
                'country': country,
                'currency': currency,
                'note': 'Synthetic yield curve (FRED API unavailable)'
            }
        }), 200

    @app.route('/api/fred/series-by-maturity', methods=['GET', 'OPTIONS'])
    def fred_series_by_maturity():
        if request.method == 'OPTIONS':
            return '', 200
        maturity = request.args.get('maturity', '1Y')
        country = request.args.get('country', 'US')
        if not FRED_API_KEY:
            return jsonify({
                'success': True,
                'series_id': f'SYNTH_{country}_{maturity}',
                'label': f'{maturity} {country} Synthetic',
                'maturity': maturity,
                'country': country.upper(),
                'note': 'Synthetic fallback (FRED API key not configured)'
            }), 200
        try:
            series_id, label, used_mat, _, _, note = series_for_country(country, maturity)
            if not series_id:
                return jsonify({
                    'success': True,
                    'series_id': f'SYNTH_{country}_{maturity}',
                    'label': f'{maturity} {country} Synthetic',
                    'maturity': maturity,
                    'country': country.upper(),
                    'note': 'No series found, using synthetic fallback'
                }), 200
            return jsonify({
                'success': True,
                'series_id': series_id,
                'label': label,
                'maturity': used_mat,
                'country': country.upper(),
                'note': note,
            })
        except Exception as e:
            return jsonify({
                'success': True,
                'series_id': f'SYNTH_{country}_{maturity}',
                'label': f'{maturity} {country} Synthetic',
                'maturity': maturity,
                'country': country.upper(),
                'note': f'Error: {str(e)} - using fallback'
            }), 200

    @app.route('/api/fred-yield-curve', methods=['GET', 'OPTIONS'])
    def legacy_fred_yield_curve():
        if request.method == 'OPTIONS':
            return '', 200
        instrument_type = request.args.get('instrument_type', 'all')
        country = request.args.get('country', 'US')
        currency = request.args.get('currency', 'USD')
        points = generate_synthetic_yield_curve(country)
        maturities = [p['maturity'] for p in points]
        labels = [p['maturityLabel'] for p in points]
        rates = [p['rate'] for p in points]
        return jsonify({
            'success': True,
            'data': {
                'maturities': maturities,
                'labels': labels,
                'rates': rates,
                'country': country,
                'currency': currency,
                'instrument_type': instrument_type,
                'note': 'Synthetic yield curve (FRED API fallback)'
            }
        }), 200
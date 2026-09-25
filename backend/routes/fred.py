# backend/.../fred.py
import os
import requests
from flask import request, jsonify
from dotenv import load_dotenv
from utils.fred_config import (
    build_filter_options,
    get_market_benchmark,
    series_for_country,
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
            return jsonify({'success': False, 'error': 'FRED_API_KEY not set'}), 500
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
                return jsonify({'success': False, 'error': data.get('error_message')}), 400
            observations = data.get('observations', [])
            result = [{'date': obs['date'], 'value': float(obs['value'])}
                      for obs in observations if obs.get('value') and obs['value'] != '.']
            return jsonify({'success': True, 'series_id': series_id, 'data': result})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

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
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/fred/benchmark', methods=['GET', 'OPTIONS'])
    def fred_benchmark():
        if request.method == 'OPTIONS':
            return '', 200
        inst = request.args.get('instrument_type')
        maturity = request.args.get('maturity') or '1Y'
        country = request.args.get('country') or 'US'
        currency = request.args.get('currency') or 'USD'
        if not inst:
            return jsonify({'success': False, 'error': 'instrument_type is required'}), 400
        data = get_market_benchmark(inst, maturity, country, currency)
        if data.get('benchmark_rate') is None:
            return jsonify({'success': False, 'error': data.get('error'), 'note': data.get('note')}), 404
        return jsonify({'success': True, 'data': data})

    @app.route('/api/fred/series-by-maturity', methods=['GET', 'OPTIONS'])
    def fred_series_by_maturity():
        if request.method == 'OPTIONS':
            return '', 200
        maturity = request.args.get('maturity')
        country = request.args.get('country')
        if not maturity or not country:
            return jsonify({'success': False, 'error': 'maturity and country are required'}), 400
        series_id, label, used_mat, _, _, note = series_for_country(country, maturity)
        if not series_id:
            return jsonify({'success': False, 'error': 'No series found'}), 404
        return jsonify({
            'success': True,
            'series_id': series_id,
            'label': label,
            'maturity': used_mat,
            'country': str(country).upper(),
            'note': note
        })

    # ─────────────────────────────────────────────────────────────────────────
    # Yield curve — accepts POST with instrument_type, currency, maturity
    # or from_date/to_date. Returns currency + instrument_type echoed back.
    # ─────────────────────────────────────────────────────────────────────────
    def _fred_yield_curve_handler():
        if request.method == 'OPTIONS':
            response = jsonify({})
            response.headers.add("Access-Control-Allow-Origin", "*")
            response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
            response.headers.add("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
            return response

        try:
            if request.method == 'POST':
                payload = request.get_json() or {}
                country = payload.get('country')
                instrument_type = payload.get('instrument_type') or 'money-market'
                currency = payload.get('currency') or 'USD'
                maturity = payload.get('maturity')
                maturities = payload.get('maturities')
                from_date = payload.get('from_date')
                to_date = payload.get('to_date')
            else:
                country = request.args.get('country')
                instrument_type = request.args.get('instrument_type') or 'money-market'
                currency = request.args.get('currency') or 'USD'
                maturity = request.args.get('maturity')
                maturities = request.args.get('maturities')
                if maturities:
                    maturities = maturities.split(',')
                from_date = request.args.get('from_date')
                to_date = request.args.get('to_date')

            if not country:
                return jsonify({'success': False,
                                'error': 'country is required'}), 400

            if not FRED_API_KEY:
                return jsonify({'success': False,
                                'error': 'FRED_API_KEY not set on server'}), 500

            logger.info(
                f"Yield curve request — country={country} "
                f"instrument_type={instrument_type} maturity={maturity} "
                f"currency={currency} from={from_date} to={to_date}"
            )

            points = get_yield_curve(
                country,
                maturities=maturities,
                from_date=from_date,
                to_date=to_date
            )

            if not points:
                return jsonify({
                    'success': False,
                    'error': 'No yield curve data could be fetched from FRED for the selected filters.',
                    'note': 'Please try different filters or verify your FRED_API_KEY.'
                }), 404

            return jsonify({
                'success': True,
                'data': {
                    'maturities': [p['maturity'] for p in points],
                    'labels': [p['maturityLabel'] for p in points],
                    'rates': [p['rate'] for p in points],
                    'country': str(country).upper(),
                    'currency': currency,
                    'instrument_type': instrument_type,
                    'from_date': from_date,
                    'to_date': to_date,
                    'note': f'Yield curve from FRED (real data only). Retrieved {len(points)} maturities.',
                    'datasets': [{
                        'label': f'{country} Yield Curve',
                        'data': [{'x': p['maturity'], 'y': p['rate']} for p in points],
                        'borderColor': '#0B2044',
                        'backgroundColor': 'rgba(11, 32, 68, 0.1)',
                        'tension': 0.1
                    }]
                }
            }), 200
        except Exception as e:
            logger.error(f"Yield curve error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    app.add_url_rule(
        '/api/fred/yield-curve',
        endpoint='fred_yield_curve_main',
        view_func=_fred_yield_curve_handler,
        methods=['GET', 'POST', 'OPTIONS']
    )

    app.add_url_rule(
        '/api/fred-yield-curve',
        endpoint='fred_yield_curve_legacy',
        view_func=_fred_yield_curve_handler,
        methods=['GET', 'POST', 'OPTIONS']
    )

    print("FRED routes registered")
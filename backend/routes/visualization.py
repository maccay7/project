import json
import math
from flask import request, jsonify
from datetime import datetime
from utils.db import get_db
import requests

FRED_API_KEY = 'b40141a5119f30bc2388d63f59d8847e'
FRED_BASE_URL = 'https://api.stlouisfed.org/fred'

def generate_yield_curve_data(instrument_type='all', country='US', currency='USD', maturity='10Y'):
    print(f"📊 Generating yield curve: instrument_type={instrument_type}, country={country}, currency={currency}, maturity={maturity}")
    try:
        maturities_to_fetch = ['DGS1MO', 'DGS3MO', 'DGS6MO', 'DGS1', 'DGS2', 'DGS3', 'DGS5', 'DGS7', 'DGS10', 'DGS20', 'DGS30']
        maturity_map = {
            'DGS1MO': {'label': '1M', 'years': 0.083},
            'DGS3MO': {'label': '3M', 'years': 0.25},
            'DGS6MO': {'label': '6M', 'years': 0.5},
            'DGS1': {'label': '1Y', 'years': 1.0},
            'DGS2': {'label': '2Y', 'years': 2.0},
            'DGS3': {'label': '3Y', 'years': 3.0},
            'DGS5': {'label': '5Y', 'years': 5.0},
            'DGS7': {'label': '7Y', 'years': 7.0},
            'DGS10': {'label': '10Y', 'years': 10.0},
            'DGS20': {'label': '20Y', 'years': 20.0},
            'DGS30': {'label': '30Y', 'years': 30.0}
        }
        maturities = []
        labels = []
        rates = []
        for series_id in maturities_to_fetch:
            try:
                params = {
                    'series_id': series_id,
                    'api_key': FRED_API_KEY,
                    'file_type': 'json',
                    'sort_order': 'desc',
                    'limit': 1
                }
                response = requests.get(f'{FRED_BASE_URL}/series/observations', params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    observations = data.get('observations', [])
                    if observations:
                        for obs in observations:
                            if obs.get('value') and obs.get('value') != '.':
                                rate = float(obs['value'])
                                mat_info = maturity_map.get(series_id, {'label': series_id, 'years': 0})
                                maturities.append(mat_info['years'])
                                labels.append(mat_info['label'])
                                rates.append(round(rate, 2))
                                break
                    else:
                        print(f"⚠️ No observations for {series_id}")
                else:
                    print(f"⚠️ Failed to fetch {series_id}: status {response.status_code}")
            except Exception as e:
                print(f"⚠️ Failed to fetch {series_id}: {e}")
                continue
        if not maturities:
            data = {
                'maturities': [],
                'labels': [],
                'rates': [],
                'country': country,
                'currency': currency,
                'instrument_type': instrument_type,
                'note': 'No data fetched from FRED'
            }
        else:
            data = {
                'maturities': maturities,
                'labels': labels,
                'rates': rates,
                'country': country,
                'currency': currency,
                'instrument_type': instrument_type,
                'note': 'Real FRED API yield curve data'
            }
            print(f"✅ Yield curve generated: {len(maturities)} points")
        return data
    except Exception as e:
        print(f"❌ Yield curve generation error: {e}")
        import traceback
        traceback.print_exc()
        return {
            'maturities': [],
            'labels': [],
            'rates': [],
            'country': country,
            'currency': currency,
            'instrument_type': instrument_type,
            'note': f'Error: {str(e)}'
        }

def prepare_chart_data(data, instrument_type='money-market'):
    if not data or not isinstance(data, list):
        return {'datasets': [], 'labels': []}
    chart_data = {'labels': [], 'datasets': []}
    if isinstance(data, dict) and 'maturities' in data and 'rates' in data:
        chart_data['labels'] = data.get('labels', [str(m) for m in data.get('maturities', [])])
        chart_data['datasets'] = [{
            'label': 'Yield Curve',
            'data': data.get('rates', []),
            'borderColor': '#0B2044',
            'backgroundColor': 'rgba(11, 32, 68, 0.1)',
            'fill': True,
            'tension': 0.3,
            'pointBackgroundColor': '#1E88E5',
            'pointRadius': 4
        }]
        return chart_data
    if isinstance(data, list) and len(data) > 0:
        values = []
        for item in data:
            val = item.get('Total Value') or item.get('Value') or item.get('amount') or 0
            try:
                values.append(float(val))
            except:
                pass
        if values:
            import numpy as np
            bins = 8
            min_val = min(values)
            max_val = max(values)
            range_val = max_val - min_val if max_val > min_val else 1
            bin_width = range_val / bins
            hist = [0] * bins
            for v in values:
                idx = int((v - min_val) / bin_width)
                if idx >= bins:
                    idx = bins - 1
                hist[idx] += 1
            labels = [f'${min_val + i*bin_width:.0f}-${min_val + (i+1)*bin_width:.0f}' for i in range(bins)]
            chart_data['labels'] = labels
            chart_data['datasets'] = [{
                'label': 'Value Distribution',
                'data': hist,
                'backgroundColor': 'rgba(26, 77, 143, 0.7)',
                'borderColor': '#1a4d8f',
                'borderWidth': 1
            }]
            return chart_data
    chart_data['labels'] = ['No Data']
    chart_data['datasets'] = [{
        'label': 'No Data',
        'data': [0],
        'backgroundColor': 'rgba(200, 200, 200, 0.5)'
    }]
    return chart_data

def visualization_routes(app):
    @app.route('/api/visualization/yield-curve', methods=['POST', 'OPTIONS'])
    def visualization_yield_curve():
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        instrument_type = payload.get('instrument_type', 'money-market')
        country = payload.get('country', 'US')
        currency = payload.get('currency', 'USD')
        maturity = payload.get('maturity', '10Y')
        data = generate_yield_curve_data(instrument_type, country, currency, maturity)
        return jsonify({'success': True, 'data': data})

    @app.route('/api/visualization/chart-data', methods=['POST', 'OPTIONS'])
    def visualization_chart_data():
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        data = payload.get('data', [])
        instrument_type = payload.get('instrument_type', 'money-market')
        chart_data = prepare_chart_data(data, instrument_type)
        return jsonify({'success': True, 'data': chart_data})

    print("✅ Visualization routes registered – no FRED endpoints")
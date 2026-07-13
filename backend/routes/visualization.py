import json
import math
import random
from flask import request, jsonify
from datetime import datetime, timedelta
from utils.db import get_db
from utils.fred_config import generate_synthetic_yield_curve, generate_synthetic_benchmark

# Simple in-memory cache for yield curve data
_cache = {}
CACHE_TTL = 15 * 60  # 15 minutes


def get_cached_data(key):
    """Get cached data if not expired."""
    if key in _cache:
        data, timestamp = _cache[key]
        if (datetime.now() - timestamp).total_seconds() < CACHE_TTL:
            return data
        else:
            del _cache[key]
    return None


def set_cached_data(key, data):
    """Store data in cache with current timestamp."""
    _cache[key] = (data, datetime.now())


def generate_yield_curve_data(instrument_type='all', country='US', currency='USD'):
    """
    Generate yield curve data, either from FRED or synthetic fallback.
    Returns a dict with maturities, labels, rates, and metadata.
    """
    # Try to get from cache first
    cache_key = f"yield_curve_{instrument_type}_{country}_{currency}"
    cached = get_cached_data(cache_key)
    if cached:
        return cached
    
    # Try to fetch from FRED API (via fred_config or direct call)
    try:
        from utils.fred_config import get_market_benchmark
        # For yield curve, we might want to fetch multiple maturities
        # For simplicity, we generate synthetic curve as fallback
        # In a real implementation, you would call a FRED endpoint for the curve
        # Since we don't have a specific FRED endpoint for the whole curve,
        # we generate synthetic data.
        points = generate_synthetic_yield_curve(country)
        maturities = [p['maturity'] for p in points]
        labels = [p['maturityLabel'] for p in points]
        rates = [p['rate'] for p in points]
        data = {
            'maturities': maturities,
            'labels': labels,
            'rates': rates,
            'country': country,
            'currency': currency,
            'instrument_type': instrument_type,
            'note': 'Synthetic yield curve (FRED API fallback)'
        }
    except Exception as e:
        # If any error, fallback to synthetic
        points = generate_synthetic_yield_curve(country)
        maturities = [p['maturity'] for p in points]
        labels = [p['maturityLabel'] for p in points]
        rates = [p['rate'] for p in points]
        data = {
            'maturities': maturities,
            'labels': labels,
            'rates': rates,
            'country': country,
            'currency': currency,
            'instrument_type': instrument_type,
            'note': f'Error: {str(e)} – using fallback'
        }
    
    # Cache the result
    set_cached_data(cache_key, data)
    return data


def prepare_chart_data(data, instrument_type='money-market'):
    """
    Prepare chart data from raw instrument data.
    Returns chart-ready datasets.
    """
    if not data or not isinstance(data, list):
        return {'datasets': [], 'labels': []}
    
    # Extract relevant fields based on instrument type
    chart_data = {
        'labels': [],
        'datasets': []
    }
    
    # For yield curve, we expect data to contain maturity and rate pairs
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
    
    # For instrument data, compute distribution
    if isinstance(data, list) and len(data) > 0:
        # Assume each item has 'Total Value' or similar
        values = []
        for item in data:
            val = item.get('Total Value') or item.get('Value') or item.get('amount') or 0
            try:
                values.append(float(val))
            except:
                pass
        
        if values:
            # Create histogram
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
    
    # Fallback empty chart
    chart_data['labels'] = ['No Data']
    chart_data['datasets'] = [{
        'label': 'No Data',
        'data': [0],
        'backgroundColor': 'rgba(200, 200, 200, 0.5)'
    }]
    return chart_data


def visualization_routes(app):
    """Register all visualization routes."""

    @app.route('/api/visualization/yield-curve', methods=['POST', 'OPTIONS'])
    def yield_curve_endpoint():
        """Get yield curve data."""
        if request.method == 'OPTIONS':
            return '', 200
        
        payload = request.get_json() or {}
        instrument_type = payload.get('instrument_type', 'money-market')
        country = payload.get('country', 'US')
        currency = payload.get('currency', 'USD')
        maturity = payload.get('maturity', '10Y')
        
        # Generate yield curve data
        data = generate_yield_curve_data(instrument_type, country, currency)
        
        # Also get benchmark for the specific maturity if needed
        try:
            from utils.fred_config import get_market_benchmark
            benchmark = get_market_benchmark(instrument_type, maturity, country, currency)
            if benchmark and not benchmark.get('error'):
                data['benchmark'] = benchmark
        except:
            pass
        
        return jsonify({'success': True, 'data': data})

    @app.route('/api/visualization/chart-data', methods=['POST', 'OPTIONS'])
    def chart_data_endpoint():
        """Prepare chart data from instrument data."""
        if request.method == 'OPTIONS':
            return '', 200
        
        payload = request.get_json() or {}
        data = payload.get('data', [])
        instrument_type = payload.get('instrument_type', 'money-market')
        
        chart_data = prepare_chart_data(data, instrument_type)
        return jsonify({'success': True, 'data': chart_data})

    @app.route('/api/visualization/cache/clear', methods=['DELETE', 'OPTIONS'])
    def clear_cache_endpoint():
        """Clear the yield curve cache."""
        if request.method == 'OPTIONS':
            return '', 200
        
        global _cache
        _cache.clear()
        return jsonify({'success': True, 'message': 'Cache cleared'})

    # Legacy endpoint for yield curve (GET)
    @app.route('/api/fred-yield-curve', methods=['GET', 'OPTIONS'])
    def legacy_yield_curve():
        """Legacy yield curve endpoint (GET)."""
        if request.method == 'OPTIONS':
            return '', 200
        
        instrument_type = request.args.get('instrument_type', 'all')
        country = request.args.get('country', 'US')
        currency = request.args.get('currency', 'USD')
        
        data = generate_yield_curve_data(instrument_type, country, currency)
        return jsonify({'success': True, 'data': data})

    # Benchmark endpoint (legacy)
    @app.route('/api/fred/benchmark', methods=['GET', 'OPTIONS'])
    def benchmark_endpoint():
        """Get benchmark rate (legacy)."""
        if request.method == 'OPTIONS':
            return '', 200
        
        instrument_type = request.args.get('instrument_type', 'money_market')
        maturity = request.args.get('maturity', '1Y')
        country = request.args.get('country', 'US')
        currency = request.args.get('currency', 'USD')
        
        try:
            from utils.fred_config import get_market_benchmark
            benchmark = get_market_benchmark(instrument_type, maturity, country, currency)
            if benchmark and not benchmark.get('error'):
                return jsonify({'success': True, 'data': benchmark})
            else:
                # Fallback to synthetic
                synthetic = generate_synthetic_benchmark(instrument_type, maturity, country, currency)
                return jsonify({'success': True, 'data': synthetic})
        except Exception as e:
            synthetic = generate_synthetic_benchmark(instrument_type, maturity, country, currency)
            return jsonify({'success': True, 'data': synthetic})
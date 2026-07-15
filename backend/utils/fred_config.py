import os
import json
import requests
import math
import random
from flask import jsonify
from dotenv import load_dotenv

load_dotenv()

FRED_API_KEY = os.environ.get('FRED_API_KEY', 'b40141a5119f30bc2388d63f59d8847e')
FRED_BASE_URL = 'https://api.stlouisfed.org/fred'

# ===== SYNTHETIC DATA GENERATORS (FALLBACK) =====

def generate_synthetic_yield_curve(country='US', maturity='10Y'):
    """
    Generate a realistic synthetic yield curve when FRED API is unavailable.
    Returns a dict with maturities, labels, rates, and metadata.
    """
    # Base parameters for different countries
    base_rates = {
        'US': {'level': 4.2, 'slope': 0.08, 'curvature': 0.02},
        'GB': {'level': 4.0, 'slope': 0.07, 'curvature': 0.01},
        'GBR': {'level': 4.0, 'slope': 0.07, 'curvature': 0.01},
        'EUR': {'level': 3.5, 'slope': 0.06, 'curvature': 0.01},
        'JP': {'level': 2.0, 'slope': 0.04, 'curvature': 0.005},
        'JPN': {'level': 2.0, 'slope': 0.04, 'curvature': 0.005},
        'CA': {'level': 4.0, 'slope': 0.07, 'curvature': 0.015},
        'CAN': {'level': 4.0, 'slope': 0.07, 'curvature': 0.015},
        'AU': {'level': 4.3, 'slope': 0.09, 'curvature': 0.02},
        'AUS': {'level': 4.3, 'slope': 0.09, 'curvature': 0.02},
        'ZA': {'level': 8.0, 'slope': 0.15, 'curvature': 0.03},
        'ZAF': {'level': 8.0, 'slope': 0.15, 'curvature': 0.03},
        'CH': {'level': 3.0, 'slope': 0.05, 'curvature': 0.01},
        'CHE': {'level': 3.0, 'slope': 0.05, 'curvature': 0.01},
        'NZ': {'level': 4.1, 'slope': 0.08, 'curvature': 0.015},
        'NZL': {'level': 4.1, 'slope': 0.08, 'curvature': 0.015},
        'NO': {'level': 3.8, 'slope': 0.07, 'curvature': 0.01},
        'NOR': {'level': 3.8, 'slope': 0.07, 'curvature': 0.01},
        'SE': {'level': 3.5, 'slope': 0.06, 'curvature': 0.01},
        'SWE': {'level': 3.5, 'slope': 0.06, 'curvature': 0.01},
        'DK': {'level': 3.3, 'slope': 0.06, 'curvature': 0.01},
        'DNK': {'level': 3.3, 'slope': 0.06, 'curvature': 0.01},
        'BR': {'level': 10.5, 'slope': 0.12, 'curvature': 0.02},
        'BRA': {'level': 10.5, 'slope': 0.12, 'curvature': 0.02},
        'MX': {'level': 8.5, 'slope': 0.11, 'curvature': 0.02},
        'MEX': {'level': 8.5, 'slope': 0.11, 'curvature': 0.02},
        'IN': {'level': 6.8, 'slope': 0.10, 'curvature': 0.015},
        'IND': {'level': 6.8, 'slope': 0.10, 'curvature': 0.015},
        'CN': {'level': 3.0, 'slope': 0.05, 'curvature': 0.01},
        'CHN': {'level': 3.0, 'slope': 0.05, 'curvature': 0.01},
        'KR': {'level': 3.5, 'slope': 0.06, 'curvature': 0.01},
        'KOR': {'level': 3.5, 'slope': 0.06, 'curvature': 0.01},
        'SG': {'level': 3.2, 'slope': 0.05, 'curvature': 0.01},
        'SGP': {'level': 3.2, 'slope': 0.05, 'curvature': 0.01},
        'HK': {'level': 3.0, 'slope': 0.05, 'curvature': 0.01},
        'HKG': {'level': 3.0, 'slope': 0.05, 'curvature': 0.01},
        'RU': {'level': 9.0, 'slope': 0.12, 'curvature': 0.02},
        'RUS': {'level': 9.0, 'slope': 0.12, 'curvature': 0.02},
        'TR': {'level': 20.0, 'slope': 0.20, 'curvature': 0.03},
        'TUR': {'level': 20.0, 'slope': 0.20, 'curvature': 0.03},
        'SA': {'level': 5.0, 'slope': 0.08, 'curvature': 0.01},
        'SAU': {'level': 5.0, 'slope': 0.08, 'curvature': 0.01},
        'AE': {'level': 4.5, 'slope': 0.07, 'curvature': 0.01},
        'ARE': {'level': 4.5, 'slope': 0.07, 'curvature': 0.01},
        'IL': {'level': 4.5, 'slope': 0.07, 'curvature': 0.01},
        'ISR': {'level': 4.5, 'slope': 0.07, 'curvature': 0.01},
    }
    
    params = base_rates.get(country.upper(), base_rates.get('US', {'level': 4.2, 'slope': 0.08, 'curvature': 0.02}))
    
    # Maturities and their labels
    maturity_map = {
        '1M': 0.083,
        '3M': 0.25,
        '6M': 0.5,
        '1Y': 1.0,
        '2Y': 2.0,
        '3Y': 3.0,
        '5Y': 5.0,
        '7Y': 7.0,
        '10Y': 10.0,
        '20Y': 20.0,
        '30Y': 30.0,
        '4W': 0.077,
        '13W': 0.25,
        '26W': 0.5,
        '52W': 1.0
    }
    
    maturities = list(maturity_map.keys())
    points = []
    
    for mat_label in maturities:
        years = maturity_map[mat_label]
        # Nelson-Siegel style: y = level + slope * (1 - exp(-maturity/tau)) / (maturity/tau) + curvature * ((1 - exp(-maturity/tau)) / (maturity/tau) - exp(-maturity/tau))
        # Simplified: polynomial + random noise
        rate = params['level'] + params['slope'] * years + params['curvature'] * math.pow(years, 1.2)
        # Add small random noise for realism
        rate += (random.random() - 0.5) * 0.15
        # Ensure rate is reasonable
        rate = max(0.1, min(25.0, rate))
        points.append({
            'maturity': years,
            'maturityLabel': mat_label,
            'rate': round(rate, 2)
        })
    
    return points


def generate_synthetic_benchmark(instrument_type='money_market', maturity='1Y', country='US', currency='USD'):
    """
    Generate a synthetic benchmark rate when FRED API fails.
    """
    # Base rates by instrument type and country
    base_rates = {
        'money_market': {'US': 4.2, 'GB': 4.0, 'EUR': 3.5, 'JP': 2.0, 'CA': 4.0, 'AU': 4.3, 'ZA': 8.0},
        'money-market': {'US': 4.2, 'GB': 4.0, 'EUR': 3.5, 'JP': 2.0, 'CA': 4.0, 'AU': 4.3, 'ZA': 8.0},
        'bonds': {'US': 4.5, 'GB': 4.2, 'EUR': 3.8, 'JP': 2.2, 'CA': 4.3, 'AU': 4.5, 'ZA': 8.5},
        'tbills': {'US': 3.8, 'GB': 3.5, 'EUR': 3.2, 'JP': 1.8, 'CA': 3.7, 'AU': 4.0, 'ZA': 7.5}
    }
    
    # Maturity adjustments (spread relative to benchmark)
    maturity_spread = {
        '1M': -0.2,
        '3M': -0.1,
        '6M': 0.0,
        '1Y': 0.1,
        '2Y': 0.3,
        '3Y': 0.5,
        '5Y': 0.8,
        '7Y': 1.0,
        '10Y': 1.2,
        '20Y': 1.5,
        '30Y': 1.6,
        '4W': -0.3,
        '13W': -0.1,
        '26W': 0.0,
        '52W': 0.1
    }
    
    inst_base = base_rates.get(instrument_type, base_rates.get('money_market', {}))
    # Try with uppercase country code
    country_upper = country.upper()
    base = inst_base.get(country_upper, inst_base.get('US', 4.0))
    
    spread = maturity_spread.get(maturity, 0.0)
    rate = base + spread + (random.random() - 0.5) * 0.2
    rate = max(0.1, min(25.0, rate))
    
    return {
        'benchmark_rate': round(rate, 2),
        'series_label': f'{maturity} {country} Synthetic',
        'series_id': f'SYNTH_{country}_{maturity}',
        'country': country_upper,
        'currency': currency,
        'maturity': maturity,
        'note': 'Synthetic fallback generated locally (FRED API unavailable)'
    }


# ===== MAPPINGS FOR SERIES IDS =====

# Mapping from country to series identifiers for different maturities
COUNTRY_SERIES_MAP = {
    'US': {
        '1M': 'DGS1MO',
        '3M': 'DGS3MO',
        '6M': 'DGS6MO',
        '1Y': 'DGS1',
        '2Y': 'DGS2',
        '3Y': 'DGS3',
        '5Y': 'DGS5',
        '7Y': 'DGS7',
        '10Y': 'DGS10',
        '20Y': 'DGS20',
        '30Y': 'DGS30',
        '4W': 'DTB4WK',
        '13W': 'DTB3',
        '26W': 'DTB6',
        '52W': 'DTB1Y',
    },
    'GB': {
        '1M': 'GB1MT',
        '3M': 'GB3MT',
        '6M': 'GB6MT',
        '1Y': 'GB1YT',
        '2Y': 'GB2YT',
        '5Y': 'GB5YT',
        '10Y': 'GB10YT',
        '30Y': 'GB30YT',
    },
    'EUR': {
        '1M': 'EUR1MT',
        '3M': 'EUR3MT',
        '6M': 'EUR6MT',
        '1Y': 'EUR1YT',
        '2Y': 'EUR2YT',
        '5Y': 'EUR5YT',
        '10Y': 'EUR10YT',
        '30Y': 'EUR30YT',
    },
    'JP': {
        '1M': 'JP1MT',
        '3M': 'JP3MT',
        '6M': 'JP6MT',
        '1Y': 'JP1YT',
        '2Y': 'JP2YT',
        '5Y': 'JP5YT',
        '10Y': 'JP10YT',
        '30Y': 'JP30YT',
    },
    'CA': {
        '1M': 'CA1MT',
        '3M': 'CA3MT',
        '6M': 'CA6MT',
        '1Y': 'CA1YT',
        '2Y': 'CA2YT',
        '5Y': 'CA5YT',
        '10Y': 'CA10YT',
        '30Y': 'CA30YT',
    },
    'AU': {
        '1M': 'AU1MT',
        '3M': 'AU3MT',
        '6M': 'AU6MT',
        '1Y': 'AU1YT',
        '2Y': 'AU2YT',
        '5Y': 'AU5YT',
        '10Y': 'AU10YT',
        '30Y': 'AU30YT',
    },
    'ZA': {
        '1M': 'ZA1MT',
        '3M': 'ZA3MT',
        '6M': 'ZA6MT',
        '1Y': 'ZA1YT',
        '2Y': 'ZA2YT',
        '5Y': 'ZA5YT',
        '10Y': 'ZA10YT',
        '30Y': 'ZA30YT',
    }
}


def series_for_country(country, maturity):
    """
    Get the appropriate FRED series ID for a country and maturity.
    Returns (series_id, label, used_maturity, country_code, currency, note)
    """
    country_upper = country.upper()
    maturity_map = COUNTRY_SERIES_MAP.get(country_upper)
    
    # If country not in map, try fallback to US
    if not maturity_map:
        maturity_map = COUNTRY_SERIES_MAP.get('US')
        country_upper = 'US'
        note = f'Country "{country}" not in map, using US fallback'
    else:
        note = ''
    
    # Try exact maturity match
    series_id = maturity_map.get(maturity)
    if series_id:
        label = f'{maturity} {country_upper} Treasury'
        return series_id, label, maturity, country_upper, 'USD', note
    
    # Try to match partial maturity
    for key in maturity_map:
        if maturity in key or key in maturity:
            series_id = maturity_map[key]
            label = f'{key} {country_upper} Treasury'
            return series_id, label, key, country_upper, 'USD', note
    
    # Fallback: 10Y
    if '10Y' in maturity_map:
        return maturity_map['10Y'], '10Y {country_upper} Treasury', '10Y', country_upper, 'USD', 'Fallback to 10Y'
    
    # Ultimate fallback: use first available
    first_key = list(maturity_map.keys())[0] if maturity_map else '10Y'
    series_id = maturity_map.get(first_key, 'DGS10')
    label = f'{first_key} {country_upper} Treasury'
    return series_id, label, first_key, country_upper, 'USD', 'Fallback'


def attach_fred_to_calculation(result, instrument_type, maturity='1Y', country='US', currency='USD'):
    """
    Attach FRED benchmark data to the calculation result.
    If FRED API fails, uses synthetic fallback.
    """
    try:
        # Try to get real benchmark
        benchmark = get_market_benchmark(instrument_type, maturity, country, currency)
        if benchmark and not benchmark.get('error'):
            result['fred'] = benchmark
            return
    except Exception as e:
        print(f"⚠️ Failed to get FRED benchmark: {e}")
    
    # 🔥 Fallback: synthetic benchmark
    synthetic = generate_synthetic_benchmark(instrument_type, maturity, country, currency)
    result['fred'] = synthetic
    print(f"ℹ️ Using synthetic benchmark for {instrument_type} {maturity} {country}")


def get_market_benchmark(instrument_type, maturity='1Y', country='US', currency='USD'):
    """
    Get market benchmark from FRED API.
    Returns dict with benchmark data or dict with error.
    """
    if not FRED_API_KEY:
        # Fallback to synthetic
        return generate_synthetic_benchmark(instrument_type, maturity, country, currency)
    
    series_id, label, used_mat, _, _, note = series_for_country(country, maturity)
    
    if not series_id:
        return {'error': f'No series found for {country} {maturity}'}
    
    # Try to fetch from FRED
    try:
        params = {
            'series_id': series_id,
            'api_key': FRED_API_KEY,
            'file_type': 'json',
            'sort_order': 'desc',
            'limit': 1
        }
        response = requests.get(f'{FRED_BASE_URL}/series/observations', params=params, timeout=10)
        if response.status_code != 200:
            print(f"⚠️ FRED API error: status {response.status_code}")
            # Fallback to synthetic
            return generate_synthetic_benchmark(instrument_type, maturity, country, currency)
        
        data = response.json()
        if 'error_code' in data:
            print(f"⚠️ FRED API error: {data.get('error_message')}")
            # Fallback to synthetic
            return generate_synthetic_benchmark(instrument_type, maturity, country, currency)
        
        observations = data.get('observations', [])
        if not observations or len(observations) == 0:
            # Fallback to synthetic
            return generate_synthetic_benchmark(instrument_type, maturity, country, currency)
        
        # Get the latest valid value
        for obs in observations:
            if obs.get('value') and obs.get('value') != '.':
                rate = float(obs['value'])
                return {
                    'benchmark_rate': round(rate, 2),
                    'series_label': label,
                    'series_id': series_id,
                    'country': country.upper(),
                    'currency': currency,
                    'maturity': used_mat,
                    'date': obs.get('date'),
                    'note': note
                }
        
        # If no valid value found, fallback
        return generate_synthetic_benchmark(instrument_type, maturity, country, currency)
        
    except Exception as e:
        print(f"⚠️ FRED fetch error: {e}")
        # Fallback to synthetic
        return generate_synthetic_benchmark(instrument_type, maturity, country, currency)


def build_filter_options():
    """
    Build filter options for FRED data.
    Returns a dict with countries, currencies, and maturities.
    If unable to load from FRED, returns fallback options.
    """
    # Try to load from FRED API first
    if FRED_API_KEY:
        try:
            # We could fetch from an API endpoint that lists available series
            # For now, build from our local map
            countries = []
            for code in COUNTRY_SERIES_MAP:
                maturities = []
                for mat in COUNTRY_SERIES_MAP[code]:
                    maturities.append({'code': mat, 'name': mat})
                countries.append({
                    'code': code,
                    'name': code,
                    'currency': 'USD',
                    'maturities': maturities
                })
            return {
                'countries': countries,
                'currencies': [{'code': 'USD', 'name': 'USD'}],
                'note': 'Filter options from local configuration'
            }
        except Exception as e:
            print(f"⚠️ Failed to build filter options: {e}")
    
    # Fallback options
    fallback_maturities = [
        {'code': '1M', 'name': '1 Month'},
        {'code': '3M', 'name': '3 Months'},
        {'code': '6M', 'name': '6 Months'},
        {'code': '1Y', 'name': '1 Year'},
        {'code': '2Y', 'name': '2 Years'},
        {'code': '5Y', 'name': '5 Years'},
        {'code': '10Y', 'name': '10 Years'},
        {'code': '30Y', 'name': '30 Years'}
    ]
    return {
        'countries': [
            {
                'code': 'US',
                'name': 'United States',
                'currency': 'USD',
                'maturities': fallback_maturities
            },
            {
                'code': 'GB',
                'name': 'United Kingdom',
                'currency': 'GBP',
                'maturities': fallback_maturities
            },
            {
                'code': 'EUR',
                'name': 'Eurozone',
                'currency': 'EUR',
                'maturities': fallback_maturities
            }
        ],
        'currencies': [
            {'code': 'USD', 'name': 'USD'},
            {'code': 'EUR', 'name': 'EUR'},
            {'code': 'GBP', 'name': 'GBP'},
            {'code': 'JPY', 'name': 'JPY'}
        ],
        'note': 'Fallback filter options (FRED API unavailable)'
    }
import os
import json
import requests
import math
import random
import logging
from flask import jsonify
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

FRED_API_KEY = os.environ.get('FRED_API_KEY', 'b40141a5119f30bc2388d63f59d8847e')
FRED_BASE_URL = 'https://api.stlouisfed.org/fred'

# ===== SYNTHETIC GENERATORS (kept only for benchmark fallback) =====
def generate_synthetic_yield_curve(country='US', maturity='10Y'):
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
    maturity_map = {
        '1M': 0.083, '3M': 0.25, '6M': 0.5, '1Y': 1.0, '2Y': 2.0, '3Y': 3.0,
        '5Y': 5.0, '7Y': 7.0, '10Y': 10.0, '20Y': 20.0, '30Y': 30.0,
        '4W': 0.077, '13W': 0.25, '26W': 0.5, '52W': 1.0
    }
    maturities = list(maturity_map.keys())
    points = []
    for mat_label in maturities:
        years = maturity_map[mat_label]
        rate = params['level'] + params['slope'] * years + params['curvature'] * math.pow(years, 1.2)
        rate += (random.random() - 0.5) * 0.15
        rate = max(0.1, min(25.0, rate))
        points.append({
            'maturity': years,
            'maturityLabel': mat_label,
            'rate': round(rate, 2)
        })
    return points

def generate_synthetic_benchmark(instrument_type='money_market', maturity='1Y', country='US', currency='USD'):
    base_rates = {
        'money_market': {'US': 4.2, 'GB': 4.0, 'EUR': 3.5, 'JP': 2.0, 'CA': 4.0, 'AU': 4.3, 'ZA': 8.0},
        'money-market': {'US': 4.2, 'GB': 4.0, 'EUR': 3.5, 'JP': 2.0, 'CA': 4.0, 'AU': 4.3, 'ZA': 8.0},
        'bonds': {'US': 4.5, 'GB': 4.2, 'EUR': 3.8, 'JP': 2.2, 'CA': 4.3, 'AU': 4.5, 'ZA': 8.5},
        'tbills': {'US': 3.8, 'GB': 3.5, 'EUR': 3.2, 'JP': 1.8, 'CA': 3.7, 'AU': 4.0, 'ZA': 7.5}
    }
    maturity_spread = {
        '1M': -0.2, '3M': -0.1, '6M': 0.0, '1Y': 0.1, '2Y': 0.3,
        '3Y': 0.5, '5Y': 0.8, '7Y': 1.0, '10Y': 1.2, '20Y': 1.5, '30Y': 1.6,
        '4W': -0.3, '13W': -0.1, '26W': 0.0, '52W': 0.1
    }
    inst_base = base_rates.get(instrument_type, base_rates.get('money_market', {}))
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

COUNTRY_SERIES_MAP = {
    'US': {
        '1M': 'DGS1MO', '3M': 'DGS3MO', '6M': 'DGS6MO', '1Y': 'DGS1',
        '2Y': 'DGS2', '3Y': 'DGS3', '5Y': 'DGS5', '7Y': 'DGS7',
        '10Y': 'DGS10', '20Y': 'DGS20', '30Y': 'DGS30',
        '4W': 'DTB4WK', '13W': 'DTB3', '26W': 'DTB6', '52W': 'DTB1Y',
    },
    'GB': {
        '1M': 'GB1MT', '3M': 'GB3MT', '6M': 'GB6MT', '1Y': 'GB1YT',
        '2Y': 'GB2YT', '5Y': 'GB5YT', '10Y': 'GB10YT', '30Y': 'GB30YT',
    },
    'EUR': {
        '1M': 'EUR1MT', '3M': 'EUR3MT', '6M': 'EUR6MT', '1Y': 'EUR1YT',
        '2Y': 'EUR2YT', '5Y': 'EUR5YT', '10Y': 'EUR10YT', '30Y': 'EUR30YT',
    },
    'JP': {
        '1M': 'JP1MT', '3M': 'JP3MT', '6M': 'JP6MT', '1Y': 'JP1YT',
        '2Y': 'JP2YT', '5Y': 'JP5YT', '10Y': 'JP10YT', '30Y': 'JP30YT',
    },
    'CA': {
        '1M': 'CA1MT', '3M': 'CA3MT', '6M': 'CA6MT', '1Y': 'CA1YT',
        '2Y': 'CA2YT', '5Y': 'CA5YT', '10Y': 'CA10YT', '30Y': 'CA30YT',
    },
    'AU': {
        '1M': 'AU1MT', '3M': 'AU3MT', '6M': 'AU6MT', '1Y': 'AU1YT',
        '2Y': 'AU2YT', '5Y': 'AU5YT', '10Y': 'AU10YT', '30Y': 'AU30YT',
    },
    'ZA': {
        '1M': 'ZA1MT', '3M': 'ZA3MT', '6M': 'ZA6MT', '1Y': 'ZA1YT',
        '2Y': 'ZA2YT', '5Y': 'ZA5YT', '10Y': 'ZA10YT', '30Y': 'ZA30YT',
    }
}

def series_for_country(country, maturity):
    country_upper = country.upper()
    maturity_map = COUNTRY_SERIES_MAP.get(country_upper)
    if not maturity_map:
        maturity_map = COUNTRY_SERIES_MAP.get('US')
        country_upper = 'US'
        note = f'Country "{country}" not in map, using US fallback'
    else:
        note = ''
    series_id = maturity_map.get(maturity)
    if series_id:
        label = f'{maturity} {country_upper} Treasury'
        return series_id, label, maturity, country_upper, 'USD', note
    for key in maturity_map:
        if maturity in key or key in maturity:
            series_id = maturity_map[key]
            label = f'{key} {country_upper} Treasury'
            return series_id, label, key, country_upper, 'USD', note
    if '10Y' in maturity_map:
        return maturity_map['10Y'], '10Y {country_upper} Treasury', '10Y', country_upper, 'USD', 'Fallback to 10Y'
    first_key = list(maturity_map.keys())[0] if maturity_map else '10Y'
    series_id = maturity_map.get(first_key, 'DGS10')
    label = f'{first_key} {country_upper} Treasury'
    return series_id, label, first_key, country_upper, 'USD', 'Fallback'

def fetch_fred_observation(series_id):
    if not FRED_API_KEY:
        logger.warning("FRED_API_KEY not set, cannot fetch real data")
        return None, None
    try:
        params = {
            'series_id': series_id,
            'api_key': FRED_API_KEY,
            'file_type': 'json',
            'sort_order': 'desc',
            'limit': 1
        }
        resp = requests.get(f'{FRED_BASE_URL}/series/observations', params=params, timeout=10)
        if resp.status_code != 200:
            logger.error(f"FRED API status {resp.status_code} for series {series_id}")
            return None, None
        data = resp.json()
        if 'error_code' in data:
            logger.error(f"FRED error: {data.get('error_message')} for series {series_id}")
            return None, None
        observations = data.get('observations', [])
        for obs in observations:
            if obs.get('value') and obs.get('value') != '.':
                try:
                    val = float(obs['value'])
                    return val, obs.get('date')
                except (ValueError, TypeError):
                    continue
        logger.warning(f"No valid observation for series {series_id}")
        return None, None
    except Exception as e:
        logger.error(f"Exception fetching FRED series {series_id}: {e}")
        return None, None

def get_yield_curve(country='US', maturities=None):
    if maturities is None:
        maturities = ['1M', '3M', '6M', '1Y', '2Y', '5Y', '10Y', '30Y']
    points = []
    maturity_map = {
        '1M': 0.083, '3M': 0.25, '6M': 0.5, '1Y': 1.0, '2Y': 2.0, '3Y': 3.0,
        '5Y': 5.0, '7Y': 7.0, '10Y': 10.0, '20Y': 20.0, '30Y': 30.0,
        '4W': 0.077, '13W': 0.25, '26W': 0.5, '52W': 1.0
    }
    for mat_label in maturities:
        series_id, label, used_mat, _, _, note = series_for_country(country, mat_label)
        if not series_id:
            logger.warning(f"No series found for {country} {mat_label} – skipping")
            continue
        val, date = fetch_fred_observation(series_id)
        if val is not None:
            points.append({
                'maturity': maturity_map.get(used_mat, 1.0),
                'maturityLabel': used_mat,
                'rate': round(val, 4),
                'date': date,
                'source': 'fred'
            })
            logger.info(f"FRED: {series_id} = {val}%")
        else:
            logger.warning(f"FRED failed for {series_id} – skipping this maturity")
    points.sort(key=lambda x: x['maturity'])
    return points

def get_market_benchmark(instrument_type, maturity='1Y', country='US', currency='USD'):
    series_id, label, used_mat, _, _, note = series_for_country(country, maturity)
    if series_id:
        val, date = fetch_fred_observation(series_id)
        if val is not None:
            return {
                'benchmark_rate': round(val, 4),
                'series_label': label,
                'series_id': series_id,
                'country': country.upper(),
                'currency': currency,
                'maturity': used_mat,
                'date': date,
                'note': note
            }
    return generate_synthetic_benchmark(instrument_type, maturity, country, currency)

def attach_fred_to_calculation(result, instrument_type, maturity='1Y', country='US', currency='USD'):
    try:
        benchmark = get_market_benchmark(instrument_type, maturity, country, currency)
        result['fred'] = benchmark
    except Exception as e:
        logger.error(f"Error attaching FRED benchmark: {e}")
        result['fred'] = generate_synthetic_benchmark(instrument_type, maturity, country, currency)

def build_filter_options():
    countries = []
    for code in COUNTRY_SERIES_MAP:
        maturities = [{'code': mat, 'name': mat} for mat in COUNTRY_SERIES_MAP[code]]
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
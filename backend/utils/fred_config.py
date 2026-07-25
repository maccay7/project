import os
import json
import requests
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

FRED_API_KEY = os.environ.get('FRED_API_KEY')
FRED_BASE_URL = 'https://api.stlouisfed.org/fred'

# Alias used by some modules
FRED_KEY = FRED_API_KEY

# Map frontend country codes to FRED country codes
COUNTRY_ALIASES = {
    'USA': 'US', 'US': 'US',
    'GBR': 'GB', 'GB': 'GB', 'UK': 'GB',
    'EUR': 'EUR', 'EU': 'EUR', 'DE': 'EUR', 'DEU': 'EUR',
    'JPN': 'JP', 'JP': 'JP',
    'CAN': 'CA', 'CA': 'CA',
    'AUS': 'AU', 'AU': 'AU',
    'ZAF': 'ZA', 'ZA': 'ZA',
    'CHE': 'CH', 'CH': 'CH',
    'NZL': 'NZ', 'NZ': 'NZ',
    'NOR': 'NO', 'NO': 'NO',
    'SWE': 'SE', 'SE': 'SE',
    'DNK': 'DK', 'DK': 'DK',
    'BRA': 'BR', 'BR': 'BR',
    'MEX': 'MX', 'MX': 'MX',
    'IND': 'IN', 'IN': 'IN',
    'CHN': 'CN', 'CN': 'CN',
    'KOR': 'KR', 'KR': 'KR',
    'SGP': 'SG', 'SG': 'SG',
    'HKG': 'HK', 'HK': 'HK',
    'RUS': 'RU', 'RU': 'RU',
    'TUR': 'TR', 'TR': 'TR',
    'SAU': 'SA', 'SA': 'SA',
    'ARE': 'AE', 'AE': 'AE',
    'ISR': 'IL', 'IL': 'IL',
}

# Valid FRED series IDs only – no fake/mock series
COUNTRY_SERIES_MAP = {
    'US': {
        '1M': 'DGS1MO', '3M': 'DGS3MO', '6M': 'DGS6MO', '1Y': 'DGS1',
        '2Y': 'DGS2', '3Y': 'DGS3', '5Y': 'DGS5', '7Y': 'DGS7',
        '10Y': 'DGS10', '20Y': 'DGS20', '30Y': 'DGS30',
        '4W': 'DTB4WK', '13W': 'DTB3', '26W': 'DTB6', '52W': 'DTB1Y',
    },
    'GB': {
        '3M': 'IR3TTS01GBM156N', '1Y': 'IR3TTS01GBM156N',
        '5Y': 'IR5TTS01GBM156N', '10Y': 'IRLTLT01GBM156N',
    },
    'JP': {
        '3M': 'IR3TTS01JPM156N', '1Y': 'IR3TTS01JPM156N',
        '5Y': 'IR5TTS01JPM156N', '10Y': 'IRLTLT01JPM156N',
    },
    'EUR': {
        '3M': 'IR3TTS01EZM156N', '1Y': 'IR3TTS01EZM156N',
        '5Y': 'IR5TTS01EZM156N', '10Y': 'IRLTLT01EZM156N',
    },
    'CA': {
        '3M': 'IR3TTS01CAM156N', '1Y': 'IR3TTS01CAM156N',
        '5Y': 'IR5TTS01CAM156N', '10Y': 'IRLTLT01CAM156N',
    },
    'AU': {
        '3M': 'IR3TTS01AUM156N', '1Y': 'IR3TTS01AUM156N',
        '5Y': 'IR5TTS01AUM156N', '10Y': 'IRLTLT01AUM156N',
    },
    'ZA': {
        '3M': 'IR3TTS01ZAM156N', '1Y': 'IR3TTS01ZAM156N',
        '5Y': 'IR5TTS01ZAM156N', '10Y': 'IRLTLT01ZAM156N',
    },
}


def normalize_country(country):
    """Convert any country code (USA, GBR, etc.) to our FRED map key."""
    if not country:
        return 'US'
    code = str(country).upper().strip()
    return COUNTRY_ALIASES.get(code, code)

def series_for_country(country, maturity):
    country_upper = country.upper()
    maturity_map = COUNTRY_SERIES_MAP.get(country_upper)
    if not maturity_map:
        # Fallback to US if country not found
        maturity_map = COUNTRY_SERIES_MAP.get('US')
        country_upper = 'US'
        note = f'Country "{country}" not in map, using US fallback'
    else:
        note = ''
    series_id = maturity_map.get(maturity)
    if series_id:
        label = f'{maturity} {country_upper} Treasury'
        return series_id, label, maturity, country_upper, 'USD', note
    # Try to find a close match
    for key in maturity_map:
        if maturity in key or key in maturity:
            series_id = maturity_map[key]
            label = f'{key} {country_upper} Treasury'
            return series_id, label, key, country_upper, 'USD', note
    return None, None, maturity, country_upper, 'USD', 'No series found'

def fetch_fred_observation(series_id):
    if not FRED_API_KEY:
        logger.error("FRED_API_KEY not set – cannot fetch real data")
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
    return points  # Will be empty if no data fetched

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
    # No synthetic fallback – return error
    return {
        'error': f'No benchmark data available for {instrument_type} {maturity} {country}',
        'benchmark_rate': None,
        'note': 'FRED API returned no data'
    }

def attach_fred_to_calculation(result, instrument_type, maturity='1Y', country='US', currency='USD'):
    try:
        benchmark = get_market_benchmark(instrument_type, maturity, country, currency)
        if benchmark.get('benchmark_rate') is not None:
            result['fred'] = benchmark
        else:
            result['fred'] = {'error': benchmark.get('error'), 'note': benchmark.get('note')}
    except Exception as e:
        logger.error(f"Error attaching FRED benchmark: {e}")
        result['fred'] = {'error': str(e), 'note': 'Failed to fetch benchmark'}

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
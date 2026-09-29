# backend/.../fred_config.py
"""
FRED API integration.

Rules:
|- Never fabricate benchmark data. If FRED returns nothing, benchmark_rate is None.
|- Country and maturity default to US / 1Y when not supplied.
|- Date range queries are supported via from_date / to_date.
"""

import os
import requests
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

FRED_API_KEY = os.environ.get('FRED_API_KEY')
FRED_BASE_URL = 'https://api.stlouisfed.org/fred'

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

# Currency per country — used to echo the right currency back to the client
COUNTRY_CURRENCY = {
    'US': 'USD', 'GB': 'GBP', 'EUR': 'EUR', 'JP': 'JPY', 'CA': 'CAD',
    'AU': 'AUD', 'ZA': 'ZAR', 'CH': 'CHF', 'NZ': 'NZD', 'NO': 'NOK',
    'SE': 'SEK', 'DK': 'DKK', 'BR': 'BRL', 'MX': 'MXN', 'IN': 'INR',
    'CN': 'CNY', 'KR': 'KRW', 'SG': 'SGD', 'HK': 'HKD', 'RU': 'RUB',
    'TR': 'TRY', 'SA': 'SAR', 'AE': 'AED', 'IL': 'ILS',
}

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
    if not country:
        return 'US'
    code = str(country).upper().strip()
    return COUNTRY_ALIASES.get(code, code)


def currency_for_country(country):
    code = normalize_country(country)
    return COUNTRY_CURRENCY.get(code, 'USD')


def series_for_country(country, maturity):
    """Return (series_id, label, used_maturity, country_upper, currency, note)."""
    if not country or not str(country).strip():
        country = 'US'
    country_upper = normalize_country(country)
    maturity_map = COUNTRY_SERIES_MAP.get(country_upper)
    if not maturity_map:
        maturity_map = COUNTRY_SERIES_MAP.get('US')
        note = f'Country "{country}" not in map, using US fallback'
        country_upper = 'US'
    else:
        note = ''

    if not maturity:
        maturity = '1Y'
    maturity = str(maturity).upper().strip()

    series_id = maturity_map.get(maturity)
    if series_id:
        label = f'{maturity} {country_upper} Treasury'
        return series_id, label, maturity, country_upper, currency_for_country(country_upper), note

    for key in maturity_map:
        if maturity in key or key in maturity:
            series_id = maturity_map[key]
            label = f'{key} {country_upper} Treasury'
            return series_id, label, key, country_upper, currency_for_country(country_upper), note

    return None, None, maturity, country_upper, currency_for_country(country_upper), 'No series found'


def fetch_fred_observation(series_id, from_date=None, to_date=None):
    """
    Fetch the latest observation for a FRED series.
    If from_date/to_date are given, uses them to filter; else returns the most recent value.
    Returns (value, date) or (None, None).
    """
    if not FRED_API_KEY:
        logger.error("FRED_API_KEY not set — cannot fetch real data")
        return None, None
    try:
        params = {
            'series_id': series_id,
            'api_key': FRED_API_KEY,
            'file_type': 'json',
        }
        if from_date and to_date:
            params['observation_start'] = from_date
            params['observation_end'] = to_date
            params['sort_order'] = 'desc'
            params['limit'] = 1
        else:
            params['sort_order'] = 'desc'
            params['limit'] = 1

        resp = requests.get(f'{FRED_BASE_URL}/series/observations',
                            params=params, timeout=10)
        if resp.status_code != 200:
            logger.error(f"FRED API status {resp.status_code} for series {series_id}")
            return None, None
        data = resp.json()
        if 'error_code' in data:
            logger.error(f"FRED error: {data.get('error_message')} for series {series_id}")
            return None, None
        for obs in data.get('observations', []):
            if obs.get('value') and obs.get('value') != '.':
                try:
                    return float(obs['value']), obs.get('date')
                except (ValueError, TypeError):
                    continue
        logger.warning(f"No valid observation for series {series_id}")
        return None, None
    except Exception as e:
        logger.error(f"Exception fetching FRED series {series_id}: {e}")
        return None, None


def get_yield_curve(country='US', maturities=None, from_date=None, to_date=None):
    """
    Return a sorted list of {maturity, maturityLabel, rate, date, source}.
    Optional `from_date`/`to_date` filter observations by date.

    NO FALLBACKS - only returns real FRED API data.
    When date range is provided, returns time series data across the date range.
    When no date range, returns current yield curve across maturities.
    """
    if not country:
        country = 'US'
    if maturities is None:
        maturities = ['1M', '3M', '6M', '1Y', '2Y', '5Y', '10Y', '30Y']

    maturity_map = {
        '1M': 0.083, '3M': 0.25, '6M': 0.5, '1Y': 1.0, '2Y': 2.0, '3Y': 3.0,
        '5Y': 5.0, '7Y': 7.0, '10Y': 10.0, '20Y': 20.0, '30Y': 30.0,
        '4W': 0.077, '13W': 0.25, '26W': 0.5, '52W': 1.0,
    }

    points = []

    # If date range is provided, fetch time series data for a key maturity
    if from_date and to_date:
        logger.info(f"Date range mode: Fetching time series from {from_date} to {to_date}")
        # For date range mode, fetch time series for a key maturity (10Y Treasury)
        key_maturity = '10Y'
        series_id, label, used_mat, _, _, note = series_for_country(country, key_maturity)
        if series_id:
            try:
                params = {
                    'series_id': series_id,
                    'api_key': FRED_API_KEY,
                    'file_type': 'json',
                    'observation_start': from_date,
                    'observation_end': to_date,
                    'sort_order': 'asc',
                    'limit': 1000
                }
                logger.info(f"Fetching FRED time series for {series_id} from {from_date} to {to_date}")
                resp = requests.get(f'{FRED_BASE_URL}/series/observations',
                                    params=params, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    if 'observations' in data:
                        for obs in data['observations']:
                            if obs.get('value') and obs.get('value') != '.':
                                try:
                                    val = float(obs['value'])
                                    points.append({
                                        'maturity': maturity_map.get(used_mat, 10.0),
                                        'maturityLabel': used_mat,
                                        'rate': round(val, 4),
                                        'date': obs.get('date'),
                                        'source': 'fred',
                                        'x': obs.get('date'),
                                        'y': round(val, 4)
                                    })
                                except (ValueError, TypeError):
                                    continue
                        logger.info(f"Fetched {len(points)} time series points for {key_maturity} from {from_date} to {to_date}")
                else:
                    logger.error(f"FRED API status {resp.status_code} for time series {series_id}")
            except Exception as e:
                logger.error(f"Error fetching time series for {series_id}: {e}")
    else:
        logger.info("Standard yield curve mode: Fetching current rates across maturities")
        # Standard yield curve mode: get current rates across maturities
        for mat_label in maturities:
            series_id, label, used_mat, _, _, note = series_for_country(country, mat_label)
            if not series_id:
                logger.warning(f"No series found for {country} {mat_label} — skipping")
                continue
            val, date = fetch_fred_observation(series_id, from_date=from_date, to_date=to_date)
            if val is not None:
                points.append({
                    'maturity': maturity_map.get(used_mat, 1.0),
                    'maturityLabel': used_mat,
                    'rate': round(val, 4),
                    'date': date,
                    'source': 'fred',
                })

    # Sort by date for time series, by maturity for yield curve
    if from_date and to_date:
        points.sort(key=lambda x: x['date'] or '')
    else:
        points.sort(key=lambda x: x['maturity'])

    logger.info(f"Returning {len(points)} FRED data points - NO FALLBACKS")
    return points


def get_market_benchmark(instrument_type, maturity='1Y', country='US', currency='USD'):
    """Return a benchmark record. benchmark_rate is None when FRED has no data."""
    if not country:
        country = 'US'
    if not maturity:
        maturity = '1Y'
    if not currency:
        currency = currency_for_country(country)

    series_id, label, used_mat, country_upper, inferred_ccy, note = series_for_country(country, maturity)
    if series_id:
        val, date = fetch_fred_observation(series_id)
        if val is not None:
            return {
                'benchmark_rate': round(val, 4),
                'series_label': label,
                'series_id': series_id,
                'country': country_upper,
                'currency': currency or inferred_ccy,
                'maturity': used_mat,
                'date': date,
                'note': note,
            }
    return {
        'error': f'No benchmark data available for {instrument_type} {maturity} {country}',
        'benchmark_rate': None,
        'note': 'FRED API returned no data',
    }


def attach_fred_to_calculation(result, instrument_type, maturity='1Y',
                               country='US', currency='USD'):
    """Attach FRED benchmark data to a calculation result. Never fabricates values."""
    if not country:
        country = 'US'
    if not maturity:
        maturity = '1Y'
    if not currency:
        currency = currency_for_country(country)
    try:
        benchmark = get_market_benchmark(instrument_type, maturity, country, currency)
        if benchmark.get('benchmark_rate') is not None:
            result['fred'] = benchmark
        else:
            result['fred'] = {
                'benchmark_rate': None,
                'error': benchmark.get('error'),
                'note': benchmark.get('note'),
            }
    except Exception as e:
        logger.error(f"Error attaching FRED benchmark: {e}")
        result['fred'] = {
            'benchmark_rate': None,
            'error': str(e),
            'note': 'FRED benchmark fetch failed',
        }


def build_filter_options():
    countries = []
    for code in COUNTRY_SERIES_MAP:
        maturities = [{'code': mat, 'name': mat} for mat in COUNTRY_SERIES_MAP[code]]
        countries.append({
            'code': code,
            'name': code,
            'currency': currency_for_country(code),
            'maturities': maturities,
        })
    return {
        'countries': countries,
        'currencies': [
            {'code': 'USD', 'name': 'USD'},
            {'code': 'GBP', 'name': 'GBP'},
            {'code': 'EUR', 'name': 'EUR'},
            {'code': 'JPY', 'name': 'JPY'},
            {'code': 'CAD', 'name': 'CAD'},
            {'code': 'AUD', 'name': 'AUD'},
            {'code': 'ZAR', 'name': 'ZAR'},
        ],
        'note': 'Filter options from local configuration',
    }

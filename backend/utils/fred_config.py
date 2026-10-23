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
    'GB': {'3M': 'IR3TTS01GBM156N', '1Y': 'IR3TTS01GBM156N',
           '5Y': 'IR5TTS01GBM156N', '10Y': 'IRLTLT01GBM156N'},
    'JP': {'3M': 'IR3TTS01JPM156N', '1Y': 'IR3TTS01JPM156N',
           '5Y': 'IR5TTS01JPM156N', '10Y': 'IRLTLT01JPM156N'},
    'EUR': {'3M': 'IR3TTS01EZM156N', '1Y': 'IR3TTS01EZM156N',
            '5Y': 'IR5TTS01EZM156N', '10Y': 'IRLTLT01EZM156N'},
    'CA': {'3M': 'IR3TTS01CAM156N', '1Y': 'IR3TTS01CAM156N',
           '5Y': 'IR5TTS01CAM156N', '10Y': 'IRLTLT01CAM156N'},
    'AU': {'3M': 'IR3TTS01AUM156N', '1Y': 'IR3TTS01AUM156N',
           '5Y': 'IR5TTS01AUM156N', '10Y': 'IRLTLT01AUM156N'},
    'ZA': {'3M': 'IR3TTS01ZAM156N', '1Y': 'IR3TTS01ZAM156N',
           '5Y': 'IR5TTS01ZAM156N', '10Y': 'IRLTLT01ZAM156N'},
}


def normalize_country(country):
    if not country:
        return 'US'
    code = str(country).upper().strip()
    return COUNTRY_ALIASES.get(code, code)


def currency_for_country(country):
    return COUNTRY_CURRENCY.get(normalize_country(country), 'USD')


def series_for_country(country, maturity):
    """Return (series_id, label, used_maturity, country, currency, note).

    Returns series_id=None when the country is not supported or no
    maturity matches. NEVER substitutes US data.
    """
    country_upper = normalize_country(country)
    maturity = (maturity or '1Y').strip().upper()
    currency = currency_for_country(country_upper)

    maturity_map = COUNTRY_SERIES_MAP.get(country_upper)
    if not maturity_map:
        return (None, None, maturity, country_upper, currency,
                f'No FRED series configured for country {country_upper}')

    series_id = maturity_map.get(maturity)
    if series_id:
        return (series_id, f'{maturity} {country_upper} Treasury',
                maturity, country_upper, currency, '')

    for key in maturity_map:
        if maturity in key or key in maturity:
            return (maturity_map[key], f'{key} {country_upper} Treasury',
                    key, country_upper, currency, '')

    return (None, None, maturity, country_upper, currency,
            f'No {maturity} series for {country_upper}')


def fetch_fred_observation(series_id, from_date=None, to_date=None, max_retries=3):
    if not FRED_API_KEY:
        logger.error("FRED_API_KEY not set — cannot fetch real data")
        return None, None

    params = {
        'series_id': series_id,
        'api_key': FRED_API_KEY,
        'file_type': 'json',
        'sort_order': 'desc',
        'limit': 1,
    }
    if from_date and to_date:
        params['observation_start'] = from_date
        params['observation_end'] = to_date

    for attempt in range(max_retries):
        try:
            resp = requests.get(f'{FRED_BASE_URL}/series/observations',
                                params=params, timeout=30)
            if resp.status_code != 200:
                logger.error(f"FRED status {resp.status_code} for {series_id} "
                             f"(attempt {attempt + 1}/{max_retries})")
                continue
            data = resp.json()
            if 'error_code' in data:
                logger.error(f"FRED error: {data.get('error_message')} for {series_id}")
                continue
            for obs in data.get('observations', []):
                if obs.get('value') and obs.get('value') != '.':
                    try:
                        return float(obs['value']), obs.get('date')
                    except (ValueError, TypeError):
                        continue
            logger.warning(f"No valid observation for {series_id}")
            return None, None
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout for {series_id} (attempt {attempt + 1}/{max_retries})")
        except Exception as e:
            logger.error(f"Exception for {series_id}: {e}")

    return None, None


def get_yield_curve(country='US', maturities=None, from_date=None, to_date=None):
    if maturities is None:
        maturities = ['1M', '3M', '6M', '1Y', '2Y', '5Y', '10Y', '30Y']

    maturity_map = {
        '1M': 0.083, '3M': 0.25, '6M': 0.5, '1Y': 1.0, '2Y': 2.0, '3Y': 3.0,
        '5Y': 5.0, '7Y': 7.0, '10Y': 10.0, '20Y': 20.0, '30Y': 30.0,
        '4W': 0.077, '13W': 0.25, '26W': 0.5, '52W': 1.0,
    }

    points = []

    if from_date and to_date:
        key_maturity = '10Y'
        series_id, label, used_mat, _, _, note = series_for_country(country, key_maturity)
        if series_id:
            try:
                resp = requests.get(
                    f'{FRED_BASE_URL}/series/observations',
                    params={
                        'series_id': series_id,
                        'api_key': FRED_API_KEY,
                        'file_type': 'json',
                        'observation_start': from_date,
                        'observation_end': to_date,
                        'sort_order': 'asc',
                        'limit': 1000,
                    },
                    timeout=30,
                )
                if resp.status_code == 200:
                    for obs in resp.json().get('observations', []):
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
                                    'y': round(val, 4),
                                })
                            except (ValueError, TypeError):
                                continue
            except Exception as e:
                logger.error(f"Error fetching time series for {series_id}: {e}")
    else:
        for mat_label in maturities:
            series_id, label, used_mat, _, _, note = series_for_country(country, mat_label)
            if not series_id:
                logger.warning(f"No series for {country} {mat_label} — skipping")
                continue
            val, date = fetch_fred_observation(series_id)
            if val is not None:
                points.append({
                    'maturity': maturity_map.get(used_mat, 1.0),
                    'maturityLabel': used_mat,
                    'rate': round(val, 4),
                    'date': date,
                    'source': 'fred',
                })

    if from_date and to_date:
        points.sort(key=lambda x: x['date'] or '')
    else:
        points.sort(key=lambda x: x['maturity'])
    return points


def get_market_benchmark(instrument_type, maturity='1Y', country='US', currency='USD'):
    series_id, label, used_mat, country_upper, inferred_ccy, note = \
        series_for_country(country, maturity)

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
        'error': f'No benchmark data for {instrument_type} {maturity} {country_upper}',
        'benchmark_rate': None,
        'note': note or 'FRED API returned no data',
    }


def attach_fred_to_calculation(result, instrument_type, maturity='1Y',
                               country='US', currency='USD'):
    try:
        benchmark = get_market_benchmark(instrument_type, maturity, country, currency)
        result['fred'] = benchmark
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
        countries.append({
            'code': code,
            'name': code,
            'currency': currency_for_country(code),
            'maturities': [{'code': m, 'name': m} for m in COUNTRY_SERIES_MAP[code]],
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
import os
import json
import hashlib
import requests
import logging
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

FRED_API_KEY = os.environ.get('FRED_API_KEY')
FRED_BASE_URL = 'https://api.stlouisfed.org/fred'
FRED_CACHE_TTL_HOURS = 6


def _fred_cache_key(*parts):
    raw = '|'.join(str(p) for p in parts)
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def _fred_cache_ensure():
    try:
        from utils.db import get_db_connection
        conn = get_db_connection()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS fred_cache (
                    cache_key CHAR(64) PRIMARY KEY,
                    payload LONGTEXT NOT NULL,
                    fetched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_fetched_at (fetched_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            conn.commit()
            cur.close()
        finally:
            conn.close()
        return True
    except Exception as e:
        logger.warning(f"fred_cache ensure failed: {e}")
        return False


def _fred_cache_get(key):
    try:
        from utils.db import execute_query
        row = execute_query(
            """SELECT payload FROM fred_cache
               WHERE cache_key = %s
                 AND fetched_at > DATE_SUB(NOW(), INTERVAL %s HOUR)
               LIMIT 1""",
            (key, FRED_CACHE_TTL_HOURS),
            fetch_one=True,
        )
        if row and row.get('payload'):
            return json.loads(row['payload'])
    except Exception as e:
        logger.warning(f"fred_cache read failed: {e}")
    return None


def _fred_cache_set(key, payload):
    try:
        from utils.db import execute_query
        execute_query(
            """INSERT INTO fred_cache (cache_key, payload, fetched_at)
               VALUES (%s, %s, NOW())
               ON DUPLICATE KEY UPDATE payload = VALUES(payload),
                   fetched_at = NOW()""",
            (key, json.dumps(payload)),
        )
    except Exception as e:
        logger.warning(f"fred_cache write failed: {e}")

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
    'CH': {'3M': 'IR3TTS01CHM156N', '1Y': 'IR3TTS01CHM156N',
           '5Y': 'IR5TTS01CHM156N', '10Y': 'IRLTLT01CHM156N'},
    'NZ': {'3M': 'IR3TTS01NZM156N', '1Y': 'IR3TTS01NZM156N',
           '5Y': 'IR5TTS01NZM156N', '10Y': 'IRLTLT01NZM156N'},
    'NO': {'3M': 'IR3TTS01NOM156N', '1Y': 'IR3TTS01NOM156N',
           '5Y': 'IR5TTS01NOM156N', '10Y': 'IRLTLT01NOM156N'},
    'SE': {'3M': 'IR3TTS01SEM156N', '1Y': 'IR3TTS01SEM156N',
           '5Y': 'IR5TTS01SEM156N', '10Y': 'IRLTLT01SEM156N'},
    'DK': {'3M': 'IR3TTS01DKM156N', '1Y': 'IR3TTS01DKM156N',
           '5Y': 'IR5TTS01DKM156N', '10Y': 'IRLTLT01DKM156N'},
    'BR': {'3M': 'IR3TTS01BRM156N', '1Y': 'IR3TTS01BRM156N',
           '5Y': 'IR5TTS01BRM156N', '10Y': 'IRLTLT01BRM156N'},
    'MX': {'3M': 'IR3TTS01MXM156N', '1Y': 'IR3TTS01MXM156N',
           '5Y': 'IR5TTS01MXM156N', '10Y': 'IRLTLT01MXM156N'},
    'IN': {'3M': 'IR3TTS01INM156N', '1Y': 'IR3TTS01INM156N',
           '5Y': 'IR5TTS01INM156N', '10Y': 'IRLTLT01INM156N'},
    'CN': {'3M': 'IR3TTS01CNM156N', '1Y': 'IR3TTS01CNM156N',
           '5Y': 'IR5TTS01CNM156N', '10Y': 'IRLTLT01CNM156N'},
    'KR': {'3M': 'IR3TTS01KRM156N', '1Y': 'IR3TTS01KRM156N',
           '5Y': 'IR5TTS01KRM156N', '10Y': 'IRLTLT01KRM156N'},
    'SG': {'3M': 'IR3TTS01SGM156N', '1Y': 'IR3TTS01SGM156N',
           '5Y': 'IR5TTS01SGM156N', '10Y': 'IRLTLT01SGM156N'},
    'HK': {'3M': 'IR3TTS01HKM156N', '1Y': 'IR3TTS01HKM156N',
           '5Y': 'IR5TTS01HKM156N', '10Y': 'IRLTLT01HKM156N'},
    'RU': {'3M': 'IR3TTS01RUM156N', '1Y': 'IR3TTS01RUM156N',
           '5Y': 'IR5TTS01RUM156N', '10Y': 'IRLTLT01RUM156N'},
    'TR': {'3M': 'IR3TTS01TRM156N', '1Y': 'IR3TTS01TRM156N',
           '5Y': 'IR5TTS01TRM156N', '10Y': 'IRLTLT01TRM156N'},
    'SA': {'3M': 'IR3TTS01SAM156N', '1Y': 'IR3TTS01SAM156N',
           '5Y': 'IR5TTS01SAM156N', '10Y': 'IRLTLT01SAM156N'},
    'AE': {'3M': 'IR3TTS01AEM156N', '1Y': 'IR3TTS01AEM156N',
           '5Y': 'IR5TTS01AEM156N', '10Y': 'IRLTLT01AEM156N'},
    'IL': {'3M': 'IR3TTS01ILM156N', '1Y': 'IR3TTS01ILM156N',
           '5Y': 'IR5TTS01ILM156N', '10Y': 'IRLTLT01ILM156N'},
}

# Per-instrument series overrides. Empty by default — all instruments
# share the country-wide series. Populate to make T-Bills / Bonds /
# Money Market use distinct FRED series.
INSTRUMENT_SERIES_OVERRIDES = {}


def normalize_country(country):
    if not country:
        return 'US'
    code = str(country).upper().strip()
    return COUNTRY_ALIASES.get(code, code)


def currency_for_country(country):
    return COUNTRY_CURRENCY.get(normalize_country(country), 'USD')


def series_for_country(country, maturity):
    """Return 6-tuple:
       (series_id, label, used_maturity, country, currency, note).
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


def _series_for_instrument(instrument_type, country_upper, maturity):
    """Resolve a series honoring the per-instrument override if present.

    ALWAYS returns a 4-tuple: (series_id, label, used_maturity, note).

    This is the ONLY place where the 6-tuple from series_for_country()
    is unpacked. Every caller unpacks 4 values.
    """
    inst = (instrument_type or '').strip().lower().replace('_', '-')
    override = INSTRUMENT_SERIES_OVERRIDES.get(inst)
    if override:
        direct = override.get(maturity)
        if direct:
            return (direct, f'{maturity} {inst} benchmark', maturity, '')
        for key in override:
            if maturity in key or key in maturity:
                return (override[key], f'{key} {inst} benchmark', key, '')

    result = series_for_country(country_upper, maturity)
    try:
        n = len(result)
    except TypeError:
        raise ValueError(
            f"series_for_country returned non-tuple {result!r} "
            f"(type={type(result).__name__})"
        )
    if n >= 6:
        sid, label, used_mat, _country, _currency, note = result[:6]
    elif n == 4:
        sid, label, used_mat, note = result
    else:
        raise ValueError(
            f"series_for_country returned {n}-tuple; expected 4 or 6. "
            f"Got: {result!r}"
        )
    return (sid, label, used_mat, note)


def fetch_fred_observation(series_id, from_date=None, to_date=None, max_retries=3):
    if not FRED_API_KEY:
        logger.error("FRED_API_KEY not set — cannot fetch real data")
        return None, None

    cache_key = _fred_cache_key('obs', series_id, from_date, to_date)
    _fred_cache_ensure()
    cached = _fred_cache_get(cache_key)
    if cached is not None:
        return cached.get('value'), cached.get('date')

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
                        value = float(obs['value'])
                        obs_date = obs.get('date')
                        _fred_cache_set(cache_key,
                                        {'value': value, 'date': obs_date})
                        return value, obs_date
                    except (ValueError, TypeError):
                        continue
            logger.warning(f"No valid observation for {series_id}")
            return None, None
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout for {series_id} (attempt {attempt + 1}/{max_retries})")
        except Exception as e:
            logger.error(f"Exception for {series_id}: {e}")

    return None, None


def get_yield_curve(country='US', maturities=None, from_date=None, to_date=None,
                    instrument_type=None, maturity=None):
    """Fetch a FRED yield curve or time series.

    When ``from_date`` and ``to_date`` are given, this returns a time
    series for one maturity (``maturity``, default ``10Y``).

    When ``from_date`` / ``to_date`` are omitted, this returns a single
    cross-sectional curve across ``maturities``.
    """
    yc_key = _fred_cache_key(
        'yc', country, instrument_type, maturity,
        tuple(sorted(maturities)) if maturities else None,
        from_date, to_date,
    )
    _fred_cache_ensure()
    yc_cached = _fred_cache_get(yc_key)
    if yc_cached is not None:
        return yc_cached.get('points', [])

    if maturities is None:
        maturities = ['1M', '3M', '6M', '1Y', '2Y', '5Y', '10Y', '30Y']

    maturity_map = {
        '1M': 0.083, '3M': 0.25, '6M': 0.5, '1Y': 1.0, '2Y': 2.0, '3Y': 3.0,
        '5Y': 5.0, '7Y': 7.0, '10Y': 10.0, '20Y': 20.0, '30Y': 30.0,
        '4W': 0.077, '13W': 0.25, '26W': 0.5, '52W': 1.0,
    }

    country_upper = normalize_country(country)
    points = []
    fallback_country = None
    use_fallback = False

    if from_date and to_date:
        key_maturity = (maturity or '10Y').strip().upper()
        series_id, label, used_mat, note = _series_for_instrument(
            instrument_type, country_upper, key_maturity
        )
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
        if maturity:
            maturity_text = str(maturity).strip().upper()
            suffix = maturity_text[-1:] if maturity_text[-1:] in {'M', 'W', 'Y'} else 'Y'
            try:
                value_text = maturity_text[:-1] if maturity_text.endswith(suffix) else maturity_text
                maturity_value = float(value_text)
                divisor = {'M': 12, 'W': 52, 'Y': 1}[suffix]
                max_years = maturity_value / divisor
                if max_years > 0:
                    selected_maturity = (
                        maturity_text
                        if maturity_text in COUNTRY_SERIES_MAP.get(country_upper, {})
                        else None
                    )
                    selected_years = maturity_map.get(selected_maturity)
                    maturities = [
                        label for label in maturities
                        if maturity_map.get(str(label).strip().upper()) is not None
                        and maturity_map[str(label).strip().upper()] <= max_years
                        and (
                            selected_years is None
                            or abs(maturity_map[str(label).strip().upper()] - selected_years) > 1e-8
                        )
                    ]
                    if selected_maturity:
                        maturities.append(selected_maturity)
            except (TypeError, ValueError):
                logger.warning("Ignoring invalid yield-curve maturity: %s", maturity)

        def fetch_maturity(mat_label):
            series_id, _label, used_mat, _note = _series_for_instrument(
                instrument_type, country_upper, mat_label
            )
            if not series_id:
                logger.warning(f"No series for {country_upper} {mat_label} — skipping")
                return None
            val, date = fetch_fred_observation(series_id)
            if val is None:
                logger.warning(f"No data for {country_upper} {mat_label} (series: {series_id}) — skipping")
                return None
            return {
                'maturity': maturity_map.get(used_mat, 1.0),
                'maturityLabel': used_mat,
                'rate': round(val, 4),
                'date': date,
                'source': 'fred',
            }

        worker_count = min(8, max(1, len(maturities)))
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            points.extend(
                point for point in executor.map(fetch_maturity, maturities)
                if point is not None
            )

    # If no points were fetched and country is not US, try US as fallback
    if not points and country_upper != 'US':
        logger.warning(f"No data for {country_upper}, trying US as fallback")
        fallback_country = 'US'
        use_fallback = True
        
        def fetch_maturity_fallback(mat_label):
            series_id, _label, used_mat, _note = _series_for_instrument(
                instrument_type, 'US', mat_label
            )
            if not series_id:
                return None
            val, date = fetch_fred_observation(series_id)
            if val is None:
                return None
            return {
                'maturity': maturity_map.get(used_mat, 1.0),
                'maturityLabel': used_mat,
                'rate': round(val, 4),
                'date': date,
                'source': 'fred',
                'note': f'Fallback: US data used (no data for {country_upper})',
            }
        
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            points.extend(
                point for point in executor.map(fetch_maturity_fallback, maturities)
                if point is not None
            )

    if from_date and to_date:
        points.sort(key=lambda x: x['date'] or '')
    else:
        points.sort(key=lambda x: x['maturity'])
    
    # Add fallback note to all points if fallback was used
    if use_fallback:
        for point in points:
            point['note'] = f'Fallback: US data used (no data for {country_upper})'

    if points:
        _fred_cache_set(yc_key, {'points': points})
    return points


def get_market_benchmark(instrument_type, maturity='1Y', country='US', currency='USD'):
    country_upper = normalize_country(country)

    series_id, label, used_mat, note = _series_for_instrument(
        instrument_type, country_upper, maturity
    )
    inferred_ccy = currency_for_country(country_upper)

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
    
    # Include all currencies from COUNTRY_CURRENCY
    currencies = []
    for code in COUNTRY_CURRENCY.values():
        if code not in currencies:
            currencies.append({'code': code, 'name': code})
    
    return {
        'countries': countries,
        'currencies': currencies,
        'note': 'Filter options from local configuration',
    }
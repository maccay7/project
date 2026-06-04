"""FRED helpers: multi-country benchmarks and yield curves."""
import os
import time
import requests

FRED_KEY = os.getenv('FRED_API_KEY', '')
FRED_URL = 'https://api.stlouisfed.org/fred/series/observations'

_cache = {}
CACHE_SEC = 300

# Country -> currency -> FRED series id (OECD / national sources on FRED)
COUNTRY_DATA = {
    'US': {
        'name': 'United States',
        'currency': 'USD',
        'series': {
            '3M': ('DTB3', '3-Month Treasury Bill'),
            '6M': ('DTB6', '6-Month Treasury Bill'),
            '1Y': ('DGS1', '1-Year Treasury Rate'),
            '2Y': ('DGS2', '2-Year Treasury Rate'),
            '5Y': ('DGS5', '5-Year Treasury Rate'),
            '10Y': ('DGS10', '10-Year Treasury Rate'),
            '30Y': ('DGS30', '30-Year Treasury Rate'),
        },
    },
    'GB': {
        'name': 'United Kingdom',
        'currency': 'GBP',
        'series': {'10Y': ('IRLTLT01GBM156N', 'UK 10-Year Government Bond Yield')},
    },
    'DE': {
        'name': 'Germany',
        'currency': 'EUR',
        'series': {'10Y': ('IRLTLT01DEM156N', 'Germany 10-Year Government Bond Yield')},
    },
    'EU': {
        'name': 'Euro Area',
        'currency': 'EUR',
        'series': {'10Y': ('IRLTLT01EZM156N', 'Euro Area 10-Year Government Bond Yield')},
    },
    'JP': {
        'name': 'Japan',
        'currency': 'JPY',
        'series': {'10Y': ('IRLTLT01JPM156N', 'Japan 10-Year Government Bond Yield')},
    },
    'CA': {
        'name': 'Canada',
        'currency': 'CAD',
        'series': {'10Y': ('IRLTLT01CAM156N', 'Canada 10-Year Government Bond Yield')},
    },
    'AU': {
        'name': 'Australia',
        'currency': 'AUD',
        'series': {'10Y': ('IRLTLT01AUS156N', 'Australia 10-Year Government Bond Yield')},
    },
    'ZA': {
        'name': 'South Africa',
        'currency': 'ZAR',
        'series': {'10Y': ('IRLTLT01ZAM156N', 'South Africa 10-Year Government Bond Yield')},
    },
    'BR': {
        'name': 'Brazil',
        'currency': 'BRL',
        'series': {'10Y': ('IRLTLT01BRM156N', 'Brazil 10-Year Government Bond Yield')},
    },
    'IN': {
        'name': 'India',
        'currency': 'INR',
        'series': {'10Y': ('IRLTLT01INM156N', 'India 10-Year Government Bond Yield')},
    },
    'MX': {
        'name': 'Mexico',
        'currency': 'MXN',
        'series': {'10Y': ('IRLTLT01MXM156N', 'Mexico 10-Year Government Bond Yield')},
    },
    'CN': {
        'name': 'China',
        'currency': 'CNY',
        'series': {'10Y': ('IRLTLT01CNM156N', 'China 10-Year Government Bond Yield')},
    },
}

DEFAULT_BENCHMARK = {
    'tbills': '3M',
    'treasury_bills': '3M',
    'bonds': '10Y',
    'money_market': '1Y',
    'money-market': '1Y',
}

COLORS = {
    'treasury_bills': '#0B2044',
    'tbills': '#0B2044',
    'bonds': '#1E88E5',
    'money_market': '#4CAF50',
    'money-market': '#4CAF50',
}


def build_filter_options():
    countries = []
    for code, info in COUNTRY_DATA.items():
        countries.append({
            'code': code,
            'name': info['name'],
            'currency': info['currency'],
            'maturities': [
                {'code': m, 'name': f'{m} – {info["series"][m][1]}'}
                for m in info['series']
            ],
        })
    currencies = []
    seen = set()
    extra = ['USD', 'EUR', 'GBP', 'ZAR', 'JPY', 'CAD', 'AUD', 'BRL', 'INR', 'MXN', 'CNY', 'CHF', 'NGN', 'KES']
    for c in extra:
        if c not in seen:
            seen.add(c)
            currencies.append({'code': c, 'name': c})
    for info in COUNTRY_DATA.values():
        if info['currency'] not in seen:
            seen.add(info['currency'])
            currencies.append({'code': info['currency'], 'name': info['currency']})
    return {
        'countries': countries,
        'currencies': currencies,
        'note': 'Rates from FRED (Federal Reserve Economic Data). Non-US countries use OECD long-term government bond yields where available.',
    }


FILTER_OPTIONS = build_filter_options()


def normalize_type(instrument_type):
    t = (instrument_type or 'all').lower().strip().replace('-', '_')
    if t in ('tbill', 't_bills', 'treasury', 'treasury_bill'):
        return 'treasury_bills'
    if t in ('moneymarket',):
        return 'money_market'
    return t


def resolve_country_input(country):
    """Match code or country name (typed search)."""
    raw = (country or 'US').strip()
    key = raw.upper()
    if key in COUNTRY_DATA:
        return key
    low = raw.lower()
    for code, info in COUNTRY_DATA.items():
        if info['name'].lower() == low or low in info['name'].lower():
            return code
    return key if len(key) == 2 else None


def get_country(country_code):
    resolved = resolve_country_input(country_code) or 'US'
    return COUNTRY_DATA.get(resolved, COUNTRY_DATA['US'])


def series_for_country(country, maturity):
    """Pick FRED series for country + maturity; fallback if maturity missing."""
    c = get_country(country)
    mat = (maturity or '10Y').upper()
    smap = c['series']
    note = None
    if mat in smap:
        sid, label = smap[mat]
        used = mat
    elif '10Y' in smap:
        sid, label = smap['10Y']
        used = '10Y'
        note = f'{mat} is not on FRED for {c["name"]}; showing 10-year benchmark.'
    else:
        used, (sid, label) = next(iter(smap.items()))
        note = f'Showing {used} benchmark for {c["name"]}.'
    return sid, label, used, c['name'], c['currency'], note


def latest_value(series_id):
    if not FRED_KEY:
        return None
    cache_key = f'latest_{series_id}'
    now = time.time()
    if cache_key in _cache and now - _cache[cache_key][0] < CACHE_SEC:
        return _cache[cache_key][1]

    params = {
        'series_id': series_id,
        'api_key': FRED_KEY,
        'file_type': 'json',
        'sort_order': 'desc',
        'limit': 12,
    }
    try:
        res = requests.get(FRED_URL, params=params, timeout=12)
        res.raise_for_status()
        for row in res.json().get('observations', []):
            val = row.get('value')
            if val and val != '.':
                rate = float(val)
                _cache[cache_key] = (now, rate)
                return rate
    except Exception:
        return None
    return None


def get_market_benchmark(instrument_type, maturity=None, country='US', currency='USD'):
    key = normalize_type(instrument_type)
    mat = (maturity or DEFAULT_BENCHMARK.get(key, '10Y')).upper()
    resolved = resolve_country_input(country)
    if not resolved or resolved not in COUNTRY_DATA:
        return {
            'error': f'Country "{country}" not in FRED catalog. Choose from the list or use US, GB, ZA, etc.',
            'country': country,
            'currency': currency,
        }
    c = COUNTRY_DATA[resolved]
    country = resolved

    if currency.upper() != c['currency']:
        return {
            'error': f'Currency {currency} does not match {c["name"]} ({c["currency"]}). Select the matching currency.',
            'country': country,
            'currency': currency,
        }

    series_id, label, used_mat, cname, ccurr, note = series_for_country(country, mat)
    rate = latest_value(series_id)

    out = {
        'country': country.upper(),
        'country_name': cname,
        'currency': ccurr,
        'maturity': used_mat,
        'requested_maturity': mat,
        'series_id': series_id,
        'series_label': label,
        'benchmark_rate': round(rate, 2) if rate is not None else None,
        'source': 'FRED API',
        'as_of': 'latest observation',
    }
    if note:
        out['note'] = note
    return out


def curve_points_for_country(country):
    c = get_country(country)
    return [(m, c['series'][m][0]) for m in c['series']]


def curve_for_type(instrument_type, country='US'):
    country = (country or 'US').upper()
    if country == 'US':
        key = normalize_type(instrument_type)
        from_points = {
            'treasury_bills': [('3M', 'DTB3'), ('6M', 'DTB6'), ('1Y', 'DTB1'), ('2Y', 'DGS2')],
            'tbills': [('3M', 'DTB3'), ('6M', 'DTB6'), ('1Y', 'DTB1'), ('2Y', 'DGS2')],
            'bonds': [('2Y', 'DGS2'), ('5Y', 'DGS5'), ('10Y', 'DGS10'), ('30Y', 'DGS30')],
            'money_market': [('3M', 'DTB3'), ('6M', 'DTB6'), ('1Y', 'DGS1'), ('2Y', 'DGS2')],
            'money-market': [('3M', 'DTB3'), ('6M', 'DTB6'), ('1Y', 'DGS1'), ('2Y', 'DGS2')],
        }
        points = from_points.get(key, from_points['bonds'])
    else:
        points = curve_points_for_country(country)

    labels, values = [], []
    for label, series_id in points:
        rate = latest_value(series_id)
        if rate is not None:
            labels.append(label)
            values.append(round(rate, 2))
    return labels, values


def build_yield_curve_response(instrument_type='all', country='US', currency='USD'):
    country = (country or 'US').upper()
    c = get_country(country)

    if currency.upper() != c['currency']:
        return {
            'labels': [],
            'current': [],
            'datasets': [],
            'error': f'Use currency {c["currency"]} for {c["name"]}.',
        }

    key = normalize_type(instrument_type)

    if key == 'all' and country == 'US':
        types = [
            ('treasury_bills', 'Treasury Bills'),
            ('bonds', 'Bonds'),
            ('money_market', 'Money Market'),
        ]
        datasets = []
        for tkey, name in types:
            labels, values = curve_for_type(tkey, country)
            if not labels:
                continue
            datasets.append({
                'label': name,
                'data': values,
                'maturities': labels,
                'borderColor': COLORS.get(tkey, '#0B2044'),
            })
        max_len = max((len(d['data']) for d in datasets), default=0)
        shared_labels = [f'Point {i + 1}' for i in range(max_len)]
        return {
            'labels': shared_labels,
            'current': datasets[0]['data'] if datasets else [],
            'datasets': datasets,
            'source': 'FRED API',
            'country': country,
            'currency': c['currency'],
        }

    labels, values = curve_for_type(key, country)
    return {
        'labels': labels,
        'current': values,
        'datasets': [{
            'label': f'{c["name"]} – {key.replace("_", " ").title()}',
            'data': values,
            'maturities': labels,
            'borderColor': COLORS.get(key, '#0B2044'),
        }],
        'source': 'FRED API',
        'country': country,
        'currency': c['currency'],
    }


def attach_fred_to_calculation(result, instrument_type, maturity=None, country='US', currency='USD'):
    if not result or not FRED_KEY:
        return result

    bench = get_market_benchmark(instrument_type, maturity, country, currency)
    if bench.get('error') or bench.get('benchmark_rate') is None:
        result['fred'] = bench
        return result

    portfolio = (
        result.get('avgRate')
        or result.get('avgYTM')
        or result.get('avgDiscountRate')
        or result.get('avgCouponRate')
        or 0
    )
    try:
        portfolio = float(portfolio)
    except (TypeError, ValueError):
        portfolio = 0.0

    bench['spread_vs_market'] = round(portfolio - bench['benchmark_rate'], 2)
    bench['portfolio_rate'] = round(portfolio, 2)
    result['fred'] = bench
    return result

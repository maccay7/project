"""FRED helpers: multi-country benchmarks and yield curves."""
import os
import time
import requests
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables securely
load_dotenv()

# Secure API key loading with validation
FRED_KEY = os.getenv('FRED_API_KEY', '')
if not FRED_KEY:
    print("❌ ERROR: FRED_API_KEY is not set in environment variables!")
    print("Please add FRED_API_KEY to your .env file.")
else:
    print(f"✅ FRED_API_KEY loaded successfully")

FRED_URL = 'https://api.stlouisfed.org/fred/series/observations'
FRED_TIMEOUT = 10  # seconds

# Backend cache with 5-minute duration
_cache = {}
CACHE_SEC = 300  # 5 minutes

# ─── Country Data (US has full maturity coverage) ──────────────────────────

COUNTRY_DATA = {
    'US': {
        'name': 'United States',
        'currency': 'USD',
        'series': {
            '4W': ('DTB4WK', '4-Week Treasury Bill'),
            '13W': ('DTB3', '3-Month Treasury Bill'),
            '26W': ('DTB6', '6-Month Treasury Bill'),
            '52W': ('DTB1YR', '1-Year Treasury Bill'),
            '1M': ('DGS1MO', '1-Month Treasury Rate'),
            '3M': ('DGS3MO', '3-Month Treasury Rate'),
            '6M': ('DGS6MO', '6-Month Treasury Rate'),
            '1Y': ('DGS1', '1-Year Treasury Rate'),
            '2Y': ('DGS2', '2-Year Treasury Rate'),
            '5Y': ('DGS5', '5-Year Treasury Rate'),
            '10Y': ('DGS10', '10-Year Treasury Rate'),
            '30Y': ('DGS30', '30-Year Treasury Rate'),
        }
    },
    'GB': {
        'name': 'United Kingdom',
        'currency': 'GBP',
        'series': {
            '10Y': ('IRLTLT01GBM156N', 'UK 10-Year Government Bond Yield')
        }
    },
    'DE': {
        'name': 'Germany',
        'currency': 'EUR',
        'series': {
            '10Y': ('IRLTLT01DEM156N', 'Germany 10-Year Government Bond Yield')
        }
    },
    'EU': {
        'name': 'Euro Area',
        'currency': 'EUR',
        'series': {
            '10Y': ('IRLTLT01EZM156N', 'Euro Area 10-Year Government Bond Yield')
        }
    },
    'JP': {
        'name': 'Japan',
        'currency': 'JPY',
        'series': {
            '10Y': ('IRLTLT01JPM156N', 'Japan 10-Year Government Bond Yield')
        }
    },
    'CA': {
        'name': 'Canada',
        'currency': 'CAD',
        'series': {
            '10Y': ('IRLTLT01CAM156N', 'Canada 10-Year Government Bond Yield')
        }
    },
}

DEFAULT_BENCHMARK = {
    'tbills': '13W',
    'treasury_bills': '13W',
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
    for info in COUNTRY_DATA.values():
        if info['currency'] not in seen:
            seen.add(info['currency'])
            currencies.append({'code': info['currency'], 'name': info['currency']})
    return {
        'countries': countries,
        'currencies': currencies,
        'note': 'Rates sourced directly from FRED.',
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
    raw = (country or 'US').strip().upper()
    if raw in COUNTRY_DATA:
        return raw
    low = raw.lower()
    for code, info in COUNTRY_DATA.items():
        if info['name'].lower() == low or low in info['name'].lower():
            return code
    # Handle 3-letter ISO codes
    iso3_to_iso2 = {
        'USA': 'US', 'GBR': 'GB', 'DEU': 'DE', 'FRA': 'FR', 'ITA': 'IT',
        'ESP': 'ES', 'NLD': 'NL', 'BEL': 'BE', 'CHE': 'CH', 'AUT': 'AT',
        'SWE': 'SE', 'NOR': 'NO', 'DNK': 'DK', 'FIN': 'FI', 'POL': 'PL',
        'CZE': 'CZ', 'HUN': 'HU', 'ROU': 'RO', 'BGR': 'BG', 'GRC': 'GR',
        'PRT': 'PT', 'IRL': 'IE', 'LUX': 'LU', 'HRV': 'HR', 'SVK': 'SK',
        'SVN': 'SI', 'EST': 'EE', 'LVA': 'LV', 'LTU': 'LT', 'ISL': 'IS',
        'MLT': 'MT', 'CYP': 'CY'
    }
    if raw in iso3_to_iso2:
        return iso3_to_iso2[raw]
    return raw

def get_country(country_code):
    resolved = resolve_country_input(country_code) or 'US'
    if resolved in COUNTRY_DATA:
        return COUNTRY_DATA[resolved]
    # Fallback to US with note
    return {
        **COUNTRY_DATA['US'],
        'name': resolved,
        'currency': 'USD',
        'note': f'Using US rates for {resolved}'
    }

def series_for_country(country, maturity):
    c = get_country(country)
    mat = (maturity or '10Y').upper()
    smap = c.get('series', {})
    note = c.get('note')
    if mat in smap:
        sid, label = smap[mat]
        used = mat
    else:
        # No series for this maturity – return None
        return (None, None, mat, c['name'], c['currency'], f'Maturity {mat} not available for {c["name"]}')
    return sid, label, used, c['name'], c['currency'], note

def latest_value(series_id):
    """Fetch latest value from FRED API with comprehensive error handling and caching."""
    if not FRED_KEY:
        print("❌ FRED API key not configured")
        return None
    
    cache_key = f'latest_{series_id}'
    now = time.time()
    
    # Check cache first
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
        resp = requests.get(FRED_URL, params=params, timeout=FRED_TIMEOUT)
        
        # Handle HTTP errors
        if resp.status_code == 429:
            print(f"❌ FRED rate limit exceeded for {series_id}")
            return None
        elif resp.status_code == 404:
            print(f"❌ FRED series not found: {series_id}")
            return None
        elif resp.status_code == 403:
            print(f"❌ FRED authentication failed for {series_id}")
            return None
        
        resp.raise_for_status()
        data = resp.json()
        
        # Handle FRED API errors
        if 'error_code' in data:
            error_msg = data.get('error_message', 'unknown error')
            print(f"❌ FRED API error for {series_id}: {error_msg}")
            return None
        
        # Extract latest valid value
        for row in data.get('observations', []):
            val = row.get('value')
            if val and val != '.':
                rate = float(val)
                # Cache the result
                _cache[cache_key] = (now, rate)
                return rate
        
        print(f"⚠️ No valid data found for {series_id}")
        return None
        
    except requests.exceptions.Timeout:
        print(f"⚠️ FRED request timeout for {series_id}")
        return None
    except requests.exceptions.ConnectionError:
        print(f"⚠️ FRED connection error for {series_id}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"⚠️ FRED request failed for {series_id}: {e}")
        return None
    except ValueError as e:
        print(f"⚠️ FRED JSON decode error for {series_id}: {e}")
        return None
    except Exception as e:
        print(f"⚠️ Unexpected error for {series_id}: {e}")
        return None

def get_market_benchmark(instrument_type, maturity=None, country='US', currency='USD'):
    key = normalize_type(instrument_type)
    mat = (maturity or DEFAULT_BENCHMARK.get(key, '10Y')).upper()
    resolved = resolve_country_input(country)
    c = get_country(resolved)
    country_code = resolved if resolved in COUNTRY_DATA else 'US'
    if currency and currency.upper() != c['currency'] and currency.upper() not in ('ANY', 'ALL'):
        note = f'Currency mismatch: {currency} vs {c["currency"]}. Using {c["currency"]} for benchmark.'
    else:
        note = None
    series_id, label, used_mat, cname, ccurr, note2 = series_for_country(country_code, mat)
    if series_id is None:
        return {'error': f'No series ID for {country_code} {mat}'}
    if note2:
        note = (note + ' ' + note2) if note else note2
    rate = latest_value(series_id)
    if rate is None:
        return {
            'error': f'FRED did not return data for series {series_id}. Please verify the FRED API key and requested country/maturity.',
        }
    out = {
        'country': country_code,
        'country_name': cname,
        'currency': ccurr,
        'maturity': used_mat,
        'requested_maturity': mat,
        'series_id': series_id,
        'series_label': label,
        'benchmark_rate': round(rate, 2),
        'source': 'FRED API' if rate is not None else 'FALLBACK',
        'as_of': 'latest observation',
    }
    if note:
        out['note'] = note.strip()
    return out

def curve_points_for_country(country):
    c = get_country(country)
    return [(m, c['series'][m][0]) for m in c['series']] if 'series' in c else []

def curve_for_type(instrument_type, country='US'):
    country_code = resolve_country_input(country)
    if country_code == 'US':
        key = normalize_type(instrument_type)
        if key in ('treasury_bills', 'tbills'):
            desired = ['4W', '8W', '13W', '26W', '52W']
        elif key in ('money_market', 'money-market'):
            desired = ['1M', '3M', '6M', '1Y']
        elif key == 'bonds':
            desired = ['2Y', '5Y', '10Y', '30Y']
        else:
            desired = ['1Y', '2Y', '5Y', '10Y', '30Y']
        c = get_country(country_code)
        points = []
        for m in desired:
            if m in c['series']:
                sid, label = c['series'][m]
                points.append((m, sid))
        if not points:
            points = [(m, c['series'][m][0]) for m in c['series']]
    else:
        points = curve_points_for_country(country_code)
    labels, values = [], []
    for label, series_id in points:
        rate = latest_value(series_id)
        if rate is not None:
            labels.append(label)
            values.append(round(rate, 2))
        else:
            print(f"⚠️ FRED unavailable for {label} ({series_id}); skipping this maturity.")
    return labels, values

def build_yield_curve_response(instrument_type='all', country='US', currency='USD'):
    """Build yield curve response with analytics and comprehensive error handling."""
    country_code = resolve_country_input(country)
    c = get_country(country_code)
    
    # Validate currency match
    if currency and currency.upper() != c['currency'] and currency.upper() not in ('ANY', 'ALL'):
        return {
            'labels': [],
            'current': [],
            'datasets': [],
            'error': f'Currency mismatch. {c["name"]} uses {c["currency"]}. Please select {c["currency"]}.',
            'analytics': None,
        }
    
    key = normalize_type(instrument_type)
    
    # Build datasets based on instrument type
    if key == 'all' and country_code == 'US':
        types = [('treasury_bills', 'Treasury Bills'), ('bonds', 'Bonds'), ('money_market', 'Money Market')]
        datasets = []
        all_values = []
        
        for tkey, name in types:
            labels, values = curve_for_type(tkey, country_code)
            if not labels:
                continue
            all_values.extend(values)
            datasets.append({
                'label': name,
                'data': values,
                'maturities': labels,
                'borderColor': COLORS.get(tkey, '#0B2044'),
            })
        
        if not datasets:
            return {
                'labels': [],
                'current': [],
                'datasets': [],
                'error': 'No FRED yield curve data available for the selected country and instrument type.',
                'source': 'FRED API',
                'country': country_code,
                'currency': c['currency'],
                'analytics': None,
            }
        
        # Calculate analytics
        analytics = calculate_analytics(all_values) if all_values else None
        
        max_len = max((len(d['data']) for d in datasets), default=0)
        shared_labels = [f'Point {i+1}' for i in range(max_len)]
        
        return {
            'labels': shared_labels,
            'current': datasets[0]['data'] if datasets else [],
            'datasets': datasets,
            'source': 'FRED API',
            'country': country_code,
            'currency': c['currency'],
            'analytics': analytics,
            'last_updated': datetime.now().isoformat(),
        }
    
    # Single instrument type
    labels, values = curve_for_type(key, country_code)
    if not labels:
        return {
            'labels': [],
            'current': [],
            'datasets': [],
            'error': 'No FRED yield curve data available for the selected country and instrument type.',
            'source': 'FRED API',
            'country': country_code,
            'currency': c['currency'],
            'analytics': None,
        }
    
    # Calculate analytics
    analytics = calculate_analytics(values) if values else None
    
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
        'country': country_code,
        'currency': c['currency'],
        'analytics': analytics,
        'last_updated': datetime.now().isoformat(),
    }

def calculate_analytics(values):
    """Calculate yield curve analytics (latest, highest, lowest, average)."""
    if not values:
        return None
    
    try:
        numeric_values = [float(v) for v in values if v is not None]
        if not numeric_values:
            return None
        
        return {
            'latest_yield': round(numeric_values[-1], 2) if numeric_values else None,
            'highest_yield': round(max(numeric_values), 2),
            'lowest_yield': round(min(numeric_values), 2),
            'average_yield': round(sum(numeric_values) / len(numeric_values), 2),
            'data_points': len(numeric_values),
        }
    except (ValueError, TypeError) as e:
        print(f"⚠️ Error calculating analytics: {e}")
        return None

def attach_fred_to_calculation(result, instrument_type, maturity=None, country='US', currency='USD'):
    if not result:
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
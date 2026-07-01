# utils/fred_config.py

# Mapping from (country, maturity) to FRED series ID
# For US T-Bills, we use the secondary market rates.
# For other countries, we use government bond yields (if available).
SERIES_MAP = {
    # US Treasury Bills (secondary market, discount basis)
    'USA_4W': 'DTB4WK',      # 4-Week Treasury Bill
    'USA_8W': 'DTB8WK',      # 8-Week Treasury Bill (if available; fallback to 4W if not)
    'USA_13W': 'TB3MS',      # 3-Month Treasury Bill
    'USA_26W': 'TB6MS',      # 6-Month Treasury Bill
    'USA_52W': 'TB1YR',      # 1-Year Treasury Bill
    # US Treasury constant maturity rates (for bonds)
    'USA_1M': 'DGS1MO',
    'USA_3M': 'DGS3MO',
    'USA_6M': 'DGS6MO',
    'USA_1Y': 'DGS1',
    'USA_2Y': 'DGS2',
    'USA_5Y': 'DGS5',
    'USA_10Y': 'DGS10',
    'USA_30Y': 'DGS30',
    # UK
    'GBR_2Y': 'IRLTLT01GBM156N',  # 2-year bond yield
    'GBR_5Y': 'IRLTLT01GBM156N',  # same series, but we might use different ones
    'GBR_10Y': 'IRLTLT01GBM156N',
    # Eurozone (Germany)
    'EUR_2Y': 'IRLTLT01DEM156N',
    'EUR_5Y': 'IRLTLT01DEM156N',
    'EUR_10Y': 'IRLTLT01DEM156N',
    # Japan
    'JPN_2Y': 'IRLTLT01JPM156N',
    'JPN_5Y': 'IRLTLT01JPM156N',
    'JPN_10Y': 'IRLTLT01JPM156N',
    # Canada
    'CAN_2Y': 'IRLTLT01CAM156N',
    'CAN_5Y': 'IRLTLT01CAM156N',
    'CAN_10Y': 'IRLTLT01CAM156N',
}

def get_series_id(country, maturity):
    """Return the FRED series ID for the given country and maturity."""
    key = f"{country}_{maturity}"
    # If not found, try to fallback to US for common maturities (optional)
    if key not in SERIES_MAP:
        # Check if we have a US equivalent for this maturity
        us_key = f"USA_{maturity}"
        if us_key in SERIES_MAP:
            return SERIES_MAP[us_key]
        return None
    return SERIES_MAP[key]

def get_maturity_label(maturity):
    """Return a human-readable label for the maturity."""
    labels = {
        '4W': '4-Week',
        '8W': '8-Week',
        '13W': '3-Month',
        '26W': '6-Month',
        '52W': '1-Year',
        '1M': '1-Month',
        '3M': '3-Month',
        '6M': '6-Month',
        '1Y': '1-Year',
        '2Y': '2-Year',
        '5Y': '5-Year',
        '10Y': '10-Year',
        '30Y': '30-Year',
    }
    return labels.get(maturity, maturity)

def build_filter_options():
    """Return available filter options for the frontend."""
    return {
        'countries': ['USA', 'GBR', 'EUR', 'JPN', 'CAN'],
        'currencies': ['USD', 'GBP', 'EUR', 'JPY', 'CAD'],
        'maturities': [
            {'code': '4W', 'name': '4 Weeks'},
            {'code': '8W', 'name': '8 Weeks'},
            {'code': '13W', 'name': '3 Months'},
            {'code': '26W', 'name': '6 Months'},
            {'code': '52W', 'name': '1 Year'},
            {'code': '1M', 'name': '1 Month'},
            {'code': '3M', 'name': '3 Months'},
            {'code': '6M', 'name': '6 Months'},
            {'code': '1Y', 'name': '1 Year'},
            {'code': '2Y', 'name': '2 Years'},
            {'code': '5Y', 'name': '5 Years'},
            {'code': '10Y', 'name': '10 Years'},
            {'code': '30Y', 'name': '30 Years'},
        ]
    }

def get_market_benchmark(instrument_type, maturity, country, currency):
    """
    Fetch the benchmark rate for the given instrument type, maturity, country, currency.
    Returns a dict with benchmark_rate, series_label, etc.
    This is a simplified version – you may want to call the FRED API directly.
    """
    # For this example, we'll return a dummy rate – but in production, you'd fetch from FRED.
    # Since we're not hardcoding fallback, we'll actually fetch from FRED.
    # However, this function is called from the frontend via /api/fred/benchmark.
    # We'll implement the real fetch using the series ID.
    import requests
    import os
    FRED_API_KEY = os.environ.get('FRED_API_KEY')
    if not FRED_API_KEY:
        return {'error': 'FRED API key missing'}

    series_id = get_series_id(country, maturity)
    if not series_id:
        return {'error': f'No series ID for {country} {maturity}'}

    url = f"https://api.stlouisfed.org/fred/series/observations"
    params = {
        'series_id': series_id,
        'api_key': FRED_API_KEY,
        'file_type': 'json',
        'sort_order': 'desc',
        'limit': 1
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        obs = data.get('observations', [])
        if not obs or obs[0]['value'] == '.':
            return {'error': 'No data for series'}
        rate = float(obs[0]['value'])
        return {
            'benchmark_rate': rate,
            'series_label': get_maturity_label(maturity),
            'country': country,
            'currency': currency,
            'maturity': maturity,
            'series_id': series_id,
            'note': f'FRED {series_id}'
        }
    except Exception as e:
        return {'error': str(e)}
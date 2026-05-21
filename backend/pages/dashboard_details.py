import os
import requests
from utils.db import get_db

FRED_API_KEY = os.environ.get('FRED_API_KEY', 'b40141a5119f30bc2388d63f59d8847e')
FRED_URL = 'https://api.stlouisfed.org/fred/series/observations'


def get_kpi():
    conn = get_db()
    if not conn:
        return {'total_users': 0, 'active_users': 0, 'datasets_processed': 0}

    try:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) AS total_users FROM users')
        total_users = cursor.fetchone().get('total_users', 0)

        cursor.execute("SELECT COUNT(*) AS active_users FROM sessions WHERE expires_at > NOW()")
        active_users = cursor.fetchone().get('active_users', 0)

        cursor.execute("SELECT COUNT(*) AS datasets_processed FROM calculations WHERE calculation_status = 'completed'")
        datasets_processed = cursor.fetchone().get('datasets_processed', 0)

        cursor.close()
        conn.close()

        return {
            'total_users': total_users,
            'active_users': active_users,
            'datasets_processed': datasets_processed
        }
    except Exception:
        return {'total_users': 0, 'active_users': 0, 'datasets_processed': 0}


def get_recent_activity():
    conn = get_db()
    if not conn:
        return []

    try:
        cursor = conn.cursor()
        cursor.execute('SELECT action, resource, created_at FROM audit_log ORDER BY created_at DESC LIMIT 5')
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [
            {
                'action': row.get('action'),
                'resource': row.get('resource'),
                'timestamp': row.get('created_at').isoformat() if row.get('created_at') else None
            }
            for row in rows
        ]
    except Exception:
        return []


def get_dashboard_charts():
    return {
        'labels': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
        'values': [24, 42, 34, 55, 62, 73]
    }


def get_yield_curve(instrument_type='all'):
    series_map = {
        'treasury_bills': 'TB3MS',
        'bonds': 'DGS10',
        'money_market': 'DFF',
        'all': 'DGS10'
    }
    series_id = series_map.get(instrument_type, 'DGS10')
    params = {
        'series_id': series_id,
        'api_key': FRED_API_KEY,
        'file_type': 'json',
        'sort_order': 'desc',
        'limit': 7
    }

    try:
        response = requests.get(FRED_URL, params=params, timeout=10)
        response.raise_for_status()
        payload = response.json()
        observations = payload.get('observations', [])[:7]
        labels = [obs.get('date', '') for obs in observations]
        current = []
        for obs in observations:
            value = obs.get('value', '0')
            try:
                current.append(float(value))
            except Exception:
                current.append(0.0)
        return {'labels': labels[::-1], 'current': current[::-1]}
    except Exception:
        return {
            'labels': ['3M', '6M', '1Y', '2Y', '5Y', '10Y', '30Y'],
            'current': [4.2, 4.4, 4.6, 4.8, 4.5, 4.3, 4.1]
        }

import os
import json
import requests
from utils.db import get_db

FRED_API_KEY = os.environ.get('FRED_API_KEY')
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
    """
    Returns real chart data from the database.
    If no data, returns empty arrays.
    Replace the query with your actual table/columns.
    """
    conn = get_db()
    if not conn:
        return {'labels': [], 'values': []}

    try:
        cursor = conn.cursor()
        # Example query – adjust to your actual schema
        cursor.execute("""
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM calculations
            WHERE calculation_status = 'completed'
            GROUP BY DATE(created_at)
            ORDER BY date DESC
            LIMIT 6
        """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        # Reverse to show chronological order
        labels = [row.get('date').strftime('%b') if row.get('date') else '' for row in reversed(rows)]
        values = [row.get('count', 0) for row in reversed(rows)]
        return {'labels': labels, 'values': values}
    except Exception:
        return {'labels': [], 'values': []}


def get_yield_curve(instrument_type='all'):
    """
    Fetches real yield curve data from FRED API.
    Returns empty arrays if no data or API key missing.
    """
    if not FRED_API_KEY:
        return {'labels': [], 'current': []}

    # Series mapping should be provided via environment to avoid hardcoding.
    # Example: FRED_DEFAULT_SERIES_MAP='{ "bonds": "DGS10", "money_market": "DTB3", "tbills": "DTB3", "all": "DGS10" }'
    series_map = {}
    map_json = os.environ.get('FRED_DEFAULT_SERIES_MAP')
    if map_json:
        try:
            series_map = json.loads(map_json)
        except Exception:
            series_map = {}

    series_id = series_map.get(instrument_type) or series_map.get('all')
    if not series_id:
        # No configured default series for this instrument type
        return {'labels': [], 'current': []}
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
        observations = payload.get('observations', [])
        if not observations:
            return {'labels': [], 'current': []}
        # Take only up to 7 observations
        observations = observations[:7]
        labels = [obs.get('date', '') for obs in observations]
        current = []
        for obs in observations:
            value = obs.get('value', '')
            try:
                current.append(float(value))
            except (ValueError, TypeError):
                current.append(0.0)
        # Reverse to have ascending order (oldest to newest)
        return {'labels': labels[::-1], 'current': current[::-1]}
    except Exception:
        return {'labels': [], 'current': []}
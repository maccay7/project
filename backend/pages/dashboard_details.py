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


def get_yield_curve(instrument_type='all', country='US', currency='USD'):
    """Fetch yield curves from FRED (one instrument or all three)."""
    from utils.fred_config import build_yield_curve_response, FRED_KEY
    if not FRED_KEY:
        return {'labels': [], 'current': [], 'datasets': [], 'error': 'FRED API key missing'}
    try:
        return build_yield_curve_response(instrument_type, country, currency)
    except Exception as err:
        return {'labels': [], 'current': [], 'datasets': [], 'error': str(err)}
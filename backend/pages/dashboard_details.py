import os
import json
import requests
from utils.db import get_db
from utils.fred_config import get_yield_curve, FRED_API_KEY   # <-- corrected import

FRED_API_KEY = os.environ.get('FRED_API_KEY', FRED_API_KEY)
FRED_URL = 'https://api.stlouisfed.org/fred/series/observations'


def get_kpi():
    conn = get_db()
    if not conn:
        return {'total_users': 0, 'active_users': 0, 'datasets_processed': 0, 'total_instruments': 0, 'total_versions': 0}

    try:
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) AS total_users FROM users')
        total_users = cursor.fetchone().get('total_users', 0)

        cursor.execute("SELECT COUNT(*) AS active_users FROM auth_sessions WHERE expires_at > NOW()")
        active_users = cursor.fetchone().get('active_users', 0)

        cursor.execute("SELECT COUNT(*) AS datasets_processed FROM calculations WHERE calculation_status = 'completed'")
        datasets_processed = cursor.fetchone().get('datasets_processed', 0)
        
        cursor.execute("""
            SELECT COUNT(DISTINCT inst_key) AS instrument_count
            FROM (
                SELECT 'money-market' AS inst_key FROM ui_sessions
                    WHERE JSON_EXTRACT(instrument_workflows, '$."money-market".data') IS NOT NULL
                       OR JSON_EXTRACT(instrument_workflows, '$."money-market".cleanedData') IS NOT NULL
                       OR JSON_EXTRACT(instrument_workflows, '$."money-market".calculations') IS NOT NULL
                UNION
                SELECT 'bonds' FROM ui_sessions
                    WHERE JSON_EXTRACT(instrument_workflows, '$.bonds.data') IS NOT NULL
                       OR JSON_EXTRACT(instrument_workflows, '$.bonds.cleanedData') IS NOT NULL
                       OR JSON_EXTRACT(instrument_workflows, '$.bonds.calculations') IS NOT NULL
                UNION
                SELECT 'tbills' FROM ui_sessions
                    WHERE JSON_EXTRACT(instrument_workflows, '$.tbills.data') IS NOT NULL
                       OR JSON_EXTRACT(instrument_workflows, '$.tbills.cleanedData') IS NOT NULL
                       OR JSON_EXTRACT(instrument_workflows, '$.tbills.calculations') IS NOT NULL
            ) AS inst_counts
        """)
        instrument_count_result = cursor.fetchone()
        total_instruments = min(instrument_count_result.get('instrument_count', 0) if instrument_count_result else 0, 3)
        
        cursor.execute("SELECT COUNT(*) AS total_versions FROM version_history")
        total_versions = cursor.fetchone().get('total_versions', 0)

        cursor.close()
        conn.close()

        return {
            'total_users': total_users,
            'active_users': active_users,
            'datasets_processed': datasets_processed,
            'total_instruments': total_instruments,
            'total_versions': total_versions
        }
    except Exception as e:
        print(f"Error getting KPI: {e}")
        return {'total_users': 0, 'active_users': 0, 'datasets_processed': 0, 'total_instruments': 0, 'total_versions': 0}


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
    conn = get_db()
    if not conn:
        return {'labels': [], 'values': []}

    try:
        cursor = conn.cursor()
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
        labels = [row.get('date').strftime('%b') if row.get('date') else '' for row in reversed(rows)]
        values = [row.get('count', 0) for row in reversed(rows)]
        return {'labels': labels, 'values': values}
    except Exception:
        return {'labels': [], 'values': []}


def get_yield_curve(instrument_type='all', country='US', currency='USD'):
    """Fetch yield curve points from FRED API only (no mock/synthetic data)."""
    from utils.fred_config import normalize_country, build_yield_curve_response
    try:
        country_code = normalize_country(country)
        result = build_yield_curve_response(instrument_type, country_code, currency)
        if result.get('error'):
            return {'labels': [], 'values': [], 'error': result['error']}
        return {
            'labels': result.get('labels', []),
            'values': result.get('values', []),
            'source': 'FRED',
            'country': country_code
        }
    except Exception as err:
        return {'labels': [], 'values': [], 'error': str(err)}
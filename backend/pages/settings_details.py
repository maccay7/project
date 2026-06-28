from utils.db import get_db


def get_user_profile(user_id=1):
    conn = get_db()
    if not conn:
        return {}

    try:
        cursor = conn.cursor()
        cursor.execute('SELECT first_name, last_name, email, phone FROM users WHERE id = %s', (user_id,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if not user:
            return {}
        name_parts = []
        if user.get('first_name'):
            name_parts.append(user.get('first_name'))
        if user.get('last_name'):
            name_parts.append(user.get('last_name'))
        name = ' '.join(name_parts) if name_parts else ''
        return {
            'name': name,
            'email': user.get('email', ''),
            'phone': user.get('phone', '')
        }
    except Exception:
        return {}


def get_user_preferences(user_id=1):
    conn = get_db()
    if not conn:
        return {}

    try:
        cursor = conn.cursor()
        cursor.execute('SELECT language, timezone, date_format, currency FROM user_preferences WHERE user_id = %s', (user_id,))
        prefs = cursor.fetchone()
        cursor.close()
        conn.close()
        if not prefs:
            return {}
        return {
            'language': prefs.get('language', ''),
            'timezone': prefs.get('timezone', ''),
            'dateFormat': prefs.get('date_format', ''),
            'currency': prefs.get('currency', '')
        }
    except Exception:
        return {}


def get_notification_settings(user_id=1):
    conn = get_db()
    if not conn:
        return {}

    try:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT email_notifications, push_notifications, weekly_reports, system_alerts FROM user_preferences WHERE user_id = %s',
            (user_id,)
        )
        prefs = cursor.fetchone()
        cursor.close()
        conn.close()
        if not prefs:
            return {}
        return {
            'emailNotifications': bool(prefs.get('email_notifications', False)),
            'pushNotifications': bool(prefs.get('push_notifications', False)),
            'weeklyReports': bool(prefs.get('weekly_reports', False)),
            'systemAlerts': bool(prefs.get('system_alerts', False))
        }
    except Exception:
        return {}


def get_system_info():
    conn = get_db()
    if not conn:
        return {}

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT config_key, config_value FROM system_config")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        result = {row.get('config_key'): row.get('config_value') for row in rows}
        if not result:
            return {}
        return {
            'last_updated': result.get('updated_at') or result.get('created_at'),
            'version': result.get('version'),
            'apiStatus': result.get('api_status'),
            'database': 'MySQL'
        }
    except Exception:
        return {}
from utils.db import get_db


def get_user_profile(user_id=1):
    conn = get_db()
    if not conn:
        return {'name': 'Guest User', 'email': 'guest@example.com'}

    try:
        cursor = conn.cursor()
        cursor.execute('SELECT first_name, last_name, email FROM users WHERE id = %s', (user_id,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if not user:
            return {'name': 'Guest User', 'email': 'guest@example.com'}
        return {
            'name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
            'email': user.get('email', '')
        }
    except Exception:
        return {'name': 'Guest User', 'email': 'guest@example.com'}


def get_user_preferences(user_id=1):
    conn = get_db()
    if not conn:
        return {'language': 'English', 'timezone': 'GMT+2', 'date_format': 'DD/MM/YYYY', 'currency': 'USD'}

    try:
        cursor = conn.cursor()
        cursor.execute('SELECT language, timezone, date_format, currency FROM user_preferences WHERE user_id = %s', (user_id,))
        prefs = cursor.fetchone()
        cursor.close()
        conn.close()
        if not prefs:
            return {'language': 'English', 'timezone': 'GMT+2', 'date_format': 'DD/MM/YYYY', 'currency': 'USD'}
        return {
            'language': prefs.get('language', 'English'),
            'timezone': prefs.get('timezone', 'GMT+2'),
            'date_format': prefs.get('date_format', 'DD/MM/YYYY'),
            'currency': prefs.get('currency', 'USD')
        }
    except Exception:
        return {'language': 'English', 'timezone': 'GMT+2', 'date_format': 'DD/MM/YYYY', 'currency': 'USD'}


def get_notification_settings(user_id=1):
    conn = get_db()
    if not conn:
        return {'emailNotifications': True, 'pushNotifications': False, 'weeklyReports': True, 'systemAlerts': True}

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
            return {'emailNotifications': True, 'pushNotifications': False, 'weeklyReports': True, 'systemAlerts': True}
        return {
            'emailNotifications': bool(prefs.get('email_notifications', True)),
            'pushNotifications': bool(prefs.get('push_notifications', False)),
            'weeklyReports': bool(prefs.get('weekly_reports', True)),
            'systemAlerts': bool(prefs.get('system_alerts', True))
        }
    except Exception:
        return {'emailNotifications': True, 'pushNotifications': False, 'weeklyReports': True, 'systemAlerts': True}


def get_system_info():
    conn = get_db()
    if not conn:
        return {'last_updated': None, 'version': '1.0.0', 'api_status': 'Online'}

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT config_key, config_value FROM system_config")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        result = {row.get('config_key'): row.get('config_value') for row in rows}
        return {
            'last_updated': result.get('updated_at') or result.get('created_at') or None,
            'version': result.get('version', '1.0.0'),
            'api_status': result.get('api_status', 'Online')
        }
    except Exception:
        return {'last_updated': None, 'version': '1.0.0', 'api_status': 'Online'}

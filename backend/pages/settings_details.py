from utils.db import get_db


def _fetch_one(query, params):
    conn = get_db()
    if not conn:
        return None
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchone()
    except Exception:
        return None
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        try:
            conn.close()
        except Exception:
            pass


def _fetch_all(query):
    conn = get_db()
    if not conn:
        return []
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        return cursor.fetchall()
    except Exception:
        return []
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        try:
            conn.close()
        except Exception:
            pass


def get_user_profile(user_id=1):
    user = _fetch_one(
        'SELECT first_name, last_name, email FROM users WHERE id = %s',
        (user_id,)
    )
    if not user:
        return {}
    name_parts = [user.get('first_name'), user.get('last_name')]
    name = ' '.join(p for p in name_parts if p)
    return {
        'name': name,
        'email': user.get('email', '')
    }


def get_user_preferences(user_id=1):
    prefs = _fetch_one(
        'SELECT language, timezone, date_format, currency FROM user_preferences WHERE user_id = %s',
        (user_id,)
    )
    if not prefs:
        return {}
    return {
        'language': prefs.get('language', ''),
        'timezone': prefs.get('timezone', ''),
        'dateFormat': prefs.get('date_format', ''),
        'currency': prefs.get('currency', '')
    }


def get_notification_settings(user_id=1):
    prefs = _fetch_one(
        'SELECT email_notifications, push_notifications, weekly_reports, system_alerts '
        'FROM user_preferences WHERE user_id = %s',
        (user_id,)
    )
    if not prefs:
        return {}
    return {
        'emailNotifications': bool(prefs.get('email_notifications', False)),
        'pushNotifications': bool(prefs.get('push_notifications', False)),
        'weeklyReports': bool(prefs.get('weekly_reports', False)),
        'systemAlerts': bool(prefs.get('system_alerts', False))
    }


def get_system_info():
    rows = _fetch_all("SELECT config_key, config_value FROM system_config")
    result = {row.get('config_key'): row.get('config_value') for row in rows}
    if not result:
        return {}
    return {
        'last_updated': result.get('updated_at') or result.get('created_at'),
        'version': result.get('version'),
        'apiStatus': result.get('api_status')
    }
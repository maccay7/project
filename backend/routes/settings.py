import json
from flask import request, jsonify
from pages.settings_details import (
    get_user_profile,
    get_user_preferences,
    get_notification_settings,
    get_system_info
)
from utils.db import get_db


def create_settings_table():
    conn = get_db()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                setting_key VARCHAR(255) NOT NULL,
                setting_value JSON,
                setting_type VARCHAR(50) DEFAULT 'preference',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY unique_user_setting (user_id, setting_key)
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error creating user_settings table: {e}")
        conn.close()
        return False


def get_setting(user_id, setting_key):
    conn = get_db()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM user_settings WHERE user_id = %s AND setting_key = %s",
            (user_id, setting_key)
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not row:
            return None
        
        return json.loads(row['setting_value']) if row['setting_value'] else None
    except Exception as e:
        print(f"Error getting setting: {e}")
        conn.close()
        return None


def save_setting(user_id, setting_key, setting_value, setting_type='preference'):
    conn = get_db()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO user_settings (user_id, setting_key, setting_value, setting_type) 
               VALUES (%s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
               setting_value = VALUES(setting_value),
               setting_type = VALUES(setting_type),
               updated_at = CURRENT_TIMESTAMP""",
            (user_id, setting_key, json.dumps(setting_value), setting_type)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving setting: {e}")
        conn.close()
        return False


def get_all_settings(user_id):
    conn = get_db()
    if not conn:
        return {}
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_settings WHERE user_id = %s", (user_id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        settings = {}
        for row in rows:
            settings[row['setting_key']] = {
                'value': json.loads(row['setting_value']) if row['setting_value'] else None,
                'type': row['setting_type'],
                'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None
            }
        return settings
    except Exception as e:
        print(f"Error getting all settings: {e}")
        conn.close()
        return {}


def settings_routes(app):
    create_settings_table()
    
    @app.route('/api/user/profile', methods=['GET', 'OPTIONS'])
    def profile():
        if request.method == 'OPTIONS':
            return '', 200
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_id = 1
        if token:
            conn = get_db()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute('SELECT user_id FROM sessions WHERE token = %s', (token,))
                    session = cursor.fetchone()
                    if session:
                        user_id = session['user_id']
                    cursor.close()
                    conn.close()
                except:
                    pass
        return jsonify({'success': True, 'data': get_user_profile(user_id)})

    @app.route('/api/user/profile', methods=['PUT', 'OPTIONS'])
    def update_profile():
        if request.method == 'OPTIONS':
            return '', 200
        data = request.get_json()
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_id = 1
        if token:
            conn = get_db()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute('SELECT user_id FROM sessions WHERE token = %s', (token,))
                    session = cursor.fetchone()
                    if session:
                        user_id = session['user_id']
                    cursor.close()
                    conn.close()
                except:
                    pass
        
        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'Database error'}), 500
        try:
            cursor = conn.cursor()
            if data.get('name'):
                name_parts = data['name'].split(' ', 1)
                cursor.execute('UPDATE users SET first_name = %s, last_name = %s WHERE id = %s',
                             (name_parts[0], name_parts[1] if len(name_parts) > 1 else '', user_id))
            if data.get('phone'):
                cursor.execute('UPDATE users SET phone = %s WHERE id = %s', (data['phone'], user_id))
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'success': True, 'data': get_user_profile(user_id)})
        except Exception as e:
            print(f"Error updating profile: {e}")
            conn.close()
            return jsonify({'success': False, 'message': 'Failed to update profile'}), 500

    @app.route('/api/user/preferences', methods=['GET', 'OPTIONS'])
    def preferences():
        if request.method == 'OPTIONS':
            return '', 200
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_id = 1
        if token:
            conn = get_db()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute('SELECT user_id FROM sessions WHERE token = %s', (token,))
                    session = cursor.fetchone()
                    if session:
                        user_id = session['user_id']
                    cursor.close()
                    conn.close()
                except:
                    pass
        return jsonify({'success': True, 'data': get_user_preferences(user_id)})

    @app.route('/api/user/preferences', methods=['PUT', 'OPTIONS'])
    def update_preferences():
        if request.method == 'OPTIONS':
            return '', 200
        data = request.get_json()
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_id = 1
        if token:
            conn = get_db()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute('SELECT user_id FROM sessions WHERE token = %s', (token,))
                    session = cursor.fetchone()
                    if session:
                        user_id = session['user_id']
                    cursor.close()
                    conn.close()
                except:
                    pass
        
        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'Database error'}), 500
        try:
            cursor = conn.cursor()
            if data.get('language'):
                cursor.execute('UPDATE user_preferences SET language = %s WHERE user_id = %s', (data['language'], user_id))
            if data.get('timezone'):
                cursor.execute('UPDATE user_preferences SET timezone = %s WHERE user_id = %s', (data['timezone'], user_id))
            if data.get('dateFormat'):
                cursor.execute('UPDATE user_preferences SET date_format = %s WHERE user_id = %s', (data['dateFormat'], user_id))
            if data.get('currency'):
                cursor.execute('UPDATE user_preferences SET currency = %s WHERE user_id = %s', (data['currency'], user_id))
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'success': True, 'data': get_user_preferences(user_id)})
        except Exception as e:
            print(f"Error updating preferences: {e}")
            conn.close()
            return jsonify({'success': False, 'message': 'Failed to update preferences'}), 500

    @app.route('/api/user/notifications/settings', methods=['GET', 'OPTIONS'])
    def notifications_settings():
        if request.method == 'OPTIONS':
            return '', 200
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_id = 1
        if token:
            conn = get_db()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute('SELECT user_id FROM sessions WHERE token = %s', (token,))
                    session = cursor.fetchone()
                    if session:
                        user_id = session['user_id']
                    cursor.close()
                    conn.close()
                except:
                    pass
        return jsonify({'success': True, 'data': get_notification_settings(user_id)})

    @app.route('/api/user/notifications/settings', methods=['PUT', 'OPTIONS'])
    def update_notification_settings():
        if request.method == 'OPTIONS':
            return '', 200
        data = request.get_json()
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_id = 1
        if token:
            conn = get_db()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute('SELECT user_id FROM sessions WHERE token = %s', (token,))
                    session = cursor.fetchone()
                    if session:
                        user_id = session['user_id']
                    cursor.close()
                    conn.close()
                except:
                    pass
        
        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'Database error'}), 500
        try:
            cursor = conn.cursor()
            if data.get('emailNotifications') is not None:
                cursor.execute('UPDATE user_preferences SET email_notifications = %s WHERE user_id = %s',
                             (data['emailNotifications'], user_id))
            if data.get('pushNotifications') is not None:
                cursor.execute('UPDATE user_preferences SET push_notifications = %s WHERE user_id = %s',
                             (data['pushNotifications'], user_id))
            if data.get('weeklyReports') is not None:
                cursor.execute('UPDATE user_preferences SET weekly_reports = %s WHERE user_id = %s',
                             (data['weeklyReports'], user_id))
            if data.get('systemAlerts') is not None:
                cursor.execute('UPDATE user_preferences SET system_alerts = %s WHERE user_id = %s',
                             (data['systemAlerts'], user_id))
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'success': True, 'data': get_notification_settings(user_id)})
        except Exception as e:
            print(f"Error updating notification settings: {e}")
            conn.close()
            return jsonify({'success': False, 'message': 'Failed to update notification settings'}), 500

    @app.route('/api/system/info', methods=['GET', 'OPTIONS'])
    def system_info():
        if request.method == 'OPTIONS':
            return '', 200
        return jsonify({'success': True, 'data': get_system_info()})
    
    @app.route('/api/settings/<int:user_id>', methods=['GET', 'OPTIONS'])
    def get_user_settings(user_id):
        if request.method == 'OPTIONS':
            return '', 200
        settings = get_all_settings(user_id)
        return jsonify({'success': True, 'data': settings})
    
    @app.route('/api/settings/<int:user_id>/<setting_key>', methods=['GET', 'OPTIONS'])
    def get_user_setting(user_id, setting_key):
        if request.method == 'OPTIONS':
            return '', 200
        value = get_setting(user_id, setting_key)
        if value is not None:
            return jsonify({'success': True, 'data': {setting_key: value}})
        else:
            return jsonify({'success': False, 'message': 'Setting not found'}), 404
    
    @app.route('/api/settings/<int:user_id>/<setting_key>', methods=['PUT', 'OPTIONS'])
    def update_user_setting(user_id, setting_key):
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        setting_value = payload.get('value')
        setting_type = payload.get('type', 'preference')
        if setting_value is None:
            return jsonify({'success': False, 'message': 'Setting value is required'}), 400
        success = save_setting(user_id, setting_key, setting_value, setting_type)
        if success:
            return jsonify({'success': True, 'data': {setting_key: setting_value}})
        else:
            return jsonify({'success': False, 'message': 'Failed to save setting'}), 500
    
    @app.route('/api/settings/<int:user_id>', methods=['POST', 'OPTIONS'])
    def save_user_settings(user_id):
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        settings = payload.get('settings', {})
        if not settings:
            return jsonify({'success': False, 'message': 'Settings data is required'}), 400
        saved_settings = {}
        for key, value in settings.items():
            setting_type = value.get('type', 'preference') if isinstance(value, dict) else 'preference'
            actual_value = value.get('value') if isinstance(value, dict) else value
            success = save_setting(user_id, key, actual_value, setting_type)
            if success:
                saved_settings[key] = actual_value
        return jsonify({'success': True, 'data': saved_settings})


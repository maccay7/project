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
        user_id = request.args.get('user_id', 1)
        return jsonify({'success': True, 'data': get_user_profile(user_id)})

    @app.route('/api/user/preferences', methods=['GET', 'OPTIONS'])
    def preferences():
        if request.method == 'OPTIONS':
            return '', 200
        user_id = request.args.get('user_id', 1)
        return jsonify({'success': True, 'data': get_user_preferences(user_id)})

    @app.route('/api/user/notifications/settings', methods=['GET', 'OPTIONS'])
    def notifications_settings():
        if request.method == 'OPTIONS':
            return '', 200
        user_id = request.args.get('user_id', 1)
        return jsonify({'success': True, 'data': get_notification_settings(user_id)})

    @app.route('/api/system/info', methods=['GET', 'OPTIONS'])
    def system_info():
        if request.method == 'OPTIONS':
            return '', 200
        return jsonify({'success': True, 'data': get_system_info()})

    @app.route('/api/user/profile', methods=['PUT', 'OPTIONS'])
    def update_profile():
        if request.method == 'OPTIONS':
            return '', 200
        data = request.get_json()
        user_id = data.get('user_id', 1)
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        email = data.get('email')
        
        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'DB error'}), 500
        try:
            cursor = conn.cursor()
            if first_name or last_name or email:
                update_fields = []
                params = []
                if first_name:
                    update_fields.append('first_name = %s')
                    params.append(first_name)
                if last_name:
                    update_fields.append('last_name = %s')
                    params.append(last_name)
                if email:
                    update_fields.append('email = %s')
                    params.append(email)
                params.append(user_id)
                
                cursor.execute(f"UPDATE users SET {', '.join(update_fields)} WHERE id = %s", params)
                conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'success': True, 'data': get_user_profile(user_id)})
        except Exception as e:
            print(f"Error updating profile: {e}")
            conn.close()
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/user/preferences', methods=['PUT', 'OPTIONS'])
    def update_preferences():
        if request.method == 'OPTIONS':
            return '', 200
        data = request.get_json()
        user_id = data.get('user_id', 1)
        
        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'DB error'}), 500
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_preferences (user_id, language, timezone, date_format, currency, email_notifications, push_notifications, weekly_reports, system_alerts)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    language = VALUES(language),
                    timezone = VALUES(timezone),
                    date_format = VALUES(date_format),
                    currency = VALUES(currency),
                    email_notifications = VALUES(email_notifications),
                    push_notifications = VALUES(push_notifications),
                    weekly_reports = VALUES(weekly_reports),
                    system_alerts = VALUES(system_alerts)
            """, (
                user_id,
                data.get('language', 'English'),
                data.get('timezone', 'GMT+2'),
                data.get('dateFormat', 'DD/MM/YYYY'),
                data.get('currency', 'USD'),
                data.get('emailNotifications', True),
                data.get('pushNotifications', False),
                data.get('weeklyReports', True),
                data.get('systemAlerts', True)
            ))
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'success': True, 'data': get_user_preferences(user_id)})
        except Exception as e:
            print(f"Error updating preferences: {e}")
            conn.close()
            return jsonify({'success': False, 'message': str(e)}), 500
    
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
    
    @app.route('/api/settings/fred', methods=['POST', 'OPTIONS'])
    def save_fred_settings():
        if request.method == 'OPTIONS':
            return '', 200
        try:
            data = request.get_json()
            user_id = data.get('user_id')
            country = data.get('country', 'US')
            currency = data.get('currency', 'USD')
            maturity = data.get('maturity', '1Y')
            
            if not user_id:
                return jsonify({'success': False, 'error': 'user_id is required'}), 400
            
            settings_value = {'country': country, 'currency': currency, 'maturity': maturity}
            success = save_setting(user_id, 'fred_preferences', settings_value, 'preference')
            
            if success:
                return jsonify({'success': True, 'data': settings_value})
            else:
                return jsonify({'success': False, 'error': 'Failed to save FRED settings'}), 500
        except Exception as e:
            print(f"Error saving FRED settings: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/settings/fred', methods=['GET', 'OPTIONS'])
    def load_fred_settings():
        if request.method == 'OPTIONS':
            return '', 200
        try:
            user_id = request.args.get('user_id')
            
            if not user_id:
                return jsonify({'success': False, 'error': 'user_id is required'}), 400
            
            settings = get_setting(user_id, 'fred_preferences')
            
            if settings:
                return jsonify({'success': True, 'data': settings})
            else:
                return jsonify({'success': True, 'data': {'country': 'US', 'currency': 'USD', 'maturity': '1Y'}})
        except Exception as e:
            print(f"Error loading FRED settings: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
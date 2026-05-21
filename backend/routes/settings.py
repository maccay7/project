from flask import request, jsonify
from pages.settings_details import (
    get_user_profile,
    get_user_preferences,
    get_notification_settings,
    get_system_info
)


def settings_routes(app):
    @app.route('/api/user/profile', methods=['GET', 'OPTIONS'])
    def profile():
        if request.method == 'OPTIONS':
            return '', 200
        return jsonify({'success': True, 'data': get_user_profile()})

    @app.route('/api/user/preferences', methods=['GET', 'OPTIONS'])
    def preferences():
        if request.method == 'OPTIONS':
            return '', 200
        return jsonify({'success': True, 'data': get_user_preferences()})

    @app.route('/api/user/notifications/settings', methods=['GET', 'OPTIONS'])
    def notifications_settings():
        if request.method == 'OPTIONS':
            return '', 200
        return jsonify({'success': True, 'data': get_notification_settings()})

    @app.route('/api/system/info', methods=['GET', 'OPTIONS'])
    def system_info():
        if request.method == 'OPTIONS':
            return '', 200
        return jsonify({'success': True, 'data': get_system_info()})

from flask import request, jsonify
from pages.dashboard_details import (
    get_kpi,
    get_recent_activity,
    get_dashboard_charts,
    get_yield_curve
)


def dashboard_routes(app):
    @app.route('/api/dashboard/kpi', methods=['GET', 'OPTIONS'])
    def dashboard_kpi():
        if request.method == 'OPTIONS':
            return '', 200
        return jsonify({'success': True, 'data': get_kpi()})

    @app.route('/api/dashboard/recent-activity', methods=['GET', 'OPTIONS'])
    def dashboard_recent_activity():
        if request.method == 'OPTIONS':
            return '', 200
        return jsonify({'success': True, 'data': get_recent_activity()})

    @app.route('/api/dashboard/charts', methods=['GET', 'OPTIONS'])
    def dashboard_charts():
        if request.method == 'OPTIONS':
            return '', 200
        return jsonify({'success': True, 'data': get_dashboard_charts()})

    @app.route('/api/fred-yield-curve', methods=['GET', 'OPTIONS'])
    def fred_yield_curve():
        if request.method == 'OPTIONS':
            return '', 200
        instrument_type = request.args.get('instrument_type', 'all')
        return jsonify({'success': True, 'data': get_yield_curve(instrument_type)})

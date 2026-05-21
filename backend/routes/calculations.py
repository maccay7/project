import json
from flask import request, jsonify
from pages.calculations_details import calculate_data
from utils.db import get_db


def save_calculation(instrument_type, input_data, result_data):
    conn = get_db()
    if not conn:
        return
    try:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO calculations (instrument_type, input_data, result_data, calculation_status) VALUES (%s, %s, %s, %s)',
            (instrument_type, json.dumps(input_data), json.dumps(result_data), 'completed')
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception:
        pass


def get_history():
    conn = get_db()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT id, instrument_type, calculation_status, created_at FROM calculations ORDER BY created_at DESC LIMIT 20')
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [
            {
                'id': row.get('id'),
                'instrument_type': row.get('instrument_type'),
                'status': row.get('calculation_status'),
                'created_at': row.get('created_at').isoformat() if row.get('created_at') else None
            }
            for row in rows
        ]
    except Exception:
        return []


def calculations_routes(app):
    @app.route('/api/calculations/execute', methods=['POST', 'OPTIONS'])
    def execute_calculations():
        if request.method == 'OPTIONS':
            return '', 200

        payload = request.get_json() or {}
        instrument_type = payload.get('instrument_type', 'treasury_bills')
        data = payload.get('data', [])
        calculations = calculate_data(data, instrument_type)
        save_calculation(instrument_type, data, calculations)
        return jsonify({'success': True, 'calculations': calculations})

    @app.route('/api/calculations/history', methods=['GET', 'OPTIONS'])
    def calculations_history():
        if request.method == 'OPTIONS':
            return '', 200
        return jsonify({'success': True, 'data': get_history()})

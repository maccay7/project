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
    except Exception as e:
        print(f"Save calculation error: {e}")

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
                'id': row['id'],
                'instrument_type': row['instrument_type'],
                'status': row['calculation_status'],
                'created_at': row['created_at'].isoformat() if row['created_at'] else None
            }
            for row in rows
        ]
    except Exception as e:
        print(f"Get history error: {e}")
        return []

def calculations_routes(app):
    @app.route('/api/calculate/<instrument_type>', methods=['POST', 'OPTIONS'])
    def calculate_endpoint(instrument_type):
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        data = payload.get('data', [])
        if not isinstance(data, list):
            return jsonify({'success': False, 'message': 'Data must be an array'}), 400
        type_map = {
            'money-market': 'money-market',
            'bonds': 'bonds',
            'tbills': 'tbills'
        }
        inst_type = type_map.get(instrument_type, 'tbills')
        try:
            result = calculate_data(data, inst_type)
            save_calculation(instrument_type, data, result)
            return jsonify({'success': True, 'data': result})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/calculations/history', methods=['GET', 'OPTIONS'])
    def calculations_history():
        if request.method == 'OPTIONS':
            return '', 200
        return jsonify({'success': True, 'data': get_history()})

    # Legacy endpoint
    @app.route('/api/calculate', methods=['POST', 'OPTIONS'])
    def calculate_legacy():
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        data = payload.get('data', [])
        instrument_type = payload.get('instrument_type', 'tbills')
        try:
            result = calculate_data(data, instrument_type)
            save_calculation(instrument_type, data, result)
            return jsonify({'success': True, 'data': result})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
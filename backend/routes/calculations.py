import json
from flask import request, jsonify
from pages.calculations_details import calculate_data
from utils.db import get_db


def normalize_instrument_type(instrument_type):
    if not instrument_type:
        return 'tbills'
    normalized = instrument_type.lower().replace('_', '-').strip()
    mapping = {
        'treasury-bills': 'tbills',
        'treasury_bills': 'tbills',
        'treasury bills': 'tbills',
        'tbills': 'tbills',
        't-bills': 'tbills',
        'bonds': 'bonds',
        'money-market': 'money-market',
        'money_market': 'money-market',
        'money market': 'money-market'
    }
    return mapping.get(normalized, normalized)

def save_calculation(instrument_type, input_data, result_data, dataset_id=None):
    conn = get_db()
    if not conn:
        return
    try:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO calculations (instrument_type, dataset_id, input_data, result_data, calculation_status) VALUES (%s, %s, %s, %s, %s)',
            (instrument_type, dataset_id, json.dumps(input_data), json.dumps(result_data), 'completed')
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
        cursor.execute('SELECT id, instrument_type, dataset_id, calculation_status, created_at FROM calculations ORDER BY created_at DESC LIMIT 20')
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [
            {
                'id': row['id'],
                'instrument_type': row['instrument_type'],
                'dataset_id': row['dataset_id'],
                'status': row['calculation_status'],
                'created_at': row['created_at'].isoformat() if row['created_at'] else None
            }
            for row in rows
        ]
    except Exception as e:
        print(f"Get history error: {e}")
        return []


def get_latest_calculation(dataset_id=None):
    conn = get_db()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        if dataset_id:
            cursor.execute('SELECT * FROM calculations WHERE dataset_id = %s ORDER BY created_at DESC LIMIT 1', (dataset_id,))
        else:
            cursor.execute('SELECT * FROM calculations ORDER BY created_at DESC LIMIT 1')
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if not row:
            return None
        result_data = row.get('result_data')
        try:
            result_data = json.loads(result_data) if isinstance(result_data, str) else result_data
        except Exception:
            result_data = None
        return {
            'id': row.get('id'),
            'instrument_type': row.get('instrument_type'),
            'dataset_id': row.get('dataset_id'),
            'result_data': result_data,
            'status': row.get('calculation_status'),
            'created_at': row.get('created_at').isoformat() if row.get('created_at') else None
        }
    except Exception as e:
        print(f"Get latest calculation error: {e}")
        return None


def calculations_routes(app):
    @app.route('/api/calculate/<instrument_type>', methods=['POST', 'OPTIONS'])
    def calculate_endpoint(instrument_type):
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        data = payload.get('data', [])
        if not isinstance(data, list):
            return jsonify({'success': False, 'message': 'Data must be an array'}), 400
        inst_type = normalize_instrument_type(instrument_type)
        dataset_id = payload.get('dataset_id')
        try:
            result = calculate_data(data, inst_type)
            save_calculation(instrument_type, data, result, dataset_id)
            return jsonify({'success': True, 'data': result})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/calculations/history', methods=['GET', 'OPTIONS'])
    def calculations_history():
        if request.method == 'OPTIONS':
            return '', 200
        return jsonify({'success': True, 'data': get_history()})

    @app.route('/api/calculations/latest', methods=['GET', 'OPTIONS'])
    def calculations_latest():
        if request.method == 'OPTIONS':
            return '', 200
        dataset_id = request.args.get('dataset_id')
        latest = get_latest_calculation(dataset_id)
        if not latest:
            return jsonify({'success': False, 'message': 'Calculation not found'}), 404
        return jsonify({'success': True, 'data': latest})

    # Legacy endpoint
    @app.route('/api/calculate', methods=['POST', 'OPTIONS'])
    def calculate_legacy():
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        data = payload.get('data', [])
        instrument_type = normalize_instrument_type(payload.get('instrument_type', 'tbills'))
        dataset_id = payload.get('dataset_id')
        try:
            result = calculate_data(data, instrument_type)
            save_calculation(instrument_type, data, result, dataset_id)
            return jsonify({'success': True, 'data': result})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
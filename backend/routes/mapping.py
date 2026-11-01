import json
from contextlib import contextmanager
from flask import request, jsonify
from utils.db import get_db
from utils.auth import resolve_current_user, session_is_owned
from utils.excel_parser import parse_full_workbook


@contextmanager
def _db():
    conn = get_db()
    cursor = None
    if conn:
        try:
            cursor = conn.cursor()
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            conn = None
    try:
        yield conn, cursor
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def _decode_mapping_row(row):
    return {
        'id': row['id'],
        'dataset_id': row['dataset_id'],
        'instrument_type': row['instrument_type'],
        'column_mapping': json.loads(row['column_mapping']) if row['column_mapping'] else {},
        'file_columns': json.loads(row['file_columns']) if row['file_columns'] else [],
        'required_columns': json.loads(row['required_columns']) if row['required_columns'] else [],
        'mapping_type': row['mapping_type'],
        'applied_at': row['applied_at'].isoformat() if row['applied_at'] else None,
    }


def create_mapping_table():
    with _db() as (conn, cursor):
        if not conn:
            return False
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS column_mappings (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    dataset_id INT NOT NULL,
                    instrument_type VARCHAR(50) NOT NULL,
                    column_mapping JSON NOT NULL,
                    file_columns JSON,
                    required_columns JSON,
                    mapping_type VARCHAR(50) DEFAULT 'manual',
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_dataset_id (dataset_id)
                )
            """)
            conn.commit()
            return True
        except Exception as e:
            print(f"Error creating column_mappings table: {e}")
            return False


def save_mapping(dataset_id, instrument_type, column_mapping, file_columns,
                 required_columns, mapping_type='manual'):
    with _db() as (conn, cursor):
        if not conn:
            return None
        try:
            cursor.execute(
                """INSERT INTO column_mappings
                   (dataset_id, instrument_type, column_mapping, file_columns,
                    required_columns, mapping_type)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (dataset_id, instrument_type, json.dumps(column_mapping),
                 json.dumps(file_columns), json.dumps(required_columns), mapping_type)
            )
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"Error saving mapping: {e}")
            return None


def get_mapping_by_dataset(dataset_id):
    with _db() as (conn, cursor):
        if not conn:
            return None
        try:
            cursor.execute(
                "SELECT * FROM column_mappings WHERE dataset_id = %s "
                "ORDER BY applied_at DESC LIMIT 1",
                (dataset_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            return _decode_mapping_row(row)
        except Exception as e:
            print(f"Error getting mapping: {e}")
            return None


def _authenticated_user():
    user_id, auth_error = resolve_current_user()
    if auth_error:
        status, message = auth_error
        return None, (jsonify({'success': False, 'message': message}), status)
    return user_id, None


def _load_owned_dataset_data(dataset_id, user_id):
    with _db() as (conn, cursor):
        if not conn:
            raise RuntimeError('Database unavailable')
        cursor.execute(
            """SELECT name, data, headers, file_path, instrument_type
               FROM datasets WHERE id = %s AND user_id = %s LIMIT 1""",
            (dataset_id, user_id)
        )
        dataset = cursor.fetchone()
    if not dataset:
        return None

    data = dataset.get('data')
    if isinstance(data, str):
        data = json.loads(data)
    if isinstance(data, list) and data:
        headers = dataset.get('headers')
        if isinstance(headers, str):
            headers = json.loads(headers)
        return {'data': data, 'headers': headers or []}

    from routes.dataset import _absolute_upload_path
    file_path = _absolute_upload_path(dataset.get('file_path'))
    if not file_path:
        return {'data': [], 'headers': []}
    parsed = parse_full_workbook(file_path, dataset.get('instrument_type'), max_rows=None)
    rows = [
        row
        for sheet in parsed.get('sheets', [])
        for row in sheet.get('data', [])
        if isinstance(row, dict)
    ]
    return {'data': rows, 'headers': list(rows[0]) if rows else []}


def apply_column_mapping(data, column_mapping):
    if not data or not column_mapping:
        return data

    mapped_data = []
    for row in data:
        mapped_row = {}
        for target_col, source_col in column_mapping.items():
            if source_col and source_col in row:
                mapped_row[target_col] = row[source_col]
        for key, value in row.items():
            if key not in column_mapping.values():
                mapped_row[key] = value
        mapped_data.append(mapped_row)

    return mapped_data


def mapping_routes(app):
    create_mapping_table()

    @app.route('/api/mapping/auto-match', methods=['POST', 'OPTIONS'])
    def auto_match_mapping():
        if request.method == 'OPTIONS':
            return '', 200
        _, auth_response = _authenticated_user()
        if auth_response:
            return auth_response

        payload = request.get_json() or {}
        file_columns = payload.get('file_columns', [])
        required_columns = payload.get('required_columns', [])

        from routes.data_processing import auto_match_columns

        mapping = auto_match_columns(file_columns, required_columns)

        return jsonify({
            'success': True,
            'data': mapping
        })

    @app.route('/api/mapping/apply', methods=['POST', 'OPTIONS'])
    def apply_mapping():
        if request.method == 'OPTIONS':
            return '', 200
        user_id, auth_response = _authenticated_user()
        if auth_response:
            return auth_response

        payload = request.get_json() or {}
        dataset_id = payload.get('dataset_id')
        instrument_type = payload.get('instrument_type')
        column_mapping = payload.get('column_mapping', {})
        file_columns = payload.get('file_columns', [])
        required_columns = payload.get('required_columns', [])
        mapping_type = payload.get('mapping_type', 'manual')
        session_id = payload.get('session_id')

        if not dataset_id or not instrument_type:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        with _db() as (conn, cursor):
            if not conn:
                return jsonify({'success': False, 'message': 'Database unavailable'}), 503
            try:
                cursor.execute(
                    "SELECT id FROM datasets WHERE id = %s AND user_id = %s LIMIT 1",
                    (dataset_id, user_id)
                )
                if not cursor.fetchone():
                    return jsonify({'success': False, 'message': 'Dataset not found'}), 404
                if session_id and not session_is_owned(cursor, session_id, user_id):
                    return jsonify({'success': False, 'message': 'Session not found'}), 404
            except Exception as error:
                return jsonify({'success': False, 'message': str(error)}), 500

        mapping_id = save_mapping(dataset_id, instrument_type, column_mapping,
                                  file_columns, required_columns, mapping_type)

        if not mapping_id:
            return jsonify({'success': False, 'message': 'Failed to save mapping'}), 500

        try:
            from routes.calculations import calculate_data, normalize_instrument_type, save_calculation

            dataset_data = _load_owned_dataset_data(dataset_id, user_id)
            if dataset_data and dataset_data.get('data'):
                mapped_data = apply_column_mapping(dataset_data['data'], column_mapping)
                inst_type = normalize_instrument_type(instrument_type)
                calc_result = calculate_data(mapped_data, inst_type)

                saved_calculation_id = save_calculation(
                    inst_type,
                    {'data': mapped_data, 'column_mapping': column_mapping},
                    calc_result,
                    dataset_id=dataset_id,
                    session_id=session_id
                )
                if not saved_calculation_id:
                    return jsonify({'success': False, 'message': 'Calculation could not be saved'}), 500

                return jsonify({
                    'success': True,
                    'data': {
                        'mapping_id': mapping_id,
                        'column_mapping': column_mapping,
                        'calculations': calc_result
                    }
                })
        except Exception as e:
            print(f"Auto-calculation after mapping failed: {e}")
            return jsonify({'success': False, 'message': 'Mapping saved, but calculation failed'}), 500

        return jsonify({'success': False, 'message': 'Dataset contains no calculable rows'}), 422

    @app.route('/api/mapping/dataset/<int:dataset_id>', methods=['GET', 'OPTIONS'])
    def get_dataset_mapping(dataset_id):
        if request.method == 'OPTIONS':
            return '', 200
        user_id, auth_response = _authenticated_user()
        if auth_response:
            return auth_response
        with _db() as (conn, cursor):
            if not conn:
                return jsonify({'success': False, 'message': 'Database unavailable'}), 503
            try:
                cursor.execute(
                    "SELECT id FROM datasets WHERE id = %s AND user_id = %s LIMIT 1",
                    (dataset_id, user_id)
                )
                if not cursor.fetchone():
                    return jsonify({'success': False, 'message': 'Dataset not found'}), 404
            except Exception as error:
                return jsonify({'success': False, 'message': str(error)}), 500

        mapping = get_mapping_by_dataset(dataset_id)

        if mapping:
            return jsonify({'success': True, 'data': mapping})
        return jsonify({'success': False, 'message': 'Mapping not found'}), 404

    @app.route('/api/mapping/validate', methods=['POST', 'OPTIONS'])
    def validate_mapping():
        if request.method == 'OPTIONS':
            return '', 200
        _, auth_response = _authenticated_user()
        if auth_response:
            return auth_response

        payload = request.get_json() or {}
        column_mapping = payload.get('column_mapping', {})
        required_columns = payload.get('required_columns', [])

        missing_columns = [col for col in required_columns
                           if col not in column_mapping or not column_mapping[col]]

        return jsonify({
            'success': True,
            'data': {
                'valid': len(missing_columns) == 0,
                'missing_columns': missing_columns,
                'mapped_columns': list(column_mapping.keys())
            }
        })
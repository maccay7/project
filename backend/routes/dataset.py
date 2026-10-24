import json
import mimetypes
import os
import uuid
import traceback
from contextlib import contextmanager
from datetime import datetime
from flask import request, jsonify, send_file
from utils.db import get_db
from utils.excel_parser import parse_full_workbook

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'xlsm', 'csv'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


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


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def create_dataset_table():
    with _db() as (conn, cursor):
        if not conn:
            return False
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS datasets (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    file_name VARCHAR(255) NOT NULL,
                    original_file_name VARCHAR(255) NOT NULL,
                    file_path VARCHAR(512) NOT NULL,
                    file_size BIGINT,
                    instrument_type VARCHAR(50),
                    sheet_count INT,
                    row_count INT,
                    column_count INT,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_id INT,
                    session_id INT,
                    status VARCHAR(50) DEFAULT 'uploaded',
                    metadata JSON,
                    UNIQUE KEY unique_file_path (file_path)
                )
            """)
            conn.commit()
            return True
        except Exception as e:
            print(f"Error creating datasets table: {e}")
            return False


def _safe_json_dumps(obj):
    if obj is None:
        return None
    try:
        return json.dumps(obj, default=str)
    except Exception:
        try:
            return json.dumps(str(obj))
        except Exception:
            return None


def save_dataset_metadata(file_name, original_name, file_path, file_size, instrument_type,
                          sheet_count, row_count, column_count,
                          user_id=None, session_id=None, metadata=None):
    with _db() as (conn, cursor):
        if not conn:
            return None
        try:
            cursor.execute(
                """INSERT INTO datasets
                   (file_name, original_file_name, file_path, file_size, instrument_type,
                    sheet_count, row_count, column_count, user_id, session_id, metadata)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (file_name, original_name, file_path, file_size, instrument_type,
                 sheet_count, row_count, column_count, user_id, session_id,
                 _safe_json_dumps(metadata))
            )
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"Error saving dataset metadata: {e}")
            traceback.print_exc()
            return None


def intelligent_parse(file_path, instrument_type):
    parsed = parse_full_workbook(file_path, instrument_type, max_rows=None)
    warnings = parsed.get('warnings', [])
    metadata = parsed.get('metadata', {})

    extracted_data = []
    for sheet in parsed.get('sheets', []):
        for row in sheet.get('data', []):
            if isinstance(row, dict):
                extracted_data.append(row)

    return {
        'data': extracted_data,
        'warnings': warnings,
        'metadata': metadata,
        'sheets': parsed.get('sheets', [])
    }


def _parse_workbook_safely(file_path, instrument_type):
    try:
        parsed = parse_full_workbook(file_path, instrument_type, max_rows=None)
        sheet_count = len(parsed.get('sheets', []))
        total_rows = sum(s.get('total_rows', 0) for s in parsed.get('sheets', []))
        total_columns = max((s.get('total_columns', 0) for s in parsed.get('sheets', [])), default=0)
        sheet_names = [s.get('name') for s in parsed.get('sheets', []) if s.get('name')]
        warnings = list(parsed.get('warnings', []) or [])
        return {
            'ok': True,
            'sheet_count': sheet_count,
            'total_rows': total_rows,
            'total_columns': total_columns,
            'sheet_names': sheet_names,
            'warnings': warnings
        }
    except Exception as parse_err:
        err_msg = f"{type(parse_err).__name__}: {parse_err}"
        print(f"[dataset/upload] parse_full_workbook failed for {file_path}: {err_msg}")
        traceback.print_exc()
        return {
            'ok': False,
            'sheet_count': 0,
            'total_rows': 0,
            'total_columns': 0,
            'sheet_names': [],
            'warnings': [f"Parse failed: {err_msg}"]
        }


def _resolve_file_row(dataset_id):
    with _db() as (conn, cursor):
        if not conn:
            return None, None
        try:
            cursor.execute(
                "SELECT file_path, original_file_name FROM datasets WHERE id = %s",
                (dataset_id,)
            )
            row = cursor.fetchone()
        except Exception:
            traceback.print_exc()
            return None, None

    if not row:
        return None, None
    if isinstance(row, dict):
        return row.get('file_path'), row.get('original_file_name')
    return row[0], row[1]


def dataset_routes(app):
    create_dataset_table()

    @app.route('/api/dataset/upload', methods=['POST', 'OPTIONS'])
    def upload_dataset():
        if request.method == 'OPTIONS':
            return '', 200

        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file provided'}), 400

        file = request.files['file']
        instrument_type = request.form.get('instrument_type') or None
        user_id = request.form.get('user_id')
        session_id = request.form.get('session_id')

        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'success': False, 'message': 'Invalid file type. Only Excel files allowed.'}), 400

        file_ext = file.filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{file_ext}"
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)

        try:
            file.save(file_path)
            file_size = os.path.getsize(file_path)
        except Exception as save_err:
            traceback.print_exc()
            return jsonify({'success': False, 'message': f'Failed to save file: {str(save_err)}'}), 500

        parse_result = _parse_workbook_safely(file_path, instrument_type)

        metadata = {
            'sheet_count': parse_result['sheet_count'],
            'sheet_names': parse_result['sheet_names'],
            'total_rows': parse_result['total_rows'],
            'total_columns': parse_result['total_columns'],
            'parse_warnings': parse_result['warnings']
        }

        try:
            dataset_id = save_dataset_metadata(
                unique_filename,
                file.filename,
                file_path,
                file_size,
                instrument_type,
                parse_result['sheet_count'],
                parse_result['total_rows'],
                parse_result['total_columns'],
                user_id,
                session_id,
                metadata
            )
        except Exception as meta_err:
            traceback.print_exc()
            # B5 FIX — cleanup the orphaned file if metadata insert raises
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass
            return jsonify({'success': False, 'message': f'Metadata save failed: {str(meta_err)}'}), 500

        if not dataset_id:
            # B5 FIX — cleanup the orphaned file if metadata insert returned None
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass
            return jsonify({'success': False, 'message': 'Failed to save dataset metadata'}), 500

        return jsonify({
            'success': True,
            'data': {
                'dataset_id': dataset_id,
                'file_name': file.filename,
                'file_size': file_size,
                'instrument_type': instrument_type,
                'metadata': metadata,
                'warnings': parse_result['warnings']
            }
        })

    @app.route('/api/dataset/<int:dataset_id>/parse', methods=['GET', 'OPTIONS'])
    def parse_dataset(dataset_id):
        if request.method == 'OPTIONS':
            return '', 200

        with _db() as (conn, cursor):
            if not conn:
                return jsonify({'success': False, 'message': 'Database error'}), 500
            try:
                cursor.execute("SELECT * FROM datasets WHERE id = %s", (dataset_id,))
                dataset = cursor.fetchone()
            except Exception as e:
                traceback.print_exc()
                return jsonify({'success': False, 'message': str(e)}), 500

        if not dataset:
            return jsonify({'success': False, 'message': 'Dataset not found'}), 404

        file_path = dataset['file_path']
        instrument_type = dataset['instrument_type']

        if not os.path.exists(file_path):
            return jsonify({'success': False, 'message': 'File not found on server'}), 404

        try:
            parsed = parse_full_workbook(file_path, instrument_type, max_rows=None)
            return jsonify({'success': True, 'data': parsed})
        except Exception as e:
            traceback.print_exc()
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/dataset/<int:dataset_id>/intelligent-parse', methods=['GET', 'OPTIONS'])
    def intelligent_parse_dataset(dataset_id):
        if request.method == 'OPTIONS':
            return '', 200

        with _db() as (conn, cursor):
            if not conn:
                return jsonify({'success': False, 'message': 'Database error'}), 500
            try:
                cursor.execute("SELECT * FROM datasets WHERE id = %s", (dataset_id,))
                dataset = cursor.fetchone()
            except Exception as e:
                traceback.print_exc()
                return jsonify({'success': False, 'message': str(e)}), 500

        if not dataset:
            return jsonify({'success': False, 'message': 'Dataset not found'}), 404

        file_path = dataset['file_path']
        instrument_type = dataset['instrument_type']

        if not os.path.exists(file_path):
            return jsonify({'success': False, 'message': 'File not found on server'}), 404

        try:
            result = intelligent_parse(file_path, instrument_type)
            return jsonify({'success': True, 'data': result})
        except Exception as e:
            traceback.print_exc()
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/dataset/<int:dataset_id>', methods=['DELETE', 'OPTIONS'])
    def delete_dataset(dataset_id):
        if request.method == 'OPTIONS':
            return '', 200

        with _db() as (conn, cursor):
            if not conn:
                return jsonify({'success': False, 'message': 'Database error'}), 500
            try:
                cursor.execute("SELECT file_path FROM datasets WHERE id = %s", (dataset_id,))
                dataset = cursor.fetchone()

                if dataset:
                    file_path = dataset['file_path']
                    if os.path.exists(file_path):
                        os.remove(file_path)

                    cursor.execute("DELETE FROM datasets WHERE id = %s", (dataset_id,))
                    conn.commit()

                return jsonify({'success': True, 'message': 'Dataset deleted'})
            except Exception as e:
                traceback.print_exc()
                return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/save-dataset', methods=['POST', 'OPTIONS'])
    def save_dataset():
        if request.method == 'OPTIONS':
            return '', 200

        try:
            data = request.get_json()
            name = data.get('name')
            file_base64 = data.get('file_base64', '')
            sheet_names = data.get('sheet_names', [])
            upload_id = data.get('upload_id')
            payload_data = data.get('data')
            headers = data.get('headers')
            instrument_type = data.get('instrument_type') or None

            if upload_id:
                with _db() as (conn, cursor):
                    if not conn:
                        return jsonify({'success': False, 'message': 'Database error'}), 500
                    try:
                        cursor.execute("SELECT * FROM datasets WHERE id = %s", (upload_id,))
                        existing = cursor.fetchone()

                        if existing:
                            metadata = existing.get('metadata', {})
                            if isinstance(metadata, str):
                                metadata = json.loads(metadata)

                            metadata['data'] = payload_data
                            metadata['headers'] = headers
                            metadata['updated_at'] = datetime.now().isoformat()

                            cursor.execute(
                                "UPDATE datasets SET metadata = %s WHERE id = %s",
                                (_safe_json_dumps(metadata), upload_id)
                            )
                            conn.commit()

                            return jsonify({
                                'success': True,
                                'data': {'id': upload_id, 'name': name}
                            })
                    except Exception as e:
                        traceback.print_exc()
                        return jsonify({'success': False, 'message': str(e)}), 500

            with _db() as (conn, cursor):
                if not conn:
                    return jsonify({'success': False, 'message': 'Database error'}), 500
                try:
                    metadata = {
                        'data': payload_data,
                        'headers': headers,
                        'sheet_names': sheet_names,
                        'instrument_type': instrument_type,
                        'created_at': datetime.now().isoformat()
                    }

                    cursor.execute(
                        """INSERT INTO datasets
                           (file_name, original_file_name, file_path, file_size,
                            instrument_type, sheet_count, row_count, column_count, metadata)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (name, name, '', 0, instrument_type,
                         len(sheet_names) if sheet_names else 1,
                         len(payload_data) if payload_data else 0,
                         len(headers) if headers else 0,
                         _safe_json_dumps(metadata))
                    )
                    conn.commit()
                    dataset_id = cursor.lastrowid

                    return jsonify({
                        'success': True,
                        'data': {'id': dataset_id, 'name': name}
                    })
                except Exception as e:
                    traceback.print_exc()
                    return jsonify({'success': False, 'message': str(e)}), 500

        except Exception as e:
            traceback.print_exc()
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/get-datasets', methods=['GET', 'OPTIONS'])
    def get_datasets():
        if request.method == 'OPTIONS':
            return '', 200

        with _db() as (conn, cursor):
            if not conn:
                return jsonify({'success': False, 'message': 'Database error'}), 500
            try:
                cursor.execute(
                    "SELECT id, original_file_name, file_size, instrument_type, "
                    "sheet_count, row_count, column_count, uploaded_at, metadata "
                    "FROM datasets ORDER BY uploaded_at DESC"
                )
                datasets = cursor.fetchall()
            except Exception as e:
                traceback.print_exc()
                return jsonify({'success': False, 'message': str(e)}), 500

        result = []
        for ds in datasets:
            metadata = ds.get('metadata', {})
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except Exception:
                    metadata = {}

            result.append({
                'id': ds['id'],
                'name': ds['original_file_name'],
                'rows': ds['row_count'],
                'file_size': ds['file_size'],
                'instrument_type': ds['instrument_type'],
                'sheet_count': ds['sheet_count'],
                'uploaded_at': ds['uploaded_at'].isoformat() if ds['uploaded_at'] else None,
                'headers': metadata.get('headers', []),
                'data': metadata.get('data', [])
            })

        return jsonify({'success': True, 'data': result})

    @app.route('/api/load-dataset', methods=['POST', 'OPTIONS'])
    def load_dataset():
        if request.method == 'OPTIONS':
            return '', 200

        try:
            data = request.get_json()
            dataset_id = data.get('dataset_id')

            if not dataset_id:
                return jsonify({'success': False, 'message': 'Dataset ID required'}), 400

            with _db() as (conn, cursor):
                if not conn:
                    return jsonify({'success': False, 'message': 'Database error'}), 500
                try:
                    cursor.execute("SELECT * FROM datasets WHERE id = %s", (dataset_id,))
                    dataset = cursor.fetchone()
                except Exception as e:
                    traceback.print_exc()
                    return jsonify({'success': False, 'message': str(e)}), 500

            if not dataset:
                return jsonify({'success': False, 'message': 'Dataset not found'}), 404

            metadata = dataset.get('metadata', {})
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except Exception:
                    metadata = {}

            if metadata.get('data') and metadata.get('headers'):
                return jsonify({
                    'success': True,
                    'data': {
                        'id': dataset['id'],
                        'name': dataset['original_file_name'],
                        'data': metadata['data'],
                        'headers': metadata['headers'],
                        'instrument_type': dataset['instrument_type']
                    }
                })

            file_path = dataset['file_path']
            if file_path and os.path.exists(file_path):
                instrument_type = dataset['instrument_type']
                parsed = intelligent_parse(file_path, instrument_type)

                return jsonify({
                    'success': True,
                    'data': {
                        'id': dataset['id'],
                        'name': dataset['original_file_name'],
                        'data': parsed['data'],
                        'headers': parsed.get('metadata', {}).get('headers', []),
                        'instrument_type': instrument_type
                    }
                })

            return jsonify({'success': False, 'message': 'No data available for this dataset'}), 404

        except Exception as e:
            traceback.print_exc()
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/delete-dataset', methods=['POST', 'OPTIONS'])
    def delete_dataset_post():
        if request.method == 'OPTIONS':
            return '', 200

        try:
            data = request.get_json()
            dataset_id = data.get('dataset_id')

            if not dataset_id:
                return jsonify({'success': False, 'message': 'Dataset ID required'}), 400

            with _db() as (conn, cursor):
                if not conn:
                    return jsonify({'success': False, 'message': 'Database error'}), 500
                try:
                    cursor.execute("SELECT file_path FROM datasets WHERE id = %s", (dataset_id,))
                    dataset = cursor.fetchone()

                    if dataset:
                        file_path = dataset['file_path']
                        if file_path and os.path.exists(file_path):
                            os.remove(file_path)

                        cursor.execute("DELETE FROM datasets WHERE id = %s", (dataset_id,))
                        conn.commit()

                    return jsonify({'success': True, 'message': 'Dataset deleted'})
                except Exception as e:
                    traceback.print_exc()
                    return jsonify({'success': False, 'message': str(e)}), 500

        except Exception as e:
            traceback.print_exc()
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/dataset/<int:dataset_id>/file', methods=['GET', 'OPTIONS'])
    def view_dataset_file(dataset_id):
        if request.method == 'OPTIONS':
            return '', 200

        file_path, original_name = _resolve_file_row(dataset_id)
        if file_path is None:
            return jsonify({'success': False, 'message': 'Dataset not found'}), 404
        if not file_path or not os.path.exists(file_path):
            return jsonify({'success': False, 'message': 'Original file missing on server'}), 404

        mime, _ = mimetypes.guess_type(original_name or file_path)
        return send_file(
            file_path,
            mimetype=mime or 'application/octet-stream',
            as_attachment=False,
            download_name=original_name or os.path.basename(file_path),
        )

    @app.route('/api/dataset/<int:dataset_id>/download', methods=['GET', 'OPTIONS'])
    def download_dataset_file(dataset_id):
        if request.method == 'OPTIONS':
            return '', 200

        file_path, original_name = _resolve_file_row(dataset_id)
        if file_path is None:
            return jsonify({'success': False, 'message': 'Dataset not found'}), 404
        if not file_path or not os.path.exists(file_path):
            return jsonify({'success': False, 'message': 'Original file missing on server'}), 404

        mime, _ = mimetypes.guess_type(original_name or file_path)
        return send_file(
            file_path,
            mimetype=mime or 'application/octet-stream',
            as_attachment=True,
            download_name=original_name or os.path.basename(file_path),
        )
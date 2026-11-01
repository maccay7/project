import json
import mimetypes
import os
import uuid
import traceback
from contextlib import contextmanager
from datetime import datetime
from flask import request, jsonify, send_file
from utils.db import get_db
from utils.auth import resolve_current_user, session_is_owned
from utils.excel_parser import parse_full_workbook

BACKEND_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
UPLOAD_FOLDER = os.path.join(BACKEND_FOLDER, 'uploads')
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
                    name VARCHAR(255),
                    file_base64 LONGTEXT,
                    data JSON,
                    headers JSON,
                    file_name VARCHAR(512),
                    original_file_name VARCHAR(255),
                    file_path VARCHAR(1024),
                    file_size BIGINT,
                    instrument_type VARCHAR(64),
                    sheet_count INT,
                    row_count INT,
                    column_count INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    user_id INT,
                    session_id VARCHAR(255),
                    status VARCHAR(50) DEFAULT 'uploaded',
                    metadata JSON,
                    INDEX idx_datasets_user_id (user_id),
                    INDEX idx_datasets_session_id (session_id),
                    CONSTRAINT fk_datasets_user FOREIGN KEY (user_id)
                        REFERENCES users(id) ON DELETE SET NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS upload_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    filename VARCHAR(255) NOT NULL,
                    file_type VARCHAR(50) NOT NULL,
                    file_size BIGINT NOT NULL,
                    upload_status ENUM('uploading', 'processing', 'completed', 'failed')
                        DEFAULT 'uploading',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_upload_history_user_id (user_id),
                    INDEX idx_upload_history_status (upload_status),
                    INDEX idx_upload_history_created_at (created_at),
                    CONSTRAINT fk_upload_history_user FOREIGN KEY (user_id)
                        REFERENCES users(id) ON DELETE CASCADE
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


def _decode_json_column(value, fallback):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return fallback
    return value if value is not None else fallback


def _absolute_upload_path(file_path):
    if not file_path:
        return None
    path = str(file_path)
    if not os.path.isabs(path):
        path = os.path.join(BACKEND_FOLDER, path)
    resolved = os.path.abspath(path)
    root = os.path.abspath(UPLOAD_FOLDER)
    try:
        inside_root = os.path.commonpath([resolved, root]) == root
    except ValueError:
        return None
    if not inside_root or resolved == root:
        return None
    return resolved


def _remove_upload_file(file_path):
    resolved = _absolute_upload_path(file_path)
    if not resolved or not os.path.isfile(resolved):
        return True
    try:
        os.remove(resolved)
        return True
    except OSError:
        traceback.print_exc()
        return False


def save_dataset_metadata(file_name, original_name, file_path, file_size, instrument_type,
                          sheet_count, row_count, column_count, upload_status='completed',
                          user_id=None, session_id=None, metadata=None):
    with _db() as (conn, cursor):
        if not conn:
            return None
        try:
            conn.begin()
            cursor.execute(
                """INSERT INTO datasets
                   (name, file_name, original_file_name, file_path, file_size, instrument_type,
                    sheet_count, row_count, column_count, user_id, session_id, data, headers, metadata)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (original_name, file_name, original_name, file_path, file_size, instrument_type,
                 sheet_count, row_count, column_count, user_id, session_id,
                 _safe_json_dumps(metadata.get('data') if isinstance(metadata, dict) else None),
                 _safe_json_dumps(metadata.get('headers') if isinstance(metadata, dict) else None),
                 _safe_json_dumps(metadata))
            )
            dataset_id = cursor.lastrowid
            cursor.execute(
                """INSERT INTO upload_history
                   (user_id, filename, file_type, file_size, upload_status)
                   VALUES (%s, %s, %s, %s, %s)""",
                (user_id, original_name, file_name.rsplit('.', 1)[-1].lower(),
                 file_size, upload_status)
            )
            conn.commit()
            return dataset_id
        except Exception as e:
            conn.rollback()
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


def _resolve_file_row(dataset_id, user_id):
    with _db() as (conn, cursor):
        if not conn:
            return None, None
        try:
            cursor.execute(
                "SELECT file_path, original_file_name FROM datasets "
                "WHERE id = %s AND user_id = %s",
                (dataset_id, user_id)
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


def _authenticated_user():
    user_id, auth_error = resolve_current_user()
    if auth_error:
        status, message = auth_error
        return None, (jsonify({'success': False, 'message': message}), status)
    return user_id, None


def _owned_dataset(cursor, dataset_id, user_id, fields='*'):
    cursor.execute(
        f'SELECT {fields} FROM datasets WHERE id = %s AND user_id = %s',
        (dataset_id, user_id)
    )
    return cursor.fetchone()


def dataset_routes(app):
    create_dataset_table()

    @app.route('/api/dataset/upload', methods=['POST', 'OPTIONS'])
    def upload_dataset():
        if request.method == 'OPTIONS':
            return '', 200
        user_id, auth_response = _authenticated_user()
        if auth_response:
            return auth_response

        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file provided'}), 400

        file = request.files['file']
        instrument_type = request.form.get('instrument_type') or None
        session_id = request.form.get('session_id')

        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'success': False, 'message': 'Invalid file type. Only Excel files allowed.'}), 400
        if session_id:
            with _db() as (conn, cursor):
                if not conn:
                    return jsonify({'success': False, 'message': 'Database error'}), 500
                try:
                    if not session_is_owned(cursor, session_id, user_id):
                        return jsonify({'success': False, 'message': 'Session not found'}), 404
                except Exception:
                    return jsonify({'success': False, 'message': 'Could not verify session ownership'}), 500

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
                'completed' if parse_result['ok'] else 'failed',
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
        user_id, auth_response = _authenticated_user()
        if auth_response:
            return auth_response

        with _db() as (conn, cursor):
            if not conn:
                return jsonify({'success': False, 'message': 'Database error'}), 500
            try:
                dataset = _owned_dataset(cursor, dataset_id, user_id)
            except Exception as e:
                traceback.print_exc()
                return jsonify({'success': False, 'message': str(e)}), 500

        if not dataset:
            return jsonify({'success': False, 'message': 'Dataset not found'}), 404

        file_path = _absolute_upload_path(dataset.get('file_path'))
        instrument_type = dataset['instrument_type']

        if not file_path or not os.path.exists(file_path):
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
        user_id, auth_response = _authenticated_user()
        if auth_response:
            return auth_response

        with _db() as (conn, cursor):
            if not conn:
                return jsonify({'success': False, 'message': 'Database error'}), 500
            try:
                dataset = _owned_dataset(cursor, dataset_id, user_id)
            except Exception as e:
                traceback.print_exc()
                return jsonify({'success': False, 'message': str(e)}), 500

        if not dataset:
            return jsonify({'success': False, 'message': 'Dataset not found'}), 404

        file_path = _absolute_upload_path(dataset.get('file_path'))
        instrument_type = dataset['instrument_type']

        if not file_path or not os.path.exists(file_path):
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
        user_id, auth_response = _authenticated_user()
        if auth_response:
            return auth_response

        with _db() as (conn, cursor):
            if not conn:
                return jsonify({'success': False, 'message': 'Database error'}), 500
            try:
                dataset = _owned_dataset(cursor, dataset_id, user_id, 'file_path')
                if not dataset:
                    return jsonify({'success': False, 'message': 'Dataset not found'}), 404
                file_path = dataset['file_path']
                conn.begin()
                cursor.execute(
                    "DELETE FROM datasets WHERE id = %s AND user_id = %s",
                    (dataset_id, user_id)
                )
                if cursor.rowcount != 1:
                    conn.rollback()
                    return jsonify({'success': False, 'message': 'Dataset not found'}), 404
                conn.commit()
                file_removed = _remove_upload_file(file_path)

                return jsonify({
                    'success': True,
                    'message': 'Dataset deleted',
                    'warning': None if file_removed else
                        'Dataset record was deleted, but the original file could not be removed.'
                })
            except Exception as e:
                traceback.print_exc()
                return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/save-dataset', methods=['POST', 'OPTIONS'])
    def save_dataset():
        if request.method == 'OPTIONS':
            return '', 200
        user_id, auth_response = _authenticated_user()
        if auth_response:
            return auth_response

        try:
            data = request.get_json(silent=True)
            if not isinstance(data, dict):
                return jsonify({'success': False, 'message': 'Invalid dataset payload'}), 400
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
                        existing = _owned_dataset(cursor, upload_id, user_id)

                        if existing:
                            metadata = _decode_json_column(existing.get('metadata'), {})
                            if not isinstance(metadata, dict):
                                metadata = {}

                            metadata['data'] = payload_data
                            metadata['headers'] = headers
                            metadata['updated_at'] = datetime.now().isoformat()

                            cursor.execute(
                                """UPDATE datasets
                                   SET name = %s, data = %s, headers = %s, metadata = %s,
                                       instrument_type = COALESCE(%s, instrument_type),
                                       file_base64 = COALESCE(NULLIF(%s, ''), file_base64)
                                   WHERE id = %s AND user_id = %s""",
                                (name, _safe_json_dumps(payload_data),
                                 _safe_json_dumps(headers), _safe_json_dumps(metadata),
                                 instrument_type, file_base64, upload_id, user_id)
                            )
                            if cursor.rowcount != 1:
                                conn.rollback()
                                return jsonify({'success': False, 'message': 'Dataset not found'}), 404
                            conn.commit()

                            return jsonify({
                                'success': True,
                                'data': {'id': upload_id, 'name': name}
                            })
                        else:
                            return jsonify({'success': False, 'message': 'Dataset not found'}), 404
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
                           (name, file_base64, data, headers, file_name,
                            original_file_name, file_path, file_size,
                            instrument_type, sheet_count, row_count, column_count,
                            user_id, status, metadata)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (name, file_base64 or None, _safe_json_dumps(payload_data),
                         _safe_json_dumps(headers), name, name, None, 0, instrument_type,
                         len(sheet_names) if sheet_names else 1,
                         len(payload_data) if payload_data else 0,
                         len(headers) if headers else 0,
                         user_id, 'processed', _safe_json_dumps(metadata))
                    )
                    dataset_id = cursor.lastrowid
                    conn.commit()

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
        user_id, auth_response = _authenticated_user()
        if auth_response:
            return auth_response

        with _db() as (conn, cursor):
            if not conn:
                return jsonify({'success': False, 'message': 'Database error'}), 500
            try:
                cursor.execute(
                    "SELECT id, name, original_file_name, file_size, instrument_type, "
                    "sheet_count, row_count, column_count, created_at AS uploaded_at, "
                    "metadata, data, headers FROM datasets "
                    "WHERE user_id = %s ORDER BY created_at DESC",
                    (user_id,)
                )
                datasets = cursor.fetchall()
            except Exception as e:
                traceback.print_exc()
                return jsonify({'success': False, 'message': str(e)}), 500

        result = []
        for ds in datasets:
            metadata = _decode_json_column(ds.get('metadata'), {})
            saved_data = _decode_json_column(ds.get('data'), None)
            saved_headers = _decode_json_column(ds.get('headers'), None)
            if not isinstance(metadata, dict):
                metadata = {}

            result.append({
                'id': ds['id'],
                'name': ds.get('name') or ds.get('original_file_name'),
                'rows': ds['row_count'],
                'file_size': ds['file_size'],
                'instrument_type': ds['instrument_type'],
                'sheet_count': ds['sheet_count'],
                'uploaded_at': ds['uploaded_at'].isoformat() if ds['uploaded_at'] else None,
                'headers': saved_headers if saved_headers is not None else metadata.get('headers', []),
                'data': saved_data if saved_data is not None else metadata.get('data', [])
            })

        return jsonify({'success': True, 'data': result})

    @app.route('/api/load-dataset', methods=['POST', 'OPTIONS'])
    def load_dataset():
        if request.method == 'OPTIONS':
            return '', 200
        user_id, auth_response = _authenticated_user()
        if auth_response:
            return auth_response

        try:
            data = request.get_json()
            dataset_id = data.get('dataset_id')

            if not dataset_id:
                return jsonify({'success': False, 'message': 'Dataset ID required'}), 400

            with _db() as (conn, cursor):
                if not conn:
                    return jsonify({'success': False, 'message': 'Database error'}), 500
                try:
                    dataset = _owned_dataset(cursor, dataset_id, user_id)
                except Exception as e:
                    traceback.print_exc()
                    return jsonify({'success': False, 'message': str(e)}), 500

            if not dataset:
                return jsonify({'success': False, 'message': 'Dataset not found'}), 404

            metadata = _decode_json_column(dataset.get('metadata'), {})
            if not isinstance(metadata, dict):
                metadata = {}
            saved_data = _decode_json_column(dataset.get('data'), None)
            saved_headers = _decode_json_column(dataset.get('headers'), None)
            if saved_data is None:
                saved_data = metadata.get('data')
            if saved_headers is None:
                saved_headers = metadata.get('headers')

            if saved_data is not None and saved_headers is not None:
                return jsonify({
                    'success': True,
                    'data': {
                        'id': dataset['id'],
                        'name': dataset.get('name') or dataset['original_file_name'],
                        'data': saved_data,
                        'headers': saved_headers,
                        'instrument_type': dataset['instrument_type']
                    }
                })

            file_path = _absolute_upload_path(dataset.get('file_path'))
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
        user_id, auth_response = _authenticated_user()
        if auth_response:
            return auth_response

        try:
            data = request.get_json()
            dataset_id = data.get('dataset_id')

            if not dataset_id:
                return jsonify({'success': False, 'message': 'Dataset ID required'}), 400

            with _db() as (conn, cursor):
                if not conn:
                    return jsonify({'success': False, 'message': 'Database error'}), 500
                try:
                    dataset = _owned_dataset(cursor, dataset_id, user_id, 'file_path')
                    if not dataset:
                        return jsonify({'success': False, 'message': 'Dataset not found'}), 404
                    file_path = dataset['file_path']
                    conn.begin()
                    cursor.execute(
                        "DELETE FROM datasets WHERE id = %s AND user_id = %s",
                        (dataset_id, user_id)
                    )
                    if cursor.rowcount != 1:
                        conn.rollback()
                        return jsonify({'success': False, 'message': 'Dataset not found'}), 404
                    conn.commit()
                    file_removed = _remove_upload_file(file_path)

                    return jsonify({
                        'success': True,
                        'message': 'Dataset deleted',
                        'warning': None if file_removed else
                            'Dataset record was deleted, but the original file could not be removed.'
                    })
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

        user_id, auth_response = _authenticated_user()
        if auth_response:
            return auth_response
        file_path, original_name = _resolve_file_row(dataset_id, user_id)
        if file_path is None:
            return jsonify({'success': False, 'message': 'Dataset not found'}), 404
        file_path = _absolute_upload_path(file_path)
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

        user_id, auth_response = _authenticated_user()
        if auth_response:
            return auth_response
        file_path, original_name = _resolve_file_row(dataset_id, user_id)
        if file_path is None:
            return jsonify({'success': False, 'message': 'Dataset not found'}), 404
        file_path = _absolute_upload_path(file_path)
        if not file_path or not os.path.exists(file_path):
            return jsonify({'success': False, 'message': 'Original file missing on server'}), 404

        mime, _ = mimetypes.guess_type(original_name or file_path)
        return send_file(
            file_path,
            mimetype=mime or 'application/octet-stream',
            as_attachment=True,
            download_name=original_name or os.path.basename(file_path),
        )
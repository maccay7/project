import json
import os
import uuid
from flask import request, jsonify, send_file
from werkzeug.utils import secure_filename
from utils.db import get_db
import openpyxl
import pandas as pd
from datetime import datetime
from utils.excel_parser import parse_full_workbook

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'xlsm', 'csv'}
# No file size limit - accept any file Excel can open

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def create_dataset_table():
    conn = get_db()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
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
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error creating datasets table: {e}")
        conn.close()
        return False


def save_dataset_metadata(file_name, original_name, file_path, file_size, instrument_type, sheet_count, row_count, column_count, user_id=None, session_id=None, metadata=None):
    conn = get_db()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO datasets 
               (file_name, original_file_name, file_path, file_size, instrument_type, sheet_count, row_count, column_count, user_id, session_id, metadata) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (file_name, original_name, file_path, file_size, instrument_type, sheet_count, row_count, column_count, user_id, session_id, json.dumps(metadata) if metadata else None)
        )
        conn.commit()
        dataset_id = cursor.lastrowid
        cursor.close()
        conn.close()
        return dataset_id
    except Exception as e:
        print(f"Error saving dataset metadata: {e}")
        conn.close()
        return None


def intelligent_parse(file_path, instrument_type):
    parsed = parse_full_workbook(file_path, instrument_type, max_rows=None)
    warnings = parsed.get('warnings', [])
    metadata = parsed.get('metadata', {})

    extracted_data = []

    for sheet in parsed.get('sheets', []):
        # excel_parser already returns sheet['data'] as a list of dicts
        # (headers applied to each row). Just aggregate them.
        data = sheet.get('data', [])
        for row in data:
            if isinstance(row, dict):
                extracted_data.append(row)

    return {
        'data': extracted_data,
        'warnings': warnings,
        'metadata': metadata,
        'sheets': parsed.get('sheets', [])
    }


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

            parsed = parse_full_workbook(file_path, instrument_type, max_rows=None)
            sheet_count = len(parsed.get('sheets', []))
            total_rows = sum(s.get('total_rows', 0) for s in parsed.get('sheets', []))
            total_columns = max((s.get('total_columns', 0) for s in parsed.get('sheets', [])), default=0)

            metadata = {
                'sheet_count': sheet_count,
                'sheet_names': [s['name'] for s in parsed.get('sheets', [])],
                'total_rows': total_rows,
                'total_columns': total_columns,
                'parse_warnings': parsed.get('warnings', [])
            }

            dataset_id = save_dataset_metadata(
                unique_filename,
                file.filename,
                file_path,
                file_size,
                instrument_type,
                sheet_count,
                total_rows,
                total_columns,
                user_id,
                session_id,
                metadata
            )

            if dataset_id:
                return jsonify({
                    'success': True,
                    'data': {
                        'dataset_id': dataset_id,
                        'file_name': file.filename,
                        'file_size': file_size,
                        'instrument_type': instrument_type,
                        'metadata': metadata,
                        'warnings': parsed.get('warnings', [])
                    }
                })
            else:
                return jsonify({'success': False, 'message': 'Failed to save dataset metadata'}), 500

        except Exception as e:
            return jsonify({'success': False, 'message': f'Upload failed: {str(e)}'}), 500

    @app.route('/api/dataset/<int:dataset_id>/parse', methods=['GET', 'OPTIONS'])
    def parse_dataset(dataset_id):
        if request.method == 'OPTIONS':
            return '', 200

        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'Database error'}), 500

        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM datasets WHERE id = %s", (dataset_id,))
            dataset = cursor.fetchone()
            cursor.close()
            conn.close()

            if not dataset:
                return jsonify({'success': False, 'message': 'Dataset not found'}), 404

            file_path = dataset['file_path']
            instrument_type = dataset['instrument_type']

            if not os.path.exists(file_path):
                return jsonify({'success': False, 'message': 'File not found on server'}), 404

            parsed = parse_full_workbook(file_path, instrument_type, max_rows=None)

            return jsonify({
                'success': True,
                'data': parsed
            })

        except Exception as e:
            conn.close()
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/dataset/<int:dataset_id>/intelligent-parse', methods=['GET', 'OPTIONS'])
    def intelligent_parse_dataset(dataset_id):
        if request.method == 'OPTIONS':
            return '', 200

        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'Database error'}), 500

        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM datasets WHERE id = %s", (dataset_id,))
            dataset = cursor.fetchone()
            cursor.close()
            conn.close()

            if not dataset:
                return jsonify({'success': False, 'message': 'Dataset not found'}), 404

            file_path = dataset['file_path']
            instrument_type = dataset['instrument_type']

            if not os.path.exists(file_path):
                return jsonify({'success': False, 'message': 'File not found on server'}), 404

            result = intelligent_parse(file_path, instrument_type)

            return jsonify({
                'success': True,
                'data': result
            })

        except Exception as e:
            conn.close()
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/dataset/<int:dataset_id>', methods=['DELETE', 'OPTIONS'])
    def delete_dataset(dataset_id):
        if request.method == 'OPTIONS':
            return '', 200

        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'Database error'}), 500

        try:
            cursor = conn.cursor()
            cursor.execute("SELECT file_path FROM datasets WHERE id = %s", (dataset_id,))
            dataset = cursor.fetchone()

            if dataset:
                file_path = dataset['file_path']
                if os.path.exists(file_path):
                    os.remove(file_path)

                cursor.execute("DELETE FROM datasets WHERE id = %s", (dataset_id,))
                conn.commit()

            cursor.close()
            conn.close()
            return jsonify({'success': True, 'message': 'Dataset deleted'})

        except Exception as e:
            conn.close()
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/save-dataset', methods=['POST', 'OPTIONS'])
    def save_dataset():
        """Save dataset with data and headers (frontend compatibility)"""
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

            # If upload_id is provided, update existing dataset
            if upload_id:
                conn = get_db()
                if not conn:
                    return jsonify({'success': False, 'message': 'Database error'}), 500

                try:
                    cursor = conn.cursor()
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
                            """UPDATE datasets SET metadata = %s WHERE id = %s""",
                            (json.dumps(metadata), upload_id)
                        )
                        conn.commit()
                        cursor.close()
                        conn.close()

                        return jsonify({
                            'success': True,
                            'data': {'id': upload_id, 'name': name}
                        })
                    else:
                        cursor.close()
                        conn.close()
                except Exception as e:
                    conn.close()
                    return jsonify({'success': False, 'message': str(e)}), 500

            # Create new dataset entry without file (data-only save)
            conn = get_db()
            if not conn:
                return jsonify({'success': False, 'message': 'Database error'}), 500

            try:
                cursor = conn.cursor()
                metadata = {
                    'data': payload_data,
                    'headers': headers,
                    'sheet_names': sheet_names,
                    'instrument_type': instrument_type,
                    'created_at': datetime.now().isoformat()
                }

                cursor.execute(
                    """INSERT INTO datasets 
                       (file_name, original_file_name, file_path, file_size, instrument_type, sheet_count, row_count, column_count, metadata) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (name, name, '', 0, instrument_type, len(sheet_names) if sheet_names else 1, 
                     len(payload_data) if payload_data else 0, len(headers) if headers else 0, 
                     json.dumps(metadata))
                )
                conn.commit()
                dataset_id = cursor.lastrowid
                cursor.close()
                conn.close()

                return jsonify({
                    'success': True,
                    'data': {'id': dataset_id, 'name': name}
                })

            except Exception as e:
                conn.close()
                return jsonify({'success': False, 'message': str(e)}), 500

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/get-datasets', methods=['GET', 'OPTIONS'])
    def get_datasets():
        """Get all datasets (frontend compatibility)"""
        if request.method == 'OPTIONS':
            return '', 200

        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'Database error'}), 500

        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, original_file_name, file_size, instrument_type, sheet_count, row_count, column_count, uploaded_at, metadata FROM datasets ORDER BY uploaded_at DESC")
            datasets = cursor.fetchall()
            cursor.close()
            conn.close()

            result = []
            for ds in datasets:
                metadata = ds.get('metadata', {})
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except:
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

        except Exception as e:
            conn.close()
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/load-dataset', methods=['POST', 'OPTIONS'])
    def load_dataset():
        """Load dataset by ID (frontend compatibility)"""
        if request.method == 'OPTIONS':
            return '', 200

        try:
            data = request.get_json()
            dataset_id = data.get('dataset_id')

            if not dataset_id:
                return jsonify({'success': False, 'message': 'Dataset ID required'}), 400

            conn = get_db()
            if not conn:
                return jsonify({'success': False, 'message': 'Database error'}), 500

            try:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM datasets WHERE id = %s", (dataset_id,))
                dataset = cursor.fetchone()
                cursor.close()
                conn.close()

                if not dataset:
                    return jsonify({'success': False, 'message': 'Dataset not found'}), 404

                metadata = dataset.get('metadata', {})
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except:
                        metadata = {}

                # If dataset has stored data/headers in metadata, return those
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

                # Otherwise, parse the file if it exists
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
                conn.close()
                return jsonify({'success': False, 'message': str(e)}), 500

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/delete-dataset', methods=['POST', 'OPTIONS'])
    def delete_dataset_post():
        """Delete dataset by ID (frontend compatibility - POST method)"""
        if request.method == 'OPTIONS':
            return '', 200

        try:
            data = request.get_json()
            dataset_id = data.get('dataset_id')

            if not dataset_id:
                return jsonify({'success': False, 'message': 'Dataset ID required'}), 400

            conn = get_db()
            if not conn:
                return jsonify({'success': False, 'message': 'Database error'}), 500

            try:
                cursor = conn.cursor()
                cursor.execute("SELECT file_path FROM datasets WHERE id = %s", (dataset_id,))
                dataset = cursor.fetchone()

                if dataset:
                    file_path = dataset['file_path']
                    if file_path and os.path.exists(file_path):
                        os.remove(file_path)

                    cursor.execute("DELETE FROM datasets WHERE id = %s", (dataset_id,))
                    conn.commit()

                cursor.close()
                conn.close()
                return jsonify({'success': True, 'message': 'Dataset deleted'})

            except Exception as e:
                conn.close()
                return jsonify({'success': False, 'message': str(e)}), 500

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
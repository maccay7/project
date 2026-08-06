import json
import os
import uuid
from flask import request, jsonify, send_file
from werkzeug.utils import secure_filename
from utils.db import get_db
import openpyxl
import pandas as pd
from datetime import datetime
from utils.excel_parser import parse_full_workbook  # Use the central parser

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
    # Use the full parser to get the raw data without field restrictions or row limits
    parsed = parse_full_workbook(file_path, instrument_type, max_rows=None)
    warnings = parsed.get('warnings', [])
    metadata = parsed.get('metadata', {})
    
    # Return all data from all sheets without field mapping restrictions
    # This allows any Excel structure to be processed
    extracted_data = []
    
    for sheet in parsed.get('sheets', []):
        # Get the raw data from each sheet
        data = sheet.get('data', [])
        headers = sheet.get('headers', [])
        
        # Preserve all columns and data as-is
        for row in data:
            row_data = {}
            # Map all columns by their actual header names
            for idx, header in enumerate(headers):
                row_data[header] = row[idx] if idx < len(row) else ''
            extracted_data.append(row_data)
    
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
        instrument_type = request.form.get('instrument_type', 'money-market')
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
            
            # Use central parser to get sheet info without row limits
            parsed = parse_full_workbook(file_path, instrument_type, max_rows=None)
            sheet_count = len(parsed.get('sheets', []))
            total_rows = sum(s.get('total_rows', 0) for s in parsed.get('sheets', []))
            total_columns = max((s.get('total_columns', 0) for s in parsed.get('sheets', [])), default=0)
            
            # Prepare metadata
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
            
            # Use central parser without row limits
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
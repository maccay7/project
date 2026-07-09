import json
import os
import uuid
from flask import request, jsonify, send_file
from werkzeug.utils import secure_filename
from utils.db import get_db
import openpyxl
import pandas as pd
from datetime import datetime

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}
MAX_FILE_SIZE = 16 * 1024 * 1024

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


def parse_excel_file(file_path, instrument_type):
    result = {
        'sheets': [],
        'metadata': {},
        'warnings': []
    }
    
    try:
        import openpyxl
        workbook = openpyxl.load_workbook(file_path, data_only=False, read_only=False)
        
        result['metadata']['sheet_names'] = workbook.sheetnames
        result['metadata']['sheet_count'] = len(workbook.sheetnames)
        
        named_ranges = []
        for name in workbook.defined_names:
            named_ranges.append({
                'name': name.name,
                'value': str(name.attr_text) if hasattr(name, 'attr_text') else str(name.value)
            })
        result['metadata']['named_ranges'] = named_ranges
        
        total_rows = 0
        total_columns = 0
        
        for sheet_name in workbook.sheetnames:
            try:
                sheet = workbook[sheet_name]
                
                tables = []
                for table in sheet.tables:
                    tables.append({
                        'name': table.name,
                        'ref': table.ref,
                        'display_name': table.displayName
                    })
                
                data_ranges = []
                if sheet.dimensions:
                    data_ranges.append(sheet.dimensions)
                
                headers = []
                data = []
                
                for row_idx, row in enumerate(sheet.iter_rows(values_only=False)):
                    row_data = []
                    for cell in row:
                        cell_info = {
                            'value': cell.value if cell.value is not None else '',
                            'formula': None,
                            'data_type': cell.data_type
                        }
                        if cell.data_type == 'f':
                            cell_info['formula'] = cell.value
                        row_data.append(cell_info)
                    
                    if row_idx == 0:
                        headers = row_data
                    else:
                        row_dict = {}
                        for idx, (header, value) in enumerate(zip(headers, row_data)):
                            row_dict[str(header)] = value
                        data.append(row_dict)
                
                merged_ranges = []
                for merge_range in sheet.merged_cells.ranges:
                    merged_ranges.append(str(merge_range))
                
                sheet_info = {
                    'name': sheet_name,
                    'headers': headers,
                    'data': data,
                    'row_count': len(data),
                    'column_count': len(headers),
                    'total_rows': sheet.max_row,
                    'tables': tables,
                    'data_ranges': data_ranges,
                    'merged_ranges': merged_ranges
                }
                
                result['sheets'].append(sheet_info)
                total_rows += len(data)
                total_columns = max(total_columns, len(headers))
                
            except Exception as e:
                result['warnings'].append(f"Error parsing sheet '{sheet_name}': {str(e)}")
        
        workbook.close()
        result['metadata']['total_rows'] = total_rows
        result['metadata']['total_columns'] = total_columns
        
    except ImportError:
        excel_file = pd.ExcelFile(file_path)
        
        result['metadata']['sheet_names'] = excel_file.sheet_names
        result['metadata']['sheet_count'] = len(excel_file.sheet_names)
        
        total_rows = 0
        total_columns = 0
        
        for sheet_name in excel_file.sheet_names:
            try:
                df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
                
                header_row_idx = 0
                max_non_null = 0
                for idx, row in df.iterrows():
                    non_null_count = row.notna().sum()
                    if non_null_count > max_non_null:
                        max_non_null = non_null_count
                        header_row_idx = idx
                
                if header_row_idx < len(df):
                    headers = df.iloc[header_row_idx].fillna('').astype(str).tolist()
                    data_df = df.iloc[header_row_idx + 1:].reset_index(drop=True)
                else:
                    headers = [f'Column {i}' for i in range(len(df.columns))]
                    data_df = df
                
                data = []
                for _, row in data_df.iterrows():
                    row_dict = {}
                    for idx, (header, value) in enumerate(zip(headers, row)):
                        row_dict[str(header)] = value if pd.notna(value) else ''
                    data.append(row_dict)
                
                sheet_info = {
                    'name': sheet_name,
                    'headers': headers,
                    'data': data,
                    'row_count': len(data),
                    'column_count': len(headers),
                    'total_rows': len(df)
                }
                
                result['sheets'].append(sheet_info)
                total_rows += len(data)
                total_columns = max(total_columns, len(headers))
                
            except Exception as e:
                result['warnings'].append(f"Error parsing sheet '{sheet_name}': {str(e)}")
        
        result['metadata']['total_rows'] = total_rows
        result['metadata']['total_columns'] = total_columns
        
    except Exception as e:
        result['warnings'].append(f"Error parsing Excel file: {str(e)}")
    
    return result


def parse_full_workbook(file_path, instrument_type):
    print(f"=== parse_full_workbook called ===")
    print(f"File path: {file_path}")
    print(f"Instrument type: {instrument_type}")
    
    result = {
        'sheets': [],
        'metadata': {},
        'warnings': []
    }
    
    try:
        import openpyxl
        print("openpyxl imported successfully")
        
        workbook = openpyxl.load_workbook(file_path, data_only=False, read_only=False)
        print(f"Workbook loaded. Sheets: {workbook.sheetnames}")
        
        result['metadata']['sheet_names'] = workbook.sheetnames
        result['metadata']['sheet_count'] = len(workbook.sheetnames)
        
        for sheet_name in workbook.sheetnames:
            try:
                print(f"Parsing sheet: {sheet_name}")
                sheet = workbook[sheet_name]
                headers = []
                data = []
                
                for row_idx, row in enumerate(sheet.iter_rows(values_only=False)):
                    row_data = []
                    for cell in row:
                        cell_info = {
                            'value': cell.value if cell.value is not None else '',
                            'formula': None
                        }
                        if cell.data_type == 'f':
                            cell_info['formula'] = cell.value
                            try:
                                cell_info['value'] = openpyxl.load_workbook(file_path, data_only=True, read_only=True)[sheet_name].cell(row=cell.row, column=cell.column).value
                            except:
                                pass
                        row_data.append(cell_info)
                    
                    if row_idx == 0:
                        headers = row_data
                    else:
                        row_dict = {}
                        for idx, (header, value) in enumerate(zip(headers, row_data)):
                            row_dict[str(header)] = value
                        data.append(row_dict)
                
                merged_ranges = []
                for merge_range in sheet.merged_cells.ranges:
                    merged_ranges.append(str(merge_range))
                
                sheet_info = {
                    'name': sheet_name,
                    'headers': headers,
                    'data': data,
                    'row_count': len(data),
                    'column_count': len(headers),
                    'total_rows': sheet.max_row,
                    'merged_ranges': merged_ranges
                }
                
                result['sheets'].append(sheet_info)
                print(f"Sheet {sheet_name} parsed: {len(data)} rows, {len(headers)} columns")
                
            except Exception as e:
                print(f"Error parsing sheet '{sheet_name}': {str(e)}")
                result['warnings'].append(f"Error parsing sheet '{sheet_name}': {str(e)}")
        
        workbook.close()
        
        result['metadata']['total_rows'] = sum(s['row_count'] for s in result['sheets'])
        result['metadata']['total_columns'] = max((s['column_count'] for s in result['sheets']), default=0)
        
        print(f"=== parse_full_workbook complete: {len(result['sheets'])} sheets ===")
        
    except ImportError as e:
        print(f"ImportError: {e}")
        result = parse_excel_file(file_path, instrument_type)
    except Exception as e:
        print(f"Exception in parse_full_workbook: {e}")
        import traceback
        traceback.print_exc()
        result['warnings'].append(f"Error parsing workbook: {str(e)}")
        try:
            result = parse_excel_file(file_path, instrument_type)
        except:
            pass
    
    return result


def intelligent_parse(file_path, instrument_type):
    field_map = {
        'money-market': {
            'required': ['Principal', 'InterestRate', 'DaysToMaturity'],
            'optional': ['InvestmentAmount', 'IssueDate', 'MaturityDate'],
            'keywords': {
                'Principal': ['principal', 'principal amount', 'investment', 'amount', 'notional'],
                'InterestRate': ['interest rate', 'rate', 'interest', 'coupon', 'annual rate'],
                'InvestmentAmount': ['investment amount', 'investment', 'amount', 'principal'],
                'DaysToMaturity': ['days to maturity', 'maturity days', 'term', 'tenor', 'duration'],
                'IssueDate': ['issue date', 'effective date', 'start date', 'trade date'],
                'MaturityDate': ['maturity date', 'maturity', 'due date', 'end date']
            }
        },
        'bonds': {
            'required': ['CouponRate', 'FaceValue', 'MaturityDate'],
            'optional': ['CouponFrequency', 'Yield', 'SettlementDate', 'IssueDate', 'Price'],
            'keywords': {
                'CouponRate': ['coupon rate', 'coupon', 'rate', 'interest rate'],
                'CouponFrequency': ['coupon frequency', 'frequency', 'payment frequency'],
                'FaceValue': ['face value', 'face', 'par value', 'par', 'amount', 'principal'],
                'Yield': ['yield', 'ytm', 'yield to maturity', 'return'],
                'SettlementDate': ['settlement date', 'settlement', 'trade date'],
                'MaturityDate': ['maturity date', 'maturity', 'due date'],
                'IssueDate': ['issue date', 'effective date', 'start date'],
                'Price': ['price', 'clean price', 'market price']
            }
        },
        'tbills': {
            'required': ['FaceValue', 'DiscountRate', 'DaysToMaturity'],
            'optional': ['PurchasePrice', 'RedemptionValue', 'IssueDate', 'MaturityDate'],
            'keywords': {
                'FaceValue': ['face value', 'face', 'par value', 'par', 'amount', 'principal'],
                'DiscountRate': ['discount rate', 'discount', 'rate'],
                'PurchasePrice': ['purchase price', 'purchase', 'price'],
                'RedemptionValue': ['redemption value', 'redemption'],
                'DaysToMaturity': ['days to maturity', 'maturity days', 'term', 'tenor'],
                'IssueDate': ['issue date', 'effective date', 'start date'],
                'MaturityDate': ['maturity date', 'maturity', 'due date']
            }
        }
    }
    
    field_config = field_map.get(instrument_type, field_map['money-market'])
    all_fields = field_config['required'] + field_config['optional']
    keywords = field_config['keywords']
    
    parsed = parse_excel_file(file_path, instrument_type)
    warnings = parsed.get('warnings', [])
    metadata = parsed.get('metadata', {})
    
    extracted_data = []
    
    for sheet in parsed.get('sheets', []):
        headers = sheet.get('headers', [])
        data = sheet.get('data', [])
        
        column_map = {}
        for field in all_fields:
            field_keywords = keywords.get(field, [])
            for idx, header in enumerate(headers):
                header_lower = str(header).lower()
                if any(kw in header_lower for kw in field_keywords):
                    column_map[field] = idx
                    break
        
        for row in data:
            row_data = {}
            for field in all_fields:
                col_idx = column_map.get(field)
                if col_idx is not None and col_idx < len(row):
                    row_data[field] = row[col_idx]
                else:
                    row_data[field] = ''
            extracted_data.append(row_data)
    
    return {
        'data': extracted_data,
        'warnings': warnings,
        'metadata': metadata
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
            
            parsed = parse_excel_file(file_path, instrument_type)
            sheet_count = parsed['metadata'].get('sheet_count', 0)
            total_rows = parsed['metadata'].get('total_rows', 0)
            total_columns = parsed['metadata'].get('total_columns', 0)
            
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
                parsed['metadata']
            )
            
            if dataset_id:
                return jsonify({
                    'success': True,
                    'data': {
                        'dataset_id': dataset_id,
                        'file_name': file.filename,
                        'file_size': file_size,
                        'instrument_type': instrument_type,
                        'metadata': parsed['metadata'],
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
            
            parsed = parse_excel_file(file_path, instrument_type)
            
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
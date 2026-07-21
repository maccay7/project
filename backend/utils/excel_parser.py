import pandas as pd
import openpyxl
import io
import os
from pathlib import Path

def parse_full_workbook(file_path_or_bytes, instrument_type='money-market', max_rows=10000):
    """
    Parse an Excel file and return all sheets with data and headers.
    Returns:
        {
            'success': bool,
            'sheets': [{'name': str, 'data': list of dict, 'headers': list, 'fullData': 2D list}],
            'error': str or None
        }
    """
    try:
        # Determine if input is file path or bytes
        if isinstance(file_path_or_bytes, (str, Path)):
            if os.path.isfile(file_path_or_bytes):
                file_path = file_path_or_bytes
                # Use openpyxl to read with full data (including merged cells handled)
                wb = openpyxl.load_workbook(file_path, data_only=True, read_only=True)
                sheets = []
                for sheet_name in wb.sheetnames:
                    ws = wb[sheet_name]
                    full_data = []
                    headers = []
                    for row in ws.iter_rows(values_only=True, max_row=max_rows):
                        if not any(cell is not None for cell in row):
                            continue
                        # Convert to list with None replaced by empty string
                        row_list = [cell if cell is not None else '' for cell in row]
                        full_data.append(row_list)
                    if full_data:
                        # Use first row as headers if they seem like text
                        first_row = full_data[0]
                        # Try to detect headers: if first row contains strings and not numbers
                        is_header_row = any(isinstance(cell, str) and not cell.isdigit() for cell in first_row)
                        if is_header_row:
                            headers = [str(h) for h in first_row]
                            data_rows = full_data[1:]
                        else:
                            headers = [f"Column_{i+1}" for i in range(len(first_row))]
                            data_rows = full_data
                        # Convert to list of dict
                        data = []
                        for row in data_rows:
                            row_dict = {}
                            for idx, val in enumerate(row):
                                if idx < len(headers):
                                    row_dict[headers[idx]] = val
                            data.append(row_dict)
                        sheets.append({
                            'name': sheet_name,
                            'data': data,
                            'headers': headers,
                            'fullData': full_data
                        })
                wb.close()
                return {'success': True, 'sheets': sheets}
            else:
                # It's bytes or a file-like object
                return parse_full_workbook_from_bytes(file_path_or_bytes, instrument_type, max_rows)
        else:
            # Assume it's bytes
            return parse_full_workbook_from_bytes(file_path_or_bytes, instrument_type, max_rows)
    except Exception as e:
        return {'success': False, 'error': str(e), 'sheets': []}

def parse_full_workbook_from_bytes(file_bytes, instrument_type='money-market', max_rows=10000):
    try:
        # Try openpyxl first
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True, read_only=True)
        sheets = []
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            full_data = []
            for row in ws.iter_rows(values_only=True, max_row=max_rows):
                if not any(cell is not None for cell in row):
                    continue
                row_list = [cell if cell is not None else '' for cell in row]
                full_data.append(row_list)
            if full_data:
                first_row = full_data[0]
                is_header_row = any(isinstance(cell, str) and not cell.isdigit() for cell in first_row)
                if is_header_row:
                    headers = [str(h) for h in first_row]
                    data_rows = full_data[1:]
                else:
                    headers = [f"Column_{i+1}" for i in range(len(first_row))]
                    data_rows = full_data
                data = []
                for row in data_rows:
                    row_dict = {}
                    for idx, val in enumerate(row):
                        if idx < len(headers):
                            row_dict[headers[idx]] = val
                    data.append(row_dict)
                sheets.append({
                    'name': sheet_name,
                    'data': data,
                    'headers': headers,
                    'fullData': full_data
                })
        wb.close()
        return {'success': True, 'sheets': sheets}
    except Exception as e:
        # Fallback to pandas
        try:
            df_dict = pd.read_excel(io.BytesIO(file_bytes), sheet_name=None, header=None, dtype=str)
            sheets = []
            for sheet_name, df in df_dict.items():
                full_data = df.values.tolist()
                # Clean NaNs
                full_data = [[str(cell) if pd.notna(cell) else '' for cell in row] for row in full_data]
                if full_data:
                    first_row = full_data[0]
                    is_header_row = any(isinstance(cell, str) and not cell.isdigit() for cell in first_row)
                    if is_header_row:
                        headers = [str(h) for h in first_row]
                        data_rows = full_data[1:]
                    else:
                        headers = [f"Column_{i+1}" for i in range(len(first_row))]
                        data_rows = full_data
                    data = []
                    for row in data_rows:
                        row_dict = {}
                        for idx, val in enumerate(row):
                            if idx < len(headers):
                                row_dict[headers[idx]] = val
                        data.append(row_dict)
                    sheets.append({
                        'name': sheet_name,
                        'data': data,
                        'headers': headers,
                        'fullData': full_data
                    })
            return {'success': True, 'sheets': sheets}
        except Exception as e2:
            return {'success': False, 'error': str(e2), 'sheets': []}
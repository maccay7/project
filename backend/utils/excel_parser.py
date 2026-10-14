import pandas as pd
import openpyxl
import io
import os
from pathlib import Path


# Phantom-range guard: Excel often declares a worksheet range as the entire
# grid (e.g. "B2:XFD1048575") because of stray formatting, even when only a
# few cells actually contain data. Reading every declared row would iterate
# billions of cells. We therefore stream rows and stop once we have seen a
# long run of fully-empty rows, with an absolute cap as a backstop.
EMPTY_ROW_LIMIT = 200          # stop after this many consecutive blank rows (post-content)
INITIAL_EMPTY_LIMIT = 5000     # allow more blank rows before the first content row
HARD_ROW_CAP = 200000          # never exceed this many rows in one sheet


def _build_sheet_dict(sheet_name, full_data, merged_ranges, max_col):
    if not full_data:
        return {
            'name': sheet_name,
            'data': [],
            'headers': [],
            'fullData': [],
            'merged_ranges': [],
            'total_rows': 0,
            'total_columns': 0
        }

    first_row = full_data[0]
    is_header_row = any(isinstance(cell, str) and cell and not cell.isdigit() for cell in first_row)
    if is_header_row:
        headers = [str(h) for h in first_row]
        data_rows = full_data[1:]
    else:
        headers = [f"Column_{i+1}" for i in range(len(first_row))]
        data_rows = full_data

    data = []
    for row in data_rows:
        if not any(cell != '' and cell is not None for cell in row):
            continue
        row_dict = {}
        for idx, val in enumerate(row):
            if idx < len(headers):
                row_dict[headers[idx]] = val
        data.append(row_dict)

    return {
        'name': sheet_name,
        'data': data,
        'headers': headers,
        'fullData': full_data,
        'merged_ranges': merged_ranges,
        'total_rows': len(full_data),
        'total_columns': max_col
    }


def _read_sheet_openpyxl(ws, max_rows):
    """
    Read a single worksheet into a raw grid (blank rows preserved), stopping
    early if Excel has declared a phantom range for the sheet.
    """
    full_data = []
    max_col = 0
    empty_run = 0
    seen_content = False
    truncated = False

    try:
        row_iter = ws.iter_rows(values_only=True)
    except Exception:
        return [], [], 0

    for row in row_iter:
        row_list = [cell if cell is not None else '' for cell in row]
        is_empty = all(c == '' for c in row_list)

        if is_empty:
            empty_run += 1
            if seen_content and empty_run >= EMPTY_ROW_LIMIT:
                truncated = True
                break
            if not seen_content and empty_run >= INITIAL_EMPTY_LIMIT:
                truncated = True
                break
        else:
            seen_content = True
            empty_run = 0

        full_data.append(row_list)
        if len(row_list) > max_col:
            max_col = len(row_list)

        if max_rows is not None and len(full_data) >= max_rows:
            break
        if len(full_data) >= HARD_ROW_CAP:
            truncated = True
            break

    for row in full_data:
        if len(row) < max_col:
            row.extend([''] * (max_col - len(row)))

    while max_col > 0 and all(
        len(row) >= max_col and (row[max_col - 1] == '' or row[max_col - 1] is None)
        for row in full_data
    ):
        max_col -= 1
    for row in full_data:
        if max_col >= 0:
            del row[max_col:]

    merged_ranges = []
    try:
        for merge in ws.merged_cells.ranges:
            merged_ranges.append({
                'min_row': merge.min_row - 1,
                'max_row': merge.max_row - 1,
                'min_col': merge.min_col - 1,
                'max_col': merge.max_col - 1
            })
    except Exception:
        pass

    return full_data, merged_ranges, max_col


def parse_full_workbook(file_path_or_bytes, instrument_type='money-market', max_rows=None):
    try:
        if isinstance(file_path_or_bytes, (str, Path)):
            if os.path.isfile(file_path_or_bytes):
                wb = openpyxl.load_workbook(file_path_or_bytes, data_only=True, read_only=True)
                sheets = []
                for sheet_name in wb.sheetnames:
                    ws = wb[sheet_name]
                    full_data, merged_ranges, max_col = _read_sheet_openpyxl(ws, max_rows)
                    sheets.append(_build_sheet_dict(sheet_name, full_data, merged_ranges, max_col))
                wb.close()
                return {'success': True, 'sheets': sheets}
            else:
                return parse_full_workbook_from_bytes(file_path_or_bytes, instrument_type, max_rows)
        else:
            return parse_full_workbook_from_bytes(file_path_or_bytes, instrument_type, max_rows)
    except Exception as e:
        return {'success': False, 'error': str(e), 'sheets': []}


def parse_full_workbook_from_bytes(file_bytes, instrument_type='money-market', max_rows=None):
    try:
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True, read_only=True)
        sheets = []
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            full_data, merged_ranges, max_col = _read_sheet_openpyxl(ws, max_rows)
            sheets.append(_build_sheet_dict(sheet_name, full_data, merged_ranges, max_col))
        wb.close()
        return {'success': True, 'sheets': sheets}
    except Exception:
        try:
            df_dict = pd.read_excel(io.BytesIO(file_bytes), sheet_name=None, header=None, dtype=str)
            sheets = []
            for sheet_name, df in df_dict.items():
                full_data = df.values.tolist()
                full_data = [[str(cell) if pd.notna(cell) else '' for cell in row] for row in full_data]
                max_col = len(full_data[0]) if full_data else 0
                sheets.append(_build_sheet_dict(sheet_name, full_data, [], max_col))
            return {'success': True, 'sheets': sheets}
        except Exception as e2:
            return {'success': False, 'error': str(e2), 'sheets': []}
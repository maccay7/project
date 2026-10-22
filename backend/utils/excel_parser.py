import pandas as pd
import openpyxl
import io
import os
from datetime import datetime, date, time, timedelta
from pathlib import Path


EMPTY_ROW_LIMIT = 200
INITIAL_EMPTY_LIMIT = 5000
HARD_ROW_CAP = 200000


def _serialize_cell_value(cell):
    """Convert Excel cell value to a JSON-safe value.

    Dates become ISO 'YYYY-MM-DD' strings so downstream parsers and the
    frontend never see a timezone-ambiguous ISO datetime. This is what
    stops '31-Dec-2025' turning into '30 Dec 2025' on the frontend.
    """
    if cell is None:
        return ''
    if isinstance(cell, datetime):
        return cell.strftime('%Y-%m-%d')
    if isinstance(cell, date):
        return cell.strftime('%Y-%m-%d')
    if isinstance(cell, time):
        return cell.strftime('%H:%M:%S')
    if isinstance(cell, timedelta):
        total_seconds = int(cell.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return cell


def _looks_like_key_value_layout(full_data):
    """Detect a single-instrument key-value sheet.

    True for narrow sheets where most rows are 'label | value'.
    False for anything wider than 4 columns (that's a real table).

    Note: a genuinely tabular 2-column sheet will also match this. That
    is rare for instrument uploads; users can force tabular parsing by
    adding a 3rd column to their sheet.
    """
    if not full_data or len(full_data) < 2:
        return False
    if len(full_data) > 200:
        return False
    max_cols = max((len(r) for r in full_data), default=0)
    if max_cols > 4:
        return False

    pair_rows = 0
    data_rows = 0
    for row in full_data:
        non_empty = [c for c in row if c is not None and c != '']
        if not non_empty:
            continue
        data_rows += 1
        if len(non_empty) == 2 and isinstance(non_empty[0], str):
            pair_rows += 1

    if data_rows < 2:
        return False
    return (pair_rows / data_rows) >= 0.75


def _build_key_value_dict(full_data, sheet_name):
    """Collapse a key-value sheet into a single dict.

    Rows with more than 2 non-empty cells are skipped — those are the
    embedded schedule/grid sections (e.g. the PV table below the
    top-level fields) and are reference-only data, not calc inputs.
    """
    kv = {}
    for row in full_data:
        non_empty = [c for c in row if c is not None and c != '']
        if len(non_empty) < 2:
            continue
        if len(non_empty) > 2:
            continue
        label = str(non_empty[0]).strip()
        value = non_empty[1]
        if not label:
            continue
        if label in kv:
            continue
        kv[label] = value

    if not kv:
        return {}

    has_explicit_name = any(
        str(k).lower().strip() in (
            'instrument_name', 'instrument name', 'instrument',
            'issuer', 'security name', 'bond name', 'tbill name',
            'security', 'name'
        )
        for k in kv.keys()
    )
    if not has_explicit_name and sheet_name:
        # Dura Capital rule: worksheet name is the instrument name on
        # single-instrument sheets.
        kv['instrument_name'] = sheet_name

    return kv


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

    if _looks_like_key_value_layout(full_data):
        kv_dict = _build_key_value_dict(full_data, sheet_name)
        if kv_dict:
            return {
                'name': sheet_name,
                'data': [kv_dict],
                'headers': list(kv_dict.keys()),
                'fullData': full_data,
                'merged_ranges': merged_ranges,
                'total_rows': len(full_data),
                'total_columns': max_col,
                'layout': 'key-value',
            }

    first_row = full_data[0]
    is_header_row = any(
        isinstance(cell, str) and cell and not cell.isdigit()
        for cell in first_row
    )
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
        row_list = [_serialize_cell_value(cell) for cell in row]
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
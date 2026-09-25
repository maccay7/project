"""
Calculations API — HTTP layer.

This module has NO financial math. It:
  1. Reads the JSON payload from the HTTP request.
  2. Passes `data` to pages/calculations_details.py.
  3. Returns the response as JSON.

Multi-instrument sheets are NOT auto-split by classification labels here.
The caller supplies the instrument_type (from the page the user is on);
we trust it verbatim and never try to re-detect.
"""

import json
import uuid
from datetime import datetime
from flask import request, jsonify

from pages.calculations_details import (
    calculate_data, normalize_row, validate_row, calc_single,
)
from utils.db import get_db
from utils.fred_config import attach_fred_to_calculation
from utils.field_mapping_engine import create_field_mapping_engine, InstrumentType
from utils.calculation_dependencies import create_calculation_dependency_engine
from utils.instrument_detection import create_instrument_detector


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def normalize_instrument_type(instrument_type):
    if not instrument_type:
        return None
    normalized = instrument_type.lower().replace('_', '-').strip()
    mapping = {
        'treasury-bills': 'tbills', 'treasury_bills': 'tbills',
        'treasury bills': 'tbills', 'tbills': 'tbills', 't-bills': 'tbills',
        'tbo': 'tbills', 'tbos': 'tbills',
        'bonds': 'bonds', 'bond': 'bonds',
        'money-market': 'money-market', 'money_market': 'money-market',
        'money market': 'money-market', 'mm': 'money-market',
    }
    return mapping.get(normalized, normalized)


def _instrument_identity(result_row):
    """
    Extract a stable identity key for an instrument result dict.
    Prefer explicit IDs; fall back to instrument name; last resort: row index.
    Returns a lower-cased string, or None if no identity can be determined.
    """
    if not isinstance(result_row, dict):
        return None
    candidates = [
        result_row.get('instrumentId'),
        result_row.get('instrument_id'),
        result_row.get('isin'),
        result_row.get('ISIN'),
        result_row.get('instrument_name'),
        result_row.get('instrumentName'),
        result_row.get('name'),
    ]
    # Also look inside 'calculation' and 'inputs'
    for nested_key in ('calculation', 'inputs', 'sourceData'):
        nested = result_row.get(nested_key)
        if isinstance(nested, dict):
            candidates.extend([
                nested.get('instrumentId'),
                nested.get('instrument_id'),
                nested.get('isin'),
                nested.get('ISIN'),
                nested.get('instrument_name'),
                nested.get('instrumentName'),
                nested.get('Instrument'),
                nested.get('Instrument ID'),
                nested.get('BondName'),
                nested.get('TBillName'),
            ])
    for c in candidates:
        if c is None:
            continue
        s = str(c).strip()
        if s and s.lower() not in ('n/a', 'na', '-', 'none', 'null'):
            return s.lower()
    return None


def _unique_instrument_count(individual_results, backend_count=0):
    """
    Return the number of UNIQUE successfully-calculated instruments.

    Preference order:
      1. backend_count if it is a positive integer
      2. count of unique identity keys from individual_results
      3. count of successful rows (last resort)
    """
    if isinstance(backend_count, int) and backend_count > 0:
        return backend_count

    if not individual_results:
        return 0

    success_rows = [r for r in (individual_results or [])
                    if isinstance(r, dict) and r.get('status') == 'success']

    if not success_rows:
        return 0

    seen = set()
    for r in success_rows:
        key = _instrument_identity(r)
        if key:
            seen.add(key)

    if seen:
        return len(seen)
    # Fallback: no identity available, count successful rows
    return len(success_rows)


def detect_instruments_from_data(data):
    """
    Detect whether a sheet has more than one instrument type.
    ONLY the 'instrument' / 'instrument_type' / 'instrument type' columns
    are treated as signals. Free-text columns like Classification,
    Category, or Asset Class are ignored so descriptive labels do not
    accidentally trigger an instrument split.
    """
    if not data:
        return {'unique_instruments': [], 'instrument_counts': {},
                'total_rows': 0, 'is_multi_instrument': False}

    instrument_column = None
    possible_names = ['instrument', 'instrument type', 'instrument_type']
    for key in data[0].keys():
        if str(key).lower().strip() in possible_names:
            instrument_column = key
            break

    if not instrument_column:
        return {'unique_instruments': [], 'instrument_counts': {},
                'total_rows': len(data), 'is_multi_instrument': False}

    values = [str(row[instrument_column]).strip() for row in data
              if row.get(instrument_column)]
    if not values:
        return {'unique_instruments': [], 'instrument_counts': {},
                'total_rows': len(data), 'is_multi_instrument': False}

    normalized = [normalize_instrument_type(v) for v in values]
    normalized = [v for v in normalized if v in ('money-market', 'bonds', 'tbills')]
    uniques = list(set(normalized))

    if len(uniques) <= 1:
        return {'unique_instruments': uniques, 'instrument_counts': {},
                'total_rows': len(data), 'is_multi_instrument': False}

    counts = {}
    for v in normalized:
        counts[v] = counts.get(v, 0) + 1

    return {
        'unique_instruments': uniques,
        'instrument_counts': counts,
        'total_rows': len(data),
        'is_multi_instrument': True,
        'instrument_column': instrument_column,
    }


def split_data_by_instrument(data, instrument_column):
    if not data or not instrument_column:
        return {}
    split = {}
    for row in data:
        v = row.get(instrument_column)
        if v:
            n = normalize_instrument_type(str(v).strip())
            if n in ('money-market', 'bonds', 'tbills'):
                split.setdefault(n, []).append(row)
    return split


# -----------------------------------------------------------------------------
# PERSISTENCE (audit history only, doesn't affect the response)
# -----------------------------------------------------------------------------

def _ensure_calculations_table(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS calculations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            calculation_id VARCHAR(64),
            instrument_type VARCHAR(64) NOT NULL,
            dataset_id VARCHAR(64),
            session_id VARCHAR(64),
            sheet_name VARCHAR(255),
            section_id VARCHAR(64),
            instrument_names JSON,
            input_data JSON,
            result_data JSON,
            calculation_status VARCHAR(32) DEFAULT 'completed',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP NULL,
            input_hash VARCHAR(64),
            INDEX (instrument_type), INDEX (dataset_id), INDEX (session_id),
            INDEX (calculation_status), INDEX (created_at),
            INDEX (input_hash), INDEX (calculation_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)


def save_calculation(instrument_type, input_data, result_data,
                     dataset_id=None, session_id=None,
                     sheet_name=None, section_id=None, instrument_names=None,
                     calculation_id=None):
    conn = get_db()
    if not conn:
        return None
    try:
        import hashlib
        cursor = conn.cursor()
        _ensure_calculations_table(cursor)
        conn.commit()
        for column_name, column_type in [
            ('sheet_name', 'VARCHAR(255)'),
            ('section_id', 'VARCHAR(64)'),
            ('input_hash', 'VARCHAR(64)'),
            ('instrument_names', 'JSON'),
            ('calculation_id', 'VARCHAR(64)'),
        ]:
            try:
                cursor.execute(f"SHOW COLUMNS FROM calculations LIKE '{column_name}'")
                if not cursor.fetchone():
                    cursor.execute(
                        f"ALTER TABLE calculations ADD COLUMN {column_name} {column_type}")
                    conn.commit()
            except Exception:
                pass

        hash_basis = {"instrument_type": instrument_type,
                      "sheet_name": sheet_name, "section_id": section_id,
                      "data": input_data}
        input_str = json.dumps(hash_basis, sort_keys=True, default=str)
        input_hash = hashlib.md5(input_str.encode()).hexdigest()

        cursor.execute(
            """SELECT id FROM calculations
               WHERE session_id = %s AND instrument_type = %s
                 AND input_hash = %s AND calculation_status = 'completed'
               ORDER BY created_at DESC LIMIT 1""",
            (session_id, instrument_type, input_hash))
        dup = cursor.fetchone()
        if dup:
            return dup['id']

        cursor.execute(
            """INSERT INTO calculations
               (calculation_id, instrument_type, dataset_id, session_id,
                sheet_name, section_id, instrument_names, input_data,
                result_data, calculation_status, completed_at, input_hash)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'completed',NOW(),%s)""",
            (calculation_id or str(uuid.uuid4()),
             instrument_type, dataset_id, session_id, sheet_name, section_id,
             json.dumps(instrument_names) if instrument_names else None,
             json.dumps(input_data, default=str),
             json.dumps(result_data, default=str),
             input_hash))
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"Save failed: {e}")
        return None


def _load_json(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return {}
    return value if value is not None else {}


# -----------------------------------------------------------------------------
# ROUTES
# -----------------------------------------------------------------------------

def calculations_routes(app):

    # ------------------------------------------------------------------ validate
    @app.route('/api/calculations/validate', methods=['POST', 'OPTIONS'])
    def calculations_validate():
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        data = payload.get('data', [])
        inst_type = normalize_instrument_type(payload.get('instrument_type'))
        valuation_date = payload.get('valuationDate') or payload.get('valuation_date')
        if not data:
            return jsonify({'status': 'error',
                            'errors': [{'field': 'data', 'code': 'empty',
                                        'message': 'No data provided'}]}), 400
        if not inst_type:
            return jsonify({'status': 'error',
                            'errors': [{'field': 'instrument_type', 'code': 'missing',
                                        'message': 'instrument_type is required'}]}), 400

        validations = []
        for idx, row in enumerate(data):
            merged = {**row}
            if valuation_date:
                merged['valuation_date'] = valuation_date
            v = validate_row(merged, inst_type)
            validations.append({
                'row_index': idx,
                'can_calculate': v['can_calculate'],
                'missing_fields': v['missing_fields'],
                'invalid_fields': v['invalid_fields'],
                'detected_fields': v['detected_fields'],
                'normalized_row': v['normalized_row'],
                'source_keys': v['all_source_keys'],
            })
        valid_count = sum(1 for v in validations if v['can_calculate'])
        return jsonify({'status': 'success', 'instrument_type': inst_type,
                        'valuation_date': valuation_date,
                        'total_rows': len(data), 'valid_rows': valid_count,
                        'invalid_rows': len(data) - valid_count,
                        'validations': validations})

    # ------------------------------------------------------------------ single
    @app.route('/api/calculations/single', methods=['POST', 'OPTIONS'])
    def calculations_single():
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        row = payload.get('data') or payload.get('row')
        inst_type = normalize_instrument_type(payload.get('instrument_type'))
        valuation_date = payload.get('valuationDate') or payload.get('valuation_date')
        currency = payload.get('currency')

        if not isinstance(row, dict) or not row:
            return jsonify({'status': 'error',
                            'errors': [{'field': 'data', 'code': 'invalid',
                                        'message': 'Single row (dict) required'}]}), 400
        if not inst_type:
            return jsonify({'status': 'error',
                            'errors': [{'field': 'instrument_type', 'code': 'missing',
                                        'message': 'instrument_type is required'}]}), 400

        result = calc_single(row, inst_type, valuation_date=valuation_date)
        if result['status'] != 'success':
            return jsonify({
                'status': 'error',
                'calculationId': None,
                'instrumentId': result['instrumentId'],
                'instrumentType': inst_type,
                'inputs': result.get('inputs', {}),
                'sourceData': result.get('sourceData', row),
                'errors': result.get('errors', []),
            }), 400

        calculation_id = str(uuid.uuid4())
        response = {
            'calculationId': calculation_id,
            'status': 'success',
            'valuationDate': valuation_date,
            'instrumentId': result['instrumentId'],
            'instrumentType': inst_type,
            'currency': currency,
            'inputs': result['inputs'],
            'calculation': result['calculation'],
            'valuation': result['valuation'],
            'methodology': f'{inst_type}-v1',
            'sourceData': row,
            'warnings': [],
        }
        try:
            attach_fred_to_calculation(response, inst_type,
                                       payload.get('maturity'),
                                       payload.get('country'), currency)
        except Exception as e:
            print(f"FRED failed: {e}")
        return jsonify(response)

    # ------------------------------------------------------------------ multiple
    @app.route('/api/calculations/multiple', methods=['POST', 'OPTIONS'])
    def calculations_multiple():
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        data = payload.get('data', [])
        inst_type = normalize_instrument_type(payload.get('instrument_type'))
        valuation_date = payload.get('valuationDate') or payload.get('valuation_date')
        currency = payload.get('currency')
        session_id = payload.get('session_id')
        dataset_id = payload.get('dataset_id')
        sheet_name = payload.get('sheet_name')
        section_id = payload.get('section_id')

        if not isinstance(data, list) or not data:
            return jsonify({'status': 'error',
                            'errors': [{'field': 'data', 'code': 'empty',
                                        'message': 'No data provided'}]}), 400
        if not inst_type:
            return jsonify({'status': 'error',
                            'errors': [{'field': 'instrument_type', 'code': 'missing',
                                        'message': 'instrument_type is required'}]}), 400

        # The caller supplies the instrument_type (based on the page the user
        # is on). We do NOT try to re-detect from a Classification-like column,
        # because free-text labels like "ZWG MM" would be misinterpreted as
        # instrument types and break the calculation for every row.
        merged = []
        for row in data:
            r = {**row}
            if valuation_date:
                r['valuation_date'] = valuation_date
            merged.append(r)

        calc_result = calculate_data(merged, inst_type, valuation_date=valuation_date)
        try:
            attach_fred_to_calculation(calc_result, inst_type,
                                       payload.get('maturity'),
                                       payload.get('country'), currency)
        except Exception as e:
            print(f"FRED failed: {e}")

        individual = []
        for idx, calc in enumerate(calc_result.get('calculations', [])):
            src = data[idx] if idx < len(data) else {}
            v = validate_row(src, inst_type)

            # Include the original input row so the frontend can dedupe
            # consistently on instrument identity even when the backend
            # calculation dict itself omits the name/id.
            merged_inputs = {**v['normalized_row']}
            for k, val in src.items():
                if k not in merged_inputs and val not in (None, ''):
                    merged_inputs[k] = val

            individual.append({
                'rowIndex': idx,
                'instrumentId': calc.get('instrument_name') or f'instrument-{idx+1}',
                'instrument_name': calc.get('instrument_name'),
                'instrumentType': inst_type,
                'status': calc.get('status', 'cannot_calculate'),
                'inputs': merged_inputs,
                'sourceData': src,
                'calculation': calc,
                'valuation': {
                    'total_value': calc.get('total_value'),
                    'principal': calc.get('principal'),
                    'face_value': calc.get('face_value'),
                    'interest_earned': calc.get('interest_earned'),
                    'effective_yield': calc.get('effective_yield'),
                    'yield_to_maturity': calc.get('yield_to_maturity'),
                },
                'errors': [] if calc.get('status') == 'success' else [
                    {'field': 'calculation', 'code': 'failed',
                     'message': calc.get('error', 'Cannot calculate')}],
            })

        success_count = sum(1 for r in individual if r['status'] == 'success')
        failure_count = len(individual) - success_count

        # ── FIX: use UNIQUE instrument count, not raw row count ───────────
        backend_count = calc_result.get('instrument_count', 0)
        unique_count = _unique_instrument_count(individual, backend_count)

        calc_id = str(uuid.uuid4())
        response = {
            'calculationId': calc_id,
            'status': 'success' if success_count > 0 else 'error',
            'valuationDate': valuation_date,
            'instrumentType': inst_type,
            'currency': currency,
            'totalRows': len(data),
            'successCount': success_count,
            'failedCount': failure_count,
            'results': individual,
            'aggregates': calc_result.get('aggregates', {}),
            'fred': calc_result.get('fred'),
            'instrument_names': [],
            'calculations': calc_result.get('calculations', []),
            'instrument_count': unique_count,
            'warnings': [],
        }

        # Make sure the aggregate dict also reports the corrected count
        if isinstance(response['aggregates'], dict):
            response['aggregates']['instrument_count'] = unique_count

        try:
            save_calculation(inst_type, data, response,
                             dataset_id=dataset_id, session_id=session_id,
                             sheet_name=sheet_name, section_id=section_id,
                             calculation_id=calc_id)
        except Exception as e:
            print(f"Save failed: {e}")

        if success_count == 0:
            return jsonify(response), 400
        return jsonify(response)

    # ------------------------------------------------------------------ portfolio
    @app.route('/api/calculations/portfolio', methods=['POST', 'OPTIONS'])
    def calculations_portfolio():
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        per_type = payload.get('results', {})
        currency = payload.get('currency')
        total = 0.0
        count = 0
        failed = 0
        by_type = {}
        for itype, res in per_type.items():
            agg = (res or {}).get('aggregates', {}) or {}
            tv = agg.get('total_value') or agg.get('total_market_value') or agg.get('total_face_value') or 0
            ic = agg.get('instrument_count') or 0
            fc = agg.get('failed_count') or 0
            total += float(tv or 0)
            count += int(ic or 0)
            failed += int(fc or 0)
            by_type[itype] = {'total_value': tv, 'instrument_count': ic, 'failed_count': fc}
        return jsonify({'status': 'success', 'portfolio_total': total,
                        'total_instrument_count': count, 'total_failed_count': failed,
                        'by_type': by_type, 'currency': currency})

    # ------------------------------------------------------------------ get by id
    @app.route('/api/calculations/<calculation_id>', methods=['GET', 'OPTIONS'])
    def calculations_get_by_id(calculation_id):
        if request.method == 'OPTIONS':
            return '', 200
        conn = get_db()
        if not conn:
            return jsonify({'status': 'error', 'errors': [
                {'field': 'db', 'code': 'unavailable',
                 'message': 'Database unavailable'}]}), 500
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM calculations WHERE calculation_id = %s LIMIT 1",
                           (calculation_id,))
            row = cursor.fetchone()
            cursor.close(); conn.close()
            if not row:
                return jsonify({'status': 'error', 'errors': [
                    {'field': 'calculationId', 'code': 'not_found',
                     'message': f'Calculation {calculation_id} not found'}]}), 404
            return jsonify({
                'status': 'success',
                'calculationId': row.get('calculation_id'),
                'instrumentType': row.get('instrument_type'),
                'createdAt': row.get('created_at').isoformat() if row.get('created_at') else None,
                'inputData': _load_json(row.get('input_data')),
                'resultData': _load_json(row.get('result_data')),
            })
        except Exception as e:
            return jsonify({'status': 'error', 'errors': [
                {'field': 'db', 'code': 'error', 'message': str(e)}]}), 500

    # ------------------------------------------------------------------ recalculate
    @app.route('/api/calculations/recalculate', methods=['POST', 'OPTIONS'])
    def calculations_recalculate():
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        data = payload.get('data', [])
        inst_type = normalize_instrument_type(payload.get('instrument_type'))
        valuation_date = payload.get('valuationDate') or payload.get('valuation_date')
        if not data:
            return jsonify({'status': 'error', 'errors': [
                {'field': 'data', 'code': 'empty',
                 'message': 'No data provided'}]}), 400
        merged = []
        for row in data:
            r = {**row}
            if valuation_date:
                r['valuation_date'] = valuation_date
            merged.append(r)
        calc_result = calculate_data(merged, inst_type, valuation_date=valuation_date)
        try:
            attach_fred_to_calculation(calc_result, inst_type, payload.get('maturity'),
                                       payload.get('country'), payload.get('currency'))
        except Exception:
            pass

        # Build a result-shaped list to compute a unique instrument count
        calc_list = calc_result.get('calculations', [])
        individual = []
        for idx, calc in enumerate(calc_list):
            individual.append({
                'instrumentId': calc.get('instrument_name') or f'instrument-{idx+1}',
                'instrument_name': calc.get('instrument_name'),
                'status': calc.get('status', 'cannot_calculate'),
            })
        unique_count = _unique_instrument_count(
            individual, calc_result.get('instrument_count', 0)
        )

        if isinstance(calc_result.get('aggregates'), dict):
            calc_result['aggregates']['instrument_count'] = unique_count

        calc_id = str(uuid.uuid4())
        return jsonify({
            'calculationId': calc_id,
            'status': 'success' if unique_count > 0 else 'error',
            'valuationDate': valuation_date,
            'instrumentType': inst_type,
            'currency': payload.get('currency'),
            'results': calc_result.get('calculations', []),
            'aggregates': calc_result.get('aggregates', {}),
            'fred': calc_result.get('fred'),
            'instrument_count': unique_count,
            'warnings': [],
        })

    # -------------------------------------------------------- legacy endpoints
    def _legacy_per_type(inst_type):
        endpoint_name = f'legacy_calculate_{inst_type.replace("-", "_")}'

        @app.route(f'/api/calculate/{inst_type}',
                   methods=['POST', 'OPTIONS'],
                   endpoint=endpoint_name)
        def _handler():
            if request.method == 'OPTIONS':
                return '', 200
            payload = request.get_json() or {}
            data = payload.get('data', [])
            valuation_date = payload.get('valuationDate') or payload.get('valuation_date')
            if not data:
                return jsonify({'success': False, 'status': 'error',
                                'message': 'No data provided'}), 400
            result = calculate_data(data, inst_type, valuation_date=valuation_date)
            try:
                attach_fred_to_calculation(result, inst_type,
                                           payload.get('maturity'),
                                           payload.get('country'),
                                           payload.get('currency'))
            except Exception:
                pass

            # Fix the aggregate instrument_count on legacy responses too
            calc_list = result.get('calculations', [])
            individual = [{
                'instrumentId': c.get('instrument_name') or f'instrument-{i+1}',
                'instrument_name': c.get('instrument_name'),
                'status': c.get('status', 'cannot_calculate'),
            } for i, c in enumerate(calc_list)]
            unique_count = _unique_instrument_count(
                individual, result.get('instrument_count', 0)
            )
            if isinstance(result.get('aggregates'), dict):
                result['aggregates']['instrument_count'] = unique_count
            result['instrument_count'] = unique_count

            return jsonify({
                'success': True,
                'is_multi_instrument': False,
                'instrument_type': inst_type,
                'data': result,
                'instrument_names': [],
                'instrument_summary': {'columns': [], 'rows': []},
                'portfolio_summary': {'columns': [], 'rows': [],
                                      'portfolio_total': 0, 'instrument_counts': {}},
            })
        return _handler

    _legacy_per_type('tbills')
    _legacy_per_type('bonds')
    _legacy_per_type('money-market')

    @app.route('/api/calculate', methods=['POST', 'OPTIONS'])
    def calculate_legacy():
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        inst_type = normalize_instrument_type(payload.get('instrument_type'))
        data = payload.get('data', [])
        valuation_date = payload.get('valuationDate') or payload.get('valuation_date')
        if not data:
            return jsonify({'success': False, 'status': 'error',
                            'message': 'No uploaded data'}), 400
        result = calculate_data(data, inst_type, valuation_date=valuation_date)
        try:
            attach_fred_to_calculation(result, inst_type, payload.get('maturity'),
                                       payload.get('country'), payload.get('currency'))
        except Exception:
            pass

        calc_list = result.get('calculations', [])
        individual = [{
            'instrumentId': c.get('instrument_name') or f'instrument-{i+1}',
            'instrument_name': c.get('instrument_name'),
            'status': c.get('status', 'cannot_calculate'),
        } for i, c in enumerate(calc_list)]
        unique_count = _unique_instrument_count(
            individual, result.get('instrument_count', 0)
        )
        if isinstance(result.get('aggregates'), dict):
            result['aggregates']['instrument_count'] = unique_count
        result['instrument_count'] = unique_count

        return jsonify({'success': True, 'data': result})

    @app.route('/api/calculate/comprehensive', methods=['POST', 'OPTIONS'])
    def calculate_comprehensive():
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        data = payload.get('data', [])
        valuation_date = payload.get('valuationDate') or payload.get('valuation_date')
        if not data:
            return jsonify({'success': False, 'status': 'error',
                            'message': 'No uploaded data'}), 400
        detection = detect_instruments_from_data(data)
        if detection.get('is_multi_instrument'):
            split = split_data_by_instrument(data, detection.get('instrument_column'))
            all_results = {}
            for itype, subset in split.items():
                if not subset:
                    continue
                r = calculate_data(subset, itype, valuation_date=valuation_date)

                calc_list = r.get('calculations', [])
                individual = [{
                    'instrumentId': c.get('instrument_name') or f'instrument-{i+1}',
                    'instrument_name': c.get('instrument_name'),
                    'status': c.get('status', 'cannot_calculate'),
                } for i, c in enumerate(calc_list)]
                unique_count = _unique_instrument_count(
                    individual, r.get('instrument_count', 0)
                )
                if isinstance(r.get('aggregates'), dict):
                    r['aggregates']['instrument_count'] = unique_count
                r['instrument_count'] = unique_count

                all_results[itype] = {'data': r, 'row_count': len(subset)}
            return jsonify({'success': True, 'is_multi_instrument': True,
                            'instrument_detection': detection,
                            'results': all_results,
                            'calculation_count': len(all_results)})
        detector = create_instrument_detector()
        det = detector.detect_from_data(data)
        inst_type = det.instrument_type or 'money-market'
        result = calculate_data(data, inst_type, valuation_date=valuation_date)

        calc_list = result.get('calculations', [])
        individual = [{
            'instrumentId': c.get('instrument_name') or f'instrument-{i+1}',
            'instrument_name': c.get('instrument_name'),
            'status': c.get('status', 'cannot_calculate'),
        } for i, c in enumerate(calc_list)]
        unique_count = _unique_instrument_count(
            individual, result.get('instrument_count', 0)
        )
        if isinstance(result.get('aggregates'), dict):
            result['aggregates']['instrument_count'] = unique_count
        result['instrument_count'] = unique_count

        return jsonify({'success': True, 'is_multi_instrument': False,
                        'instrument_type': inst_type, 'data': result})

    # -------------------------------------------------------- summaries
    @app.route('/api/calculations/history', methods=['GET', 'OPTIONS'])
    def calculations_history():
        if request.method == 'OPTIONS':
            return '', 200
        conn = get_db()
        if not conn:
            return jsonify({'success': True, 'data': []})
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, instrument_type, dataset_id, session_id, "
                           "calculation_status, created_at FROM calculations "
                           "ORDER BY created_at DESC LIMIT 20")
            rows = cursor.fetchall()
            cursor.close(); conn.close()
            return jsonify({'success': True, 'data': [{
                'id': r['id'], 'instrument_type': r['instrument_type'],
                'dataset_id': r['dataset_id'], 'session_id': r['session_id'],
                'status': r['calculation_status'],
                'created_at': r['created_at'].isoformat() if r['created_at'] else None,
            } for r in rows]})
        except Exception:
            return jsonify({'success': True, 'data': []})

    @app.route('/api/calculations/latest', methods=['GET', 'OPTIONS'])
    def calculations_latest():
        if request.method == 'OPTIONS':
            return '', 200
        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'DB unavailable'}), 500
        try:
            cursor = conn.cursor()
            dataset_id = request.args.get('dataset_id')
            session_id = request.args.get('session_id')
            if dataset_id:
                cursor.execute("SELECT * FROM calculations WHERE dataset_id = %s "
                               "ORDER BY created_at DESC LIMIT 1", (dataset_id,))
            elif session_id:
                cursor.execute("SELECT * FROM calculations WHERE session_id = %s "
                               "ORDER BY created_at DESC LIMIT 1", (session_id,))
            else:
                cursor.execute("SELECT * FROM calculations ORDER BY created_at DESC LIMIT 1")
            row = cursor.fetchone()
            cursor.close(); conn.close()
            if not row:
                return jsonify({'success': False, 'message': 'Not found'}), 404
            return jsonify({'success': True, 'data': {
                'id': row.get('id'),
                'instrument_type': row.get('instrument_type'),
                'result_data': _load_json(row.get('result_data')),
                'status': row.get('calculation_status'),
                'created_at': row.get('created_at').isoformat() if row.get('created_at') else None,
            }})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/calculations/instrument-summary', methods=['POST', 'OPTIONS'])
    def instrument_summary():
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        session_id = payload.get('session_id')
        if not session_id:
            return jsonify({'success': False, 'message': 'session_id required'}), 400
        conn = get_db()
        if not conn:
            return jsonify({'success': True, 'data': {'columns': [], 'rows': []}})
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM calculations WHERE session_id = %s "
                           "ORDER BY created_at DESC", (session_id,))
            rows = cursor.fetchall()
            cursor.close(); conn.close()
            summary_rows = []
            for row in rows:
                result_data = _load_json(row.get('result_data'))
                calcs = result_data.get('calculations') or result_data.get('results') or []
                if isinstance(calcs, list):
                    for c in calcs:
                        if not isinstance(c, dict):
                            continue
                        summary_rows.append({
                            'Instrument Name': c.get('instrument_name') or c.get('instrumentId') or 'Instrument',
                            'Instrument Type': row.get('instrument_type'),
                            **c,
                        })
            cols = set()
            for r in summary_rows:
                cols.update(r.keys())
            return jsonify({'success': True,
                            'data': {'columns': sorted(cols), 'rows': summary_rows}})
        except Exception:
            return jsonify({'success': True, 'data': {'columns': [], 'rows': []}})

    @app.route('/api/calculations/portfolio-summary', methods=['POST', 'OPTIONS'])
    def portfolio_summary():
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        session_id = payload.get('session_id')
        if not session_id:
            return jsonify({'success': False, 'message': 'session_id required'}), 400
        conn = get_db()
        if not conn:
            return jsonify({'success': True, 'data': {
                'columns': [], 'rows': [], 'portfolio_total': 0, 'instrument_counts': {}}})
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM calculations WHERE session_id = %s "
                           "ORDER BY created_at DESC", (session_id,))
            rows = cursor.fetchall()
            cursor.close(); conn.close()
            portfolio_rows = []
            portfolio_total = 0
            instrument_counts = {}
            seen = set()
            for row in rows:
                cid = row.get('id')
                if cid in seen:
                    continue
                seen.add(cid)
                result_data = _load_json(row.get('result_data'))
                agg = result_data.get('aggregates', {}) or {}
                tv = agg.get('total_value') or agg.get('total_market_value') or agg.get('total_face_value') or 0
                portfolio_total += float(tv or 0)

                # Fix: derive a unique count from stored results if the
                # stored aggregate is wrong (old rows pre-fix).
                stored_count = agg.get('instrument_count') or 0
                stored_results = result_data.get('results') or result_data.get('calculations') or []
                unique_count = _unique_instrument_count(stored_results, stored_count)

                itype = row.get('instrument_type')
                instrument_counts[itype] = instrument_counts.get(itype, 0) + int(unique_count or 0)
                portfolio_rows.append({
                    'Instrument Type': itype, 'Total Value': tv,
                    'Instrument Count': unique_count,
                    'Failed Count': agg.get('failed_count') or 0,
                    'Calculation ID': cid,
                })
            return jsonify({'success': True, 'data': {
                'columns': ['Instrument Type', 'Total Value', 'Instrument Count',
                            'Failed Count', 'Calculation ID'],
                'rows': portfolio_rows,
                'portfolio_total': portfolio_total,
                'instrument_counts': instrument_counts,
            }})
        except Exception:
            return jsonify({'success': True, 'data': {
                'columns': [], 'rows': [], 'portfolio_total': 0, 'instrument_counts': {}}})

    @app.route('/api/calculations/session/<session_id>', methods=['GET', 'OPTIONS'])
    def calculations_by_session(session_id):
        if request.method == 'OPTIONS':
            return '', 200
        conn = get_db()
        if not conn:
            return jsonify({'success': True, 'data': []})
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM calculations WHERE session_id = %s "
                           "ORDER BY created_at DESC", (session_id,))
            rows = cursor.fetchall()
            cursor.close(); conn.close()
            return jsonify({'success': True, 'data': [{
                'id': r.get('id'),
                'instrument_type': r.get('instrument_type'),
                'result_data': _load_json(r.get('result_data')),
                'status': r.get('calculation_status'),
                'created_at': r.get('created_at').isoformat() if r.get('created_at') else None,
            } for r in rows]})
        except Exception:
            return jsonify({'success': True, 'data': []})

    @app.route('/api/calculations/session-workflows/<session_id>', methods=['GET', 'OPTIONS'])
    def session_workflows(session_id):
        if request.method == 'OPTIONS':
            return '', 200
        conn = get_db()
        if not conn:
            return jsonify({'success': True, 'data': {}})
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT instrument_workflows FROM ui_sessions WHERE session_id = %s",
                           (session_id,))
            row = cursor.fetchone()
            cursor.close(); conn.close()
            if row and row.get('instrument_workflows'):
                try:
                    v = row['instrument_workflows']
                    return jsonify({'success': True,
                                    'data': json.loads(v) if isinstance(v, str) else v})
                except Exception:
                    return jsonify({'success': True, 'data': {}})
            return jsonify({'success': True, 'data': {}})
        except Exception:
            return jsonify({'success': True, 'data': {}})


def auto_detect_instrument_type(inputs: dict) -> str:
    if inputs.get('discount_rate') and not inputs.get('coupon_rate'):
        return 'tbills'
    if inputs.get('coupon_rate') and inputs.get('years_to_maturity'):
        return 'bonds'
    if inputs.get('interest_rate') and inputs.get('principal'):
        return 'money-market'
    return None
import json
import math
import re
import uuid
from contextlib import contextmanager
from flask import request, jsonify

from pages.calculations_details import (
    calculate_data, validate_row, calc_single, normalize_row, parse_date,
)
from utils.db import get_db
from utils.auth import resolve_current_user, session_is_owned
from utils.fred_config import attach_fred_to_calculation, get_market_benchmark
from utils.instrument_detection import create_instrument_detector


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


def _to_snake_case(name):
    """Normalise a column name so camelCase / snake_case / spaced variants
    all collapse to the same key. Words are preserved so genuinely
    different columns (e.g. face_value vs current_price) stay distinct."""
    s = str(name).strip()
    s = re.sub(r'[\s\-]+', '_', s)
    s = re.sub(r'(?<=[a-z0-9])([A-Z])', r'_\1', s)
    return s.lower()


def dedupe_columns(columns):
    """Keep only the first occurrence of each semantically-identical column.

    Two columns are considered identical when their snake_case forms match.
    Example: face_value / faceValue / Face Value -> keep only the first.
    Example: face_value / current_price -> both kept, they are different.
    """
    seen = set()
    kept = []
    for col in columns:
        key = _to_snake_case(col)
        if key in seen:
            continue
        seen.add(key)
        kept.append(col)
    return kept


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
    if not isinstance(result_row, dict):
        return None
    candidates = [
        result_row.get('instrumentId'),
        result_row.get('instrument_id'),
        result_row.get('isin'), result_row.get('ISIN'),
        result_row.get('instrument_name'), result_row.get('instrumentName'),
        result_row.get('name'),
    ]
    for nested_key in ('calculation', 'inputs', 'sourceData'):
        nested = result_row.get(nested_key)
        if isinstance(nested, dict):
            candidates.extend([
                nested.get('instrumentId'), nested.get('instrument_id'),
                nested.get('isin'), nested.get('ISIN'),
                nested.get('instrument_name'), nested.get('instrumentName'),
                nested.get('Instrument'), nested.get('Instrument ID'),
                nested.get('BondName'), nested.get('TBillName'),
            ])
    for c in candidates:
        if c is None:
            continue
        s = str(c).strip()
        if s and s.lower() not in ('n/a', 'na', '-', 'none', 'null'):
            return s.lower()
    fingerprint_fields = (
        'face_value', 'principal', 'interest_rate', 'coupon_rate',
        'discount_rate', 'term_days', 'days_to_maturity',
        'maturity_date', 'currency',
    )
    fingerprint = []
    for field in fingerprint_fields:
        value = result_row.get(field)
        if value is None or str(value).strip() == '':
            continue
        fingerprint.append(f'{field}:{str(value).strip().lower()}')
    if fingerprint:
        return '|'.join(fingerprint)
    return None


def _unique_instrument_count(individual_results, backend_count=0):
    """Count distinct instruments.

    Partial rows (e.g. bond with defaulted frequency) count as real
    instruments. Rows with no identity get counted individually so we
    never silently under-count a workbook.
    """
    if isinstance(backend_count, int) and backend_count > 0:
        return backend_count
    if not individual_results:
        return 0
    counted = [r for r in (individual_results or [])
               if isinstance(r, dict)
               and r.get('status') in ('success', 'partial')]
    if not counted:
        return 0
    seen = set()
    unnamed = 0
    for r in counted:
        key = _instrument_identity(r)
        if key:
            seen.add(key)
        else:
            unnamed += 1
    return len(seen) + unnamed


def _resolve_instrument_name(rows, sheet_name):
    """Only inject sheet_name when the row has no usable name.

    Checks every alias that could carry an instrument identity, so a row
    that already had 'Instrument Name' (or ISIN / Ticker / etc.) is left
    untouched. Prevents sheet_name from clobbering a genuine instrument
    name downstream.
    """
    if not sheet_name:
        return rows
    name = str(sheet_name).strip()
    if not name:
        return rows

    def _row_has_name(row):
        if not isinstance(row, dict):
            return False
        for key in ('instrument_name', 'Instrument Name', 'instrumentName',
                    'instrument', 'Instrument', 'security', 'Security',
                    'name', 'Name', 'bondname', 'BondName',
                    'tbillname', 'TBillName', 'Security Name',
                    'Instrument ID', 'ISIN', 'isin', 'Ticker', 'ticker',
                    'Symbol', 'symbol'):
            v = row.get(key)
            if v is None:
                continue
            s = str(v).strip()
            if s and s.lower() not in ('n/a', 'na', '-', 'none', 'null'):
                return True
        return False

    if isinstance(rows, dict):
        if _row_has_name(rows):
            return rows
        updated = dict(rows)
        updated['instrument_name'] = name
        return updated

    if not isinstance(rows, list) or len(rows) != 1:
        return rows
    row = rows[0]
    if not isinstance(row, dict) or _row_has_name(row):
        return rows
    updated = dict(row)
    updated['instrument_name'] = name
    return [updated]


def _apply_currency_fallback(rows, currency):
    if not currency:
        return rows
    fallback = str(currency).strip().upper()
    if not fallback:
        return rows

    def apply(row):
        if not isinstance(row, dict):
            return row
        if normalize_row(row).get('currency'):
            return row
        return {**row, 'currency': fallback}

    if isinstance(rows, dict):
        return apply(rows)
    if isinstance(rows, list):
        return [apply(row) for row in rows]
    return rows


def detect_instruments_from_data(data):
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
            calculation_status ENUM('pending','processing','completed','failed') DEFAULT 'pending',
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
    cursor = None
    try:
        import hashlib
        cursor = conn.cursor()
        _ensure_calculations_table(cursor)
        conn.commit()

        hash_basis = {"instrument_type": instrument_type,
                      "sheet_name": sheet_name, "section_id": section_id,
                      "data": input_data}
        input_str = json.dumps(hash_basis, sort_keys=True, default=str)
        input_hash = hashlib.sha256(input_str.encode()).hexdigest()
        calculation_rows = result_data.get('data', {}).get('calculations', [])
        if not calculation_rows:
            calculation_rows = result_data.get('calculations', [])
        statuses = [row.get('status') for row in calculation_rows if isinstance(row, dict)]
        if statuses and all(status == 'success' for status in statuses):
            stored_status = 'completed'
        elif any(status in ('success', 'partial') for status in statuses):
            stored_status = 'completed'
        else:
            stored_status = 'failed'

        cursor.execute(
            """INSERT INTO calculations
               (calculation_id, instrument_type, dataset_id, session_id,
                sheet_name, section_id, instrument_names, input_data,
                result_data, calculation_status, completed_at, input_hash)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),%s)""",
            (calculation_id or str(uuid.uuid4()),
             instrument_type, dataset_id, session_id, sheet_name, section_id,
             json.dumps(instrument_names) if instrument_names else None,
             json.dumps(input_data, default=str),
             json.dumps(result_data, default=str),
             stored_status,
             input_hash))
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        raise RuntimeError(f"Could not persist calculation: {e}") from e
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        try:
            conn.close()
        except Exception:
            pass


def _load_json(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return {}
    return value if value is not None else {}


def _fetch_benchmark(inst_type, maturity, country, currency):
    try:
        benchmark = get_market_benchmark(inst_type, maturity, country, currency)
        print(f"[BENCHMARK-TRACE] type={inst_type} maturity={maturity} "
              f"country={country} currency={currency} -> "
              f"benchmark_rate={benchmark.get('benchmark_rate')}")
        if benchmark.get('benchmark_rate') is not None:
            return benchmark['benchmark_rate']
    except Exception as e:
        print(f"FRED benchmark fetch failed: {e}")
    return None


def _provided_benchmark(payload):
    value = payload.get('benchmark_yield')
    if value is None or value == '':
        return None
    try:
        benchmark = float(value)
    except (TypeError, ValueError):
        raise ValueError('benchmark_yield must be a finite number')
    if not math.isfinite(benchmark):
        raise ValueError('benchmark_yield must be a finite number')
    return benchmark


def _attach_fred(result, inst_type, maturity, country, currency):
    try:
        attach_fred_to_calculation(result, inst_type, maturity, country, currency)
    except Exception as e:
        print(f"FRED failed: {e}")


def _fix_instrument_count(result):
    calc_list = result.get('calculations', [])
    unique_count = _unique_instrument_count(calc_list)
    if isinstance(result.get('aggregates'), dict):
        result['aggregates']['instrument_count'] = unique_count
    result['instrument_count'] = unique_count
    return unique_count


def _owned_calculation_scope(cursor, user_id, session_id=None, dataset_id=None):
    if session_id and not session_is_owned(cursor, session_id, user_id):
        return False
    if dataset_id:
        cursor.execute(
            'SELECT id FROM datasets WHERE id = %s AND user_id = %s LIMIT 1',
            (dataset_id, user_id)
        )
        if not cursor.fetchone():
            return False
    return bool(session_id or dataset_id)


def _authenticated_user():
    user_id, auth_error = resolve_current_user()
    if auth_error:
        status, message = auth_error
        return None, (jsonify({'success': False, 'message': message}), status)
    return user_id, None


_DERIVATION_LABELS = {
    'days_to_maturity': 'Days to Maturity',
    'interest_earned': 'Interest Earned',
    'total_value': 'Total Value / Maturity Value',
    'discount_yield': 'Discount Yield',
    'effective_annual_rate': 'Effective Annual Rate',
    'bond_equivalent_yield': 'Bond Equivalent Yield',
    'effective_yield': 'Effective Yield',
    'present_value': 'Present Value',
    'fair_value': 'Fair Value',
    'purchase_price': 'Purchase Price',
    'discount_amount': 'Discount Amount',
    'discount_rate': 'Discount Rate',
    'money_market_yield': 'Money-Market Yield',
    'holding_period_yield': 'Holding Period Yield',
    'effective_annual_yield': 'Effective Annual Yield',
    'annual_coupon': 'Annual Coupon',
    'coupon_payment': 'Coupon per Period',
    'current_price': 'Current Price',
    'yield_to_maturity': 'Yield to Maturity',
    'current_yield': 'Current Yield',
    'price_per_100': 'Price per 100',
    'days_accrued': 'Days Accrued',
    'accrued_interest': 'Accrued Interest',
    'macaulay_duration': 'Macaulay Duration',
    'modified_duration': 'Modified Duration',
    'convexity': 'Convexity',
    'dv01': 'DV01',
}


def _build_display_derivations(calc):
    """Flatten backend derivations into an ordered, label-friendly list
    that the frontend breakdown popup can render directly."""
    derivations = (calc or {}).get('derivations') or {}
    if not isinstance(derivations, dict):
        return []
    out = []
    for name, d in derivations.items():
        if not isinstance(d, dict):
            continue
        out.append({
            'name': name,
            'label': d.get('display_label') or _DERIVATION_LABELS.get(name, name),
            'formula': d.get('formula', ''),
            'inputs': d.get('display_inputs') or d.get('inputs') or {},
            'result': d.get('result'),
            'raw': d.get('result_raw'),
            'unit': d.get('unit', 'number'),
            'status': d.get('status', 'unknown'),
            'error': d.get('error'),
            'dependencies': d.get('dependencies', []),
        })
    return out


def calculations_routes(app):

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
            cleaned_date = parse_date(
                normalize_row(row).get('valuation_date')
            )
            if valuation_date and cleaned_date is None:
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

    @app.route('/api/calculations/single', methods=['POST', 'OPTIONS'])
    def calculations_single():
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        row = payload.get('data') or payload.get('row')
        inst_type = normalize_instrument_type(payload.get('instrument_type'))
        valuation_date = payload.get('valuationDate') or payload.get('valuation_date')
        currency = payload.get('currency')
        maturity = payload.get('maturity')
        country = payload.get('country')
        sheet_name = payload.get('sheet_name')

        if not isinstance(row, dict) or not row:
            return jsonify({'status': 'error',
                            'errors': [{'field': 'data', 'code': 'invalid',
                                        'message': 'Single row (dict) required'}]}), 400
        if not inst_type:
            return jsonify({'status': 'error',
                            'errors': [{'field': 'instrument_type', 'code': 'missing',
                                        'message': 'instrument_type is required'}]}), 400

        row = _resolve_instrument_name(row, sheet_name)
        row = _apply_currency_fallback(row, currency)
        benchmark_yield = _fetch_benchmark(inst_type, maturity, country, currency)

        result = calc_single(row, inst_type, valuation_date=valuation_date,
                             benchmark_yield=benchmark_yield)

        calculation_id = str(uuid.uuid4())
        response = {
            'calculationId': calculation_id,
            'status': result['status'],
            'valuationDate': valuation_date,
            'instrumentId': result['instrumentId'],
            'instrumentType': inst_type,
            'currency': currency,
            'inputs': result['inputs'],
            'calculation': result['calculation'],
            'derivations': (result['calculation'] or {}).get('derivations', {}),
            'display_derivations': _build_display_derivations(result['calculation']),
            'valuation': result['valuation'],
            'methodology': f'{inst_type}-v1',
            'sourceData': row,
            'missing_fields': result.get('missing_fields', []),
            'invalid_fields': result.get('invalid_fields', []),
            'errors': result.get('errors', []),
            'warnings': [],
        }
        _attach_fred(response, inst_type, maturity, country, currency)

        if result['status'] == 'error' and not result['calculation']:
            return jsonify(response), 400
        return jsonify(response)

    @app.route('/api/calculations/multiple', methods=['POST', 'OPTIONS'])
    def calculations_multiple():
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        data = payload.get('data', [])
        inst_type = normalize_instrument_type(payload.get('instrument_type'))
        valuation_date = payload.get('valuationDate') or payload.get('valuation_date')
        currency = payload.get('currency')
        maturity = payload.get('maturity')
        country = payload.get('country')
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
        if session_id or dataset_id:
            user_id, auth_response = _authenticated_user()
            if auth_response:
                return auth_response
            with _db() as (conn, cursor):
                if not conn:
                    return jsonify({'success': False, 'message': 'Database unavailable'}), 503
                try:
                    if not _owned_calculation_scope(cursor, user_id, session_id, dataset_id):
                        return jsonify({'success': False, 'message': 'Session or dataset not found'}), 404
                except Exception as error:
                    return jsonify({'success': False, 'message': 'Could not verify calculation ownership'}), 500

        data = _resolve_instrument_name(data, sheet_name)
        data = _apply_currency_fallback(data, currency)

        merged = []
        for row in data:
            merged.append(dict(row))

        benchmark_yield = _fetch_benchmark(inst_type, maturity, country, currency)
        calc_result = calculate_data(merged, inst_type, valuation_date=valuation_date,
                                     benchmark_yield=benchmark_yield)
        _attach_fred(calc_result, inst_type, maturity, country, currency)

        individual = []
        for idx, calc in enumerate(calc_result.get('calculations', [])):
            src = data[idx] if idx < len(data) else {}
            v = validate_row(src, inst_type)
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
                'derivations': calc.get('derivations', {}),
                'display_derivations': _build_display_derivations(calc),
                'validation_errors': calc.get('validation_errors', []),
                'valuation': {
                    'total_value': calc.get('total_value'),
                    'principal': calc.get('principal'),
                    'face_value': calc.get('face_value'),
                    'interest_earned': calc.get('interest_earned'),
                    'effective_yield': calc.get('effective_yield'),
                    'yield_to_maturity': calc.get('yield_to_maturity'),
                },
                'errors': [] if calc.get('status') in ('success', 'partial') else [
                    {'field': 'calculation', 'code': 'failed',
                     'message': calc.get('error', 'Cannot calculate')}],
            })

        success_count = sum(1 for r in individual if r['status'] in ('success', 'partial'))
        failure_count = len(individual) - success_count

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

        if isinstance(response['aggregates'], dict):
            response['aggregates']['instrument_count'] = unique_count

        if session_id or dataset_id:
            try:
                saved_id = save_calculation(
                    inst_type, data, response,
                    dataset_id=dataset_id, session_id=session_id,
                    sheet_name=sheet_name, section_id=section_id,
                    calculation_id=calc_id)
            except Exception as error:
                print(f"Save failed: {error}")
                return jsonify({'success': False, 'message': 'Calculation completed but could not be saved'}), 500
            if not saved_id:
                return jsonify({'success': False, 'message': 'Calculation completed but could not be saved'}), 500

        if success_count == 0:
            return jsonify(response), 400
        return jsonify(response)

    @app.route('/api/calculations/portfolio', methods=['POST', 'OPTIONS'])
    def calculations_portfolio():
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        per_type = payload.get('results', {})
        currency = payload.get('currency')
        currency_totals = {}
        count = 0
        failed = 0
        unresolved_currency = False
        unresolved_valuation = False
        by_type = {}
        for itype, res in per_type.items():
            agg = (res or {}).get('aggregates', {}) or {}
            tv = agg.get('total_value')
            if tv is None:
                tv = agg.get('total_market_value')
            ic = agg.get('instrument_count') or 0
            fc = agg.get('failed_count') or 0
            count += int(ic or 0)
            failed += int(fc or 0)
            unresolved_valuation = unresolved_valuation or int(fc or 0) > 0
            by_type[itype] = {'total_value': tv, 'instrument_count': ic,
                              'failed_count': fc}

            groups = agg.get('currency_groups')
            if isinstance(groups, dict) and groups:
                by_type[itype]['currency_groups'] = groups
                for group_currency, group in groups.items():
                    group_value = group.get('total_value')
                    if group_value is None:
                        group_value = group.get('total_market_value')
                    if group_value is None:
                        if ic:
                            unresolved_valuation = True
                        continue
                    key = str(group_currency or 'UNSPECIFIED').strip().upper()
                    if key == 'UNSPECIFIED':
                        unresolved_currency = True
                    currency_totals[key] = (
                        currency_totals.get(key, 0.0) + float(group_value)
                    )
            elif tv is not None:
                group_currency = (
                    (res or {}).get('currency')
                    or agg.get('currency')
                    or currency
                )
                key = str(group_currency or 'UNSPECIFIED').strip().upper()
                if key == 'UNSPECIFIED':
                    unresolved_currency = True
                currency_totals[key] = (
                    currency_totals.get(key, 0.0) + float(tv)
                )
            elif ic:
                unresolved_valuation = True

        known_currencies = {
            key for key in currency_totals if key != 'UNSPECIFIED'
        }
        can_combine = (
            len(known_currencies) == 1
            and not unresolved_currency
            and not unresolved_valuation
        )
        portfolio_total = (
            sum(currency_totals.values()) if can_combine else None
        )
        return jsonify({'status': 'success', 'portfolio_total': portfolio_total,
                        'total_instrument_count': count,
                        'total_failed_count': failed,
                        'by_type': by_type,
                        'currency_totals': currency_totals,
                        'currency': (
                            next(iter(known_currencies)) if can_combine else None
                        ),
                        'warning': None if can_combine else (
                            'Portfolio total is unavailable because valuations '
                            'are missing, incomplete, or have different currencies.'
                        )})

    @app.route('/api/calculations/<calculation_id>', methods=['GET', 'OPTIONS'])
    def calculations_get_by_id(calculation_id):
        if request.method == 'OPTIONS':
            return '', 200
        user_id, auth_response = _authenticated_user()
        if auth_response:
            return auth_response
        with _db() as (conn, cursor):
            if not conn:
                return jsonify({'status': 'error', 'errors': [
                    {'field': 'db', 'code': 'unavailable',
                     'message': 'Database unavailable'}]}), 500
            try:
                cursor.execute("SELECT * FROM calculations WHERE calculation_id = %s LIMIT 1",
                               (calculation_id,))
                row = cursor.fetchone()
                if not row or not _owned_calculation_scope(
                        cursor, user_id, row.get('session_id'), row.get('dataset_id')):
                    return jsonify({'status': 'error', 'errors': [
                        {'field': 'calculationId', 'code': 'not_found',
                         'message': f'Calculation {calculation_id} not found'}]}), 404
            except Exception as e:
                return jsonify({'status': 'error', 'errors': [
                    {'field': 'db', 'code': 'error', 'message': str(e)}]}), 500
            return jsonify({
                'status': 'success',
                'calculationId': row.get('calculation_id'),
                'instrumentType': row.get('instrument_type'),
                'createdAt': (row.get('created_at').isoformat()
                              if row.get('created_at') else None),
                'inputData': _load_json(row.get('input_data')),
                'resultData': _load_json(row.get('result_data')),
            })

    @app.route('/api/calculations/recalculate', methods=['POST', 'OPTIONS'])
    def calculations_recalculate():
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        data = payload.get('data', [])
        inst_type = normalize_instrument_type(payload.get('instrument_type'))
        valuation_date = payload.get('valuationDate') or payload.get('valuation_date')
        currency = payload.get('currency')
        maturity = payload.get('maturity')
        country = payload.get('country')
        sheet_name = payload.get('sheet_name')
        if not data:
            return jsonify({'status': 'error', 'errors': [
                {'field': 'data', 'code': 'empty',
                 'message': 'No data provided'}]}), 400

        data = _resolve_instrument_name(data, sheet_name)
        data = _apply_currency_fallback(data, currency)

        merged = []
        for row in data:
            merged.append(dict(row))

        benchmark_yield = _fetch_benchmark(inst_type, maturity, country, currency)
        calc_result = calculate_data(merged, inst_type, valuation_date=valuation_date,
                                     benchmark_yield=benchmark_yield)
        _attach_fred(calc_result, inst_type, maturity, country, currency)

        calc_list = calc_result.get('calculations', [])
        individual = [{
            'instrumentId': c.get('instrument_name') or f'instrument-{i+1}',
            'instrument_name': c.get('instrument_name'),
            'status': c.get('status', 'cannot_calculate'),
        } for i, c in enumerate(calc_list)]
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
            currency = payload.get('currency')
            maturity = payload.get('maturity')
            country = payload.get('country')
            sheet_name = payload.get('sheet_name')
            session_id = payload.get('session_id')
            dataset_id = payload.get('dataset_id')
            section_id = payload.get('section_id')
            if not data:
                return jsonify({'success': False, 'status': 'error',
                                'message': 'No data provided'}), 400

            if session_id or dataset_id:
                user_id, auth_response = _authenticated_user()
                if auth_response:
                    return auth_response
                with _db() as (conn, cursor):
                    if not conn:
                        return jsonify({'success': False, 'message': 'Database unavailable'}), 503
                    try:
                        if not _owned_calculation_scope(cursor, user_id, session_id, dataset_id):
                            return jsonify({'success': False, 'message': 'Session or dataset not found'}), 404
                    except Exception:
                        return jsonify({'success': False, 'message': 'Could not verify calculation ownership'}), 500

            data = _resolve_instrument_name(data, sheet_name)
            data = _apply_currency_fallback(data, currency)
            try:
                benchmark_yield = _provided_benchmark(payload)
            except ValueError as error:
                return jsonify({'success': False, 'status': 'error',
                                'message': str(error)}), 400
            result = calculate_data(
                data,
                inst_type,
                valuation_date=valuation_date,
                benchmark_yield=benchmark_yield,
            )
            _fix_instrument_count(result)

            response_body = {
                'success': True,
                'is_multi_instrument': False,
                'instrument_type': inst_type,
                'data': result,
                'instrument_names': [],
                'instrument_summary': {'columns': [], 'rows': []},
                'portfolio_summary': {'columns': [], 'rows': [],
                                      'portfolio_total': 0, 'instrument_counts': {}},
            }
            if (session_id or dataset_id) and result.get('calculations'):
                try:
                    saved_id = save_calculation(
                        inst_type, data, response_body,
                        dataset_id=dataset_id, session_id=session_id,
                        sheet_name=sheet_name, section_id=section_id,
                    )
                except Exception as e:
                    print(f"Legacy save failed: {e}")
                    return jsonify({'success': False, 'message': 'Calculation completed but could not be saved'}), 500
                if not saved_id:
                    return jsonify({'success': False, 'message': 'Calculation completed but could not be saved'}), 500
            return jsonify(response_body)
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
        currency = payload.get('currency')
        sheet_name = payload.get('sheet_name')
        if not data:
            return jsonify({'success': False, 'status': 'error',
                            'message': 'No uploaded data'}), 400

        data = _resolve_instrument_name(data, sheet_name)
        data = _apply_currency_fallback(data, currency)
        result = calculate_data(data, inst_type, valuation_date=valuation_date)
        _fix_instrument_count(result)

        return jsonify({'success': True, 'data': result})

    @app.route('/api/aggregate/results', methods=['POST', 'OPTIONS'])
    def aggregate_results():
        """Aggregate already-calculated per-instrument result rows from
        multiple worksheets/workbooks. Mirrors the frontend computeAggregate
        contract: totals, averages, weighted averages, counts, and
        per-currency grouping (mixed currencies are never combined)."""
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        rows = payload.get('rows', [])
        if not isinstance(rows, list):
            return jsonify({'success': False, 'message': 'rows must be a list'}), 400

        def norm(k):
            return ''.join(ch for ch in str(k).lower() if ch.isalnum())

        def num(row, *aliases):
            idx = {norm(k): v for k, v in (row or {}).items()}
            for a in aliases:
                v = idx.get(norm(a))
                if v is None or v == '':
                    continue
                try:
                    return float(str(v).replace('%', '').replace(',', '').replace('$', '').strip())
                except (TypeError, ValueError):
                    continue
            return None

        VALUE_KEYS = ('Total Value', 'total_value', 'Calculated Value',
                      'calculated_value', 'Value', 'value', 'total_value_calc')
        RATE_KEYS = ('Avg Rate', 'avg_rate', 'Rate', 'rate', 'Interest Rate',
                     'interest_rate', 'Coupon Rate', 'coupon_rate',
                     'Discount Rate', 'discount_rate', 'Yield', 'yield')
        DAYS_KEYS = ('Days to Maturity', 'days_to_maturity', 'Avg Days to Maturity',
                     'avg_days_to_maturity', 'Term', 'term', 'Term Days', 'term_days')
        COUPON_KEYS = ('Avg Coupon Rate', 'avg_coupon_rate', 'Coupon Rate', 'coupon_rate')
        DISC_KEYS = ('Avg Discount Rate', 'avg_discount_rate', 'Discount Rate', 'discount_rate')

        def ccy(row):
            for k in ('Currency', 'currency', 'Currency Code', 'ccy'):
                v = row.get(k)
                if v not in (None, ''):
                    return str(v).strip().upper() or 'UNSPECIFIED'
            return 'UNSPECIFIED'

        groups = {}
        for r in rows:
            groups.setdefault(ccy(r), []).append(r)

        def aggregate_group(group_rows):
            total = 0.0
            rate_sum = 0.0
            weighted = 0.0
            n = 0
            day_vals = []
            coupon_vals = []
            disc_vals = []
            for r in group_rows:
                v = num(r, *VALUE_KEYS)
                rate = num(r, *RATE_KEYS)
                if v is not None:
                    total += v
                if rate is not None:
                    rate_sum += rate
                if v is not None and rate is not None:
                    weighted += v * rate
                d = num(r, *DAYS_KEYS)
                if d is not None and d > 0:
                    day_vals.append(d)
                c = num(r, *COUPON_KEYS)
                if c is not None:
                    coupon_vals.append(c)
                dc = num(r, *DISC_KEYS)
                if dc is not None:
                    disc_vals.append(dc)
                n += 1
            count = len(group_rows)
            return {
                'totalValue': round(total, 2),
                'totalPrincipal': round(total, 2),
                'instrumentCount': count,
                'avgRate': round(rate_sum / count, 4) if count else None,
                'weightedAvgRate': round(weighted / total, 4) if total > 0 else None,
                'avgDaysToMaturity': round(sum(day_vals) / len(day_vals), 2) if day_vals else None,
                'avgCouponRate': round(sum(coupon_vals) / len(coupon_vals), 4) if coupon_vals else None,
                'weightedAvgCoupon': round(weighted / total, 4) if total > 0 else None,
                'avgDiscountRate': round(sum(disc_vals) / len(disc_vals), 4) if disc_vals else None,
                'weightedAvgDiscount': round(weighted / total, 4) if total > 0 else None,
                'avgInvestment': round(total / count, 2) if count else None,
                'avgYTM': round(rate_sum / count, 4) if count else None,
            }

        requires_sep = len(groups) > 1
        result = {'success': True, 'rows': len(rows)}
        if requires_sep:
            result['warning'] = (
                'Portfolio totals are not combined because instruments have '
                f"different currencies: {', '.join(sorted(groups))}."
            )
            result['currency_groups'] = {
                c: {**aggregate_group(g), 'currency': c, 'instrument_count': len(g)}
                for c, g in groups.items()
            }
            # Combined monetary totals stay null — never sum across currencies.
            for k in ('totalValue', 'totalPrincipal', 'totalInterest',
                      'interestEarned', 'totalPurchasePrice', 'totalDiscount'):
                result[k] = None
            # Unitless averages may still be reported.
            all_rows = rows
            count = len(all_rows)
            rate_sum = sum(v for v in (num(r, *RATE_KEYS) for r in all_rows) if v is not None)
            result.update({
                'instrumentCount': count,
                'avgRate': round(rate_sum / count, 4) if count else None,
                'avgDaysToMaturity': None,
                'avgCouponRate': None,
                'avgDiscountRate': None,
            })
        else:
            only = next(iter(groups.values()), [])
            currency = next(iter(groups.keys()), 'UNSPECIFIED') if groups else 'UNSPECIFIED'
            agg = aggregate_group(only)
            result.update(agg)
            result['currency'] = currency
            result['currency_groups'] = {currency: {**agg, 'currency': currency,
                                                    'instrument_count': len(only)}}
        return jsonify(result)

    @app.route('/api/calculate/comprehensive', methods=['POST', 'OPTIONS'])
    def calculate_comprehensive():
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        data = payload.get('data', [])
        valuation_date = payload.get('valuationDate') or payload.get('valuation_date')
        currency = payload.get('currency')
        maturity = payload.get('maturity')
        country = payload.get('country')
        if not data:
            return jsonify({'success': False, 'status': 'error',
                            'message': 'No uploaded data'}), 400

        data = _apply_currency_fallback(data, currency)
        detection = detect_instruments_from_data(data)
        if detection.get('is_multi_instrument'):
            split = split_data_by_instrument(data, detection.get('instrument_column'))
            all_results = {}
            for itype, subset in split.items():
                if not subset:
                    continue
                benchmark_yield = _fetch_benchmark(itype, maturity, country, currency)
                r = calculate_data(subset, itype, valuation_date=valuation_date,
                                   benchmark_yield=benchmark_yield)
                _fix_instrument_count(r)
                all_results[itype] = {'data': r, 'row_count': len(subset)}
            return jsonify({'success': True, 'is_multi_instrument': True,
                            'instrument_detection': detection,
                            'results': all_results,
                            'calculation_count': len(all_results)})

        detector = create_instrument_detector()
        det = detector.detect_from_data(data)
        inst_type = det.instrument_type if det else None
        if not inst_type:
            return jsonify({
                'success': False, 'status': 'error',
                'message': ('Could not determine instrument type from the '
                            'uploaded data. Please specify instrument_type '
                            'explicitly.'),
            }), 400

        benchmark_yield = _fetch_benchmark(inst_type, maturity, country, currency)
        result = calculate_data(data, inst_type, valuation_date=valuation_date,
                                benchmark_yield=benchmark_yield)
        _fix_instrument_count(result)

        return jsonify({'success': True, 'is_multi_instrument': False,
                        'instrument_type': inst_type, 'data': result})

    @app.route('/api/calculations/history', methods=['GET', 'OPTIONS'])
    def calculations_history():
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
                    """SELECT DISTINCT c.id, c.instrument_type, c.dataset_id, c.session_id,
                              c.calculation_status, c.created_at
                       FROM calculations c
                       LEFT JOIN ui_sessions s
                         ON s.session_id = c.session_id AND s.user_id = %s
                       LEFT JOIN datasets d
                         ON d.id = c.dataset_id AND d.user_id = %s
                       WHERE s.session_id IS NOT NULL OR d.id IS NOT NULL
                       ORDER BY c.created_at DESC LIMIT 20""",
                    (user_id, user_id)
                )
                rows = cursor.fetchall()
            except Exception as error:
                return jsonify({'success': False, 'message': str(error)}), 500
            return jsonify({'success': True, 'data': [{
                'id': r['id'], 'instrument_type': r['instrument_type'],
                'dataset_id': r['dataset_id'], 'session_id': r['session_id'],
                'status': r['calculation_status'],
                'created_at': (r['created_at'].isoformat()
                               if r['created_at'] else None),
            } for r in rows]})

    @app.route('/api/calculations/latest', methods=['GET', 'OPTIONS'])
    def calculations_latest():
        if request.method == 'OPTIONS':
            return '', 200
        user_id, auth_response = _authenticated_user()
        if auth_response:
            return auth_response
        dataset_id = request.args.get('dataset_id')
        session_id = request.args.get('session_id')
        if not dataset_id and not session_id:
            return jsonify({'success': False, 'message': 'session_id or dataset_id is required'}), 400
        with _db() as (conn, cursor):
            if not conn:
                return jsonify({'success': False, 'message': 'DB unavailable'}), 503
            try:
                if not _owned_calculation_scope(cursor, user_id, session_id, dataset_id):
                    return jsonify({'success': False, 'message': 'Session or dataset not found'}), 404
                if dataset_id:
                    cursor.execute("SELECT * FROM calculations WHERE dataset_id = %s "
                                   "ORDER BY created_at DESC LIMIT 1", (dataset_id,))
                else:
                    cursor.execute("SELECT * FROM calculations WHERE session_id = %s "
                                   "ORDER BY created_at DESC LIMIT 1", (session_id,))
                row = cursor.fetchone()
            except Exception as e:
                return jsonify({'success': False, 'message': str(e)}), 500
            if not row:
                return jsonify({'success': False, 'message': 'Not found'}), 404
            return jsonify({'success': True, 'data': {
                'id': row.get('id'),
                'instrument_type': row.get('instrument_type'),
                'result_data': _load_json(row.get('result_data')),
                'status': row.get('calculation_status'),
                'created_at': (row.get('created_at').isoformat()
                               if row.get('created_at') else None),
            }})

    @app.route('/api/calculations/instrument-summary', methods=['POST', 'OPTIONS'])
    def instrument_summary():
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        session_id = payload.get('session_id')
        if not session_id:
            return jsonify({'success': False, 'message': 'session_id required'}), 400
        user_id, auth_response = _authenticated_user()
        if auth_response:
            return auth_response
        with _db() as (conn, cursor):
            if not conn:
                return jsonify({'success': False, 'message': 'Database unavailable'}), 503
            try:
                if not session_is_owned(cursor, session_id, user_id):
                    return jsonify({'success': False, 'message': 'Session not found'}), 404
                cursor.execute("SELECT * FROM calculations WHERE session_id = %s "
                               "ORDER BY created_at DESC", (session_id,))
                rows = cursor.fetchall()
            except Exception as error:
                return jsonify({'success': False, 'message': str(error)}), 500
            summary_rows = []
            for row in rows:
                result_data = _load_json(row.get('result_data'))
                calcs = (result_data.get('calculations')
                         or result_data.get('results') or [])
                if isinstance(calcs, list):
                    for c in calcs:
                        if not isinstance(c, dict):
                            continue
                        summary_rows.append({
                            'Instrument Type': row.get('instrument_type'),
                            **c,
                        })
            cols = []
            seen = set()
            for r in summary_rows:
                for k in r.keys():
                    if k not in seen:
                        seen.add(k)
                        cols.append(k)
            cols = dedupe_columns(cols)
            return jsonify({'success': True,
                            'data': {'columns': cols, 'rows': summary_rows}})

    @app.route('/api/calculations/portfolio-summary', methods=['POST', 'OPTIONS'])
    def portfolio_summary():
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        session_id = payload.get('session_id')
        if not session_id:
            return jsonify({'success': False, 'message': 'session_id required'}), 400
        user_id, auth_response = _authenticated_user()
        if auth_response:
            return auth_response
        with _db() as (conn, cursor):
            if not conn:
                return jsonify({'success': False, 'message': 'Database unavailable'}), 503
            try:
                if not session_is_owned(cursor, session_id, user_id):
                    return jsonify({'success': False, 'message': 'Session not found'}), 404
                cursor.execute("SELECT * FROM calculations WHERE session_id = %s "
                               "ORDER BY created_at DESC", (session_id,))
                rows = cursor.fetchall()
            except Exception as error:
                return jsonify({'success': False, 'message': str(error)}), 500
            portfolio_rows = []
            currency_totals = {}
            unresolved_currency = False
            unresolved_valuation = False
            instrument_counts = {}
            seen = set()
            for row in rows:
                cid = row.get('id')
                if cid in seen:
                    continue
                seen.add(cid)
                result_data = _load_json(row.get('result_data'))
                agg = result_data.get('aggregates', {}) or {}
                tv = agg.get('total_value')
                if tv is None:
                    tv = agg.get('total_market_value')
                groups = agg.get('currency_groups')
                stored_count = agg.get('instrument_count') or 0
                if agg.get('failed_count') or (tv is None and stored_count):
                    unresolved_valuation = True
                if isinstance(groups, dict) and groups:
                    for group_currency, group in groups.items():
                        group_value = group.get('total_value')
                        if group_value is None:
                            group_value = group.get('total_market_value')
                        if group_value is None:
                            if stored_count:
                                unresolved_valuation = True
                            continue
                        key = str(group_currency or 'UNSPECIFIED').strip().upper()
                        if key == 'UNSPECIFIED':
                            unresolved_currency = True
                        currency_totals[key] = (
                            currency_totals.get(key, 0.0) + float(group_value)
                        )
                elif tv is not None:
                    row_currency = (
                        agg.get('currency')
                        or result_data.get('currency')
                        or row.get('currency')
                    )
                    key = str(row_currency or 'UNSPECIFIED').strip().upper()
                    if key == 'UNSPECIFIED':
                        unresolved_currency = True
                    currency_totals[key] = (
                        currency_totals.get(key, 0.0) + float(tv)
                    )

                stored_results = (result_data.get('results')
                                  or result_data.get('calculations') or [])
                unique_count = _unique_instrument_count(stored_results, stored_count)

                itype = row.get('instrument_type')
                instrument_counts[itype] = (instrument_counts.get(itype, 0)
                                            + int(unique_count or 0))
                portfolio_rows.append({
                    'Instrument Type': itype, 'Total Value': tv,
                    'Instrument Count': unique_count,
                    'Failed Count': agg.get('failed_count') or 0,
                    'Calculation ID': cid,
                })
            known_currencies = {
                key for key in currency_totals if key != 'UNSPECIFIED'
            }
            can_combine = (
                len(known_currencies) == 1
                and not unresolved_currency
                and not unresolved_valuation
            )
            portfolio_total = (
                sum(currency_totals.values()) if can_combine else None
            )
            return jsonify({'success': True, 'data': {
                'columns': ['Instrument Type', 'Total Value', 'Instrument Count',
                            'Failed Count', 'Calculation ID'],
                'rows': portfolio_rows,
                'portfolio_total': portfolio_total,
                'instrument_counts': instrument_counts,
                'currency_totals': currency_totals,
                'currency': (
                    next(iter(known_currencies)) if can_combine else None
                ),
                'warning': None if can_combine else (
                    'Portfolio total is unavailable because valuations have '
                    'missing, incomplete, or different currencies.'
                ),
            }})

    @app.route('/api/calculations/session/<session_id>', methods=['GET', 'OPTIONS'])
    def calculations_by_session(session_id):
        if request.method == 'OPTIONS':
            return '', 200
        user_id, auth_response = _authenticated_user()
        if auth_response:
            return auth_response
        with _db() as (conn, cursor):
            if not conn:
                return jsonify({'success': False, 'message': 'Database unavailable'}), 503
            try:
                if not session_is_owned(cursor, session_id, user_id):
                    return jsonify({'success': False, 'message': 'Session not found'}), 404
                cursor.execute("SELECT * FROM calculations WHERE session_id = %s "
                               "ORDER BY created_at DESC", (session_id,))
                rows = cursor.fetchall()
            except Exception as error:
                return jsonify({'success': False, 'message': str(error)}), 500
            return jsonify({'success': True, 'data': [{
                'id': r.get('id'),
                'instrument_type': r.get('instrument_type'),
                'result_data': _load_json(r.get('result_data')),
                'status': r.get('calculation_status'),
                'created_at': (r.get('created_at').isoformat()
                               if r.get('created_at') else None),
            } for r in rows]})

    @app.route('/api/calculations/session-workflows/<session_id>',
               methods=['GET', 'OPTIONS'])
    def session_workflows(session_id):
        if request.method == 'OPTIONS':
            return '', 200
        user_id, auth_response = _authenticated_user()
        if auth_response:
            return auth_response
        with _db() as (conn, cursor):
            if not conn:
                return jsonify({'success': False, 'message': 'Database unavailable'}), 503
            try:
                cursor.execute("SELECT instrument_workflows FROM ui_sessions "
                               "WHERE session_id = %s AND user_id = %s", (session_id, user_id))
                row = cursor.fetchone()
            except Exception as error:
                return jsonify({'success': False, 'message': str(error)}), 500
            if not row:
                return jsonify({'success': False, 'message': 'Session not found'}), 404
            workflows = _load_json(row.get('instrument_workflows'))
            return jsonify({'success': True, 'data': workflows})

def auto_detect_instrument_type(inputs: dict) -> str:
    if inputs.get('discount_rate') and not inputs.get('coupon_rate'):
        return 'tbills'
    if inputs.get('coupon_rate') and inputs.get('years_to_maturity'):
        return 'bonds'
    if inputs.get('interest_rate') and inputs.get('principal'):
        return 'money-market'
    return None
import json
import pymysql.cursors
import traceback
from contextlib import contextmanager
from datetime import datetime
from flask import request, jsonify
from utils.db import get_db


_EXPECTED_SESSION_COLUMNS = {
    'user_id':              'INT DEFAULT 0',
    'status':               "VARCHAR(64) DEFAULT 'in-progress'",
    'date':                 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
    'versions':             'JSON',
    'instrument_workflows': 'JSON',
    'payload':              'JSON',
    'instrument_data':      'JSON',
    'instrument_count':     'INT DEFAULT 0',
    'total_value':          'DECIMAL(20,2) DEFAULT 0',
    'version_count':        'INT DEFAULT 0',
    'created_at':           'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
    'updated_at':           'TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP',
}


@contextmanager
def _db(dict_cursor=False):
    conn = get_db()
    cursor = None
    if conn:
        try:
            cursor = conn.cursor(pymysql.cursors.DictCursor) if dict_cursor else conn.cursor()
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


def _decode_json(value, empty, preserve_raw_on_fail=False):
    if not value:
        return empty
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except Exception:
        return value if preserve_raw_on_fail else empty


def _count_from_workflows(workflows):
    if not workflows or not isinstance(workflows, dict):
        return 0
    count = 0
    for key in ['money-market', 'bonds', 'tbills']:
        wf = workflows.get(key)
        if wf and (
            (wf.get('cleanedData') and len(wf.get('cleanedData')) > 0) or
            (wf.get('rawData') and len(wf.get('rawData')) > 0) or
            (wf.get('data') and len(wf.get('data')) > 0) or
            (wf.get('calculations') and wf.get('calculations', {}).get('totalValue', 0) > 0) or
            (wf.get('instrumentSummary') and wf.get('instrumentSummary', {}).get('rows') and len(wf.get('instrumentSummary', {}).get('rows')) > 0)
        ):
            count += 1
    return min(count, 3)


def _get_existing_columns(cursor, table):
    cursor.execute(f"SHOW COLUMNS FROM `{table}`")
    return {row[0] if isinstance(row, tuple) else row.get('Field') for row in cursor.fetchall()}


def create_sessions_table():
    with _db() as (conn, cursor):
        if not conn:
            print("DB connection failed – cannot create ui_sessions")
            return
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ui_sessions (
                    session_id VARCHAR(255) PRIMARY KEY,
                    user_id INT DEFAULT 0,
                    name VARCHAR(255),
                    status VARCHAR(64) DEFAULT 'in-progress',
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    versions JSON,
                    instrument_workflows JSON,
                    payload JSON,
                    instrument_data JSON,
                    instrument_count INT DEFAULT 0,
                    total_value DECIMAL(20,2) DEFAULT 0,
                    version_count INT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            ''')
            conn.commit()

            existing = _get_existing_columns(cursor, 'ui_sessions')
            added = []
            for column, definition in _EXPECTED_SESSION_COLUMNS.items():
                if column not in existing:
                    try:
                        cursor.execute(
                            f"ALTER TABLE ui_sessions ADD COLUMN `{column}` {definition}"
                        )
                        added.append(column)
                    except Exception as alter_err:
                        print(f"Could not add column {column}: {alter_err}")
            if added:
                conn.commit()
                print(f"ui_sessions migrated – added columns: {', '.join(added)}")
            else:
                print("ui_sessions schema OK – no missing columns")

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS version_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    version_id VARCHAR(64),
                    session_id VARCHAR(255),
                    instrument_type VARCHAR(64),
                    change_summary TEXT,
                    dataset_snapshot JSON,
                    mapping_snapshot JSON,
                    calculation_snapshot JSON,
                    portfolio_snapshot JSON,
                    report_snapshot JSON,
                    user_id INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX (session_id),
                    INDEX (version_id),
                    INDEX (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            ''')
            conn.commit()
            print("version_history verified/created")

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS portfolio_summaries (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    session_id VARCHAR(255) NOT NULL,
                    instrument_type VARCHAR(64) NOT NULL,
                    instrument_name VARCHAR(255),
                    total_value DECIMAL(20,2) DEFAULT 0,
                    face_value DECIMAL(20,2) DEFAULT 0,
                    count INT DEFAULT 0,
                    avg_rate DECIMAL(10,4) DEFAULT 0,
                    details JSON,
                    detail_headers JSON,
                    aggregate JSON,
                    valuation_date DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_session_instrument (session_id, instrument_type),
                    INDEX (session_id),
                    INDEX (instrument_type)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            ''')
            conn.commit()
            print("portfolio_summaries verified/created")

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS report_configurations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    session_id VARCHAR(255) NOT NULL,
                    selected_instruments JSON,
                    report_type VARCHAR(64) DEFAULT 'session',
                    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_session_report (session_id),
                    INDEX (session_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            ''')
            conn.commit()

            # Add visualisation_config column if it does not exist yet.
            cursor.execute("SHOW COLUMNS FROM report_configurations LIKE 'visualisation_config'")
            if not cursor.fetchone():
                cursor.execute(
                    "ALTER TABLE report_configurations ADD COLUMN visualisation_config JSON"
                )
                conn.commit()
                print("report_configurations migrated – added visualisation_config")
            else:
                print("report_configurations verified/created")

        except Exception as e:
            print(f"Table setup error: {e}")
            traceback.print_exc()


create_sessions_table()


def sessions_routes(app):

    @app.route('/api/sessions/save', methods=['POST', 'OPTIONS'])
    def save_session():
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        session_id = payload.get('id') or payload.get('session_id')

        if not session_id:
            return jsonify({'success': False, 'message': 'session_id is required'}), 400

        name = payload.get('name') or ''
        status = payload.get('status') or 'in-progress'
        user_id = payload.get('user_id')
        versions = payload.get('versions', [])
        instrument_workflows = payload.get('instrument_workflows', {})
        legacy_payload = payload.get('payload')
        initial_instrument_count = payload.get('instrument_count', 0)
        version_count = payload.get('version_count', 0)
        total_value = payload.get('total_value', 0)
        worksheets = payload.get('worksheets', {})
        workbook_name = payload.get('workbookName') or payload.get('workbook_name')

        if instrument_workflows and isinstance(instrument_workflows, dict):
            instrument_count = _count_from_workflows(instrument_workflows)
        elif legacy_payload:
            instrument_count = 0
            for key in ['money-market', 'bonds', 'tbills']:
                if legacy_payload.get(key):
                    instrument_count += 1
            instrument_count = min(instrument_count, 3)
        else:
            try:
                instrument_count = min(int(initial_instrument_count or 0), 3)
            except Exception:
                instrument_count = 0

        merged_payload = legacy_payload if isinstance(legacy_payload, dict) else {}
        if worksheets:
            merged_payload['worksheets'] = worksheets
        if workbook_name:
            merged_payload['workbookName'] = workbook_name

        with _db() as (conn, cursor):
            if not conn:
                return jsonify({'success': False, 'message': 'DB connection failed'}), 500
            try:
                cursor.execute('''
                    INSERT INTO ui_sessions
                        (session_id, user_id, name, status, versions,
                         instrument_workflows, payload, instrument_count, version_count, total_value)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        name = VALUES(name),
                        status = VALUES(status),
                        versions = VALUES(versions),
                        instrument_workflows = VALUES(instrument_workflows),
                        payload = VALUES(payload),
                        instrument_count = VALUES(instrument_count),
                        version_count = VALUES(version_count),
                        total_value = VALUES(total_value),
                        updated_at = CURRENT_TIMESTAMP
                ''', (
                    session_id,
                    user_id if user_id is not None else 0,
                    name,
                    status,
                    json.dumps(versions) if versions else None,
                    json.dumps(instrument_workflows) if instrument_workflows else None,
                    json.dumps(merged_payload) if merged_payload else None,
                    instrument_count,
                    version_count,
                    total_value,
                ))
                conn.commit()
                return jsonify({'success': True, 'session_id': session_id, 'version_count': version_count})
            except Exception as e:
                print(f"Save session error: {e}")
                traceback.print_exc()
                return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/sessions/get', methods=['POST', 'OPTIONS'])
    def get_session():
        if request.method == 'OPTIONS':
            return '', 200
        data = request.get_json() or {}
        session_id = data.get('session_id')
        if not session_id:
            return jsonify({'success': False, 'message': 'session_id required'}), 400

        with _db(dict_cursor=True) as (conn, cursor):
            if not conn:
                return jsonify({'success': False, 'message': 'DB error'}), 500
            try:
                cursor.execute('''
                    SELECT session_id AS id, name, status, versions, instrument_workflows,
                           payload, instrument_count, version_count, total_value,
                           created_at, updated_at
                    FROM ui_sessions
                    WHERE session_id = %s
                    LIMIT 1
                ''', (session_id,))
                row = cursor.fetchone()
            except Exception as e:
                print(f"Get session error: {e}")
                traceback.print_exc()
                return jsonify({'success': False, 'message': f'Query failed: {str(e)}'}), 500

            if not row:
                return jsonify({'success': True, 'data': None, 'message': 'Session not found'}), 200

            try:
                hist_cursor = conn.cursor(pymysql.cursors.DictCursor)
                try:
                    hist_cursor.execute(
                        'SELECT COUNT(*) AS cnt FROM version_history WHERE session_id = %s',
                        (session_id,)
                    )
                    hist_row = hist_cursor.fetchone()
                    hist_count = (hist_row or {}).get('cnt', 0)
                    if hist_count > (row.get('version_count') or 0):
                        row['version_count'] = hist_count
                        upd = conn.cursor()
                        try:
                            upd.execute(
                                'UPDATE ui_sessions SET version_count = %s WHERE session_id = %s',
                                (hist_count, session_id)
                            )
                            conn.commit()
                        finally:
                            upd.close()
                finally:
                    hist_cursor.close()
            except Exception as e:
                print(f"Failed to check version history: {e}")

        versions = _decode_json(row.get('versions'), [])
        instrument_workflows = _decode_json(row.get('instrument_workflows'), {})
        payload = _decode_json(row.get('payload'), {}, preserve_raw_on_fail=True)

        worksheets = payload.get('worksheets', {}) if isinstance(payload, dict) else {}
        workbook_name = payload.get('workbookName') if isinstance(payload, dict) else None

        return jsonify({
            'success': True,
            'data': {
                'id': row['id'],
                'session_id': row['id'],
                'name': row['name'],
                'status': row['status'],
                'versions': versions,
                'instrument_workflows': instrument_workflows,
                'instrument_workflow': instrument_workflows,
                'payload': payload,
                'worksheets': worksheets,
                'workbookName': workbook_name,
                'instrument_count': row.get('instrument_count', 0),
                'version_count': row.get('version_count', 0),
                'total_value': float(row.get('total_value') or 0),
                'created_at': row['created_at'].isoformat() if row.get('created_at') else None,
                'updated_at': row['updated_at'].isoformat() if row.get('updated_at') else None,
            }
        })

    @app.route('/api/sessions/list', methods=['GET', 'OPTIONS'])
    def list_sessions():
        if request.method == 'OPTIONS':
            return '', 200

        with _db(dict_cursor=True) as (conn, cursor):
            if not conn:
                return jsonify({'success': False, 'message': 'DB error'}), 500
            try:
                cursor.execute('''
                    SELECT s.session_id, s.name, s.status, s.instrument_workflows,
                           s.created_at, s.updated_at, s.instrument_count, s.version_count,
                           (SELECT COUNT(*) FROM version_history v
                            WHERE v.session_id = s.session_id) AS version_count_from_history
                    FROM ui_sessions s
                    ORDER BY created_at DESC
                    LIMIT 200
                ''')
                rows = cursor.fetchall()
            except Exception as e:
                print(f"List sessions error: {e}")
                traceback.print_exc()
                return jsonify({'success': False, 'message': 'Query failed', 'data': []}), 200

        sessions_list = []
        for row in rows:
            instrument_workflows = _decode_json(row.get('instrument_workflows'), {})

            instrument_count = row.get('instrument_count', 0)
            if instrument_count == 0 and instrument_workflows:
                instrument_count = _count_from_workflows(instrument_workflows)

            version_count = max(
                row.get('version_count', 0) or 0,
                row.get('version_count_from_history', 0) or 0,
            )

            sessions_list.append({
                'id': row['session_id'],
                'session_id': row['session_id'],
                'name': row['name'],
                'status': row['status'],
                'versions': [],
                'version_count': version_count,
                'instrument_count': instrument_count,
                'date': row['created_at'].isoformat() if row.get('created_at') else None,
                'created_at': row['created_at'].isoformat() if row.get('created_at') else None,
                'updated_at': row['updated_at'].isoformat() if row.get('updated_at') else None,
            })

        return jsonify({'success': True, 'data': sessions_list})

    @app.route('/api/sessions/delete', methods=['POST', 'OPTIONS'])
    def delete_session():
        if request.method == 'OPTIONS':
            return '', 200
        data = request.get_json() or {}
        session_id = data.get('session_id')
        if not session_id:
            return jsonify({'success': False, 'message': 'session_id required'}), 400

        with _db() as (conn, cursor):
            if not conn:
                return jsonify({'success': False, 'message': 'DB error'}), 500
            try:
                try:
                    cursor.execute('DELETE FROM version_history WHERE session_id = %s', (session_id,))
                except Exception as e:
                    print(f"version_history delete skipped: {e}")
                cursor.execute('DELETE FROM ui_sessions WHERE session_id = %s', (session_id,))
                conn.commit()
                print(f'Session {session_id} and all related records deleted')
                return jsonify({'success': True})
            except Exception as e:
                print(f"Delete session error: {e}")
                traceback.print_exc()
                return jsonify({'success': False, 'message': 'Delete failed'}), 500

    @app.route('/api/portfolio/summary', methods=['POST', 'OPTIONS'])
    def save_portfolio_summary():
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        session_id = payload.get('session_id')
        if not session_id:
            return jsonify({'success': False, 'message': 'session_id is required'}), 400

        instrument_type = payload.get('instrument_type')
        if not instrument_type:
            return jsonify({'success': False, 'message': 'instrument_type is required'}), 400

        with _db() as (conn, cursor):
            if not conn:
                return jsonify({'success': False, 'message': 'DB connection failed'}), 500
            try:
                cursor.execute('''
                    INSERT INTO portfolio_summaries
                        (session_id, instrument_type, instrument_name, total_value, face_value,
                         count, avg_rate, details, detail_headers, aggregate, valuation_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        instrument_name = VALUES(instrument_name),
                        total_value = VALUES(total_value),
                        face_value = VALUES(face_value),
                        count = VALUES(count),
                        avg_rate = VALUES(avg_rate),
                        details = VALUES(details),
                        detail_headers = VALUES(detail_headers),
                        aggregate = VALUES(aggregate),
                        valuation_date = VALUES(valuation_date),
                        updated_at = CURRENT_TIMESTAMP
                ''', (
                    session_id,
                    instrument_type,
                    payload.get('instrument_name'),
                    float(payload.get('total_value', 0)),
                    float(payload.get('face_value', 0)),
                    int(payload.get('count', 0)),
                    float(payload.get('avg_rate', 0)),
                    json.dumps(payload.get('details', [])) if payload.get('details') else None,
                    json.dumps(payload.get('detail_headers', [])) if payload.get('detail_headers') else None,
                    json.dumps(payload.get('aggregate', {})) if payload.get('aggregate') else None,
                    payload.get('valuation_date')
                ))
                conn.commit()
                return jsonify({'success': True})
            except Exception as e:
                print(f"Save portfolio summary error: {e}")
                traceback.print_exc()
                return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/portfolio/summary/<session_id>', methods=['GET', 'OPTIONS'])
    def get_portfolio_summaries(session_id):
        if request.method == 'OPTIONS':
            return '', 200

        with _db(dict_cursor=True) as (conn, cursor):
            if not conn:
                return jsonify({'success': False, 'message': 'DB connection failed'}), 500
            try:
                cursor.execute('''
                    SELECT instrument_type, instrument_name, total_value, face_value,
                           count, avg_rate, details, detail_headers, aggregate, valuation_date
                    FROM portfolio_summaries
                    WHERE session_id = %s
                    ORDER BY instrument_type
                ''', (session_id,))
                rows = cursor.fetchall()
            except Exception as e:
                print(f"Get portfolio summaries error: {e}")
                traceback.print_exc()
                return jsonify({'success': False, 'message': str(e)}), 500

        summaries = []
        for row in rows:
            summaries.append({
                'id': row['instrument_type'],
                'name': row['instrument_name'] or row['instrument_type'],
                'details': _decode_json(row.get('details'), []),
                'detailHeaders': _decode_json(row.get('detail_headers'), []),
                'aggregate': _decode_json(row.get('aggregate'), {}),
                'totalValue': float(row.get('total_value', 0)),
                'faceValue': float(row.get('face_value', 0)),
                'count': int(row.get('count', 0)),
                'avgRate': float(row.get('avg_rate', 0)),
                'valuationDate': row.get('valuation_date')
            })

        return jsonify({'success': True, 'data': summaries})

    @app.route('/api/report/configuration', methods=['POST', 'OPTIONS'])
    def save_report_configuration():
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        session_id = payload.get('session_id')
        if not session_id:
            return jsonify({'success': False, 'message': 'session_id is required'}), 400

        visualisation_config = payload.get('visualisation_config')
        visualisation_json = None
        if visualisation_config is not None:
            try:
                visualisation_json = json.dumps(visualisation_config)
            except Exception as e:
                return jsonify({'success': False,
                                'message': f'visualisation_config must be JSON-serialisable: {e}'}), 400

        with _db() as (conn, cursor):
            if not conn:
                return jsonify({'success': False, 'message': 'DB connection failed'}), 500
            try:
                cursor.execute('''
                    INSERT INTO report_configurations
                        (session_id, selected_instruments, report_type, visualisation_config)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        selected_instruments = VALUES(selected_instruments),
                        report_type = VALUES(report_type),
                        visualisation_config = COALESCE(VALUES(visualisation_config),
                                                        visualisation_config),
                        updated_at = CURRENT_TIMESTAMP
                ''', (
                    session_id,
                    json.dumps(payload.get('selected_instruments', {})) if payload.get('selected_instruments') else None,
                    payload.get('report_type', 'session'),
                    visualisation_json,
                ))
                conn.commit()
                return jsonify({'success': True})
            except Exception as e:
                print(f"Save report configuration error: {e}")
                traceback.print_exc()
                return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/report/configuration/<session_id>', methods=['GET', 'OPTIONS'])
    def get_report_configuration(session_id):
        if request.method == 'OPTIONS':
            return '', 200

        with _db(dict_cursor=True) as (conn, cursor):
            if not conn:
                return jsonify({'success': False, 'message': 'DB connection failed'}), 500
            try:
                cursor.execute('''
                    SELECT selected_instruments, report_type, visualisation_config,
                           generated_at, updated_at
                    FROM report_configurations
                    WHERE session_id = %s
                    LIMIT 1
                ''', (session_id,))
                row = cursor.fetchone()
            except Exception as e:
                print(f"Get report configuration error: {e}")
                traceback.print_exc()
                return jsonify({'success': False, 'message': str(e)}), 500

        if not row:
            return jsonify({'success': True, 'data': None})

        return jsonify({
            'success': True,
            'data': {
                'selectedInstruments': _decode_json(row.get('selected_instruments'), {}),
                'reportType': row.get('report_type', 'session'),
                'visualisationConfig': _decode_json(row.get('visualisation_config'), {}),
                'generatedAt': row.get('generated_at').isoformat() if row.get('generated_at') else None,
                'updatedAt': row.get('updated_at').isoformat() if row.get('updated_at') else None
            }
        })
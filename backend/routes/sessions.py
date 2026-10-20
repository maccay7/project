import json
import uuid
import pymysql.cursors
from flask import request, jsonify
from utils.db import get_db
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════════════
# SCHEMA BOOTSTRAP + MIGRATION
# ═══════════════════════════════════════════════════════════════════════════

# Columns we expect on ui_sessions and their SQL definitions.
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


def _get_existing_columns(cursor, table):
    """Return a set of column names that already exist on `table`."""
    cursor.execute(f"SHOW COLUMNS FROM `{table}`")
    return {row[0] if isinstance(row, tuple) else row.get('Field') for row in cursor.fetchall()}


def create_sessions_table():
    """
    Idempotent schema setup.
      1. Create ui_sessions if missing (full schema).
      2. Add any missing columns if the table already exists
         (this fixes the 500 error from older schemas).
      3. Create version_history if missing.
      4. Create portfolio_summaries if missing.
      5. Create report_configurations if missing.
    """
    conn = get_db()
    if not conn:
        print("DB connection failed – cannot create ui_sessions")
        return
    try:
        cursor = conn.cursor()

        # ── 1) Create ui_sessions if missing ────────────────────────────────
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

        # ── 2) Migrate missing columns ──────────────────────────────────────
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

        # ── 3) Create version_history if missing ────────────────────────────
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

        # ── 4) Create portfolio_summaries if missing ────────────────────────
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

        # ── 5) Create report_configurations if missing ────────────────────────
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
        print("report_configurations verified/created")

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Table setup error: {e}")
        import traceback
        traceback.print_exc()
        try:
            conn.close()
        except Exception:
            pass


# Run at import time – matches previous behaviour.
create_sessions_table()


# ═══════════════════════════════════════════════════════════════════════════
# ROUTES
# ═══════════════════════════════════════════════════════════════════════════

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
        instrument_count = payload.get('instrument_count', 0)
        version_count = payload.get('version_count', 0)
        total_value = payload.get('total_value', 0)
        worksheets = payload.get('worksheets', {})
        workbook_name = payload.get('workbookName') or payload.get('workbook_name')

        # Compute instrument_count from instrument_workflows if provided
        if instrument_workflows and isinstance(instrument_workflows, dict):
            instrument_count = 0
            for key in ['money-market', 'bonds', 'tbills']:
                wf = instrument_workflows.get(key)
                if wf and (
                    (wf.get('cleanedData') and len(wf.get('cleanedData')) > 0) or
                    (wf.get('rawData') and len(wf.get('rawData')) > 0) or
                    (wf.get('data') and len(wf.get('data')) > 0) or
                    (wf.get('calculations') and wf.get('calculations', {}).get('totalValue', 0) > 0) or
                    (wf.get('instrumentSummary') and wf.get('instrumentSummary', {}).get('rows') and len(wf.get('instrumentSummary', {}).get('rows')) > 0)
                ):
                    instrument_count += 1
            instrument_count = min(instrument_count, 3)
        elif legacy_payload:
            instrument_count = 0
            for key in ['money-market', 'bonds', 'tbills']:
                if legacy_payload.get(key):
                    instrument_count += 1
            instrument_count = min(instrument_count, 3)
        else:
            try:
                instrument_count = min(int(instrument_count or 0), 3)
            except Exception:
                instrument_count = 0

        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'DB connection failed'}), 500
        try:
            cursor = conn.cursor()

            # Merge worksheets into the payload JSON so we don't need a
            # dedicated column just for worksheets.
            merged_payload = legacy_payload if isinstance(legacy_payload, dict) else {}
            if worksheets:
                merged_payload['worksheets'] = worksheets
            if workbook_name:
                merged_payload['workbookName'] = workbook_name

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

            cursor.close()
            conn.close()

            return jsonify({'success': True, 'session_id': session_id, 'version_count': version_count})
        except Exception as e:
            print(f"Save session error: {e}")
            import traceback
            traceback.print_exc()
            try:
                conn.close()
            except Exception:
                pass
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/sessions/get', methods=['POST', 'OPTIONS'])
    def get_session():
        if request.method == 'OPTIONS':
            return '', 200
        data = request.get_json() or {}
        session_id = data.get('session_id')
        if not session_id:
            return jsonify({'success': False, 'message': 'session_id required'}), 400

        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'DB error'}), 500
        try:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute('''
                SELECT session_id AS id, name, status, versions, instrument_workflows,
                       payload, instrument_count, version_count, total_value,
                       created_at, updated_at
                FROM ui_sessions
                WHERE session_id = %s
                LIMIT 1
            ''', (session_id,))
            row = cursor.fetchone()

            if not row:
                cursor.close()
                conn.close()
                return jsonify({'success': True, 'data': None, 'message': 'Session not found'}), 200

            # Reconcile version_count against version_history
            try:
                hist_cursor = conn.cursor(pymysql.cursors.DictCursor)
                hist_cursor.execute(
                    'SELECT COUNT(*) AS cnt FROM version_history WHERE session_id = %s',
                    (session_id,)
                )
                hist_row = hist_cursor.fetchone()
                hist_count = (hist_row or {}).get('cnt', 0)
                if hist_count > (row.get('version_count') or 0):
                    row['version_count'] = hist_count
                    upd = conn.cursor()
                    upd.execute(
                        'UPDATE ui_sessions SET version_count = %s WHERE session_id = %s',
                        (hist_count, session_id)
                    )
                    conn.commit()
                    upd.close()
                hist_cursor.close()
            except Exception as e:
                print(f"Failed to check version history: {e}")

            cursor.close()
            conn.close()

            # ── Decode JSON columns safely ──────────────────────────────────
            versions = []
            if row.get('versions'):
                try:
                    versions = json.loads(row['versions']) if isinstance(row['versions'], str) else row['versions']
                except Exception:
                    versions = []

            instrument_workflows = {}
            if row.get('instrument_workflows'):
                try:
                    instrument_workflows = (
                        json.loads(row['instrument_workflows'])
                        if isinstance(row['instrument_workflows'], str)
                        else row['instrument_workflows']
                    )
                except Exception:
                    instrument_workflows = {}

            payload = {}
            if row.get('payload'):
                try:
                    payload = json.loads(row['payload']) if isinstance(row['payload'], str) else row['payload']
                except Exception:
                    payload = row['payload'] or {}

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
                    'instrument_workflow': instrument_workflows,   # alias
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
        except Exception as e:
            print(f"Get session error: {e}")
            import traceback
            traceback.print_exc()
            try:
                conn.close()
            except Exception:
                pass
            return jsonify({'success': False, 'message': f'Query failed: {str(e)}'}), 500

    @app.route('/api/sessions/list', methods=['GET', 'OPTIONS'])
    def list_sessions():
        if request.method == 'OPTIONS':
            return '', 200
        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'DB error'}), 500
        try:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
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
            cursor.close()
            conn.close()

            sessions_list = []
            for row in rows:
                instrument_workflows = {}
                if row.get('instrument_workflows'):
                    try:
                        instrument_workflows = (
                            json.loads(row['instrument_workflows'])
                            if isinstance(row['instrument_workflows'], str)
                            else row['instrument_workflows']
                        )
                    except Exception:
                        pass

                instrument_count = row.get('instrument_count', 0)
                if instrument_count == 0 and instrument_workflows:
                    for key in ['money-market', 'bonds', 'tbills']:
                        wf = instrument_workflows.get(key)
                        if wf and (
                            (wf.get('cleanedData') and len(wf.get('cleanedData')) > 0) or
                            (wf.get('rawData') and len(wf.get('rawData')) > 0) or
                            (wf.get('data') and len(wf.get('data')) > 0) or
                            (wf.get('calculations') and wf.get('calculations', {}).get('totalValue', 0) > 0) or
                            (wf.get('instrumentSummary') and wf.get('instrumentSummary', {}).get('rows') and len(wf.get('instrumentSummary', {}).get('rows')) > 0)
                        ):
                            instrument_count += 1
                    instrument_count = min(instrument_count, 3)

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
        except Exception as e:
            print(f"List sessions error: {e}")
            import traceback
            traceback.print_exc()
            try:
                conn.close()
            except Exception:
                pass
            return jsonify({'success': False, 'message': 'Query failed', 'data': []}), 200

    @app.route('/api/sessions/delete', methods=['POST', 'OPTIONS'])
    def delete_session():
        if request.method == 'OPTIONS':
            return '', 200
        data = request.get_json() or {}
        session_id = data.get('session_id')
        if not session_id:
            return jsonify({'success': False, 'message': 'session_id required'}), 400
        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'DB error'}), 500
        try:
            cursor = conn.cursor()
            try:
                cursor.execute('DELETE FROM version_history WHERE session_id = %s', (session_id,))
            except Exception as e:
                print(f"version_history delete skipped: {e}")
            cursor.execute('DELETE FROM ui_sessions WHERE session_id = %s', (session_id,))
            conn.commit()
            cursor.close()
            conn.close()
            print(f'Session {session_id} and all related records deleted')
            return jsonify({'success': True})
        except Exception as e:
            print(f"Delete session error: {e}")
            import traceback
            traceback.print_exc()
            try:
                conn.close()
            except Exception:
                pass
            return jsonify({'success': False, 'message': 'Delete failed'}), 500

    @app.route('/api/portfolio/summary', methods=['POST', 'OPTIONS'])
    def save_portfolio_summary():
        """Save or update portfolio summary for an instrument in a session."""
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        session_id = payload.get('session_id')
        if not session_id:
            return jsonify({'success': False, 'message': 'session_id is required'}), 400

        instrument_type = payload.get('instrument_type')
        if not instrument_type:
            return jsonify({'success': False, 'message': 'instrument_type is required'}), 400

        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'DB connection failed'}), 500
        try:
            cursor = conn.cursor()
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
            cursor.close()
            conn.close()
            return jsonify({'success': True})
        except Exception as e:
            print(f"Save portfolio summary error: {e}")
            import traceback
            traceback.print_exc()
            try:
                conn.close()
            except Exception:
                pass
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/portfolio/summary/<session_id>', methods=['GET', 'OPTIONS'])
    def get_portfolio_summaries(session_id):
        """Get all portfolio summaries for a session."""
        if request.method == 'OPTIONS':
            return '', 200
        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'DB connection failed'}), 500
        try:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute('''
                SELECT instrument_type, instrument_name, total_value, face_value,
                       count, avg_rate, details, detail_headers, aggregate, valuation_date
                FROM portfolio_summaries
                WHERE session_id = %s
                ORDER BY instrument_type
            ''', (session_id,))
            rows = cursor.fetchall()
            cursor.close()
            conn.close()

            # Decode JSON columns
            summaries = []
            for row in rows:
                details = []
                if row.get('details'):
                    try:
                        details = json.loads(row['details']) if isinstance(row['details'], str) else row['details']
                    except Exception:
                        pass

                detail_headers = []
                if row.get('detail_headers'):
                    try:
                        detail_headers = json.loads(row['detail_headers']) if isinstance(row['detail_headers'], str) else row['detail_headers']
                    except Exception:
                        pass

                aggregate = {}
                if row.get('aggregate'):
                    try:
                        aggregate = json.loads(row['aggregate']) if isinstance(row['aggregate'], str) else row['aggregate']
                    except Exception:
                        pass

                summaries.append({
                    'id': row['instrument_type'],
                    'name': row['instrument_name'] or row['instrument_type'],
                    'details': details,
                    'detailHeaders': detail_headers,
                    'aggregate': aggregate,
                    'totalValue': float(row.get('total_value', 0)),
                    'faceValue': float(row.get('face_value', 0)),
                    'count': int(row.get('count', 0)),
                    'avgRate': float(row.get('avg_rate', 0)),
                    'valuationDate': row.get('valuation_date')
                })

            return jsonify({'success': True, 'data': summaries})
        except Exception as e:
            print(f"Get portfolio summaries error: {e}")
            import traceback
            traceback.print_exc()
            try:
                conn.close()
            except Exception:
                pass
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/report/configuration', methods=['POST', 'OPTIONS'])
    def save_report_configuration():
        """Save report configuration for a session."""
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        session_id = payload.get('session_id')
        if not session_id:
            return jsonify({'success': False, 'message': 'session_id is required'}), 400

        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'DB connection failed'}), 500
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO report_configurations
                    (session_id, selected_instruments, report_type)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    selected_instruments = VALUES(selected_instruments),
                    report_type = VALUES(report_type),
                    updated_at = CURRENT_TIMESTAMP
            ''', (
                session_id,
                json.dumps(payload.get('selected_instruments', {})) if payload.get('selected_instruments') else None,
                payload.get('report_type', 'session')
            ))
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'success': True})
        except Exception as e:
            print(f"Save report configuration error: {e}")
            import traceback
            traceback.print_exc()
            try:
                conn.close()
            except Exception:
                pass
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/report/configuration/<session_id>', methods=['GET', 'OPTIONS'])
    def get_report_configuration(session_id):
        """Get report configuration for a session."""
        if request.method == 'OPTIONS':
            return '', 200
        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'DB connection failed'}), 500
        try:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute('''
                SELECT selected_instruments, report_type, generated_at, updated_at
                FROM report_configurations
                WHERE session_id = %s
                LIMIT 1
            ''', (session_id,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()

            if not row:
                return jsonify({'success': True, 'data': None})

            selected_instruments = {}
            if row.get('selected_instruments'):
                try:
                    selected_instruments = json.loads(row['selected_instruments']) if isinstance(row['selected_instruments'], str) else row['selected_instruments']
                except Exception:
                    pass

            return jsonify({
                'success': True,
                'data': {
                    'selectedInstruments': selected_instruments,
                    'reportType': row.get('report_type', 'session'),
                    'generatedAt': row.get('generated_at').isoformat() if row.get('generated_at') else None,
                    'updatedAt': row.get('updated_at').isoformat() if row.get('updated_at') else None
                }
            })
        except Exception as e:
            print(f"Get report configuration error: {e}")
            import traceback
            traceback.print_exc()
            try:
                conn.close()
            except Exception:
                pass
            return jsonify({'success': False, 'message': str(e)}), 500
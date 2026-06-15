import json
import uuid
from flask import request, jsonify
from utils.db import get_db

def sessions_routes(app):
    # Ensure table has versions column (JSON) and instrument_workflows column (JSON)
    @app.before_request
    def ensure_table_schema():
        conn = get_db()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ui_sessions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    session_id VARCHAR(255) UNIQUE,
                    user_id INT,
                    name VARCHAR(255),
                    status VARCHAR(64),
                    versions JSON,
                    instrument_workflows JSON,
                    payload JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            ''')
            # Add columns if missing (MySQL 5.7 compatibility)
            for col in ['versions', 'instrument_workflows']:
                try:
                    cursor.execute(f"ALTER TABLE ui_sessions ADD COLUMN {col} JSON DEFAULT NULL")
                except Exception:
                    pass
            cursor.close()
        except Exception as e:
            print(f"Schema check error: {e}")
        finally:
            conn.close()

    @app.route('/api/sessions/save', methods=['POST', 'OPTIONS'])
    def save_session():
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        session_id = payload.get('id') or payload.get('session_id') or str(int(uuid.uuid4().int % 1e12))
        name = payload.get('name') or ''
        status = payload.get('status') or 'in-progress'
        user_id = payload.get('user_id')
        versions = payload.get('versions', [])
        instrument_workflows = payload.get('instrument_workflows', {})
        legacy_payload = payload.get('payload')

        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'DB connection failed'}), 500
        try:
            cursor = conn.cursor()
            # Upsert
            cursor.execute('''
                INSERT INTO ui_sessions (session_id, user_id, name, status, versions, instrument_workflows, payload)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    name = VALUES(name),
                    status = VALUES(status),
                    versions = VALUES(versions),
                    instrument_workflows = VALUES(instrument_workflows),
                    payload = VALUES(payload)
            ''', (
                session_id,
                user_id if user_id is not None else 0,
                name,
                status,
                json.dumps(versions) if versions else None,
                json.dumps(instrument_workflows) if instrument_workflows else None,
                json.dumps(legacy_payload) if legacy_payload else None
            ))
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'success': True, 'session_id': session_id})
        except Exception as e:
            print(f"Save session error: {e}")
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
            cursor = conn.cursor()
            cursor.execute('''
                SELECT session_id, name, status, versions, instrument_workflows, payload, created_at, updated_at
                FROM ui_sessions WHERE session_id = %s LIMIT 1
            ''', (session_id,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            if not row:
                return jsonify({'success': True, 'data': None, 'message': 'Session not found'}), 200
            # Parse JSON fields
            versions = []
            if row.get('versions'):
                try:
                    versions = json.loads(row['versions']) if isinstance(row['versions'], str) else row['versions']
                except:
                    versions = []
            instrument_workflows = {}
            if row.get('instrument_workflows'):
                try:
                    instrument_workflows = json.loads(row['instrument_workflows']) if isinstance(row['instrument_workflows'], str) else row['instrument_workflows']
                except:
                    instrument_workflows = {}
            payload = {}
            if row.get('payload'):
                try:
                    payload = json.loads(row['payload']) if isinstance(row['payload'], str) else row['payload']
                except:
                    payload = row['payload']
            return jsonify({
                'success': True,
                'data': {
                    'session_id': row['session_id'],
                    'name': row['name'],
                    'status': row['status'],
                    'versions': versions,
                    'instrument_workflows': instrument_workflows,
                    'payload': payload,
                    'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                    'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None
                }
            })
        except Exception as e:
            print(f"Get session error: {e}")
            return jsonify({'success': False, 'message': 'Query failed'}), 500

    @app.route('/api/sessions/list', methods=['GET', 'OPTIONS'])
    def list_sessions():
        if request.method == 'OPTIONS':
            return '', 200
        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'DB error'}), 500
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT session_id, name, status, versions, instrument_workflows, created_at, updated_at
                FROM ui_sessions ORDER BY updated_at DESC LIMIT 200
            ''')
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            sessions_list = []
            for row in rows:
                versions = []
                if row.get('versions'):
                    try:
                        versions = json.loads(row['versions']) if isinstance(row['versions'], str) else row['versions']
                    except:
                        versions = []
                sessions_list.append({
                    'id': row['session_id'],
                    'name': row['name'],
                    'status': row['status'],
                    'versions': versions,
                    'instrumentCount': len(row.get('instrument_workflows', {}) or {}) if row.get('instrument_workflows') else 0,
                    'date': row['created_at'].isoformat() if row['created_at'] else None
                })
            return jsonify({'success': True, 'data': sessions_list})
        except Exception as e:
            print(f"List sessions error: {e}")
            return jsonify({'success': False, 'message': 'Query failed'}), 500

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
            cursor.execute('DELETE FROM ui_sessions WHERE session_id = %s', (session_id,))
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'success': True})
        except Exception as e:
            print(f"Delete session error: {e}")
            return jsonify({'success': False, 'message': 'Delete failed'}), 500

    # NEW: Save instrument workflow for a session
    @app.route('/api/sessions/workflow/save', methods=['POST', 'OPTIONS'])
    def save_instrument_workflow():
        if request.method == 'OPTIONS':
            return '', 200
        data = request.get_json() or {}
        session_id = data.get('session_id')
        instrument_type = data.get('instrument_type')
        workflow = data.get('workflow')
        if not session_id or not instrument_type:
            return jsonify({'success': False, 'message': 'session_id and instrument_type required'}), 400
        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'DB error'}), 500
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT instrument_workflows FROM ui_sessions WHERE session_id = %s', (session_id,))
            row = cursor.fetchone()
            workflows = {}
            if row and row.get('instrument_workflows'):
                try:
                    workflows = json.loads(row['instrument_workflows']) if isinstance(row['instrument_workflows'], str) else row['instrument_workflows']
                except:
                    workflows = {}
            workflows[instrument_type] = workflow
            cursor.execute('''
                UPDATE ui_sessions SET instrument_workflows = %s WHERE session_id = %s
            ''', (json.dumps(workflows), session_id))
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'success': True})
        except Exception as e:
            print(f"Save workflow error: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    # NEW: Get instrument workflow for a session
    @app.route('/api/sessions/workflow/get', methods=['POST', 'OPTIONS'])
    def get_instrument_workflow():
        if request.method == 'OPTIONS':
            return '', 200
        data = request.get_json() or {}
        session_id = data.get('session_id')
        instrument_type = data.get('instrument_type')
        if not session_id or not instrument_type:
            return jsonify({'success': False, 'message': 'session_id and instrument_type required'}), 400
        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'DB error'}), 500
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT instrument_workflows FROM ui_sessions WHERE session_id = %s', (session_id,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            if not row or not row.get('instrument_workflows'):
                return jsonify({'success': True, 'data': None})
            workflows = json.loads(row['instrument_workflows']) if isinstance(row['instrument_workflows'], str) else row['instrument_workflows']
            workflow = workflows.get(instrument_type)
            return jsonify({'success': True, 'data': workflow})
        except Exception as e:
            print(f"Get workflow error: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
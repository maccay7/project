import json
import uuid
import pymysql.cursors
from flask import request, jsonify
from utils.db import get_db
from datetime import datetime

def create_sessions_table():
    """Create ui_sessions table if it doesn't exist."""
    conn = get_db()
    if not conn:
        print("❌ DB connection failed – cannot create ui_sessions")
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
        # Add optional columns if they don't exist
        optional_columns = {
            'user_id': 'INT DEFAULT NULL',
            'payload': 'JSON DEFAULT NULL',
            'versions': 'JSON DEFAULT NULL',
            'instrument_workflows': 'JSON DEFAULT NULL',
            'workflow_data': 'JSON DEFAULT NULL'
        }
        for col, definition in optional_columns.items():
            try:
                cursor.execute('SHOW COLUMNS FROM ui_sessions LIKE %s', (col,))
                if not cursor.fetchone():
                    cursor.execute(f"ALTER TABLE ui_sessions ADD COLUMN {col} {definition}")
            except Exception:
                pass
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ ui_sessions table verified/created")
    except Exception as e:
        print(f"❌ Table creation error: {e}")
        conn.close()

# Create table immediately
create_sessions_table()

def sessions_routes(app):

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
        
        # Version control data
        create_version = payload.get('create_version', False)
        instrument_type = payload.get('instrument_type')
        change_summary = payload.get('change_summary')
        dataset_snapshot = payload.get('dataset_snapshot')
        mapping_snapshot = payload.get('mapping_snapshot')
        calculation_snapshot = payload.get('calculation_snapshot')
        portfolio_snapshot = payload.get('portfolio_snapshot')
        report_snapshot = payload.get('report_snapshot')

        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'DB connection failed'}), 500
        try:
            cursor = conn.cursor()

            # Extract workflow_data from payload if present (backwards compatibility)
            workflow_data = None
            try:
                workflow_data = legacy_payload.get('workflow_progress') if isinstance(legacy_payload, dict) else None
            except Exception:
                workflow_data = None

            cursor.execute('''
                INSERT INTO ui_sessions (session_id, user_id, name, status, versions, instrument_workflows, payload, workflow_data)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    name = VALUES(name),
                    status = VALUES(status),
                    versions = VALUES(versions),
                    instrument_workflows = VALUES(instrument_workflows),
                    payload = VALUES(payload),
                    workflow_data = VALUES(workflow_data)
            ''', (
                session_id,
                user_id if user_id is not None else 0,
                name,
                status,
                json.dumps(versions) if versions else None,
                json.dumps(instrument_workflows) if instrument_workflows else None,
                json.dumps(legacy_payload) if legacy_payload else None,
                json.dumps(workflow_data) if workflow_data else None
            ))

            conn.commit()
            cursor.close()
            conn.close()
            
            # Create version entry if requested (only on Save to Session click)
            if create_version and instrument_type:
                from routes.version_history import create_version, get_next_version_number
                next_version = get_next_version_number(session_id)
                version_id = create_version(
                    session_id, next_version, instrument_type, change_summary,
                    dataset_snapshot, mapping_snapshot, calculation_snapshot,
                    portfolio_snapshot, report_snapshot, user_id
                )
                if version_id:
                    print(f"✅ Created version {next_version} for session {session_id}")
            
            return jsonify({'success': True, 'session_id': session_id})
        except Exception as e:
            print(f"❌ Save session error: {e}")
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
            cursor = conn.cursor(pymysql.cursors.DictCursor)  # <-- FIXED
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
            print(f"❌ Get session error: {e}")
            return jsonify({'success': False, 'message': 'Query failed'}), 500

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
                SELECT session_id, name, status, versions, instrument_workflows, created_at, updated_at
                FROM ui_sessions LIMIT 200
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
                instrument_workflows = {}
                if row.get('instrument_workflows'):
                    try:
                        instrument_workflows = json.loads(row['instrument_workflows']) if isinstance(row['instrument_workflows'], str) else row['instrument_workflows']
                    except:
                        pass
                sessions_list.append({
                    'id': row['session_id'],
                    'name': row['name'],
                    'status': row['status'],
                    'versions': versions,
                    'instrumentCount': len(instrument_workflows) if instrument_workflows else 0,
                    'date': row['created_at'].isoformat() if row['created_at'] else None
                })
            return jsonify({'success': True, 'data': sessions_list})
        except Exception as e:
            print(f"❌ List sessions error: {e}")
            import traceback
            traceback.print_exc()
            # Return empty list with 200 to avoid breaking the frontend
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
            cursor.execute('DELETE FROM ui_sessions WHERE session_id = %s', (session_id,))
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'success': True})
        except Exception as e:
            print(f"❌ Delete session error: {e}")
            return jsonify({'success': False, 'message': 'Delete failed'}), 500
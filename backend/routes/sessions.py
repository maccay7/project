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
                instrument_count INT DEFAULT 0,
                version_count INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        ''')
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

    # ===== 🔥 FIXED: save_session with version_count increment =====
    @app.route('/api/sessions/save', methods=['POST', 'OPTIONS'])
    def save_session():
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        session_id = payload.get('id') or payload.get('session_id')
        
        # Require session_id - do not auto-create sessions
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
            # Fallback to legacy payload structure
            instrument_count = 0
            for key in ['money-market', 'bonds', 'tbills']:
                if legacy_payload.get(key):
                    instrument_count += 1
            instrument_count = min(instrument_count, 3)
        else:
            instrument_count = min(instrument_count, 3)

        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'DB connection failed'}), 500
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO ui_sessions (session_id, user_id, name, status, versions, instrument_workflows, payload, instrument_count, version_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    name = VALUES(name),
                    status = VALUES(status),
                    versions = VALUES(versions),
                    instrument_workflows = VALUES(instrument_workflows),
                    payload = VALUES(payload),
                    instrument_count = VALUES(instrument_count),
                    version_count = VALUES(version_count),
                    updated_at = CURRENT_TIMESTAMP
            ''', (
                session_id,
                user_id if user_id is not None else 0,
                name,
                status,
                json.dumps(versions) if versions else None,
                json.dumps(instrument_workflows) if instrument_workflows else None,
                json.dumps(legacy_payload) if legacy_payload else None,
                instrument_count,
                version_count
            ))
            conn.commit()
            
            # 🔥 REMOVED: Version creation logic - only /api/version endpoint should create versions
            # This endpoint only saves session data, never creates versions
            final_version_count = version_count
            
            cursor.close()
            conn.close()
            
            return jsonify({'success': True, 'session_id': session_id, 'version_count': final_version_count})
        except Exception as e:
            print(f"❌ Save session error: {e}")
            import traceback
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
        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'DB error'}), 500
        try:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute('''
                SELECT session_id as id, name, status, versions, instrument_workflows, payload, 
                       instrument_count, version_count, created_at, updated_at
                FROM ui_sessions WHERE session_id = %s LIMIT 1
            ''', (session_id,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            if not row:
                return jsonify({'success': True, 'data': None, 'message': 'Session not found'}), 200
            
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
            
            # 🔥 Ensure version_count is accurate from history table
            try:
                hist_cursor = conn.cursor()
                hist_cursor.execute('SELECT COUNT(*) as cnt FROM version_history WHERE session_id = %s', (session_id,))
                hist_row = hist_cursor.fetchone()
                if hist_row and hist_row.get('cnt', 0) > row.get('version_count', 0):
                    row['version_count'] = hist_row.get('cnt', 0)
                    # Update session to fix version_count
                    upd_cursor = conn.cursor()
                    upd_cursor.execute('UPDATE ui_sessions SET version_count = %s WHERE session_id = %s', (row['version_count'], session_id))
                    conn.commit()
                    upd_cursor.close()
                hist_cursor.close()
            except Exception as e:
                print(f"⚠️ Failed to check version history: {e}")
            
            return jsonify({
                'success': True,
                'data': {
                    'id': row['session_id'],
                    'session_id': row['session_id'],
                    'name': row['name'],
                    'status': row['status'],
                    'versions': versions,
                    'instrument_workflows': instrument_workflows,
                    'instrument_workflow': instrument_workflows,  # alias for frontend
                    'payload': payload,
                    'instrument_count': row.get('instrument_count', 0),
                    'version_count': row.get('version_count', 0),
                    'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                    'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None
                }
            })
        except Exception as e:
            print(f"❌ Get session error: {e}")
            import traceback
            traceback.print_exc()
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
                SELECT s.session_id, s.name, s.status, s.instrument_workflows, 
                       s.created_at, s.updated_at, s.instrument_count, s.version_count,
                       (SELECT COUNT(*) FROM version_history v WHERE v.session_id = s.session_id) as version_count_from_history
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
                        instrument_workflows = json.loads(row['instrument_workflows']) if isinstance(row['instrument_workflows'], str) else row['instrument_workflows']
                    except:
                        pass
                instrument_count = row.get('instrument_count', 0)
                # Recompute instrument_count from workflows if it's 0 or missing
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
                
                # Use the larger version count
                version_count = max(row.get('version_count', 0), row.get('version_count_from_history', 0))
                
                sessions_list.append({
                    'id': row['session_id'],
                    'name': row['name'],
                    'status': row['status'],
                    'versions': [],
                    'version_count': version_count,
                    'instrument_count': instrument_count,
                    'date': row['created_at'].isoformat() if row['created_at'] else None,
                    'created_at': row['created_at'].isoformat() if row['created_at'] else None
                })
            return jsonify({'success': True, 'data': sessions_list})
        except Exception as e:
            print(f"❌ List sessions error: {e}")
            import traceback
            traceback.print_exc()
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
            cursor.execute('DELETE FROM version_history WHERE session_id = %s', (session_id,))
            cursor.execute('DELETE FROM ui_sessions WHERE session_id = %s', (session_id,))
            conn.commit()
            cursor.close()
            conn.close()
            print(f'✅ Session {session_id} and all related records deleted')
            return jsonify({'success': True})
        except Exception as e:
            print(f"❌ Delete session error: {e}")
            conn.close()
            return jsonify({'success': False, 'message': 'Delete failed'}), 500

    # ===== 🔥 NEW: Endpoint to increment version count =====
    # 🔥 REMOVED: increment-version endpoint - version_count should only be updated by create_version
    # This endpoint was dangerous as it could increment count without creating a version
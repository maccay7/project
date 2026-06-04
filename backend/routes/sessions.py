import json
import uuid
from flask import request, jsonify
from utils.db import get_db


def sessions_routes(app):
    @app.route('/api/sessions/save', methods=['POST', 'OPTIONS'])
    def save_session():
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        session_id = payload.get('id') or payload.get('session_id') or str(int(uuid.uuid4().int % 1e12))
        name = payload.get('name') or ''
        instrument = payload.get('instrument') or payload.get('instrumentType') or ''
        status = payload.get('status') or 'upload'
        user_id = payload.get('user_id')
        payload_json = json.dumps(payload.get('payload') or payload)

        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'DB connection failed'}), 500
        try:
            cursor = conn.cursor()
            # create a separate ui_sessions table if not exists (avoid colliding with auth sessions table)
            try:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS ui_sessions (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        session_id VARCHAR(255) UNIQUE,
                        user_id INT,
                        name VARCHAR(255),
                        instrument VARCHAR(128),
                        payload JSON,
                        status VARCHAR(64),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                ''')
            except Exception:
                # ignore if cannot create; will attempt to work with existing table name
                try:
                    cursor.execute('ALTER TABLE ui_sessions ADD COLUMN session_id VARCHAR(255)')
                except Exception:
                    pass
                try:
                    cursor.execute('ALTER TABLE ui_sessions ADD COLUMN payload JSON')
                except Exception:
                    pass
            # Ensure expected columns exist (MySQL 8+ supports IF NOT EXISTS; wrap in try/except for compatibility)
            # Ensure commonly expected columns exist on ui_sessions; best-effort add if missing
            for col_sql in [
                "ALTER TABLE ui_sessions ADD COLUMN IF NOT EXISTS session_id VARCHAR(255)",
                "ALTER TABLE ui_sessions ADD COLUMN IF NOT EXISTS payload JSON",
                "ALTER TABLE ui_sessions ADD COLUMN IF NOT EXISTS name VARCHAR(255)",
                "ALTER TABLE ui_sessions ADD COLUMN IF NOT EXISTS instrument VARCHAR(128)",
                "ALTER TABLE ui_sessions ADD COLUMN IF NOT EXISTS status VARCHAR(64)"
            ]:
                try:
                    cursor.execute(col_sql)
                except Exception:
                    try:
                        fallback = col_sql.replace('IF NOT EXISTS ', '')
                        cursor.execute(fallback)
                    except Exception:
                        pass

            # normalize user_id to non-null (some schemas require NOT NULL)
            user_db_id = user_id if user_id is not None else 0

            # Try the expected upsert first; if the table has a different schema, fall back to a generic insert.
            try:
                cursor.execute(
                    'REPLACE INTO ui_sessions (session_id, user_id, name, instrument, payload, status) VALUES (%s, %s, %s, %s, %s, %s)',
                    (session_id, user_db_id, name, instrument, payload_json, status)
                )
                conn.commit()
                cursor.close()
                conn.close()
                return jsonify({'success': True, 'session_id': session_id})
            except Exception as primary_exc:
                print(f"Primary REPLACE failed, attempting fallback insert: {primary_exc}")
                # Inspect existing columns and try to insert into a sensible column
                try:
                    cursor.execute('SHOW COLUMNS FROM ui_sessions')
                    cols = [r.get('Field') for r in cursor.fetchall()]
                except Exception as e:
                    print(f"Failed to inspect columns: {e}")
                    cols = []

                inserted = False
                for candidate in ('payload', 'data', 'json', 'session_data'):
                    if candidate in cols:
                        try:
                            cursor.execute(f'INSERT INTO ui_sessions ({candidate}) VALUES (%s)', (payload_json,))
                            conn.commit()
                            inserted = True
                            break
                        except Exception as e:
                            print(f"Insert into {candidate} failed: {e}")
                            continue

                if not inserted:
                    try:
                        cursor.execute('INSERT INTO ui_sessions SET payload = %s', (payload_json,))
                        conn.commit()
                        inserted = True
                    except Exception as e:
                        print(f"Generic INSERT SET payload failed: {e}")

                cursor.close()
                conn.close()
                if inserted:
                    return jsonify({'success': True, 'session_id': session_id})
                else:
                    # Nothing worked — return diagnostic info to help debugging
                    return jsonify({'success': False, 'message': str(primary_exc), 'columns': cols}), 500
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
            cursor.execute('SELECT session_id, name, instrument, payload, status, created_at FROM ui_sessions WHERE session_id = %s LIMIT 1', (session_id,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            if not row:
                # Local-only session (not saved to DB yet) — avoid 404 noise in browser
                return jsonify({'success': True, 'data': None, 'message': 'Session not in database yet'}), 200
            try:
                payload = json.loads(row.get('payload') or '{}')
            except Exception:
                payload = row.get('payload')
            return jsonify({'success': True, 'data': { 'session_id': row.get('session_id'), 'name': row.get('name'), 'instrument': row.get('instrument'), 'payload': payload, 'status': row.get('status'), 'created_at': row.get('created_at') }})
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
            cursor.execute('SELECT session_id, name, instrument, status, created_at FROM ui_sessions ORDER BY created_at DESC LIMIT 200')
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return jsonify({'success': True, 'data': rows})
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

import json
import uuid
from flask import request, jsonify
from datetime import datetime
from utils.db import get_db

# ===== HELPER FUNCTIONS =====

def get_next_version_number(session_id):
    conn = get_db()
    if not conn:
        return 1
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT MAX(version_number) as max_version FROM version_history WHERE session_id = %s",
            (session_id,)
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row and row.get('max_version'):
            return row['max_version'] + 1
        return 1
    except Exception as e:
        print(f"❌ Failed to get next version number: {e}")
        return 1


def create_version(
    session_id,
    version_number,
    instrument_type,
    change_summary,
    dataset_snapshot=None,
    mapping_snapshot=None,
    calculation_snapshot=None,
    portfolio_snapshot=None,
    report_snapshot=None,
    user_id=None
):
    conn = get_db()
    if not conn:
        print("❌ DB connection failed – version not saved")
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS version_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                session_id VARCHAR(64) NOT NULL,
                version_number INT NOT NULL,
                instrument_type VARCHAR(64) NOT NULL,
                change_summary TEXT,
                dataset_snapshot JSON,
                mapping_snapshot JSON,
                calculation_snapshot JSON,
                portfolio_snapshot JSON,
                report_snapshot JSON,
                user_id INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX (session_id),
                INDEX (version_number),
                INDEX (instrument_type),
                INDEX (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        conn.commit()
        
        cursor.execute("""
            INSERT INTO version_history (
                session_id, version_number, instrument_type, change_summary,
                dataset_snapshot, mapping_snapshot, calculation_snapshot,
                portfolio_snapshot, report_snapshot, user_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            session_id,
            version_number,
            instrument_type,
            change_summary,
            json.dumps(dataset_snapshot) if dataset_snapshot else None,
            json.dumps(mapping_snapshot) if mapping_snapshot else None,
            json.dumps(calculation_snapshot) if calculation_snapshot else None,
            json.dumps(portfolio_snapshot) if portfolio_snapshot else None,
            json.dumps(report_snapshot) if report_snapshot else None,
            user_id if user_id is not None else 0
        ))
        conn.commit()
        version_id = cursor.lastrowid
        cursor.close()
        conn.close()
        
        print(f"✅ Created version {version_number} for session {session_id} (ID: {version_id})")
        
        # Update session version_count using COUNT
        try:
            update_conn = get_db()
            if update_conn:
                up_cursor = update_conn.cursor()
                up_cursor.execute(
                    "UPDATE ui_sessions SET version_count = (SELECT COUNT(*) FROM version_history WHERE session_id = %s) WHERE session_id = %s",
                    (session_id, session_id)
                )
                update_conn.commit()
                up_cursor.close()
                update_conn.close()
                print(f"✅ Updated session {session_id} version_count using COUNT query")
        except Exception as e:
            print(f"⚠️ Failed to update session version_count: {e}")
        
        return version_id
    except Exception as e:
        print(f"❌ Failed to create version: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_versions_by_session(session_id, limit=100, offset=0):
    conn = get_db()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        print(f"🔍 Querying versions for session_id: {session_id} (type: {type(session_id)})")
        # Remove ORDER BY to avoid sort buffer memory issues, sort in frontend instead
        cursor.execute("""
            SELECT id, version_number, instrument_type, change_summary,
                   dataset_snapshot, mapping_snapshot, calculation_snapshot,
                   portfolio_snapshot, report_snapshot, user_id, created_at
            FROM version_history
            WHERE session_id = %s
            LIMIT %s OFFSET %s
        """, (session_id, limit, offset))
        rows = cursor.fetchall()
        print(f"🔍 Found {len(rows)} versions for session {session_id}")
        cursor.close()
        conn.close()
        
        versions = []
        for row in rows:
            version = {
                'id': row.get('id'),
                'versionNumber': row.get('version_number'),
                'instrumentType': row.get('instrument_type'),
                'changeSummary': row.get('change_summary'),
                'timestamp': row.get('created_at').isoformat() if row.get('created_at') else None,
                'userId': row.get('user_id'),
            }
            for snapshot_field in ['dataset_snapshot', 'mapping_snapshot', 'calculation_snapshot',
                                   'portfolio_snapshot', 'report_snapshot']:
                value = row.get(snapshot_field)
                if value:
                    try:
                        version[snapshot_field] = json.loads(value) if isinstance(value, str) else value
                    except:
                        version[snapshot_field] = None
                else:
                    version[snapshot_field] = None
            versions.append(version)
        return versions
    except Exception as e:
        print(f"❌ Failed to get versions: {e}")
        return []


def get_latest_version(session_id):
    versions = get_versions_by_session(session_id, limit=1)
    return versions[0] if versions else None


def get_version_by_id(version_id):
    conn = get_db()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, session_id, version_number, instrument_type, change_summary,
                   dataset_snapshot, mapping_snapshot, calculation_snapshot,
                   portfolio_snapshot, report_snapshot, user_id, created_at
            FROM version_history
            WHERE id = %s
        """, (version_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if not row:
            return None
        version = {
            'id': row.get('id'),
            'sessionId': row.get('session_id'),
            'versionNumber': row.get('version_number'),
            'instrumentType': row.get('instrument_type'),
            'changeSummary': row.get('change_summary'),
            'timestamp': row.get('created_at').isoformat() if row.get('created_at') else None,
            'userId': row.get('user_id'),
        }
        for snapshot_field in ['dataset_snapshot', 'mapping_snapshot', 'calculation_snapshot',
                               'portfolio_snapshot', 'report_snapshot']:
            value = row.get(snapshot_field)
            if value:
                try:
                    version[snapshot_field] = json.loads(value) if isinstance(value, str) else value
                except:
                    version[snapshot_field] = None
            else:
                version[snapshot_field] = None
        return version
    except Exception as e:
        print(f"❌ Failed to get version by ID: {e}")
        return None


def delete_versions_by_session(session_id):
    conn = get_db()
    if not conn:
        return 0
    try:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM version_history WHERE session_id = %s",
            (session_id,)
        )
        deleted = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()
        print(f"✅ Deleted {deleted} versions for session {session_id}")
        return deleted
    except Exception as e:
        print(f"❌ Failed to delete versions: {e}")
        return 0


def get_version_count(session_id):
    conn = get_db()
    if not conn:
        return 0
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) as count FROM version_history WHERE session_id = %s",
            (session_id,)
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row.get('count', 0) if row else 0
    except Exception as e:
        print(f"❌ Failed to get version count: {e}")
        return 0


def version_history_routes(app):
    @app.route('/api/version', methods=['POST', 'OPTIONS'])
    def create_version_endpoint():
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        session_id = payload.get('session_id')
        instrument_type = payload.get('instrument_type', 'general')
        change_summary = payload.get('change_summary', 'Version saved')
        dataset_snapshot = payload.get('dataset_snapshot')
        mapping_snapshot = payload.get('mapping_snapshot')
        calculation_snapshot = payload.get('calculation_snapshot')
        portfolio_snapshot = payload.get('portfolio_snapshot')
        report_snapshot = payload.get('report_snapshot')
        user_id = payload.get('user_id')
        if not session_id:
            return jsonify({'success': False, 'message': 'session_id required'}), 400
        next_version = get_next_version_number(session_id)
        version_id = create_version(
            session_id,
            next_version,
            instrument_type,
            change_summary,
            dataset_snapshot,
            mapping_snapshot,
            calculation_snapshot,
            portfolio_snapshot,
            report_snapshot,
            user_id
        )
        if version_id:
            return jsonify({
                'success': True,
                'version_id': version_id,
                'version_number': next_version
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to create version'}), 500

    @app.route('/api/version/session/<session_id>', methods=['GET', 'OPTIONS'])
    def get_versions(session_id):
        if request.method == 'OPTIONS':
            return '', 200
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        versions = get_versions_by_session(session_id, limit, offset)
        total = get_version_count(session_id)
        return jsonify({
            'success': True,
            'data': versions,
            'total': total,
            'limit': limit,
            'offset': offset
        })

    @app.route('/api/version/session/<session_id>/latest', methods=['GET', 'OPTIONS'])
    def get_latest_version_endpoint(session_id):
        if request.method == 'OPTIONS':
            return '', 200
        version = get_latest_version(session_id)
        if version:
            return jsonify({'success': True, 'data': version})
        else:
            return jsonify({'success': False, 'message': 'No versions found'}), 404

    @app.route('/api/version/<int:version_id>', methods=['GET', 'OPTIONS'])
    def get_version_by_id_endpoint(version_id):
        if request.method == 'OPTIONS':
            return '', 200
        version = get_version_by_id(version_id)
        if version:
            return jsonify({'success': True, 'data': version})
        else:
            return jsonify({'success': False, 'message': 'Version not found'}), 404

    @app.route('/api/version/<int:version_id>/restore', methods=['POST', 'OPTIONS'])
    def restore_version_endpoint(version_id):
        if request.method == 'OPTIONS':
            return '', 200
        version = get_version_by_id(version_id)
        if not version:
            return jsonify({'success': False, 'message': 'Version not found'}), 404
        
        session_id = version.get('sessionId')
        if not session_id:
            return jsonify({'success': False, 'message': 'Session ID not found in version'}), 400
        
        # Restore the version data to the session
        dataset_snapshot = version.get('dataset_snapshot')
        if dataset_snapshot:
            conn = get_db()
            if not conn:
                return jsonify({'success': False, 'message': 'DB connection failed'}), 500
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE ui_sessions 
                    SET instrument_workflows = %s,
                        payload = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE session_id = %s
                """, (
                    json.dumps(dataset_snapshot) if dataset_snapshot else None,
                    json.dumps(dataset_snapshot) if dataset_snapshot else None,
                    session_id
                ))
                conn.commit()
                cursor.close()
                conn.close()
                print(f"✅ Restored session {session_id} to version {version.get('versionNumber')}")
                return jsonify({
                    'success': True,
                    'message': f'Session restored to version {version.get("versionNumber")}',
                    'data': version
                })
            except Exception as e:
                print(f"❌ Failed to restore version: {e}")
                return jsonify({'success': False, 'message': f'Restore failed: {str(e)}'}), 500
        else:
            return jsonify({'success': False, 'message': 'No dataset snapshot found in version'}), 400

    @app.route('/api/version/count', methods=['GET', 'OPTIONS'])
    def get_total_version_count():
        if request.method == 'OPTIONS':
            return '', 200
        conn = get_db()
        if not conn:
            return jsonify({'success': True, 'count': 0})
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM version_history")
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            return jsonify({'success': True, 'count': row.get('count', 0) if row else 0})
        except Exception as e:
            print(f"❌ Failed to get total version count: {e}")
            return jsonify({'success': True, 'count': 0})

    @app.route('/api/version/session/<session_id>/delete', methods=['DELETE', 'OPTIONS'])
    def delete_versions_endpoint(session_id):
        if request.method == 'OPTIONS':
            return '', 200
        deleted = delete_versions_by_session(session_id)
        return jsonify({'success': True, 'deleted': deleted})

    @app.route('/api/version/<int:version_id>/delete', methods=['DELETE', 'OPTIONS'])
    def delete_version_by_id_endpoint(version_id):
        if request.method == 'OPTIONS':
            return '', 200
        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'DB connection failed'}), 500
        try:
            cursor = conn.cursor()
            # Get session_id before deleting
            cursor.execute('SELECT session_id FROM version_history WHERE id = %s', (version_id,))
            row = cursor.fetchone()
            if not row:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': 'Version not found'}), 404
            session_id = row.get('session_id')
            
            # Delete the version
            cursor.execute('DELETE FROM version_history WHERE id = %s', (version_id,))
            deleted = cursor.rowcount
            conn.commit()
            cursor.close()
            
            # Update session version_count using COUNT
            try:
                update_conn = get_db()
                if update_conn:
                    up_cursor = update_conn.cursor()
                    up_cursor.execute(
                        'UPDATE ui_sessions SET version_count = (SELECT COUNT(*) FROM version_history WHERE session_id = %s) WHERE session_id = %s',
                        (session_id, session_id)
                    )
                    update_conn.commit()
                    up_cursor.close()
                    update_conn.close()
                    print(f'✅ Updated session {session_id} version_count after deletion')
            except Exception as e:
                print(f'⚠️ Failed to update session version_count: {e}')
            
            conn.close()
            print(f'✅ Deleted version {version_id} for session {session_id}')
            return jsonify({'success': True, 'deleted': deleted, 'session_id': session_id})
        except Exception as e:
            print(f'❌ Failed to delete version: {e}')
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'message': str(e)}), 500
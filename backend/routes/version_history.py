import json
from flask import request, jsonify
from utils.db import get_db
from datetime import datetime


def create_version_history_table():
    """Create the version_history table if it doesn't exist."""
    conn = get_db()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS version_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                session_id INT NOT NULL,
                version_number INT NOT NULL,
                instrument_type VARCHAR(50),
                workflow_snapshot JSON,
                change_summary TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id INT,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error creating version_history table: {e}")
        conn.close()
        return False


def create_version(session_id, version_number, instrument_type, workflow_snapshot, change_summary, user_id=None):
    """Create a new version."""
    conn = get_db()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO version_history 
               (session_id, version_number, instrument_type, workflow_snapshot, change_summary, user_id) 
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (session_id, version_number, instrument_type, json.dumps(workflow_snapshot), change_summary, user_id)
        )
        conn.commit()
        version_id = cursor.lastrowid
        cursor.close()
        conn.close()
        return version_id
    except Exception as e:
        print(f"Error creating version: {e}")
        conn.close()
        return None


def get_version_history(session_id):
    """Get all versions for a session."""
    conn = get_db()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM version_history WHERE session_id = %s ORDER BY version_number DESC",
            (session_id,)
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        versions = []
        for row in rows:
            versions.append({
                'id': row['id'],
                'session_id': row['session_id'],
                'version_number': row['version_number'],
                'instrument_type': row['instrument_type'],
                'workflow_snapshot': json.loads(row['workflow_snapshot']) if row['workflow_snapshot'] else {},
                'change_summary': row['change_summary'],
                'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                'user_id': row['user_id']
            })
        return versions
    except Exception as e:
        print(f"Error getting version history: {e}")
        conn.close()
        return []


def get_latest_version(session_id):
    """Get the latest version for a session."""
    conn = get_db()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM version_history WHERE session_id = %s ORDER BY version_number DESC LIMIT 1",
            (session_id,)
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not row:
            return None
        
        return {
            'id': row['id'],
            'session_id': row['session_id'],
            'version_number': row['version_number'],
            'instrument_type': row['instrument_type'],
            'workflow_snapshot': json.loads(row['workflow_snapshot']) if row['workflow_snapshot'] else {},
            'change_summary': row['change_summary'],
            'created_at': row['created_at'].isoformat() if row['created_at'] else None,
            'user_id': row['user_id']
        }
    except Exception as e:
        print(f"Error getting latest version: {e}")
        conn.close()
        return None


def restore_version(version_id):
    """Restore a version by returning its workflow snapshot."""
    conn = get_db()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM version_history WHERE id = %s", (version_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not row:
            return None
        
        return {
            'id': row['id'],
            'session_id': row['session_id'],
            'version_number': row['version_number'],
            'instrument_type': row['instrument_type'],
            'workflow_snapshot': json.loads(row['workflow_snapshot']) if row['workflow_snapshot'] else {},
            'change_summary': row['change_summary'],
            'created_at': row['created_at'].isoformat() if row['created_at'] else None,
            'user_id': row['user_id']
        }
    except Exception as e:
        print(f"Error restoring version: {e}")
        conn.close()
        return None


def version_history_routes(app):
    """Register all version history routes."""
    
    # Create table on module load
    create_version_history_table()
    
    @app.route('/api/version', methods=['POST', 'OPTIONS'])
    def create_version_endpoint():
        if request.method == 'OPTIONS':
            return '', 200
        
        payload = request.get_json() or {}
        session_id = payload.get('session_id')
        instrument_type = payload.get('instrument_type')
        workflow_snapshot = payload.get('workflow_snapshot', {})
        change_summary = payload.get('change_summary', '')
        user_id = payload.get('user_id')
        
        if not session_id:
            return jsonify({'success': False, 'message': 'Session ID is required'}), 400
        
        # Get next version number
        versions = get_version_history(session_id)
        next_version = len(versions) + 1
        
        version_id = create_version(session_id, next_version, instrument_type, workflow_snapshot, change_summary, user_id)
        
        if version_id:
            version = restore_version(version_id)
            return jsonify({'success': True, 'data': version})
        else:
            return jsonify({'success': False, 'message': 'Failed to create version'}), 500
    
    @app.route('/api/version/session/<int:session_id>', methods=['GET', 'OPTIONS'])
    def get_session_versions(session_id):
        if request.method == 'OPTIONS':
            return '', 200
        
        versions = get_version_history(session_id)
        
        return jsonify({'success': True, 'data': versions})
    
    @app.route('/api/version/session/<int:session_id>/latest', methods=['GET', 'OPTIONS'])
    def get_latest_version_endpoint(session_id):
        if request.method == 'OPTIONS':
            return '', 200
        
        version = get_latest_version(session_id)
        
        if version:
            return jsonify({'success': True, 'data': version})
        else:
            return jsonify({'success': False, 'message': 'No versions found'}), 404
    
    @app.route('/api/version/<int:version_id>/restore', methods=['POST', 'OPTIONS'])
    def restore_version_endpoint(version_id):
        if request.method == 'OPTIONS':
            return '', 200
        
        version = restore_version(version_id)
        
        if version:
            return jsonify({'success': True, 'data': version})
        else:
            return jsonify({'success': False, 'message': 'Version not found'}), 404

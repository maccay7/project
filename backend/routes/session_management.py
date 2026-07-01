import json
from flask import request, jsonify
from utils.db import get_db
from datetime import datetime


def create_session_table():
    """Create the sessions table if it doesn't exist."""
    conn = get_db()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ui_sessions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                user_id INT,
                instrument_type VARCHAR(50),
                workflow_data JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT FALSE
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error creating sessions table: {e}")
        conn.close()
        return False


def create_session(name, user_id, instrument_type, workflow_data):
    """Create a new session."""
    conn = get_db()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO ui_sessions (name, user_id, instrument_type, workflow_data) 
               VALUES (%s, %s, %s, %s)""",
            (name, user_id, instrument_type, json.dumps(workflow_data))
        )
        conn.commit()
        session_id = cursor.lastrowid
        cursor.close()
        conn.close()
        return session_id
    except Exception as e:
        print(f"Error creating session: {e}")
        conn.close()
        return None


def update_session(session_id, workflow_data):
    """Update an existing session."""
    conn = get_db()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE ui_sessions SET workflow_data = %s, updated_at = CURRENT_TIMESTAMP 
               WHERE id = %s""",
            (json.dumps(workflow_data), session_id)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating session: {e}")
        conn.close()
        return False


def get_session(session_id):
    """Get a session by ID."""
    conn = get_db()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ui_sessions WHERE id = %s", (session_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not row:
            return None
        
        return {
            'id': row['id'],
            'name': row['name'],
            'user_id': row['user_id'],
            'instrument_type': row['instrument_type'],
            'workflow_data': json.loads(row['workflow_data']) if row['workflow_data'] else {},
            'created_at': row['created_at'].isoformat() if row['created_at'] else None,
            'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None,
            'is_active': row['is_active']
        }
    except Exception as e:
        print(f"Error getting session: {e}")
        conn.close()
        return None


def get_all_sessions(user_id=None):
    """Get all sessions, optionally filtered by user."""
    conn = get_db()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        if user_id:
            cursor.execute("SELECT * FROM ui_sessions WHERE user_id = %s ORDER BY updated_at DESC", (user_id,))
        else:
            cursor.execute("SELECT * FROM ui_sessions ORDER BY updated_at DESC")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        sessions = []
        for row in rows:
            sessions.append({
                'id': row['id'],
                'name': row['name'],
                'user_id': row['user_id'],
                'instrument_type': row['instrument_type'],
                'workflow_data': json.loads(row['workflow_data']) if row['workflow_data'] else {},
                'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None,
                'is_active': row['is_active']
            })
        return sessions
    except Exception as e:
        print(f"Error getting sessions: {e}")
        conn.close()
        return []


def delete_session(session_id):
    """Delete a session."""
    conn = get_db()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ui_sessions WHERE id = %s", (session_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error deleting session: {e}")
        conn.close()
        return False


def set_active_session(session_id):
    """Set a session as active (deactivate all others)."""
    conn = get_db()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE ui_sessions SET is_active = FALSE")
        cursor.execute("UPDATE ui_sessions SET is_active = TRUE WHERE id = %s", (session_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error setting active session: {e}")
        conn.close()
        return False


def session_management_routes(app):
    """Register all session management routes."""
    
    # Create table on module load
    create_session_table()
    
    @app.route('/api/session', methods=['POST', 'OPTIONS'])
    def create_session_endpoint():
        if request.method == 'OPTIONS':
            return '', 200
        
        payload = request.get_json() or {}
        name = payload.get('name')
        user_id = payload.get('user_id')
        instrument_type = payload.get('instrument_type')
        workflow_data = payload.get('workflow_data', {})
        
        if not name:
            return jsonify({'success': False, 'message': 'Session name is required'}), 400
        
        session_id = create_session(name, user_id, instrument_type, workflow_data)
        
        if session_id:
            session = get_session(session_id)
            return jsonify({'success': True, 'data': session})
        else:
            return jsonify({'success': False, 'message': 'Failed to create session'}), 500
    
    @app.route('/api/session/<int:session_id>', methods=['GET', 'OPTIONS'])
    def get_session_endpoint(session_id):
        if request.method == 'OPTIONS':
            return '', 200
        
        session = get_session(session_id)
        
        if session:
            return jsonify({'success': True, 'data': session})
        else:
            return jsonify({'success': False, 'message': 'Session not found'}), 404
    
    @app.route('/api/session/<int:session_id>', methods=['PUT', 'OPTIONS'])
    def update_session_endpoint(session_id):
        if request.method == 'OPTIONS':
            return '', 200
        
        payload = request.get_json() or {}
        workflow_data = payload.get('workflow_data')
        
        if not workflow_data:
            return jsonify({'success': False, 'message': 'Workflow data is required'}), 400
        
        success = update_session(session_id, workflow_data)
        
        if success:
            session = get_session(session_id)
            return jsonify({'success': True, 'data': session})
        else:
            return jsonify({'success': False, 'message': 'Failed to update session'}), 500
    
    @app.route('/api/session/<int:session_id>', methods=['DELETE', 'OPTIONS'])
    def delete_session_endpoint(session_id):
        if request.method == 'OPTIONS':
            return '', 200
        
        success = delete_session(session_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Session deleted'})
        else:
            return jsonify({'success': False, 'message': 'Failed to delete session'}), 500
    
    @app.route('/api/sessions', methods=['GET', 'OPTIONS'])
    def get_all_sessions_endpoint():
        if request.method == 'OPTIONS':
            return '', 200
        
        user_id = request.args.get('user_id', type=int)
        sessions = get_all_sessions(user_id)
        
        return jsonify({'success': True, 'data': sessions})
    
    @app.route('/api/session/<int:session_id>/activate', methods=['POST', 'OPTIONS'])
    def activate_session_endpoint(session_id):
        if request.method == 'OPTIONS':
            return '', 200
        
        success = set_active_session(session_id)
        
        if success:
            session = get_session(session_id)
            return jsonify({'success': True, 'data': session})
        else:
            return jsonify({'success': False, 'message': 'Failed to activate session'}), 500

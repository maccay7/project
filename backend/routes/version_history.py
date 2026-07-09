import json
import pymysql.cursors
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
                session_id VARCHAR(255) NOT NULL,
                version_number INT NOT NULL,
                instrument_type VARCHAR(50),
                change_summary TEXT,
                dataset_snapshot JSON,
                mapping_snapshot JSON,
                calculation_snapshot JSON,
                portfolio_snapshot JSON,
                report_snapshot JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id INT,
                INDEX idx_session_version (session_id, version_number),
                INDEX idx_session_id (session_id),
                INDEX idx_created_at (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ version_history table created/updated")
        return True
    except Exception as e:
        print(f"Error creating version_history table: {e}")
        conn.close()
        return False


def create_version(session_id, version_number, instrument_type, change_summary, dataset_snapshot=None, mapping_snapshot=None, calculation_snapshot=None, portfolio_snapshot=None, report_snapshot=None, user_id=None):
    """Create a new version."""
    conn = get_db()
    if not conn:
        print("❌ Failed to get database connection for version creation")
        return None
    try:
        cursor = conn.cursor()
        print(f"📝 Inserting version: session_id={session_id}, version_number={version_number}, instrument_type={instrument_type}")
        cursor.execute(
            """INSERT INTO version_history 
               (session_id, version_number, instrument_type, change_summary, dataset_snapshot, mapping_snapshot, calculation_snapshot, portfolio_snapshot, report_snapshot, user_id) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (session_id, version_number, instrument_type, change_summary, 
             json.dumps(dataset_snapshot) if dataset_snapshot else None,
             json.dumps(mapping_snapshot) if mapping_snapshot else None,
             json.dumps(calculation_snapshot) if calculation_snapshot else None,
             json.dumps(portfolio_snapshot) if portfolio_snapshot else None,
             json.dumps(report_snapshot) if report_snapshot else None,
             user_id)
        )
        conn.commit()
        version_id = cursor.lastrowid
        print(f"✅ Version inserted with ID: {version_id}")
        
        # ===== FIX: Update session version_count =====
        try:
            cursor.execute('UPDATE ui_sessions SET version_count = %s WHERE session_id = %s', (version_number, session_id))
            conn.commit()
            print(f"✅ Session {session_id} version_count updated to {version_number}")
        except Exception as e:
            print(f"⚠️ Failed to update version_count: {e}")
        
        # Create audit trail entry
        try:
            cursor.execute("""
                INSERT INTO audit_log (user_id, action, resource, created_at)
                VALUES (%s, %s, %s, NOW())
            """, (user_id, 'Save to Session', f'Version {version_number} - {instrument_type}'))
            conn.commit()
            print(f"✅ Audit log entry created")
        except Exception as audit_error:
            print(f"Warning: Failed to create audit log entry: {audit_error}")
        
        cursor.close()
        conn.close()
        return version_id
    except Exception as e:
        print(f"❌ Error creating version: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.close()
        return None


def get_version_history(session_id):
    """Get all versions for a session in reverse chronological order."""
    conn = get_db()
    if not conn:
        return []
    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
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
                'change_summary': row['change_summary'],
                'dataset_snapshot': json.loads(row['dataset_snapshot']) if row['dataset_snapshot'] else None,
                'mapping_snapshot': json.loads(row['mapping_snapshot']) if row['mapping_snapshot'] else None,
                'calculation_snapshot': json.loads(row['calculation_snapshot']) if row['calculation_snapshot'] else None,
                'portfolio_snapshot': json.loads(row['portfolio_snapshot']) if row['portfolio_snapshot'] else None,
                'report_snapshot': json.loads(row['report_snapshot']) if row['report_snapshot'] else None,
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
        cursor = conn.cursor(pymysql.cursors.DictCursor)
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
            'change_summary': row['change_summary'],
            'dataset_snapshot': json.loads(row['dataset_snapshot']) if row['dataset_snapshot'] else None,
            'mapping_snapshot': json.loads(row['mapping_snapshot']) if row['mapping_snapshot'] else None,
            'calculation_snapshot': json.loads(row['calculation_snapshot']) if row['calculation_snapshot'] else None,
            'portfolio_snapshot': json.loads(row['portfolio_snapshot']) if row['portfolio_snapshot'] else None,
            'report_snapshot': json.loads(row['report_snapshot']) if row['report_snapshot'] else None,
            'created_at': row['created_at'].isoformat() if row['created_at'] else None,
            'user_id': row['user_id']
        }
    except Exception as e:
        print(f"Error getting latest version: {e}")
        conn.close()
        return None


def restore_version(version_id):
    """Restore a version by returning its complete snapshot."""
    conn = get_db()
    if not conn:
        return None
    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
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
            'change_summary': row['change_summary'],
            'dataset_snapshot': json.loads(row['dataset_snapshot']) if row['dataset_snapshot'] else None,
            'mapping_snapshot': json.loads(row['mapping_snapshot']) if row['mapping_snapshot'] else None,
            'calculation_snapshot': json.loads(row['calculation_snapshot']) if row['calculation_snapshot'] else None,
            'portfolio_snapshot': json.loads(row['portfolio_snapshot']) if row['portfolio_snapshot'] else None,
            'report_snapshot': json.loads(row['report_snapshot']) if row['report_snapshot'] else None,
            'created_at': row['created_at'].isoformat() if row['created_at'] else None,
            'user_id': row['user_id']
        }
    except Exception as e:
        print(f"Error restoring version: {e}")
        conn.close()
        return None


def generate_change_summary(previous_snapshot, current_snapshot, instrument_type):
    """Generate automatic change summary based on differences between snapshots."""
    changes = []
    
    if previous_snapshot.get('dataset') != current_snapshot.get('dataset'):
        if current_snapshot.get('dataset'):
            changes.append('Dataset uploaded')
        else:
            changes.append('Dataset removed')
    
    if previous_snapshot.get('mapping') != current_snapshot.get('mapping'):
        changes.append('Excel mapping changed')
    
    prev_calc = previous_snapshot.get('calculation', {})
    curr_calc = current_snapshot.get('calculation', {})
    
    if prev_calc.get('principal') != curr_calc.get('principal'):
        changes.append('Principal updated')
    if prev_calc.get('interest_rate') != curr_calc.get('interest_rate'):
        changes.append('Interest Rate updated')
    if prev_calc.get('face_value') != curr_calc.get('face_value'):
        changes.append('Face Value changed')
    if prev_calc.get('formula') != curr_calc.get('formula'):
        changes.append('Formula updated')
    
    if previous_snapshot.get('portfolio') != current_snapshot.get('portfolio'):
        changes.append('Portfolio recalculated')
    
    if not changes and previous_snapshot != current_snapshot:
        changes.append('Data updated')
    
    return ' • '.join(changes) if changes else 'Initial save'


def get_next_version_number(session_id):
    """Get the next sequential version number for a session."""
    conn = get_db()
    if not conn:
        return 1
    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(
            "SELECT COALESCE(MAX(version_number), 0) + 1 as next_ver FROM version_history WHERE session_id = %s",
            (session_id,)
        )
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result['next_ver'] if result else 1
    except Exception as e:
        print(f"Error getting next version number: {e}")
        conn.close()
        return 1


def version_history_routes(app):
    
    create_version_history_table()
    
    @app.route('/api/version', methods=['POST', 'OPTIONS'])
    def create_version_endpoint():
        if request.method == 'OPTIONS':
            return '', 200
        
        payload = request.get_json() or {}
        session_id = payload.get('session_id')
        instrument_type = payload.get('instrument_type')
        change_summary = payload.get('change_summary')
        dataset_snapshot = payload.get('dataset_snapshot')
        mapping_snapshot = payload.get('mapping_snapshot')
        calculation_snapshot = payload.get('calculation_snapshot')
        portfolio_snapshot = payload.get('portfolio_snapshot')
        report_snapshot = payload.get('report_snapshot')
        user_id = payload.get('user_id')
        
        print(f'📝 Version creation request: session_id={session_id}, instrument_type={instrument_type}')
        
        if not session_id:
            print('❌ Session ID is required')
            return jsonify({'success': False, 'message': 'Session ID is required'}), 400
        
        next_version = get_next_version_number(session_id)
        print(f'📝 Next version number: {next_version}')
        
        if not change_summary:
            previous = get_latest_version(session_id)
            prev_snapshot = {}
            if previous:
                prev_snapshot = {
                    'dataset': previous.get('dataset_snapshot'),
                    'mapping': previous.get('mapping_snapshot'),
                    'calculation': previous.get('calculation_snapshot'),
                    'portfolio': previous.get('portfolio_snapshot')
                }
            
            curr_snapshot = {
                'dataset': dataset_snapshot,
                'mapping': mapping_snapshot,
                'calculation': calculation_snapshot,
                'portfolio': portfolio_snapshot
            }
            
            change_summary = generate_change_summary(prev_snapshot, curr_snapshot, instrument_type)
            print(f'📝 Auto-generated change summary: {change_summary}')
        
        version_id = create_version(
            session_id, next_version, instrument_type, change_summary,
            dataset_snapshot, mapping_snapshot, calculation_snapshot,
            portfolio_snapshot, report_snapshot, user_id
        )
        
        print(f'📝 Version ID returned: {version_id}')
        
        if version_id:
            version = restore_version(version_id)
            print(f'✅ Version created successfully: {version_id}')
            # Update session version_count (already done in create_version)
            return jsonify({'success': True, 'data': version})
        else:
            print(f'❌ Failed to create version')
            return jsonify({'success': False, 'message': 'Failed to create version'}), 500
    
    @app.route('/api/version/session/<session_id>', methods=['GET', 'OPTIONS'])
    def get_session_versions(session_id):
        if request.method == 'OPTIONS':
            return '', 200
        
        versions = get_version_history(session_id)
        return jsonify({'success': True, 'data': versions})
    
    @app.route('/api/version/session/<session_id>/latest', methods=['GET', 'OPTIONS'])
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

    @app.route('/api/version/count', methods=['GET', 'OPTIONS'])
    def get_total_version_count():
        if request.method == 'OPTIONS':
            return '', 200
        
        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'DB error'}), 500
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as total FROM version_history")
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            return jsonify({'success': True, 'count': result['total'] if result else 0})
        except Exception as e:
            print(f"Error getting version count: {e}")
            conn.close()
            return jsonify({'success': False, 'message': str(e)}), 500
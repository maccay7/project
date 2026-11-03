import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.db import get_db

def check_version_history(session_id):
    """Check version_history table for a specific session"""
    conn = get_db()
    if not conn:
        print("Failed to connect to database")
        return False
    
    cursor = None
    try:
        cursor = conn.cursor()
        
        # Check if session exists in ui_sessions
        cursor.execute("SELECT session_id, name FROM ui_sessions WHERE session_id = %s", (session_id,))
        session = cursor.fetchone()
        if session:
            print(f"Session found: {session}")
        else:
            print(f"Session {session_id} not found in ui_sessions")
        
        # Check version_history table structure
        cursor.execute("DESCRIBE version_history")
        columns = cursor.fetchall()
        print("\nVersion history table structure:")
        for col in columns:
            print(f"  {col}")
        
        # Check version_history for this session
        cursor.execute("SELECT COUNT(*) as count FROM version_history WHERE session_id = %s", (session_id,))
        count = cursor.fetchone()
        print(f"\nVersion count for session {session_id}: {count.get('count', 0)}")
        
        # List all versions
        cursor.execute("""
            SELECT id, version_number, instrument_type, change_summary, created_at
            FROM version_history
            WHERE session_id = %s
            ORDER BY version_number DESC
        """, (session_id,))
        versions = cursor.fetchall()
        print(f"\nVersions for session {session_id}:")
        for v in versions:
            print(f"  {v}")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    session_id = sys.argv[1] if len(sys.argv) > 1 else "1793693185080"
    check_version_history(session_id)

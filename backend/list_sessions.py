import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.db import get_db

def list_sessions():
    """List all sessions in the database"""
    conn = get_db()
    if not conn:
        print("Failed to connect to database")
        return False
    
    cursor = None
    try:
        cursor = conn.cursor()
        
        cursor.execute("SELECT session_id, name, user_id, status, instrument_count, version_count FROM ui_sessions ORDER BY created_at DESC LIMIT 10")
        sessions = cursor.fetchall()
        
        print(f"Found {len(sessions)} sessions:")
        for s in sessions:
            print(f"  Session ID: {s.get('session_id')}")
            print(f"    Name: {s.get('name')}")
            print(f"    User ID: {s.get('user_id')}")
            print(f"    Status: {s.get('status')}")
            print(f"    Instrument Count: {s.get('instrument_count')}")
            print(f"    Version Count: {s.get('version_count')}")
            print()
        
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
    list_sessions()

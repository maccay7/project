import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.db import get_db

def list_version_history():
    """List all version history records"""
    conn = get_db()
    if not conn:
        print("Failed to connect to database")
        return False
    
    cursor = None
    try:
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as count FROM version_history")
        count = cursor.fetchone()
        print(f"Total version history records: {count.get('count', 0)}")
        
        cursor.execute("""
            SELECT id, session_id, version_number, instrument_type, change_summary, created_at
            FROM version_history
            ORDER BY created_at DESC
            LIMIT 10
        """)
        versions = cursor.fetchall()
        
        print(f"\nRecent version history records:")
        for v in versions:
            print(f"  ID: {v.get('id')}")
            print(f"    Session ID: {v.get('session_id')}")
            print(f"    Version Number: {v.get('version_number')}")
            print(f"    Instrument Type: {v.get('instrument_type')}")
            print(f"    Change Summary: {v.get('change_summary')}")
            print(f"    Created At: {v.get('created_at')}")
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
    list_version_history()

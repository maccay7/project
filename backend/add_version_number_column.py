import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.db import get_db

def add_version_number_column():
    """Add version_number column to version_history table if it doesn't exist"""
    conn = get_db()
    if not conn:
        print("Failed to connect to database")
        return False
    
    cursor = None
    try:
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'version_history' 
            AND COLUMN_NAME = 'version_number'
        """)
        result = cursor.fetchone()
        
        if result:
            print("Column version_number already exists in version_history table")
            return True
        
        # Add the column
        cursor.execute("""
            ALTER TABLE version_history 
            ADD COLUMN version_number INT DEFAULT 1 
            AFTER version_id
        """)
        
        # Add index
        cursor.execute("""
            ALTER TABLE version_history 
            ADD INDEX version_number (version_number)
        """)
        
        conn.commit()
        print("Successfully added version_number column to version_history table")
        return True
        
    except Exception as e:
        print(f"Error adding version_number column: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    success = add_version_number_column()
    sys.exit(0 if success else 1)

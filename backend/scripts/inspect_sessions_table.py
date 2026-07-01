import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.db import get_db

def inspect():
    conn = get_db()
    if not conn:
        print('DB connection failed')
        return
    try:
        cursor = conn.cursor()
        cursor.execute("SHOW CREATE TABLE sessions")
        row = cursor.fetchone()
        print('SHOW CREATE TABLE sessions:')
        print(row)
        cursor.execute("SHOW COLUMNS FROM sessions")
        cols = cursor.fetchall()
        print('COLUMNS:')
        for c in cols:
            print(c)
        cursor.close()
        conn.close()
    except Exception as e:
        print('Error inspecting sessions table:', e)

if __name__ == '__main__':
    inspect()

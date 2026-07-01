#!/usr/bin/env python3
"""Reset a user's password by email.

Usage: python backend/scripts/reset_password.py user@example.com NewPassword
Make sure backend/.env is configured so get_db() can connect.
"""
import os
import sys
from werkzeug.security import generate_password_hash

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.db import get_db


def reset_password(email, new_password):
    conn = get_db()
    if not conn:
        print('Database connection failed. Check .env and DB server.')
        return 1
    try:
        password_hash = generate_password_hash(new_password)
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET password_hash = %s WHERE email = %s', (password_hash, email))
        conn.commit()
        updated = cursor.rowcount
        cursor.close()
        conn.close()
        if updated:
            print(f'Updated password for {email}')
            return 0
        else:
            print(f'No user found with email: {email}')
            return 2
    except Exception as e:
        print(f'Error updating password: {e}')
        return 3


def main():
    if len(sys.argv) < 3:
        print('Usage: python backend/scripts/reset_password.py EMAIL NEW_PASSWORD')
        sys.exit(1)
    email = sys.argv[1]
    new_password = sys.argv[2]
    code = reset_password(email, new_password)
    sys.exit(code)


if __name__ == '__main__':
    main()

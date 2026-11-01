from flask import request
from utils.db import get_db


def resolve_current_user():
    authorization = request.headers.get('Authorization', '')
    scheme, _, token = authorization.partition(' ')
    if scheme.lower() != 'bearer' or not token.strip():
        return None, (401, 'Authentication required')

    conn = get_db()
    if not conn:
        return None, (503, 'Authentication service unavailable')

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                'SELECT u.id FROM auth_sessions s '
                'JOIN users u ON u.id = s.user_id '
                'WHERE s.token = %s AND s.expires_at > NOW() '
                'LIMIT 1',
                (token.strip(),)
            )
            row = cursor.fetchone()
        if not row:
            return None, (401, 'Authentication required')
        user_id = row.get('id') if isinstance(row, dict) else row[0]
        return int(user_id), None
    except Exception:
        return None, (503, 'Authentication service unavailable')
    finally:
        conn.close()


def session_is_owned(cursor, session_id, user_id, lock=False):
    query = 'SELECT user_id FROM ui_sessions WHERE session_id = %s'
    if lock:
        query += ' FOR UPDATE'
    cursor.execute(query, (session_id,))
    row = cursor.fetchone()
    if not row:
        return False
    owner_id = row.get('user_id') if isinstance(row, dict) else row[0]
    return owner_id is not None and int(owner_id) == int(user_id)

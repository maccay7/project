from utils.db import get_db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import uuid

class User:
    
    @staticmethod
    def find_by_email(email):
        """Find user by email"""
        conn = get_db()
        if not conn:
            return None
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            cursor.close()
            conn.close()
            return user
        except Exception as e:
            print(f"Find user error: {e}")
            return None

    @staticmethod
    def create_user(email, password, first_name, last_name):
        conn = get_db()
        if not conn:
            return None
        try:
            password_hash = generate_password_hash(password)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (email, password_hash, first_name, last_name) VALUES (%s, %s, %s, %s)",
                (email, password_hash, first_name, last_name)
            )
            conn.commit()
            user_id = cursor.lastrowid
            cursor.close()
            conn.close()
            return user_id
        except Exception as e:
            print(f"Create user error: {e}")
            return None

    @staticmethod
    def verify_session(token):
        if not token:
            return False
        conn = get_db()
        if not conn:
            return False
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM sessions WHERE token = %s AND expires_at > NOW()",
                (token,)
            )
            session = cursor.fetchone()
            cursor.close()
            conn.close()
            return bool(session)
        except Exception as e:
            print(f"Verify session error: {e}")
            return False

    @staticmethod
    def verify_password(user, password):
        """Verify password against stored hash"""
        if not user or not user.get('password_hash'):
            return False
        return check_password_hash(user['password_hash'], password)
    
    @staticmethod
    def create_session(user_id, ip_address=None, user_agent=None):
        """Create a new session token for user"""
        conn = get_db()
        if not conn:
            return None
        try:
            token = str(uuid.uuid4())
            expires_at = datetime.now() + timedelta(days=7)
            
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO sessions (user_id, token, expires_at, ip_address, user_agent) 
                   VALUES (%s, %s, %s, %s, %s)""",
                (user_id, token, expires_at, ip_address, user_agent)
            )
            conn.commit()
            cursor.close()
            conn.close()
            return token
        except Exception as e:
            print(f"Create session error: {e}")
            return None
    
    @staticmethod
    def get_user_preferences(user_id):
        """Get user preferences"""
        conn = get_db()
        if not conn:
            return {}
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM user_preferences WHERE user_id = %s",
                (user_id,)
            )
            prefs = cursor.fetchone()
            cursor.close()
            conn.close()
            return prefs if prefs else {}
        except Exception as e:
            print(f"Get preferences error: {e}")
            return {}
    
    @staticmethod
    def log_audit(user_id, action, resource=None, ip_address=None, user_agent=None):
        """Log user action to audit_log table"""
        conn = get_db()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO audit_log (user_id, action, resource, ip_address, user_agent) 
                   VALUES (%s, %s, %s, %s, %s)""",
                (user_id, action, resource, ip_address, user_agent)
            )
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Audit log error: {e}")
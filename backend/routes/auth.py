from flask import request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from utils.db import get_db
import uuid
from datetime import datetime, timedelta

def auth_routes(app):
    @app.route('/api/register', methods=['POST', 'OPTIONS'])
    def register():
        if request.method == 'OPTIONS':
            return '', 200
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        full_name = data.get('full_name', '').strip()
        
        if not email or not password:
            return jsonify({'success': False, 'message': 'Email and password required'}), 400
        
        name_parts = full_name.split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM users WHERE email = %s', (email,))
            if cursor.fetchone():
                return jsonify({'success': False, 'message': 'Email already registered'}), 400
            
            password_hash = generate_password_hash(password)
            cursor.execute(
                'INSERT INTO users (email, password_hash, first_name, last_name) VALUES (%s, %s, %s, %s)',
                (email, password_hash, first_name, last_name)
            )
            user_id = cursor.lastrowid
            
            cursor.execute('INSERT INTO user_preferences (user_id) VALUES (%s)', (user_id,))
            
            token = str(uuid.uuid4())
            expires_at = datetime.now() + timedelta(days=7)
            cursor.execute(
                'INSERT INTO sessions (user_id, token, expires_at) VALUES (%s, %s, %s)',
                (user_id, token, expires_at)
            )
            conn.commit()
            cursor.close()
            conn.close()
            
            return jsonify({
                'success': True,
                'token': token,
                'user': {
                    'id': user_id,
                    'email': email,
                    'name': full_name,
                    'first_name': first_name,
                    'last_name': last_name
                }
            })
        except Exception as e:
            print(f"Registration error: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/login', methods=['POST', 'OPTIONS'])
    def login():
        if request.method == 'OPTIONS':
            return '', 200
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        if not email or not password:
            return jsonify({'success': False, 'message': 'Email and password required'}), 400
        
        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'Database error'}), 500
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT id, email, password_hash, first_name, last_name FROM users WHERE email = %s', (email,))
            user = cursor.fetchone()
            if not user or not check_password_hash(user['password_hash'], password):
                return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
            
            token = str(uuid.uuid4())
            expires_at = datetime.now() + timedelta(days=7)
            cursor.execute(
                'INSERT INTO sessions (user_id, token, expires_at) VALUES (%s, %s, %s)',
                (user['id'], token, expires_at)
            )
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({
                'success': True,
                'token': token,
                'user': {
                    'id': user['id'],
                    'email': user['email'],
                    'name': f"{user['first_name']} {user['last_name']}".strip(),
                    'first_name': user['first_name'],
                    'last_name': user['last_name']
                }
            })
        except Exception as e:
            print(f"Login error: {e}")
            return jsonify({'success': False, 'message': 'Login failed'}), 500

    @app.route('/api/logout', methods=['POST', 'OPTIONS'])
    def logout():
        if request.method == 'OPTIONS':
            return '', 200
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'success': True})
        conn = get_db()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM sessions WHERE token = %s', (token,))
                conn.commit()
                cursor.close()
                conn.close()
            except:
                pass
        return jsonify({'success': True})

    @app.route('/api/session', methods=['GET', 'OPTIONS'])
    def check_session():
        if request.method == 'OPTIONS':
            return '', 200
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'authenticated': False}), 401
        conn = get_db()
        if not conn:
            return jsonify({'authenticated': False}), 401
        try:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT s.user_id, u.email, u.first_name, u.last_name FROM sessions s JOIN users u ON s.user_id = u.id WHERE s.token = %s AND s.expires_at > NOW()',
                (token,)
            )
            session = cursor.fetchone()
            cursor.close()
            conn.close()
            if not session:
                return jsonify({'authenticated': False}), 401
            return jsonify({
                'authenticated': True,
                'user': {
                    'id': session['user_id'],
                    'email': session['email'],
                    'name': f"{session['first_name']} {session['last_name']}".strip(),
                    'first_name': session['first_name'],
                    'last_name': session['last_name']
                }
            })
        except:
            return jsonify({'authenticated': False}), 401

    @app.route('/api/forgot-password', methods=['POST', 'OPTIONS'])
    def forgot_password():
        if request.method == 'OPTIONS':
            return '', 200
        data = request.get_json()
        email = data.get('email')
        if not email:
            return jsonify({'success': False, 'message': 'Email required'}), 400
        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'Database error'}), 500
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM users WHERE email = %s', (email,))
            user = cursor.fetchone()
            if not user:
                return jsonify({'success': True, 'message': 'If the email exists, a reset link has been sent.'})
            reset_token = str(uuid.uuid4())
            expires = datetime.now() + timedelta(hours=1)
            cursor.execute('''CREATE TABLE IF NOT EXISTS password_resets (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                token VARCHAR(255) NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                used BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )''')
            cursor.execute(
                'INSERT INTO password_resets (user_id, token, expires_at) VALUES (%s, %s, %s)',
                (user['id'], reset_token, expires)
            )
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'success': True, 'reset_token': reset_token, 'message': 'Reset token generated (for development)'})
        except Exception as e:
            print(f"Forgot password error: {e}")
            return jsonify({'success': False, 'message': 'Server error'}), 500

    @app.route('/api/reset-password', methods=['POST', 'OPTIONS'])
    def reset_password():
        if request.method == 'OPTIONS':
            return '', 200
        data = request.get_json()
        token = data.get('token')
        new_password = data.get('new_password')
        if not token or not new_password:
            return jsonify({'success': False, 'message': 'Token and new password required'}), 400
        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'Database error'}), 500
        try:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT user_id FROM password_resets WHERE token = %s AND expires_at > NOW() AND used = FALSE',
                (token,)
            )
            reset = cursor.fetchone()
            if not reset:
                return jsonify({'success': False, 'message': 'Invalid or expired token'}), 400
            password_hash = generate_password_hash(new_password)
            cursor.execute('UPDATE users SET password_hash = %s WHERE id = %s', (password_hash, reset['user_id']))
            cursor.execute('UPDATE password_resets SET used = TRUE WHERE token = %s', (token,))
            cursor.execute('DELETE FROM sessions WHERE user_id = %s', (reset['user_id'],))
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'success': True, 'message': 'Password reset successfully'})
        except Exception as e:
            print(f"Reset password error: {e}")
            return jsonify({'success': False, 'message': 'Server error'}), 500

    @app.route('/api/change-password', methods=['POST', 'OPTIONS'])
    def change_password():
        if request.method == 'OPTIONS':
            return '', 200
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'success': False, 'message': 'Not authenticated'}), 401
        data = request.get_json()
        old_password = data.get('old_password')
        new_password = data.get('new_password')
        if not old_password or not new_password:
            return jsonify({'success': False, 'message': 'Old and new password required'}), 400
        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'Database error'}), 500
        try:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT u.id, u.password_hash FROM sessions s JOIN users u ON s.user_id = u.id WHERE s.token = %s AND s.expires_at > NOW()',
                (token,)
            )
            session = cursor.fetchone()
            if not session:
                return jsonify({'success': False, 'message': 'Invalid session'}), 401
            if not check_password_hash(session['password_hash'], old_password):
                return jsonify({'success': False, 'message': 'Incorrect old password'}), 400
            new_hash = generate_password_hash(new_password)
            cursor.execute('UPDATE users SET password_hash = %s WHERE id = %s', (new_hash, session['id']))
            cursor.execute('DELETE FROM sessions WHERE user_id = %s AND token != %s', (session['id'], token))
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'success': True, 'message': 'Password changed successfully'})
        except Exception as e:
            print(f"Change password error: {e}")
            return jsonify({'success': False, 'message': 'Server error'}), 500
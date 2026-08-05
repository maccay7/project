from flask import request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from utils.db import get_db
import uuid
import os
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
            # ensure auth_sessions exists
            try:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS auth_sessions (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT NOT NULL,
                        token VARCHAR(255) UNIQUE NOT NULL,
                        expires_at TIMESTAMP NOT NULL,
                        ip_address VARCHAR(45),
                        user_agent TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                ''')
            except Exception:
                pass
            cursor.execute(
                'INSERT INTO auth_sessions (user_id, token, expires_at) VALUES (%s, %s, %s)',
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
                'INSERT INTO auth_sessions (user_id, token, expires_at) VALUES (%s, %s, %s)',
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
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'message': str(e)}), 500

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
                cursor.execute('DELETE FROM auth_sessions WHERE token = %s', (token,))
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
                'SELECT s.user_id, u.email, u.first_name, u.last_name FROM auth_sessions s JOIN users u ON s.user_id = u.id WHERE s.token = %s AND s.expires_at > NOW()',
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

    @app.route('/api/login-history', methods=['GET', 'OPTIONS'])
    def login_history():
        if request.method == 'OPTIONS':
            return '', 200
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'Database error'}), 500
        try:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT s.user_id FROM auth_sessions s WHERE s.token = %s AND s.expires_at > NOW()',
                (token,)
            )
            session = cursor.fetchone()
            if not session:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': 'Unauthorized'}), 401
            
            cursor.execute(
                '''SELECT s.created_at, s.expires_at, s.token, u.email 
                   FROM auth_sessions s 
                   JOIN users u ON s.user_id = u.id
                   WHERE s.user_id = %s 
                   ORDER BY s.created_at DESC 
                   LIMIT 20''',
                (session['user_id'],)
            )
            sessions = cursor.fetchall()
            cursor.close()
            conn.close()
            
            history = []
            for s in sessions:
                history.append({
                    'email': s['email'],
                    'login_time': s['created_at'].isoformat() if s['created_at'] else None,
                    'expires_at': s['expires_at'].isoformat() if s['expires_at'] else None,
                    'status': 'Active' if s['expires_at'] and s['expires_at'] > datetime.now() else 'Expired'
                })
            
            return jsonify({'success': True, 'history': history})
        except Exception as e:
            print(f"Login history error: {e}")
            return jsonify({'success': False, 'message': 'Server error'}), 500

    @app.route('/api/active-sessions', methods=['GET', 'OPTIONS'])
    def active_sessions():
        if request.method == 'OPTIONS':
            return '', 200
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'Database error'}), 500
        try:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT s.user_id FROM auth_sessions s WHERE s.token = %s AND s.expires_at > NOW()',
                (token,)
            )
            session = cursor.fetchone()
            if not session:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': 'Unauthorized'}), 401
            
            cursor.execute(
                '''SELECT s.created_at, s.expires_at, s.token, u.email 
                   FROM auth_sessions s 
                   JOIN users u ON s.user_id = u.id
                   WHERE s.user_id = %s AND s.expires_at > NOW()
                   ORDER BY s.created_at DESC''',
                (session['user_id'],)
            )
            sessions = cursor.fetchall()
            cursor.close()
            conn.close()
            
            active = []
            for s in sessions:
                active.append({
                    'email': s['email'],
                    'login_time': s['created_at'].isoformat() if s['created_at'] else None,
                    'expires_at': s['expires_at'].isoformat() if s['expires_at'] else None,
                    'device': 'Web Browser',
                    'location': 'Unknown'
                })
            
            return jsonify({'success': True, 'sessions': active})
        except Exception as e:
            print(f"Active sessions error: {e}")
            return jsonify({'success': False, 'message': 'Server error'}), 500

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
                return jsonify({'success': True, 'message': 'If the email exists, a verification code has been sent.'})
            # Generate 6-digit verification code
            import random
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            verification_code = str(random.randint(100000, 999999))
            expires = datetime.now() + timedelta(minutes=15)
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
                (user['id'], verification_code, expires)
            )
            conn.commit()
            cursor.close()
            conn.close()
            
            # Send email with verification code
            try:
                smtp_host = 'smtp.gmail.com'
                smtp_port = 587
                smtp_username = os.environ.get('SMTP_USERNAME', 'your-email@gmail.com')
                smtp_password = os.environ.get('SMTP_PASSWORD', 'your-app-password')
                
                msg = MIMEMultipart()
                msg['From'] = smtp_username
                msg['To'] = email
                msg['Subject'] = 'Password Reset Verification Code'
                
                body = f"""
                Your verification code is: {verification_code}
                
                This code will expire in 15 minutes.
                
                If you did not request this code, please ignore this email.
                """
                msg.attach(MIMEText(body, 'plain'))
                
                server = smtplib.SMTP(smtp_host, smtp_port)
                server.starttls()
                server.login(smtp_username, smtp_password)
                server.send_message(msg)
                server.quit()
                
                return jsonify({
                    'success': True,
                    'message': 'Verification code sent to your email'
                })
            except Exception as email_error:
                print(f"Email sending error: {email_error}")
                # Fallback: return code if email fails (for development)
                return jsonify({
                    'success': True,
                    'message': 'Verification code sent to your email',
                    'verification_code': verification_code,
                    'note': 'Email sending failed, code returned for development'
                })
        except Exception as e:
            print(f"Forgot password error: {e}")
            return jsonify({'success': False, 'message': 'Server error'}), 500

    @app.route('/api/verify-reset-code', methods=['POST', 'OPTIONS'])
    def verify_reset_code():
        if request.method == 'OPTIONS':
            return '', 200
        data = request.get_json()
        email = data.get('email')
        code = data.get('code')
        if not email or not code:
            return jsonify({'success': False, 'message': 'Email and code required'}), 400
        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'Database error'}), 500
        try:
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT pr.user_id FROM password_resets pr 
                   JOIN users u ON pr.user_id = u.id 
                   WHERE u.email = %s AND pr.token = %s AND pr.expires_at > NOW() AND pr.used = FALSE''',
                (email, code)
            )
            reset = cursor.fetchone()
            cursor.close()
            conn.close()
            if not reset:
                return jsonify({'success': False, 'message': 'Invalid or expired code'}), 400
            return jsonify({'success': True, 'message': 'Code verified'})
        except Exception as e:
            print(f"Verify code error: {e}")
            return jsonify({'success': False, 'message': 'Server error'}), 500

    @app.route('/api/reset-password', methods=['POST', 'OPTIONS'])
    def reset_password():
        if request.method == 'OPTIONS':
            return '', 200
        data = request.get_json()
        code = data.get('code')
        email = data.get('email')
        new_password = data.get('new_password')
        if not code or not email or not new_password:
            return jsonify({'success': False, 'message': 'Code, email, and new password required'}), 400
        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'Database error'}), 500
        try:
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT pr.user_id FROM password_resets pr 
                   JOIN users u ON pr.user_id = u.id 
                   WHERE u.email = %s AND pr.token = %s AND pr.expires_at > NOW() AND pr.used = FALSE''',
                (email, code)
            )
            reset = cursor.fetchone()
            if not reset:
                return jsonify({'success': False, 'message': 'Invalid or expired code'}), 400
            password_hash = generate_password_hash(new_password)
            cursor.execute('UPDATE users SET password_hash = %s WHERE id = %s', (password_hash, reset['user_id']))
            cursor.execute('UPDATE password_resets SET used = TRUE WHERE token = %s', (code,))
            cursor.execute('DELETE FROM auth_sessions WHERE user_id = %s', (reset['user_id'],))
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
                'SELECT u.id, u.password_hash FROM auth_sessions s JOIN users u ON s.user_id = u.id WHERE s.token = %s AND s.expires_at > NOW()',
                (token,)
            )
            session = cursor.fetchone()
            if not session:
                return jsonify({'success': False, 'message': 'Invalid session'}), 401
            if not check_password_hash(session['password_hash'], old_password):
                return jsonify({'success': False, 'message': 'Incorrect old password'}), 400
            new_hash = generate_password_hash(new_password)
            cursor.execute('UPDATE users SET password_hash = %s WHERE id = %s', (new_hash, session['id']))
            cursor.execute('DELETE FROM auth_sessions WHERE user_id = %s AND token != %s', (session['id'], token))
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'success': True, 'message': 'Password changed successfully'})
        except Exception as e:
            print(f"Change password error: {e}")
            return jsonify({'success': False, 'message': 'Server error'}), 500
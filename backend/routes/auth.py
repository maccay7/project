from flask import request, jsonify
from models.user import User

def auth_routes(app):
    
    @app.route('/api/login', methods=['POST', 'OPTIONS'])
    def login():
        if request.method == 'OPTIONS':
            return '', 200
        
        try:
            data = request.get_json()
            email = data.get('email')
            password = data.get('password')
            
            # Validate input
            if not email or not password:
                return jsonify({
                    'success': False,
                    'message': 'Email and password are required'
                }), 400
            
            # Find user in database
            user = User.find_by_email(email)
            
            # Verify password
            if not user or not User.verify_password(user, password):
                return jsonify({
                    'success': False,
                    'message': 'Invalid email or password'
                }), 401
            
            # Create session token
            ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
            user_agent = request.headers.get('User-Agent')
            
            token = User.create_session(user['id'], ip_address, user_agent)
            
            if not token:
                return jsonify({
                    'success': False,
                    'message': 'Failed to create session'
                }), 500
            
            # Get user preferences
            preferences = User.get_user_preferences(user['id'])
            
            # Log the login action
            User.log_audit(user['id'], 'LOGIN', 'User logged in', ip_address, user_agent)
            
            # Return success response
            return jsonify({
                'success': True,
                'token': token,
                'user': {
                    'id': user['id'],
                    'email': user['email'],
                    'first_name': user['first_name'],
                    'last_name': user['last_name'],
                    'full_name': f"{user['first_name']} {user['last_name']}",
                    'role': user['role'],
                    'phone': user.get('phone', '')
                },
                'preferences': preferences
            })
            
        except Exception as e:
            print(f"Login error: {e}")
            return jsonify({
                'success': False,
                'message': 'Internal server error'
            }), 500
    
    @app.route('/api/logout', methods=['POST', 'OPTIONS'])
    def logout():
        if request.method == 'OPTIONS':
            return '', 200
        return jsonify({'success': True, 'message': 'Logged out successfully'})

    @app.route('/api/register', methods=['POST', 'OPTIONS'])
    def register():
        if request.method == 'OPTIONS':
            return '', 200

        try:
            data = request.get_json() or {}
            email = data.get('email')
            password = data.get('password')
            full_name = data.get('full_name', '')

            if not email or not password or not full_name:
                return jsonify({'success': False, 'message': 'Email, password, and full name are required'}), 400

            if User.find_by_email(email):
                return jsonify({'success': False, 'message': 'Email already registered'}), 409

            first_name, *rest = full_name.strip().split(' ')
            last_name = ' '.join(rest) if rest else ''
            user_id = User.create_user(email, password, first_name, last_name)
            if not user_id:
                return jsonify({'success': False, 'message': 'Failed to create user'}), 500

            ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
            user_agent = request.headers.get('User-Agent')
            token = User.create_session(user_id, ip_address, user_agent)
            if not token:
                return jsonify({'success': False, 'message': 'Failed to create session'}), 500

            user = User.find_by_email(email)
            User.log_audit(user_id, 'REGISTER', 'User registered', ip_address, user_agent)

            return jsonify({
                'success': True,
                'token': token,
                'user': {
                    'id': user['id'],
                    'email': user['email'],
                    'first_name': user['first_name'],
                    'last_name': user['last_name'],
                    'full_name': f"{user['first_name']} {user['last_name']}"
                }
            })
        except Exception as e:
            print(f"Register error: {e}")
            return jsonify({'success': False, 'message': 'Internal server error'}), 500

    @app.route('/api/verify-token', methods=['POST', 'OPTIONS'])
    def verify_token():
        if request.method == 'OPTIONS':
            return '', 200

        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        valid = User.verify_session(token)
        return jsonify({'success': True, 'valid': valid})
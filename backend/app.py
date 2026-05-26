from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os

load_dotenv()

from routes.auth import auth_routes
from routes.dashboard import dashboard_routes
from routes.calculations import calculations_routes
from routes.upload import upload_routes
from routes.settings import settings_routes

app = Flask(__name__)

# Only use Flask-CORS - remove the @app.after_request
CORS(app, 
     origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://192.168.0.125:3000"],
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization", "X-Requested-With", "Accept"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

# Register routes
auth_routes(app)
dashboard_routes(app)
calculations_routes(app)
upload_routes(app)
settings_routes(app)

@app.route('/')
def home():
    return jsonify({
        'message': 'DuraCapital API',
        'status': 'running',
        'version': '1.0.0'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Server running on http://0.0.0.0:{port}")
    app.run(debug=True, port=port, host='0.0.0.0')
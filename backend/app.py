from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os

load_dotenv()

from routes.auth import auth_routes
from routes.calculations import calculations_routes
from routes.settings import settings_routes
from routes.fred import fred_routes
from routes.sessions import sessions_routes
from routes.dataset import dataset_routes
from routes.version_history import version_history_routes
from routes.reports import reports_routes
from routes.mapping_templates import mapping_templates_routes
from routes.mapping import mapping_routes

app = Flask(__name__)

CORS(app, 
     resources={r"/api/*": {"origins": ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "http://127.0.0.1:5173", "*"]}},
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization", "X-Requested-With", "Accept"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

auth_routes(app)
calculations_routes(app)
settings_routes(app)
fred_routes(app)
sessions_routes(app)
dataset_routes(app)
version_history_routes(app)
reports_routes(app)
mapping_templates_routes(app)
mapping_routes(app)

@app.route('/api/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    response = jsonify({})
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
    return response

@app.route('/')
def home():
    return jsonify({
        'message': 'DuraCapital API',
        'status': 'running',
        'version': '1.0.0'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, port=port, host='0.0.0.0')
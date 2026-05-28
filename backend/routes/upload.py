import json
import os
from flask import request, jsonify
from pages.upload_details import (
    parse_upload_file,
    clean_data,
    save_dataset,
    get_saved_datasets,
    load_saved_dataset,
    delete_saved_dataset,
    mark_dataset_done
)
from pages.calculations_details import calculate_data


def upload_routes(app):
    @app.route('/api/upload', methods=['POST', 'OPTIONS'])
    def upload_file():
        if request.method == 'OPTIONS':
            return '', 200
        uploaded_file = request.files.get('file')
        if not uploaded_file:
            return jsonify({'success': False, 'message': 'No file uploaded'}), 400
        encoded = parse_upload_file(uploaded_file)
        return jsonify({'success': True, 'data': {'file_base64': encoded}})

    @app.route('/api/clean', methods=['POST', 'OPTIONS'])
    def clean_route():
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        data = payload.get('data', [])
        options = payload.get('options', {})
        cleaned, stats = clean_data(data, options)
        return jsonify({'success': True, 'data': cleaned, 'stats': stats})

    # ========== NEW: Endpoint that matches frontend InstrumentPage ==========
    @app.route('/api/calculate/<instrument_type>', methods=['POST', 'OPTIONS'])
    def calculate_by_type(instrument_type):
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        data = payload.get('data', [])
        # instrument_type from URL: 'money-market', 'bonds', 'tbills'
        try:
            result = calculate_data(data, instrument_type)
            # Return exactly what frontend expects: { success: true, data: {...} }
            return jsonify({'success': True, 'data': result})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    # Keep old endpoint for backward compatibility (if any)
    @app.route('/api/calculate', methods=['POST', 'OPTIONS'])
    def calculate_route():
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        data = payload.get('data', [])
        instrument_type = payload.get('instrument_type', 'tbills')
        try:
            result = calculate_data(data, instrument_type)
            return jsonify({'success': True, 'data': result})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/save-dataset', methods=['POST', 'OPTIONS'])
    def save_dataset_route():
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        dataset = save_dataset(
            payload.get('name', 'dataset'),
            payload.get('file_base64', ''),
            payload.get('sheet_names', []),
            payload.get('upload_id'),
            payload.get('data'),
            payload.get('headers'),
            payload.get('instrument_type')
        )
        return jsonify({'success': True, 'data': dataset})

    @app.route('/api/get-datasets', methods=['GET', 'OPTIONS'])
    def get_datasets_route():
        if request.method == 'OPTIONS':
            return '', 200
        return jsonify({'success': True, 'data': get_saved_datasets()})

    @app.route('/api/load-dataset', methods=['POST', 'OPTIONS'])
    def load_dataset_route():
        if request.method == 'OPTIONS':
            return '', 200
        dataset_id = request.get_json() or {}
        dataset_id = dataset_id.get('dataset_id') or dataset_id.get('upload_id')
        dataset = load_saved_dataset(dataset_id)
        if dataset is None:
            return jsonify({'success': False, 'message': 'Dataset not found'}), 404
        return jsonify({'success': True, 'data': dataset})

    @app.route('/api/delete-dataset', methods=['POST', 'OPTIONS'])
    def delete_dataset_route():
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        dataset_id = payload.get('dataset_id') or payload.get('upload_id')
        delete_saved_dataset(dataset_id)
        return jsonify({'success': True, 'message': 'Dataset deleted'})

    @app.route('/api/dataset/done', methods=['POST', 'OPTIONS'])
    def dataset_done_route():
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        dataset_id = payload.get('dataset_id') or payload.get('upload_id')
        done = payload.get('done', True)
        if payload.get('delete'):
            ok = delete_saved_dataset(dataset_id)
            if ok:
                return jsonify({'success': True, 'message': 'Dataset deleted'})
            else:
                return jsonify({'success': False, 'message': 'Failed to delete'}), 500
        else:
            marked = mark_dataset_done(dataset_id, bool(done))
            if marked:
                return jsonify({'success': True, 'message': 'Dataset updated'})
            else:
                return jsonify({'success': False, 'message': 'Failed to update dataset'}), 500
import json
from flask import request, jsonify
from utils.db import get_db


def create_mapping_table():
    """Create the column_mappings table if it doesn't exist."""
    conn = get_db()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS column_mappings (
                id INT AUTO_INCREMENT PRIMARY KEY,
                dataset_id INT NOT NULL,
                instrument_type VARCHAR(50) NOT NULL,
                column_mapping JSON NOT NULL,
                file_columns JSON,
                required_columns JSON,
                mapping_type VARCHAR(50) DEFAULT 'manual',
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_dataset_id (dataset_id)
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error creating column_mappings table: {e}")
        conn.close()
        return False


def save_mapping(dataset_id, instrument_type, column_mapping, file_columns, required_columns, mapping_type='manual'):
    """Save a column mapping to database."""
    conn = get_db()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO column_mappings 
               (dataset_id, instrument_type, column_mapping, file_columns, required_columns, mapping_type) 
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (dataset_id, instrument_type, json.dumps(column_mapping), 
             json.dumps(file_columns), json.dumps(required_columns), mapping_type)
        )
        conn.commit()
        mapping_id = cursor.lastrowid
        cursor.close()
        conn.close()
        return mapping_id
    except Exception as e:
        print(f"Error saving mapping: {e}")
        conn.close()
        return None


def get_mapping_by_dataset(dataset_id):
    """Get mapping for a specific dataset."""
    conn = get_db()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM column_mappings WHERE dataset_id = %s ORDER BY applied_at DESC LIMIT 1", (dataset_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not row:
            return None
        
        return {
            'id': row['id'],
            'dataset_id': row['dataset_id'],
            'instrument_type': row['instrument_type'],
            'column_mapping': json.loads(row['column_mapping']) if row['column_mapping'] else {},
            'file_columns': json.loads(row['file_columns']) if row['file_columns'] else [],
            'required_columns': json.loads(row['required_columns']) if row['required_columns'] else [],
            'mapping_type': row['mapping_type'],
            'applied_at': row['applied_at'].isoformat() if row['applied_at'] else None
        }
    except Exception as e:
        print(f"Error getting mapping: {e}")
        conn.close()
        return None


def mapping_routes(app):
    """Register all mapping routes."""
    
    # Create table on module load
    create_mapping_table()
    
    @app.route('/api/mapping/auto-match', methods=['POST', 'OPTIONS'])
    def auto_match_mapping():
        if request.method == 'OPTIONS':
            return '', 200
        
        payload = request.get_json() or {}
        file_columns = payload.get('file_columns', [])
        required_columns = payload.get('required_columns', [])
        
        # Import auto-match function from data_processing
        from routes.data_processing import auto_match_columns
        
        mapping = auto_match_columns(file_columns, required_columns)
        
        return jsonify({
            'success': True,
            'data': mapping
        })
    
    @app.route('/api/mapping/apply', methods=['POST', 'OPTIONS'])
    def apply_mapping():
        if request.method == 'OPTIONS':
            return '', 200
        
        payload = request.get_json() or {}
        dataset_id = payload.get('dataset_id')
        instrument_type = payload.get('instrument_type')
        column_mapping = payload.get('column_mapping', {})
        file_columns = payload.get('file_columns', [])
        required_columns = payload.get('required_columns', [])
        mapping_type = payload.get('mapping_type', 'manual')
        
        if not dataset_id or not instrument_type:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        mapping_id = save_mapping(dataset_id, instrument_type, column_mapping, file_columns, required_columns, mapping_type)
        
        if mapping_id:
            return jsonify({
                'success': True,
                'data': {
                    'mapping_id': mapping_id,
                    'column_mapping': column_mapping
                }
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to save mapping'}), 500
    
    @app.route('/api/mapping/dataset/<int:dataset_id>', methods=['GET', 'OPTIONS'])
    def get_dataset_mapping(dataset_id):
        if request.method == 'OPTIONS':
            return '', 200
        
        mapping = get_mapping_by_dataset(dataset_id)
        
        if mapping:
            return jsonify({
                'success': True,
                'data': mapping
            })
        else:
            return jsonify({'success': False, 'message': 'Mapping not found'}), 404
    
    @app.route('/api/mapping/validate', methods=['POST', 'OPTIONS'])
    def validate_mapping():
        if request.method == 'OPTIONS':
            return '', 200
        
        payload = request.get_json() or {}
        column_mapping = payload.get('column_mapping', {})
        required_columns = payload.get('required_columns', [])
        
        # Check if all required columns are mapped
        missing_columns = [col for col in required_columns if col not in column_mapping or not column_mapping[col]]
        
        return jsonify({
            'success': True,
            'data': {
                'valid': len(missing_columns) == 0,
                'missing_columns': missing_columns,
                'mapped_columns': list(column_mapping.keys())
            }
        })

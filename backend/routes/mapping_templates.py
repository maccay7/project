import json
from flask import request, jsonify
from utils.db import get_db


def create_mapping_template_table():
    """Create the mapping_templates table if it doesn't exist."""
    conn = get_db()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mapping_templates (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                instrument_type VARCHAR(50) NOT NULL,
                column_mapping JSON NOT NULL,
                required_columns JSON,
                file_columns JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY unique_name_instrument (name, instrument_type)
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error creating mapping_templates table: {e}")
        conn.close()
        return False


def save_mapping_template(name, instrument_type, column_mapping, required_columns=None, file_columns=None):
    """Save a new mapping template to the database."""
    conn = get_db()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO mapping_templates 
               (name, instrument_type, column_mapping, required_columns, file_columns) 
               VALUES (%s, %s, %s, %s, %s)""",
            (name, instrument_type, json.dumps(column_mapping), 
             json.dumps(required_columns) if required_columns else None,
             json.dumps(file_columns) if file_columns else None)
        )
        conn.commit()
        template_id = cursor.lastrowid
        cursor.close()
        conn.close()
        return template_id
    except Exception as e:
        print(f"Error saving mapping template: {e}")
        conn.close()
        return None


def get_mapping_templates(instrument_type=None):
    """Get all mapping templates, optionally filtered by instrument type."""
    conn = get_db()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        if instrument_type:
            cursor.execute(
                "SELECT * FROM mapping_templates WHERE instrument_type = %s ORDER BY created_at DESC",
                (instrument_type,)
            )
        else:
            cursor.execute("SELECT * FROM mapping_templates ORDER BY created_at DESC")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        templates = []
        for row in rows:
            templates.append({
                'id': row['id'],
                'name': row['name'],
                'instrument_type': row['instrument_type'],
                'column_mapping': json.loads(row['column_mapping']) if row['column_mapping'] else {},
                'required_columns': json.loads(row['required_columns']) if row['required_columns'] else [],
                'file_columns': json.loads(row['file_columns']) if row['file_columns'] else [],
                'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None
            })
        return templates
    except Exception as e:
        print(f"Error getting mapping templates: {e}")
        conn.close()
        return []


def get_mapping_template_by_id(template_id):
    """Get a specific mapping template by ID."""
    conn = get_db()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM mapping_templates WHERE id = %s", (template_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not row:
            return None
        
        return {
            'id': row['id'],
            'name': row['name'],
            'instrument_type': row['instrument_type'],
            'column_mapping': json.loads(row['column_mapping']) if row['column_mapping'] else {},
            'required_columns': json.loads(row['required_columns']) if row['required_columns'] else [],
            'file_columns': json.loads(row['file_columns']) if row['file_columns'] else [],
            'created_at': row['created_at'].isoformat() if row['created_at'] else None,
            'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None
        }
    except Exception as e:
        print(f"Error getting mapping template: {e}")
        conn.close()
        return None


def update_mapping_template(template_id, column_mapping=None, file_columns=None, name=None):
    """Update an existing mapping template."""
    conn = get_db()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        
        # Build dynamic update query
        updates = []
        params = []
        
        if column_mapping is not None:
            updates.append("column_mapping = %s")
            params.append(json.dumps(column_mapping))
        if file_columns is not None:
            updates.append("file_columns = %s")
            params.append(json.dumps(file_columns))
        if name is not None:
            updates.append("name = %s")
            params.append(name)
        
        if not updates:
            conn.close()
            return False
        
        params.append(template_id)
        query = f"UPDATE mapping_templates SET {', '.join(updates)} WHERE id = %s"
        
        cursor.execute(query, params)
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating mapping template: {e}")
        conn.close()
        return False


def delete_mapping_template(template_id):
    """Delete a mapping template."""
    conn = get_db()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM mapping_templates WHERE id = %s", (template_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error deleting mapping template: {e}")
        conn.close()
        return False


def mapping_templates_routes(app):
    """Register all mapping template routes."""
    
    # Create table on module load
    create_mapping_template_table()
    
    @app.route('/api/mapping-templates', methods=['GET', 'OPTIONS'])
    def get_templates():
        if request.method == 'OPTIONS':
            return '', 200
        instrument_type = request.args.get('instrument_type')
        templates = get_mapping_templates(instrument_type)
        return jsonify({'success': True, 'data': templates})
    
    @app.route('/api/mapping-templates/<int:template_id>', methods=['GET', 'OPTIONS'])
    def get_template(template_id):
        if request.method == 'OPTIONS':
            return '', 200
        template = get_mapping_template_by_id(template_id)
        if not template:
            return jsonify({'success': False, 'message': 'Template not found'}), 404
        return jsonify({'success': True, 'data': template})
    
    @app.route('/api/mapping-templates', methods=['POST', 'OPTIONS'])
    def create_template():
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        name = payload.get('name')
        instrument_type = payload.get('instrument_type')
        column_mapping = payload.get('column_mapping')
        required_columns = payload.get('required_columns')
        file_columns = payload.get('file_columns')
        
        if not name or not instrument_type or not column_mapping:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        template_id = save_mapping_template(name, instrument_type, column_mapping, required_columns, file_columns)
        if template_id:
            template = get_mapping_template_by_id(template_id)
            return jsonify({'success': True, 'data': template})
        return jsonify({'success': False, 'message': 'Failed to save template'}), 500
    
    @app.route('/api/mapping-templates/<int:template_id>', methods=['PUT', 'OPTIONS'])
    def update_template(template_id):
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        column_mapping = payload.get('column_mapping')
        file_columns = payload.get('file_columns')
        name = payload.get('name')
        
        success = update_mapping_template(template_id, column_mapping, file_columns, name)
        if success:
            template = get_mapping_template_by_id(template_id)
            return jsonify({'success': True, 'data': template})
        return jsonify({'success': False, 'message': 'Failed to update template'}), 500
    
    @app.route('/api/mapping-templates/<int:template_id>', methods=['DELETE', 'OPTIONS'])
    def delete_template(template_id):
        if request.method == 'OPTIONS':
            return '', 200
        success = delete_mapping_template(template_id)
        if success:
            return jsonify({'success': True, 'message': 'Template deleted'})
        return jsonify({'success': False, 'message': 'Failed to delete template'}), 500

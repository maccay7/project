import json
import traceback
from contextlib import contextmanager
from flask import request, jsonify
from utils.db import get_db


@contextmanager
def _db():
    conn = get_db()
    cursor = None
    if conn:
        try:
            cursor = conn.cursor()
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            conn = None
    try:
        yield conn, cursor
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def _decode_template_row(row):
    return {
        'id': row['id'],
        'name': row['name'],
        'instrument_type': row['instrument_type'],
        'column_mapping': json.loads(row['column_mapping']) if row['column_mapping'] else {},
        'required_columns': json.loads(row['required_columns']) if row['required_columns'] else [],
        'file_columns': json.loads(row['file_columns']) if row['file_columns'] else [],
        'created_at': row['created_at'].isoformat() if row['created_at'] else None,
        'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None,
    }


def create_mapping_template_table():
    with _db() as (conn, cursor):
        if not conn:
            return False
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS mapping_templates (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    instrument_type VARCHAR(50) NOT NULL,
                    column_mapping JSON NOT NULL,
                    required_columns JSON,
                    file_columns JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            return True
        except Exception as e:
            print(f"Error creating mapping_templates table: {e}")
            return False


def save_mapping_template(name, instrument_type, column_mapping,
                          required_columns=None, file_columns=None):
    with _db() as (conn, cursor):
        if not conn:
            return None
        try:
            cursor.execute(
                "SELECT id FROM mapping_templates WHERE name = %s AND instrument_type = %s",
                (name, instrument_type)
            )
            existing = cursor.fetchone()

            if existing:
                print(f"Updating existing template: {name} (ID: {existing['id']})")
                cursor.execute(
                    """UPDATE mapping_templates
                       SET column_mapping = %s, required_columns = %s, file_columns = %s
                       WHERE id = %s""",
                    (json.dumps(column_mapping),
                     json.dumps(required_columns) if required_columns else None,
                     json.dumps(file_columns) if file_columns else None,
                     existing['id'])
                )
                conn.commit()
                return existing['id']

            print(f"Creating new template: {name}")
            cursor.execute(
                """INSERT INTO mapping_templates
                   (name, instrument_type, column_mapping, required_columns, file_columns)
                   VALUES (%s, %s, %s, %s, %s)""",
                (name, instrument_type, json.dumps(column_mapping),
                 json.dumps(required_columns) if required_columns else None,
                 json.dumps(file_columns) if file_columns else None)
            )
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"Error saving mapping template: {e}")
            traceback.print_exc()
            return None


def get_mapping_templates(instrument_type=None):
    with _db() as (conn, cursor):
        if not conn:
            return []
        try:
            if instrument_type:
                cursor.execute(
                    "SELECT * FROM mapping_templates WHERE instrument_type = %s ORDER BY created_at DESC",
                    (instrument_type,)
                )
            else:
                cursor.execute("SELECT * FROM mapping_templates ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [_decode_template_row(row) for row in rows]
        except Exception as e:
            print(f"Error getting mapping templates: {e}")
            return []


def get_mapping_template_by_id(template_id):
    with _db() as (conn, cursor):
        if not conn:
            return None
        try:
            cursor.execute("SELECT * FROM mapping_templates WHERE id = %s", (template_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return _decode_template_row(row)
        except Exception as e:
            print(f"Error getting mapping template: {e}")
            return None


def update_mapping_template(template_id, column_mapping=None, file_columns=None, name=None):
    with _db() as (conn, cursor):
        if not conn:
            return False
        try:
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
                return False

            params.append(template_id)
            query = f"UPDATE mapping_templates SET {', '.join(updates)} WHERE id = %s"

            cursor.execute(query, params)
            conn.commit()
            return True
        except Exception as e:
            print(f"Error updating mapping template: {e}")
            return False


def delete_mapping_template(template_id):
    with _db() as (conn, cursor):
        if not conn:
            return False
        try:
            cursor.execute("DELETE FROM mapping_templates WHERE id = %s", (template_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting mapping template: {e}")
            return False


def mapping_templates_routes(app):
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

        print(f"POST /api/mapping-templates - payload: {payload}")

        if not name or not instrument_type or not column_mapping:
            print("Missing required fields")
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400

        template_id = save_mapping_template(name, instrument_type, column_mapping,
                                            required_columns, file_columns)
        if template_id:
            template = get_mapping_template_by_id(template_id)
            return jsonify({'success': True, 'data': template})
        print(f"Failed to save template, template_id: {template_id}")
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
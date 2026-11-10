import json
import traceback
from contextlib import contextmanager
from flask import request, jsonify
from utils.db import get_db
from utils.auth import resolve_current_user


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
                    user_id INT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_mapping_templates_user_id (user_id),
                    CONSTRAINT fk_mapping_templates_user FOREIGN KEY (user_id)
                        REFERENCES users(id) ON DELETE SET NULL
                )
            """)
            conn.commit()
            return True
        except Exception as e:
            print(f"Error creating mapping_templates table: {e}")
            return False


def save_mapping_template(name, instrument_type, column_mapping,
                          required_columns=None, file_columns=None, user_id=None):
    with _db() as (conn, cursor):
        if not conn:
            return None
        try:
            cursor.execute(
                "SELECT id FROM mapping_templates WHERE name = %s "
                "AND instrument_type = %s AND (user_id = %s OR user_id IS NULL)",
                (name, instrument_type, user_id)
            )
            existing = cursor.fetchone()

            if existing:
                print(f"Updating existing template: {name} (ID: {existing['id']})")
                cursor.execute(
                    """UPDATE mapping_templates
                       SET column_mapping = %s, required_columns = %s, file_columns = %s
                       WHERE id = %s AND (user_id = %s OR user_id IS NULL)""",
                    (json.dumps(column_mapping),
                     json.dumps(required_columns) if required_columns else None,
                     json.dumps(file_columns) if file_columns else None,
                     existing['id'], user_id)
                )
                conn.commit()
                return existing['id']

            print(f"Creating new template: {name}")
            cursor.execute(
                """INSERT INTO mapping_templates
                   (name, instrument_type, column_mapping, required_columns, file_columns, user_id)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (name, instrument_type, json.dumps(column_mapping),
                 json.dumps(required_columns) if required_columns else None,
                 json.dumps(file_columns) if file_columns else None, user_id)
            )
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"Error saving mapping template: {e}")
            traceback.print_exc()
            return None


def get_mapping_templates(user_id, instrument_type=None):
    with _db() as (conn, cursor):
        if not conn:
            raise RuntimeError('Database unavailable')
        try:
            if instrument_type:
                cursor.execute(
                    "SELECT * FROM mapping_templates WHERE instrument_type = %s "
                    "AND (user_id = %s OR user_id IS NULL) ORDER BY created_at DESC",
                    (instrument_type, user_id)
                )
            else:
                cursor.execute(
                    "SELECT * FROM mapping_templates WHERE user_id = %s OR user_id IS NULL "
                    "ORDER BY created_at DESC", (user_id,))
            rows = cursor.fetchall()
            return [_decode_template_row(row) for row in rows]
        except Exception as e:
            print(f"Error getting mapping templates: {e}")
            raise RuntimeError('Could not load mapping templates') from e


def get_mapping_template_by_id(template_id, user_id):
    with _db() as (conn, cursor):
        if not conn:
            raise RuntimeError('Database unavailable')
        try:
            cursor.execute(
                "SELECT * FROM mapping_templates WHERE id = %s "
                "AND (user_id = %s OR user_id IS NULL)",
                (template_id, user_id))
            row = cursor.fetchone()
            if not row:
                return None
            return _decode_template_row(row)
        except Exception as e:
            print(f"Error getting mapping template: {e}")
            raise RuntimeError('Could not load mapping template') from e


def update_mapping_template(template_id, user_id, column_mapping=None,
                            file_columns=None, name=None):
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
            query = (f"UPDATE mapping_templates SET {', '.join(updates)} "
                     "WHERE id = %s AND (user_id = %s OR user_id IS NULL)")

            cursor.execute(query, [*params, user_id])
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error updating mapping template: {e}")
            return False


def delete_mapping_template(template_id, user_id):
    with _db() as (conn, cursor):
        if not conn:
            return False
        try:
            cursor.execute(
                "DELETE FROM mapping_templates WHERE id = %s "
                "AND (user_id = %s OR user_id IS NULL)",
                (template_id, user_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error deleting mapping template: {e}")
            return False


def mapping_templates_routes(app):
    create_mapping_template_table()

    def authenticated_user():
        user_id, auth_error = resolve_current_user()
        if auth_error:
            status, message = auth_error
            return None, (jsonify({'success': False, 'message': message}), status)
        return user_id, None

    @app.route('/api/mapping-templates', methods=['GET', 'OPTIONS'])
    def get_templates():
        if request.method == 'OPTIONS':
            return '', 200
        user_id, auth_response = authenticated_user()
        if auth_response:
            return auth_response
        instrument_type = request.args.get('instrument_type')
        try:
            templates = get_mapping_templates(user_id, instrument_type)
        except Exception as error:
            return jsonify({'success': False, 'message': str(error)}), 500
        return jsonify({'success': True, 'data': templates})

    @app.route('/api/mapping-templates/<int:template_id>', methods=['GET', 'OPTIONS'])
    def get_template(template_id):
        if request.method == 'OPTIONS':
            return '', 200
        user_id, auth_response = authenticated_user()
        if auth_response:
            return auth_response
        try:
            template = get_mapping_template_by_id(template_id, user_id)
        except Exception as error:
            return jsonify({'success': False, 'message': str(error)}), 500
        if not template:
            return jsonify({'success': False, 'message': 'Template not found'}), 404
        return jsonify({'success': True, 'data': template})

    @app.route('/api/mapping-templates', methods=['POST', 'OPTIONS'])
    def create_template():
        if request.method == 'OPTIONS':
            return '', 200
        user_id, auth_response = authenticated_user()
        if auth_response:
            return auth_response
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
                                            required_columns, file_columns, user_id)
        if template_id:
            template = get_mapping_template_by_id(template_id, user_id)
            return jsonify({'success': True, 'data': template})
        print(f"Failed to save template, template_id: {template_id}")
        return jsonify({'success': False, 'message': 'Failed to save template'}), 500

    @app.route('/api/mapping-templates/<int:template_id>', methods=['PUT', 'OPTIONS'])
    def update_template(template_id):
        if request.method == 'OPTIONS':
            return '', 200
        user_id, auth_response = authenticated_user()
        if auth_response:
            return auth_response
        payload = request.get_json() or {}
        column_mapping = payload.get('column_mapping')
        file_columns = payload.get('file_columns')
        name = payload.get('name')

        success = update_mapping_template(
            template_id, user_id, column_mapping, file_columns, name)
        if success:
            template = get_mapping_template_by_id(template_id, user_id)
            return jsonify({'success': True, 'data': template})
        return jsonify({'success': False, 'message': 'Template not found or update failed'}), 404

    @app.route('/api/mapping-templates/<int:template_id>', methods=['DELETE', 'OPTIONS'])
    def delete_template(template_id):
        if request.method == 'OPTIONS':
            return '', 200
        user_id, auth_response = authenticated_user()
        if auth_response:
            return auth_response
        success = delete_mapping_template(template_id, user_id)
        if success:
            return jsonify({'success': True, 'message': 'Template deleted'})
        return jsonify({'success': False, 'message': 'Template not found or delete failed'}), 404
import json
import traceback
from contextlib import contextmanager
from flask import request, jsonify
from utils.db import get_db
from utils.auth import resolve_current_user, session_is_owned


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


def _decode_snapshot(value):
    if not value:
        return None
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except Exception:
        return None


def _update_session_version_count(session_id, context="using COUNT query"):
    try:
        with _db() as (conn, cursor):
            if not conn:
                return
            cursor.execute(
                "UPDATE ui_sessions SET version_count = "
                "(SELECT COUNT(*) FROM version_history WHERE session_id = %s) "
                "WHERE session_id = %s",
                (session_id, session_id)
            )
            conn.commit()
            print(f"Updated session {session_id} version_count {context}")
    except Exception as e:
        print(f"Failed to update session version_count: {e}")


def get_next_version_number(session_id):
    with _db() as (conn, cursor):
        if not conn:
            return 1
        try:
            cursor.execute(
                "SELECT MAX(version_number) as max_version FROM version_history WHERE session_id = %s",
                (session_id,)
            )
            row = cursor.fetchone()
            if row and row.get('max_version'):
                return row['max_version'] + 1
            return 1
        except Exception as e:
            print(f"Failed to get next version number: {e}")
            return 1


def create_version(session_id, version_number, instrument_type, change_summary,
                   dataset_snapshot=None, mapping_snapshot=None,
                   calculation_snapshot=None, portfolio_snapshot=None,
                   report_snapshot=None, user_id=None):
    with _db() as (conn, cursor):
        if not conn:
            return None
        try:
            conn.begin()
            if user_id is None or not session_is_owned(cursor, session_id, user_id, lock=True):
                conn.rollback()
                return None
            cursor.execute(
                "SELECT COALESCE(MAX(version_number), 0) + 1 AS next_version "
                "FROM version_history WHERE session_id = %s",
                (session_id,)
            )
            next_version = cursor.fetchone()['next_version']

            cursor.execute("""
                INSERT INTO version_history (
                    session_id, version_number, instrument_type, change_summary,
                    dataset_snapshot, mapping_snapshot, calculation_snapshot,
                    portfolio_snapshot, report_snapshot, user_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                session_id,
                next_version,
                instrument_type,
                change_summary,
                json.dumps(dataset_snapshot) if dataset_snapshot else None,
                json.dumps(mapping_snapshot) if mapping_snapshot else None,
                json.dumps(calculation_snapshot) if calculation_snapshot else None,
                json.dumps(portfolio_snapshot) if portfolio_snapshot else None,
                json.dumps(report_snapshot) if report_snapshot else None,
                user_id if user_id is not None else 0
            ))
            version_id = cursor.lastrowid

            cursor.execute(
                "UPDATE ui_sessions SET version_count = "
                "(SELECT COUNT(*) FROM version_history WHERE session_id = %s), "
                "updated_at = CURRENT_TIMESTAMP WHERE session_id = %s AND user_id = %s",
                (session_id, session_id, user_id)
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Failed to create version: {e}")
            traceback.print_exc()
            return None

    return version_id, next_version


def get_versions_by_session(session_id, limit=100, offset=0):
    with _db() as (conn, cursor):
        if not conn:
            raise RuntimeError('Database unavailable')
        try:
            cursor.execute("""
                SELECT id, version_number, instrument_type, change_summary,
                       dataset_snapshot, mapping_snapshot, calculation_snapshot,
                       portfolio_snapshot, report_snapshot, user_id, created_at
                FROM version_history
                WHERE session_id = %s
                ORDER BY version_number DESC
                LIMIT %s OFFSET %s
            """, (session_id, limit, offset))
            rows = cursor.fetchall()
        except Exception as e:
            print(f"Failed to get versions: {e}")
            raise RuntimeError('Failed to retrieve version history') from e

    versions = []
    for row in rows:
        version = {
            'id': row.get('id'),
            'versionNumber': row.get('version_number'),
            'instrumentType': row.get('instrument_type'),
            'changeSummary': row.get('change_summary'),
            'timestamp': row.get('created_at').isoformat() if row.get('created_at') else None,
            'userId': row.get('user_id'),
        }
        for field in ['dataset_snapshot', 'mapping_snapshot', 'calculation_snapshot',
                      'portfolio_snapshot', 'report_snapshot']:
            version[field] = _decode_snapshot(row.get(field))
        versions.append(version)
    return versions


def get_latest_version(session_id):
    versions = get_versions_by_session(session_id, limit=1)
    return versions[0] if versions else None


def get_version_by_id(version_id):
    with _db() as (conn, cursor):
        if not conn:
            raise RuntimeError('Database unavailable')
        try:
            cursor.execute("""
                SELECT id, session_id, version_number, instrument_type, change_summary,
                       dataset_snapshot, mapping_snapshot, calculation_snapshot,
                       portfolio_snapshot, report_snapshot, user_id, created_at
                FROM version_history
                WHERE id = %s
            """, (version_id,))
            row = cursor.fetchone()
        except Exception as e:
            print(f"Failed to get version by ID: {e}")
            raise RuntimeError('Failed to retrieve version') from e

    if not row:
        return None

    version = {
        'id': row.get('id'),
        'sessionId': row.get('session_id'),
        'versionNumber': row.get('version_number'),
        'instrumentType': row.get('instrument_type'),
        'changeSummary': row.get('change_summary'),
        'timestamp': row.get('created_at').isoformat() if row.get('created_at') else None,
        'userId': row.get('user_id'),
    }
    for field in ['dataset_snapshot', 'mapping_snapshot', 'calculation_snapshot',
                  'portfolio_snapshot', 'report_snapshot']:
        version[field] = _decode_snapshot(row.get(field))
    return version


def delete_versions_by_session(session_id):
    with _db() as (conn, cursor):
        if not conn:
            raise RuntimeError('Database unavailable')
        try:
            cursor.execute(
                "DELETE FROM version_history WHERE session_id = %s",
                (session_id,)
            )
            deleted = cursor.rowcount
            conn.commit()
            print(f"Deleted {deleted} versions for session {session_id}")
            return deleted
        except Exception as e:
            print(f"Failed to delete versions: {e}")
            raise RuntimeError('Failed to delete version history') from e


def get_version_count(session_id):
    with _db() as (conn, cursor):
        if not conn:
            raise RuntimeError('Database unavailable')
        try:
            cursor.execute(
                "SELECT COUNT(*) as count FROM version_history WHERE session_id = %s",
                (session_id,)
            )
            row = cursor.fetchone()
            return row.get('count', 0) if row else 0
        except Exception as e:
            print(f"Failed to get version count: {e}")
            raise RuntimeError('Failed to count versions') from e


def version_history_routes(app):
    def authenticated_user():
        user_id, auth_error = resolve_current_user()
        if auth_error:
            status, message = auth_error
            return None, (jsonify({'success': False, 'message': message}), status)
        return user_id, None

    def verify_session_owner(session_id, user_id):
        with _db() as (conn, cursor):
            if not conn:
                return False, (jsonify({'success': False, 'message': 'Database unavailable'}), 503)
            try:
                if not session_is_owned(cursor, session_id, user_id):
                    return False, (jsonify({'success': False, 'message': 'Session not found'}), 404)
            except Exception as error:
                return False, (jsonify({'success': False, 'message': str(error)}), 500)
        return True, None

    @app.route('/api/version', methods=['POST', 'OPTIONS'])
    def create_version_endpoint():
        if request.method == 'OPTIONS':
            return '', 200
        user_id, auth_response = authenticated_user()
        if auth_response:
            return auth_response
        payload = request.get_json() or {}
        session_id = payload.get('session_id')
        instrument_type = payload.get('instrument_type', 'general')
        change_summary = payload.get('change_summary', 'Version saved')
        dataset_snapshot = payload.get('dataset_snapshot')
        mapping_snapshot = payload.get('mapping_snapshot')
        calculation_snapshot = payload.get('calculation_snapshot')
        portfolio_snapshot = payload.get('portfolio_snapshot')
        report_snapshot = payload.get('report_snapshot')
        if not session_id:
            return jsonify({'success': False, 'message': 'session_id required'}), 400
        if len(str(session_id)) > 255:
            return jsonify({'success': False, 'message': 'session_id is too long'}), 400
        allowed, owner_error = verify_session_owner(session_id, user_id)
        if not allowed:
            return owner_error
        created = create_version(
            session_id, 0, instrument_type, change_summary,
            dataset_snapshot, mapping_snapshot, calculation_snapshot,
            portfolio_snapshot, report_snapshot, user_id
        )
        if created:
            version_id, actual_version_number = created
            return jsonify({
                'success': True,
                'version_id': version_id,
                'version_number': actual_version_number
            })
        return jsonify({'success': False, 'message': 'Failed to create version'}), 500

    @app.route('/api/version/session/<session_id>', methods=['GET', 'OPTIONS'])
    def get_versions(session_id):
        if request.method == 'OPTIONS':
            return '', 200
        user_id, auth_response = authenticated_user()
        if auth_response:
            return auth_response
        allowed, owner_error = verify_session_owner(session_id, user_id)
        if not allowed:
            return owner_error
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        limit = min(max(limit, 1), 500)
        offset = max(offset, 0)
        try:
            versions = get_versions_by_session(session_id, limit, offset)
            total = get_version_count(session_id)
        except RuntimeError as error:
            return jsonify({'success': False, 'message': str(error)}), 500
        return jsonify({
            'success': True,
            'data': versions,
            'total': total,
            'limit': limit,
            'offset': offset
        })

    @app.route('/api/version/session/<session_id>/latest', methods=['GET', 'OPTIONS'])
    def get_latest_version_endpoint(session_id):
        if request.method == 'OPTIONS':
            return '', 200
        user_id, auth_response = authenticated_user()
        if auth_response:
            return auth_response
        allowed, owner_error = verify_session_owner(session_id, user_id)
        if not allowed:
            return owner_error
        try:
            version = get_latest_version(session_id)
        except RuntimeError as error:
            return jsonify({'success': False, 'message': str(error)}), 500
        if version:
            return jsonify({'success': True, 'data': version})
        return jsonify({'success': False, 'message': 'No versions found'}), 404

    @app.route('/api/version/<int:version_id>', methods=['GET', 'OPTIONS'])
    def get_version_by_id_endpoint(version_id):
        if request.method == 'OPTIONS':
            return '', 200
        user_id, auth_response = authenticated_user()
        if auth_response:
            return auth_response
        try:
            version = get_version_by_id(version_id)
        except RuntimeError as error:
            return jsonify({'success': False, 'message': str(error)}), 500
        if version:
            allowed, owner_error = verify_session_owner(version.get('sessionId'), user_id)
            if not allowed:
                return owner_error
            return jsonify({'success': True, 'data': version})
        return jsonify({'success': False, 'message': 'Version not found'}), 404

    @app.route('/api/version/<int:version_id>/restore', methods=['POST', 'OPTIONS'])
    def restore_version_endpoint(version_id):
        if request.method == 'OPTIONS':
            return '', 200
        user_id, auth_response = authenticated_user()
        if auth_response:
            return auth_response
        try:
            version = get_version_by_id(version_id)
        except RuntimeError as error:
            return jsonify({'success': False, 'message': str(error)}), 500
        if not version:
            return jsonify({'success': False, 'message': 'Version not found'}), 404

        session_id = version.get('sessionId')
        allowed, owner_error = verify_session_owner(session_id, user_id)
        if not allowed:
            return owner_error
        if not session_id:
            return jsonify({'success': False, 'message': 'Session ID not found in version'}), 400

        dataset_snapshot = version.get('dataset_snapshot')

        if not dataset_snapshot:
            return jsonify({'success': False, 'message': 'No dataset snapshot found in version'}), 400

        with _db() as (conn, cursor):
            if not conn:
                return jsonify({'success': False, 'message': 'DB connection failed'}), 500
            try:
                cursor.execute("""
                    UPDATE ui_sessions
                    SET instrument_workflows = %s,
                        payload = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE session_id = %s AND user_id = %s
                """, (
                    json.dumps(dataset_snapshot) if dataset_snapshot else None,
                    json.dumps(dataset_snapshot) if dataset_snapshot else None,
                    session_id, user_id
                ))
                if cursor.rowcount != 1:
                    conn.rollback()
                    return jsonify({'success': False, 'message': 'Session not found'}), 404
                conn.commit()
                print(f"Restored session {session_id} to version {version.get('versionNumber')}")
                return jsonify({
                    'success': True,
                    'message': f'Session restored to version {version.get("versionNumber")}. You can now continue working on this version.',
                    'data': version
                })
            except Exception as e:
                conn.rollback()
                print(f"Failed to restore version: {e}")
                return jsonify({'success': False, 'message': f'Restore failed: {str(e)}'}), 500

    @app.route('/api/version/count', methods=['GET', 'OPTIONS'])
    def get_total_version_count():
        if request.method == 'OPTIONS':
            return '', 200
        user_id, auth_response = authenticated_user()
        if auth_response:
            return auth_response
        with _db() as (conn, cursor):
            if not conn:
                return jsonify({'success': False, 'message': 'Database unavailable'}), 503
            try:
                cursor.execute(
                    """SELECT COUNT(*) AS count
                       FROM version_history v
                       JOIN ui_sessions s ON s.session_id = v.session_id
                       WHERE s.user_id = %s""",
                    (user_id,)
                )
                row = cursor.fetchone()
                return jsonify({'success': True, 'count': row.get('count', 0) if row else 0})
            except Exception as e:
                print(f"Failed to get total version count: {e}")
                return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/version/session/<session_id>/delete', methods=['DELETE', 'OPTIONS'])
    def delete_versions_endpoint(session_id):
        if request.method == 'OPTIONS':
            return '', 200
        user_id, auth_response = authenticated_user()
        if auth_response:
            return auth_response
        allowed, owner_error = verify_session_owner(session_id, user_id)
        if not allowed:
            return owner_error
        try:
            deleted = delete_versions_by_session(session_id)
        except RuntimeError as error:
            return jsonify({'success': False, 'message': str(error)}), 500
        return jsonify({'success': True, 'deleted': deleted})

    @app.route('/api/version/<int:version_id>/delete', methods=['DELETE', 'OPTIONS'])
    def delete_version_by_id_endpoint(version_id):
        if request.method == 'OPTIONS':
            return '', 200
        user_id, auth_response = authenticated_user()
        if auth_response:
            return auth_response

        session_id = None
        deleted = 0

        with _db() as (conn, cursor):
            if not conn:
                return jsonify({'success': False, 'message': 'DB connection failed'}), 500
            try:
                cursor.execute('SELECT session_id FROM version_history WHERE id = %s', (version_id,))
                row = cursor.fetchone()
                if not row:
                    return jsonify({'success': False, 'message': 'Version not found'}), 404
                session_id = row.get('session_id')
                if not session_is_owned(cursor, session_id, user_id):
                    return jsonify({'success': False, 'message': 'Version not found'}), 404

                conn.begin()
                cursor.execute(
                    'DELETE FROM version_history WHERE id = %s AND session_id = %s',
                    (version_id, session_id)
                )
                deleted = cursor.rowcount
                conn.commit()
            except Exception as e:
                print(f"Failed to delete versions: {e}")
                traceback.print_exc()
                return jsonify({'success': False, 'message': str(e)}), 500

        _update_session_version_count(session_id, context="after deletion")
        print(f'Deleted version {version_id} for session {session_id}')
        return jsonify({'success': True, 'deleted': deleted, 'session_id': session_id})
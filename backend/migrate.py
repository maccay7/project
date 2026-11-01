"""Apply additive database migrations and record their verified versions."""

import hashlib
import os

from utils.db import get_db


MIGRATION_ID = '20260715_001_persistence_ownership'
MIGRATION_FILE = os.path.join(
    os.path.dirname(__file__), 'migrations',
    f'{MIGRATION_ID}.sql',
)


def _migration_checksum():
    with open(MIGRATION_FILE, 'rb') as migration_file:
        return hashlib.sha256(migration_file.read()).hexdigest()


def _column_metadata(cursor, table):
    cursor.execute(f'SHOW COLUMNS FROM `{table}`')
    return {
        row['Field']: row
        for row in cursor.fetchall()
    }


def _index_names(cursor, table):
    cursor.execute(f'SHOW INDEX FROM `{table}`')
    return {row['Key_name'] for row in cursor.fetchall()}


def _foreign_key_exists(cursor, table, column, referenced_table):
    cursor.execute(
        """SELECT CONSTRAINT_NAME
           FROM information_schema.KEY_COLUMN_USAGE
           WHERE TABLE_SCHEMA = DATABASE()
             AND TABLE_NAME = %s
             AND COLUMN_NAME = %s
             AND REFERENCED_TABLE_NAME = %s
           LIMIT 1""",
        (table, column, referenced_table),
    )
    return cursor.fetchone() is not None


def _schema_is_applied(cursor):
    columns = {
        table: _column_metadata(cursor, table)
        for table in (
            'datasets', 'upload_history', 'version_history',
            'mapping_templates', 'reports',
        )
    }
    indexes = {
        table: _index_names(cursor, table)
        for table in ('datasets', 'mapping_templates', 'reports')
    }

    return (
        columns['datasets'].get('user_id', {}).get('Type') == 'int'
        and columns['datasets']['user_id'].get('Null') == 'YES'
        and 'idx_datasets_user_id' in indexes['datasets']
        and _foreign_key_exists(cursor, 'datasets', 'user_id', 'users')
        and columns['upload_history'].get('file_size', {}).get('Type') == 'bigint'
        and columns['version_history'].get('session_id', {}).get('Type') == 'varchar(255)'
        and columns['version_history']['session_id'].get('Null') == 'NO'
        and 'user_id' in columns['mapping_templates']
        and 'idx_mapping_templates_user_id' in indexes['mapping_templates']
        and _foreign_key_exists(cursor, 'mapping_templates', 'user_id', 'users')
        and {'session_id', 'report_data', 'generated_at'} <= set(columns['reports'])
        and 'idx_reports_session_id' in indexes['reports']
    )


def _assert_safe_to_alter(cursor):
    cursor.execute(
        """SELECT COUNT(*) AS invalid_count
           FROM datasets d
           WHERE d.user_id IS NOT NULL
             AND (
                 CAST(d.user_id AS CHAR) NOT REGEXP '^[0-9]+$'
                 OR NOT EXISTS (
                     SELECT 1 FROM users u
                     WHERE u.id = CAST(d.user_id AS UNSIGNED)
                 )
             )"""
    )
    invalid_owner = cursor.fetchone()['invalid_count']
    if invalid_owner:
        raise RuntimeError(
            f'{invalid_owner} dataset owner values cannot be safely converted '
            'to valid user IDs; no migration changes were applied'
        )

    cursor.execute(
        """SELECT COUNT(*) AS invalid_count
           FROM version_history
           WHERE session_id IS NULL OR CHAR_LENGTH(session_id) > 255"""
    )
    invalid_session = cursor.fetchone()['invalid_count']
    if invalid_session:
        raise RuntimeError(
            f'{invalid_session} version-history session IDs cannot be stored '
            'as VARCHAR(255); no migration changes were applied'
        )


def _ensure_column_type(cursor, table, column, expected_type, expected_null):
    metadata = _column_metadata(cursor, table).get(column)
    if not metadata:
        raise RuntimeError(f'Required column {table}.{column} does not exist')
    if metadata['Type'].lower() != expected_type or metadata['Null'] != expected_null:
        cursor.execute(
            f'ALTER TABLE `{table}` MODIFY COLUMN `{column}` '
            f'{expected_type.upper()} {"NULL" if expected_null == "YES" else "NOT NULL"}'
        )


def _ensure_index(cursor, table, index_name, statement):
    if index_name not in _index_names(cursor, table):
        cursor.execute(statement)


def _ensure_foreign_key(cursor, table, column, referenced_table, statement):
    if not _foreign_key_exists(cursor, table, column, referenced_table):
        cursor.execute(statement)


def _apply_schema_changes(cursor):
    _ensure_column_type(cursor, 'datasets', 'user_id', 'int', 'YES')
    _ensure_index(
        cursor, 'datasets', 'idx_datasets_user_id',
        'ALTER TABLE datasets ADD INDEX idx_datasets_user_id (user_id)',
    )
    _ensure_foreign_key(
        cursor, 'datasets', 'user_id', 'users',
        """ALTER TABLE datasets ADD CONSTRAINT fk_datasets_user
           FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL""",
    )
    _ensure_column_type(cursor, 'upload_history', 'file_size', 'bigint', 'NO')
    _ensure_column_type(cursor, 'version_history', 'session_id', 'varchar(255)', 'NO')

    mapping_columns = _column_metadata(cursor, 'mapping_templates')
    if 'user_id' not in mapping_columns:
        cursor.execute('ALTER TABLE mapping_templates ADD COLUMN user_id INT NULL')
    _ensure_index(
        cursor, 'mapping_templates', 'idx_mapping_templates_user_id',
        'ALTER TABLE mapping_templates ADD INDEX idx_mapping_templates_user_id (user_id)',
    )
    _ensure_foreign_key(
        cursor, 'mapping_templates', 'user_id', 'users',
        """ALTER TABLE mapping_templates ADD CONSTRAINT fk_mapping_templates_user
           FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL""",
    )

    report_columns = _column_metadata(cursor, 'reports')
    if 'session_id' not in report_columns:
        cursor.execute('ALTER TABLE reports ADD COLUMN session_id VARCHAR(255) NULL')
    if 'report_data' not in report_columns:
        cursor.execute('ALTER TABLE reports ADD COLUMN report_data JSON NULL')
    if 'generated_at' not in report_columns:
        cursor.execute(
            'ALTER TABLE reports ADD COLUMN generated_at '
            'TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP'
        )
    _ensure_index(
        cursor, 'reports', 'idx_reports_session_id',
        'ALTER TABLE reports ADD INDEX idx_reports_session_id (session_id)',
    )


def apply_persistence_migration(connection=None):
    owns_connection = connection is None
    connection = connection or get_db()
    if connection is None:
        raise RuntimeError('Database unavailable')

    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS application_schema_migrations (
                migration_id VARCHAR(128) PRIMARY KEY,
                checksum CHAR(64) NOT NULL,
                applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        connection.commit()

        checksum = _migration_checksum()
        cursor.execute(
            'SELECT checksum FROM application_schema_migrations WHERE migration_id = %s',
            (MIGRATION_ID,),
        )
        recorded = cursor.fetchone()
        if recorded:
            recorded_checksum = recorded['checksum']
            if recorded_checksum != checksum:
                raise RuntimeError(
                    f'Migration {MIGRATION_ID} was recorded with a different checksum'
                )
            if not _schema_is_applied(cursor):
                raise RuntimeError(
                    f'Migration {MIGRATION_ID} is recorded, but the expected schema '
                    'is incomplete'
                )
            return 'already_applied'

        if not _schema_is_applied(cursor):
            _assert_safe_to_alter(cursor)
            _apply_schema_changes(cursor)
            connection.commit()
            if not _schema_is_applied(cursor):
                raise RuntimeError(
                    f'Migration {MIGRATION_ID} did not produce the expected schema'
                )
            result = 'applied'
        else:
            result = 'recorded_existing_schema'

        cursor.execute(
            """INSERT INTO application_schema_migrations
               (migration_id, checksum) VALUES (%s, %s)""",
            (MIGRATION_ID, checksum),
        )
        connection.commit()
        return result
    except Exception:
        try:
            connection.rollback()
        except Exception:
            pass
        raise
    finally:
        if cursor:
            cursor.close()
        if owns_connection:
            connection.close()


if __name__ == '__main__':
    print(apply_persistence_migration())

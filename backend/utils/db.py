import os
import pymysql
import pymysql.cursors
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = int(os.environ.get('DB_PORT', 3306))
DB_USER = os.environ.get('DB_USER', 'root')
DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
DB_NAME = os.environ.get('DB_NAME', 'duracapital')
DB_CHARSET = os.environ.get('DB_CHARSET', 'utf8mb4')


def get_db_connection():
    try:
        return pymysql.connect(
            host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD,
            database=DB_NAME, charset=DB_CHARSET,
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True, connect_timeout=10,
            read_timeout=30, write_timeout=30,
        )
    except pymysql.Error as e:
        print(f"Database connection error: {e}")
        return None


def get_db():
    return get_db_connection()


def get_cursor(connection=None):
    if connection is None:
        connection = get_db_connection()
        if connection is None:
            return None, None
    try:
        return connection, connection.cursor()
    except pymysql.Error as e:
        print(f"Cursor creation error: {e}")
        return connection, None


def close_connection(connection):
    if connection:
        try:
            connection.close()
        except Exception as e:
            print(f"Error closing connection: {e}")


def close_cursor(cursor):
    if cursor:
        try:
            cursor.close()
        except Exception as e:
            print(f"Error closing cursor: {e}")


def execute_query(query, params=None, fetch_one=False, fetch_all=False):
    connection = get_db_connection()
    if not connection:
        return None
    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute(query, params or ())
        if fetch_one:
            return cursor.fetchone()
        elif fetch_all:
            return cursor.fetchall()
        else:
            return cursor.rowcount
    except pymysql.Error as e:
        print(f"Query execution error: {e}")
        return None
    finally:
        close_cursor(cursor)
        close_connection(connection)


def execute_insert(query, params=None):
    connection = get_db_connection()
    if not connection:
        return None
    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute(query, params or ())
        return cursor.lastrowid
    except pymysql.Error as e:
        print(f"Insert error: {e}")
        return None
    finally:
        close_cursor(cursor)
        close_connection(connection)


def execute_update(query, params=None):
    connection = get_db_connection()
    if not connection:
        return 0
    cursor = None
    try:
        cursor = connection.cursor()
        return cursor.execute(query, params or ())
    except pymysql.Error as e:
        print(f"Update error: {e}")
        return 0
    finally:
        close_cursor(cursor)
        close_connection(connection)


def test_connection():
    connection = get_db_connection()
    if not connection:
        return False
    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        return True
    except Exception:
        return False
    finally:
        close_cursor(cursor)
        close_connection(connection)


def get_db_info():
    return {
        'host': DB_HOST,
        'port': DB_PORT,
        'database': DB_NAME,
        'charset': DB_CHARSET,
        'connected': test_connection(),
    }
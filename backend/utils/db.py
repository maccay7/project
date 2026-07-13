import os
import pymysql
import pymysql.cursors
from dotenv import load_dotenv

load_dotenv()

# Database configuration from environment variables
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = int(os.environ.get('DB_PORT', 3306))
DB_USER = os.environ.get('DB_USER', 'root')
DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
DB_NAME = os.environ.get('DB_NAME', 'duracapital')
DB_CHARSET = os.environ.get('DB_CHARSET', 'utf8mb4')

# Connection pool settings
DB_POOL_SIZE = int(os.environ.get('DB_POOL_SIZE', 5))
DB_POOL_RECYCLE = int(os.environ.get('DB_POOL_RECYCLE', 3600))

# Global connection cache
_connections = []
_connection_index = 0


def get_db_connection():
    """
    Get a MySQL database connection.
    Returns a connection object, or None if connection fails.
    """
    try:
        connection = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset=DB_CHARSET,
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True,
            connect_timeout=10,
            read_timeout=30,
            write_timeout=30
        )
        return connection
    except pymysql.Error as e:
        print(f"❌ Database connection error: {e}")
        return None


def get_db():
    """
    Get a database connection.
    Alias for get_db_connection() for backward compatibility.
    """
    return get_db_connection()


def get_cursor(connection=None):
    """
    Get a database cursor.
    If no connection is provided, creates a new one.
    Returns (connection, cursor) or (None, None) on failure.
    """
    if connection is None:
        connection = get_db_connection()
        if connection is None:
            return None, None
    
    try:
        cursor = connection.cursor()
        return connection, cursor
    except pymysql.Error as e:
        print(f"❌ Cursor creation error: {e}")
        return connection, None


def close_connection(connection):
    """
    Close a database connection safely.
    """
    if connection:
        try:
            connection.close()
        except Exception as e:
            print(f"⚠️ Error closing connection: {e}")


def close_cursor(cursor):
    """
    Close a database cursor safely.
    """
    if cursor:
        try:
            cursor.close()
        except Exception as e:
            print(f"⚠️ Error closing cursor: {e}")


def execute_query(query, params=None, fetch_one=False, fetch_all=False):
    """
    Execute a query and return results.
    Handles connection and cursor management automatically.
    Returns results or None on failure.
    """
    connection = get_db_connection()
    if not connection:
        return None
    
    try:
        cursor = connection.cursor()
        cursor.execute(query, params or ())
        
        if fetch_one:
            result = cursor.fetchone()
        elif fetch_all:
            result = cursor.fetchall()
        else:
            result = cursor.rowcount
        
        cursor.close()
        connection.close()
        return result
    except pymysql.Error as e:
        print(f"❌ Query execution error: {e}")
        close_connection(connection)
        return None


def execute_insert(query, params=None):
    """
    Execute an INSERT query and return the last inserted ID.
    """
    connection = get_db_connection()
    if not connection:
        return None
    
    try:
        cursor = connection.cursor()
        cursor.execute(query, params or ())
        last_id = cursor.lastrowid
        cursor.close()
        connection.close()
        return last_id
    except pymysql.Error as e:
        print(f"❌ Insert error: {e}")
        close_connection(connection)
        return None


def execute_update(query, params=None):
    """
    Execute an UPDATE or DELETE query and return the number of affected rows.
    """
    connection = get_db_connection()
    if not connection:
        return 0
    
    try:
        cursor = connection.cursor()
        affected = cursor.execute(query, params or ())
        cursor.close()
        connection.close()
        return affected
    except pymysql.Error as e:
        print(f"❌ Update error: {e}")
        close_connection(connection)
        return 0


def test_connection():
    """
    Test the database connection.
    Returns True if connection is successful, False otherwise.
    """
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        connection.close()
        return True
    except:
        return False


def get_db_info():
    """
    Get database connection information (for debugging).
    """
    return {
        'host': DB_HOST,
        'port': DB_PORT,
        'database': DB_NAME,
        'charset': DB_CHARSET,
        'connected': test_connection()
    }
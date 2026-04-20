"""
Write password hash to MySQL (safe parameters — no manual hash pasting).

Creates database + all app tables if missing, then sets your web login password.

PowerShell (password must be in quotes):
  cd backend   # folder that contains this script
  $env:BOOTSTRAP_PASSWORD = "maccay"
  python sync_user_password.py
  Remove-Item Env:BOOTSTRAP_PASSWORD
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

load_dotenv()

EMAIL = (os.environ.get("ALLOWED_LOGIN_EMAIL") or "makanakakanyai@gmail.com").strip().lower()
DB_NAME = (os.environ.get("MYSQL_DATABASE") or "dura_capital").strip()

# Everything the Flask app expects (matches schema.sql, without DELETE/INSERT seeds).
BOOTSTRAP_DDL = [
    """
CREATE TABLE IF NOT EXISTS users (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(512) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB
""",
    """
CREATE TABLE IF NOT EXISTS instruments (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  instrument_type VARCHAR(64) NOT NULL COMMENT 'Bonds | T-Bills | Money Market',
  issuer VARCHAR(255) NOT NULL DEFAULT '',
  face_value DECIMAL(18, 2) NOT NULL DEFAULT 0,
  current_value DECIMAL(18, 2) NOT NULL DEFAULT 0,
  yield_pct DECIMAL(12, 6) NOT NULL DEFAULT 0 COMMENT 'e.g. 4.5 for 4.5%',
  maturity_label VARCHAR(64) NOT NULL DEFAULT '' COMMENT 'YYYY-MM-DD or Rolling',
  days_left INT NULL,
  rating VARCHAR(32) DEFAULT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'Active',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_type (instrument_type)
) ENGINE=InnoDB
""",
    """
CREATE TABLE IF NOT EXISTS file_uploads (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  original_name VARCHAR(512) NOT NULL,
  stored_path VARCHAR(1024) NOT NULL,
  instrument_type VARCHAR(64) DEFAULT NULL,
  counter_party VARCHAR(255) DEFAULT NULL,
  eval_date DATE NULL,
  description TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB
""",
    """
CREATE TABLE IF NOT EXISTS audit_log (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  action VARCHAR(64) NOT NULL,
  detail JSON NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB
""",
]


def _connect(**kwargs):
    import pymysql

    return pymysql.connect(
        host=os.environ.get("MYSQL_HOST", "127.0.0.1"),
        port=int(os.environ.get("MYSQL_PORT", "3306")),
        user=os.environ.get("MYSQL_USER", "root"),
        password=os.environ.get("MYSQL_PASSWORD", ""),
        autocommit=True,
        **kwargs,
    )


def main() -> None:
    pw = os.environ.get("BOOTSTRAP_PASSWORD", "").strip()
    if not pw:
        print(
            "Set BOOTSTRAP_PASSWORD first (use quotes in PowerShell):\n"
            '  $env:BOOTSTRAP_PASSWORD = "your_app_password"\n'
            "  python sync_user_password.py",
            file=sys.stderr,
        )
        sys.exit(1)

    import pymysql

    try:
        server = _connect()
    except pymysql.err.OperationalError as e:
        if e.args[0] == 2003:
            print(
                "Cannot connect to MySQL (connection refused).\n"
                "Start MySQL in services.msc (MySQL80) or XAMPP, then try again.",
                file=sys.stderr,
            )
        elif e.args[0] == 1045:
            print(
                "MySQL rejected the login. Fix MYSQL_USER and MYSQL_PASSWORD in backend/.env.",
                file=sys.stderr,
            )
        raise

    try:
        with server.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            cur.execute(f"USE `{DB_NAME}`")
            for stmt in BOOTSTRAP_DDL:
                cur.execute(stmt)
    finally:
        server.close()

    try:
        conn = _connect(database=DB_NAME)
    except pymysql.err.OperationalError as e:
        if e.args[0] == 1049:
            print(f"Database {DB_NAME!r} missing after create — check MySQL permissions.", file=sys.stderr)
        raise

    h = generate_password_hash(pw)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET password_hash = %s WHERE LOWER(email) = %s",
                (h, EMAIL),
            )
            if cur.rowcount == 0:
                cur.execute(
                    "INSERT INTO users (email, password_hash) VALUES (%s, %s)",
                    (EMAIL, h),
                )
                print("Created user and password for:", EMAIL)
            else:
                print("Updated password for:", EMAIL)
    finally:
        conn.close()

    print("OK — restart Flask (python app.py), then log in.")
    print("  Email:", EMAIL)
    print("  Password: (the one you set in BOOTSTRAP_PASSWORD)")


if __name__ == "__main__":
    main()

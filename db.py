"""MySQL connection for Dura Capital API (MySQL Workbench / local server)."""

from __future__ import annotations

import os

import pymysql
from pymysql.cursors import DictCursor


def get_connection():
    return pymysql.connect(
        host=os.environ.get("MYSQL_HOST", "127.0.0.1"),
        port=int(os.environ.get("MYSQL_PORT", "3306")),
        user=os.environ.get("MYSQL_USER", "root"),
        password=os.environ.get("MYSQL_PASSWORD", ""),
        database=os.environ.get("MYSQL_DATABASE", "dura_capital"),
        cursorclass=DictCursor,
        autocommit=True,
    )


def ping_db() -> bool:
    try:
        conn = get_connection()
        conn.ping(reconnect=False)
        conn.close()
        return True
    except Exception:
        return False

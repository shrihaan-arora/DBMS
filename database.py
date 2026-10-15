"""
SkyReserve — Database Connection & Management Module (MySQL)
Provides MySQL database connection, query execution wrapper, and initialization.
"""
from __future__ import annotations

import os
import re
import mysql.connector
from mysql.connector import Error as MySQLError
from dotenv import load_dotenv

# Load environment variables from .env file if present
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", 3306))
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME = os.environ.get("DB_NAME", "skyreserve")


class RowDict(dict):
    """
    Dictionary-like row object that allows case-insensitive key access
    and integer index access, matching sqlite3.Row functionality.
    """
    def __init__(self, data: dict, col_order: list[str] | None = None):
        super().__init__(data)
        self._lower_map = {k.lower(): k for k in data.keys()}
        self._col_order = col_order or list(data.keys())

    def __getitem__(self, key):
        if isinstance(key, int):
            col_name = self._col_order[key]
            return super().__getitem__(col_name)
        if key in self:
            return super().__getitem__(key)
        lower = str(key).lower()
        if lower in self._lower_map:
            return super().__getitem__(self._lower_map[lower])
        raise KeyError(key)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default


class MySQLCursorWrapper:
    """Wrapper around MySQL cursor providing dict-like row access and SQLite compatibility."""
    def __init__(self, raw_cursor):
        self._cursor = raw_cursor

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def description(self):
        return self._cursor.description

    def _convert_row(self, row: dict | tuple | None):
        if row is None:
            return None
        if isinstance(row, dict):
            col_order = [d[0] for d in self._cursor.description] if self._cursor.description else list(row.keys())
            return RowDict(row, col_order)
        return row

    def execute(self, query: str, params: tuple | list | dict | None = None):
        query = _translate_query(query)
        if params is not None:
            self._cursor.execute(query, params)
        else:
            self._cursor.execute(query)
        return self

    def fetchone(self):
        row = self._cursor.fetchone()
        return self._convert_row(row)

    def fetchall(self):
        rows = self._cursor.fetchall()
        return [self._convert_row(r) for r in rows]

    def fetchmany(self, size=None):
        rows = self._cursor.fetchmany(size)
        return [self._convert_row(r) for r in rows]

    def close(self):
        self._cursor.close()


def _translate_query(query: str) -> str:
    """
    Translates common SQLite query patterns to MySQL syntax:
      - '?' placeholders -> '%s'
      - String concatenation: a || ' ' || b -> CONCAT(a, ' ', b)
    """
    # Replace SQLite concatenation operator: col1 || ' ' || col2
    concat_pattern = re.compile(r"(\b[\w\.]+\b)\s*\|\|\s*' '\s*\|\|\s*(\b[\w\.]+\b)", re.IGNORECASE)
    query = concat_pattern.sub(r"CONCAT(\1, ' ', \2)", query)

    # Replace ? with %s for MySQL Connector parameter binding
    # (avoid replacing ? inside quotes)
    parts = []
    in_quote = False
    quote_char = ''
    i = 0
    while i < len(query):
        ch = query[i]
        if ch in ("'", '"'):
            if not in_quote:
                in_quote = True
                quote_char = ch
            elif quote_char == ch:
                in_quote = False
            parts.append(ch)
        elif ch == '?' and not in_quote:
            parts.append('%s')
        else:
            parts.append(ch)
        i += 1
    return "".join(parts)


class MySQLConnectionWrapper:
    """Wrapper around mysql.connector connection providing SQLite-like conveniences."""
    def __init__(self, raw_conn):
        self._conn = raw_conn
        self._open_cursors: list[MySQLCursorWrapper] = []

    def cursor(self, dictionary: bool = True):
        raw_cur = self._conn.cursor(dictionary=dictionary)
        wrapped = MySQLCursorWrapper(raw_cur)
        self._open_cursors.append(wrapped)
        return wrapped

    def execute(self, query: str, params: tuple | list | dict | None = None) -> MySQLCursorWrapper:
        cur = self.cursor(dictionary=True)
        cur.execute(query, params)
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        for c in self._open_cursors:
            try:
                c.close()
            except Exception:
                pass
        self._open_cursors.clear()
        try:
            self._conn.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()


import sqlite3

CURRENT_BACKEND = "mysql"


class SQLiteConnectionWrapper:
    """Fallback connection wrapper using local SQLite airline.db if MySQL is offline/unauthenticated."""
    def __init__(self, raw_conn: sqlite3.Connection):
        self._conn = raw_conn
        self.is_sqlite = True

    def cursor(self, dictionary: bool = True):
        return self

    def execute(self, query: str, params: tuple | list | dict | None = None):
        # Convert %s to ? for SQLite parameter binding
        query = query.replace("%s", "?")
        if params is not None:
            return self._conn.execute(query, params)
        return self._conn.execute(query)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()


def get_db():
    """
    Get a database connection. Attempts MySQL connection first using credentials
    from .env. If MySQL is unconfigured or unreachable, automatically falls back
    to the local SQLite airline.db instance so the website runs reliably.
    """
    global CURRENT_BACKEND
    try:
        raw_conn = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            autocommit=False,
            charset="utf8mb4",
            collation="utf8mb4_unicode_ci",
        )
        CURRENT_BACKEND = "mysql"
        return MySQLConnectionWrapper(raw_conn)
    except Exception as err:
        sqlite_path = os.path.join(BASE_DIR, "airline.db")
        if os.path.exists(sqlite_path):
            raw_sqlite = sqlite3.connect(sqlite_path)
            raw_sqlite.row_factory = sqlite3.Row
            raw_sqlite.execute("PRAGMA foreign_keys = ON")
            CURRENT_BACKEND = "sqlite"
            return SQLiteConnectionWrapper(raw_sqlite)
        raise MySQLError(
            f"Failed to connect to MySQL database '{DB_NAME}' at {DB_HOST}:{DB_PORT} as '{DB_USER}'. "
            f"Details: {err}. Please verify your .env file and ensure MySQL Server is running."
        ) from err


def get_raw_server_connection():
    """Connect to MySQL server directly without selecting a database (useful for CREATE DATABASE)."""
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        autocommit=True,
        charset="utf8mb4",
    )


def execute_sql_file_content(conn_wrapper: MySQLConnectionWrapper, sql_content: str):
    """
    Executes a script containing multiple SQL statements, handling DELIMITER
    blocks for triggers, views, and tables.
    """
    # Normalize delimiter blocks
    raw_conn = conn_wrapper._conn
    cursor = raw_conn.cursor()

    lines = sql_content.splitlines()
    current_delimiter = ";"
    statement_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("--") or stripped.startswith("#"):
            continue

        # Check for DELIMITER command
        if stripped.upper().startswith("DELIMITER"):
            parts = stripped.split()
            if len(parts) >= 2:
                current_delimiter = parts[1]
            continue

        statement_lines.append(line)
        joined = "\n".join(statement_lines).strip()

        if current_delimiter == ";" and joined.endswith(";"):
            stmt = joined[:-1].strip()
            if stmt:
                cursor.execute(stmt)
            statement_lines = []
        elif current_delimiter != ";" and joined.endswith(current_delimiter):
            stmt = joined[:-len(current_delimiter)].strip()
            if stmt:
                cursor.execute(stmt)
            statement_lines = []

    if statement_lines:
        remainder = "\n".join(statement_lines).strip()
        if remainder:
            cursor.execute(remainder)

    cursor.close()
    conn_wrapper.commit()


def init_db():
    """
    Initialize the database:
    1. Connects to server to ensure database DB_NAME exists.
    2. Runs schema.sql to create tables, views, and triggers.
    3. Runs seed_data.sql to populate initial sample records safely.
    """
    schema_path = os.path.join(BASE_DIR, "schema.sql")
    seed_path = os.path.join(BASE_DIR, "seed_data.sql")

    # Step 1: Ensure database exists
    server_conn = get_raw_server_connection()
    try:
        cur = server_conn.cursor()
        cur.execute(
            f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
            f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        cur.close()
    finally:
        server_conn.close()

    # Step 2: Run schema and seed scripts
    conn = get_db()
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            execute_sql_file_content(conn, f.read())
        with open(seed_path, "r", encoding="utf-8") as f:
            execute_sql_file_content(conn, f.read())
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    print(f"Connecting to MySQL ({DB_USER}@{DB_HOST}:{DB_PORT})...")
    init_db()
    print(f"Database '{DB_NAME}' initialized successfully with schema and seed data.")

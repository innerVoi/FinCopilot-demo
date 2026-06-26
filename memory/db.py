import os
import sqlite3
from pathlib import Path


DEFAULT_MEMORY_DB_PATH = "data/fincopilot_memory.db"


def get_memory_db_path() -> str:
    """
    Return the configured memory database path.
    """
    return os.getenv("FINCOPILOT_MEMORY_DB_PATH", DEFAULT_MEMORY_DB_PATH).strip() or DEFAULT_MEMORY_DB_PATH


def ensure_parent_dir(path: str) -> None:
    """
    Ensure the parent directory for a database path exists.
    """
    parent = Path(path).expanduser().parent
    if str(parent) and str(parent) != ".":
        parent.mkdir(parents=True, exist_ok=True)


def get_connection(db_path: str | None = None):
    """
    Return a SQLite connection with row_factory configured.
    """
    path = db_path or get_memory_db_path()
    ensure_parent_dir(path)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def execute_sql(sql: str, params: tuple | dict | None = None, db_path: str | None = None):
    """
    Execute a single SQL statement and commit it.
    """
    with get_connection(db_path) as connection:
        cursor = connection.execute(sql, params or ())
        connection.commit()
        return cursor


def query_all(sql: str, params: tuple | dict | None = None, db_path: str | None = None) -> list[dict]:
    """
    Query multiple rows and return list[dict].
    """
    with get_connection(db_path) as connection:
        rows = connection.execute(sql, params or ()).fetchall()
    return [dict(row) for row in rows]


def query_one(sql: str, params: tuple | dict | None = None, db_path: str | None = None) -> dict | None:
    """
    Query one row and return dict or None.
    """
    with get_connection(db_path) as connection:
        row = connection.execute(sql, params or ()).fetchone()
    return dict(row) if row else None


def initialize_memory_db(db_path: str | None = None) -> str:
    """
    Initialize all memory tables and return the database path.
    """
    path = db_path or get_memory_db_path()
    ensure_parent_dir(path)
    from memory.schema import create_all_tables

    create_all_tables(db_path=path)
    return path

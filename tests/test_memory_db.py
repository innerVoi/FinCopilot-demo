import sqlite3

from memory.db import (
    ensure_parent_dir,
    execute_sql,
    get_connection,
    get_memory_db_path,
    initialize_memory_db,
    query_all,
    query_one,
)


def test_get_memory_db_path_has_default(monkeypatch):
    monkeypatch.delenv("FINCOPILOT_MEMORY_DB_PATH", raising=False)
    assert get_memory_db_path() == "data/fincopilot_memory.db"


def test_get_memory_db_path_reads_env(monkeypatch):
    monkeypatch.setenv("FINCOPILOT_MEMORY_DB_PATH", "/tmp/test_memory.db")
    assert get_memory_db_path() == "/tmp/test_memory.db"


def test_ensure_parent_dir_creates_directory(tmp_path):
    db_path = tmp_path / "nested" / "memory.db"
    ensure_parent_dir(str(db_path))
    assert db_path.parent.exists()


def test_get_connection_creates_sqlite_connection(tmp_path):
    connection = get_connection(str(tmp_path / "memory.db"))
    assert isinstance(connection, sqlite3.Connection)
    connection.close()


def test_execute_and_query_helpers(tmp_path):
    db_path = str(tmp_path / "memory.db")
    execute_sql("CREATE TABLE test_items (id TEXT PRIMARY KEY, value TEXT)", db_path=db_path)
    execute_sql("INSERT INTO test_items (id, value) VALUES (?, ?)", ("a", "one"), db_path=db_path)
    assert query_one("SELECT * FROM test_items WHERE id = ?", ("a",), db_path=db_path)["value"] == "one"
    assert query_all("SELECT * FROM test_items", db_path=db_path) == [{"id": "a", "value": "one"}]


def test_initialize_memory_db_creates_file(tmp_path):
    db_path = tmp_path / "memory.db"
    initialize_memory_db(str(db_path))
    assert db_path.exists()

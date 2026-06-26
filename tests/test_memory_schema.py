from memory.db import query_all
from memory.schema import create_all_tables, get_schema_statements


def test_get_schema_statements_returns_list():
    statements = get_schema_statements()
    assert isinstance(statements, list)
    assert statements


def test_schema_contains_required_tables_and_fields():
    schema = "\n".join(get_schema_statements())
    for name in [
        "users",
        "workspaces",
        "business_memory",
        "user_feedback",
        "action_memory",
        "agent_turns",
        "agent_traces",
        "reports",
        "user_id",
        "workspace_id",
        "embedding_text",
        "retrieval_tags",
        "report_title",
        "report_summary",
        "report_markdown",
    ]:
        assert name in schema


def test_create_all_tables_creates_tables(tmp_path):
    db_path = str(tmp_path / "memory.db")
    create_all_tables(db_path=db_path)
    rows = query_all("SELECT name FROM sqlite_master WHERE type = 'table'", db_path=db_path)
    table_names = {row["name"] for row in rows}
    assert {"users", "workspaces", "business_memory", "reports"}.issubset(table_names)

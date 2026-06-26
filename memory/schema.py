from memory.db import execute_sql


def get_schema_statements() -> list[str]:
    """
    Return all CREATE TABLE statements for V2.3 memory.
    """
    return [
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            user_name TEXT,
            created_at TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS workspaces (
            workspace_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            workspace_name TEXT,
            business_type TEXT,
            created_at TEXT,
            PRIMARY KEY (user_id, workspace_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS business_memory (
            memory_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            workspace_id TEXT NOT NULL,
            memory_type TEXT NOT NULL,
            entity_name TEXT,
            fact_text TEXT NOT NULL,
            structured_value_json TEXT,
            source TEXT,
            confidence TEXT,
            created_at TEXT,
            updated_at TEXT,
            last_used_at TEXT,
            is_active INTEGER DEFAULT 1,
            embedding_text TEXT,
            retrieval_tags TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS user_feedback (
            feedback_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            workspace_id TEXT NOT NULL,
            turn_id TEXT,
            target_type TEXT,
            target_id TEXT,
            feedback_type TEXT,
            feedback_text TEXT,
            created_at TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS action_memory (
            action_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            workspace_id TEXT NOT NULL,
            title TEXT,
            description TEXT,
            priority TEXT,
            status TEXT,
            source TEXT,
            related_turn_id TEXT,
            created_at TEXT,
            updated_at TEXT,
            due_date TEXT,
            metadata_json TEXT,
            PRIMARY KEY (user_id, workspace_id, action_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS agent_turns (
            turn_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            workspace_id TEXT NOT NULL,
            user_query TEXT,
            manager_plan_json TEXT,
            tool_results_json TEXT,
            specialist_outputs_json TEXT,
            final_answer TEXT,
            mode TEXT,
            created_at TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS agent_traces (
            trace_id TEXT PRIMARY KEY,
            turn_id TEXT,
            user_id TEXT NOT NULL,
            workspace_id TEXT NOT NULL,
            trace_json TEXT,
            trace_markdown TEXT,
            created_at TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS reports (
            report_id TEXT PRIMARY KEY,
            turn_id TEXT,
            user_id TEXT NOT NULL,
            workspace_id TEXT NOT NULL,
            report_title TEXT,
            report_summary TEXT,
            report_markdown TEXT,
            created_at TEXT
        )
        """,
    ]


def create_all_tables(db_path: str | None = None) -> None:
    """
    Create all memory tables.
    """
    for statement in get_schema_statements():
        execute_sql(statement, db_path=db_path)

import uuid
from datetime import datetime, timezone

from memory.db import execute_sql, initialize_memory_db, query_all, query_one
from memory.turn_service import safe_json_dumps, safe_json_loads


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def generate_trace_id() -> str:
    return f"trace_{uuid.uuid4().hex}"


def _hydrate_trace(row: dict | None) -> dict | None:
    if not row:
        return None
    item = dict(row)
    item["trace"] = safe_json_loads(item.get("trace_json"))
    return item


def persist_agent_trace(
    user_id: str,
    workspace_id: str,
    turn_id: str,
    trace: dict | None = None,
    trace_markdown: str | None = None,
    db_path: str | None = None,
) -> dict:
    initialize_memory_db(db_path=db_path)
    trace_id = (trace or {}).get("trace_id") or generate_trace_id()
    execute_sql(
        """
        INSERT OR REPLACE INTO agent_traces (
            trace_id, turn_id, user_id, workspace_id, trace_json, trace_markdown, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (trace_id, turn_id, user_id, workspace_id, safe_json_dumps(trace or {}), trace_markdown or "", now_iso()),
        db_path=db_path,
    )
    return get_agent_trace(user_id, workspace_id, trace_id, db_path=db_path) or {}


def get_agent_trace(user_id: str, workspace_id: str, trace_id: str, db_path: str | None = None) -> dict | None:
    return _hydrate_trace(
        query_one(
            """
            SELECT *
            FROM agent_traces
            WHERE user_id = ? AND workspace_id = ? AND trace_id = ?
            """,
            (user_id, workspace_id, trace_id),
            db_path=db_path,
        )
    )


def list_agent_traces(user_id: str, workspace_id: str, limit: int = 50, db_path: str | None = None) -> list[dict]:
    initialize_memory_db(db_path=db_path)
    rows = query_all(
        """
        SELECT *
        FROM agent_traces
        WHERE user_id = ? AND workspace_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (user_id, workspace_id, max(1, int(limit))),
        db_path=db_path,
    )
    return [item for item in (_hydrate_trace(row) for row in rows) if item]

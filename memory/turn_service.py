import json
import uuid
from datetime import datetime, timezone

from memory.db import execute_sql, initialize_memory_db, query_all, query_one


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def generate_turn_id() -> str:
    return f"turn_{uuid.uuid4().hex}"


def safe_json_dumps(value) -> str:
    return json.dumps(value or {}, ensure_ascii=False, sort_keys=True, default=str)


def safe_json_loads(value: str | None):
    if not value:
        return {}
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return {}


def _hydrate_turn(row: dict | None) -> dict | None:
    if not row:
        return None
    item = dict(row)
    item["manager_plan"] = safe_json_loads(item.get("manager_plan_json"))
    item["tool_results"] = safe_json_loads(item.get("tool_results_json"))
    item["specialist_outputs"] = safe_json_loads(item.get("specialist_outputs_json"))
    return item


def persist_agent_turn(user_id: str, workspace_id: str, turn_result: dict, db_path: str | None = None) -> dict:
    initialize_memory_db(db_path=db_path)
    turn_result = turn_result or {}
    turn_id = turn_result.get("turn_id") or generate_turn_id()
    turn_result["turn_id"] = turn_id
    execute_sql(
        """
        INSERT OR REPLACE INTO agent_turns (
            turn_id, user_id, workspace_id, user_query, manager_plan_json,
            tool_results_json, specialist_outputs_json, final_answer, mode, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            turn_id,
            user_id,
            workspace_id,
            turn_result.get("user_query", ""),
            safe_json_dumps(turn_result.get("manager_plan", {})),
            safe_json_dumps(turn_result.get("tool_results", [])),
            safe_json_dumps(turn_result.get("specialist_outputs", {})),
            turn_result.get("assistant_reply", ""),
            turn_result.get("mode", "fallback"),
            now_iso(),
        ),
        db_path=db_path,
    )
    return get_agent_turn(user_id, workspace_id, turn_id, db_path=db_path) or {}


def get_agent_turn(user_id: str, workspace_id: str, turn_id: str, db_path: str | None = None) -> dict | None:
    return _hydrate_turn(
        query_one(
            """
            SELECT *
            FROM agent_turns
            WHERE user_id = ? AND workspace_id = ? AND turn_id = ?
            """,
            (user_id, workspace_id, turn_id),
            db_path=db_path,
        )
    )


def list_agent_turns(user_id: str, workspace_id: str, limit: int = 50, db_path: str | None = None) -> list[dict]:
    initialize_memory_db(db_path=db_path)
    rows = query_all(
        """
        SELECT *
        FROM agent_turns
        WHERE user_id = ? AND workspace_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (user_id, workspace_id, max(1, int(limit))),
        db_path=db_path,
    )
    return [item for item in (_hydrate_turn(row) for row in rows) if item]

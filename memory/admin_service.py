from memory.action_memory_service import (
    count_handled_actions,
    count_pending_actions,
    list_action_items,
)
from memory.db import execute_sql, initialize_memory_db, query_all, query_one
from memory.feedback_service import count_user_feedback, list_user_feedback
from memory.memory_service import count_business_memory, list_business_memory
from memory.report_service import list_reports
from memory.trace_service import list_agent_traces
from memory.turn_service import list_agent_turns


def _count_table(table_name: str, user_id: str, workspace_id: str, db_path: str | None = None) -> int:
    initialize_memory_db(db_path=db_path)
    row = query_one(
        f"""
        SELECT COUNT(*) AS item_count
        FROM {table_name}
        WHERE user_id = ? AND workspace_id = ?
        """,
        (user_id, workspace_id),
        db_path=db_path,
    )
    return int(row.get("item_count", 0)) if row else 0


def _delete_table(table_name: str, user_id: str, workspace_id: str, db_path: str | None = None) -> int:
    initialize_memory_db(db_path=db_path)
    cursor = execute_sql(
        f"""
        DELETE FROM {table_name}
        WHERE user_id = ? AND workspace_id = ?
        """,
        (user_id, workspace_id),
        db_path=db_path,
    )
    return max(0, cursor.rowcount)


def get_workspace_memory_stats(user_id: str, workspace_id: str, db_path: str | None = None) -> dict:
    return {
        "business_memory_count": count_business_memory(user_id, workspace_id, active_only=False, db_path=db_path),
        "active_business_memory_count": count_business_memory(user_id, workspace_id, active_only=True, db_path=db_path),
        "user_feedback_count": count_user_feedback(user_id, workspace_id, db_path=db_path),
        "action_count": _count_table("action_memory", user_id, workspace_id, db_path=db_path),
        "pending_action_count": count_pending_actions(user_id, workspace_id, db_path=db_path),
        "handled_action_count": count_handled_actions(user_id, workspace_id, db_path=db_path),
        "agent_turn_count": _count_table("agent_turns", user_id, workspace_id, db_path=db_path),
        "report_count": _count_table("reports", user_id, workspace_id, db_path=db_path),
        "trace_count": _count_table("agent_traces", user_id, workspace_id, db_path=db_path),
    }


def list_workspace_overview(user_id: str, workspace_id: str, db_path: str | None = None) -> dict:
    return {
        "identity": {"user_id": user_id, "workspace_id": workspace_id},
        "stats": get_workspace_memory_stats(user_id, workspace_id, db_path=db_path),
        "latest_business_memory": list_business_memory(user_id, workspace_id, active_only=False, limit=10, db_path=db_path),
        "latest_feedback": list_user_feedback(user_id, workspace_id, limit=10, db_path=db_path),
        "latest_actions": list_action_items(user_id, workspace_id, limit=10, db_path=db_path),
        "latest_turns": list_agent_turns(user_id, workspace_id, limit=10, db_path=db_path),
        "latest_reports": list_reports(user_id, workspace_id, limit=10, db_path=db_path),
    }


def clear_workspace_business_memory(user_id: str, workspace_id: str, db_path: str | None = None) -> int:
    return _delete_table("business_memory", user_id, workspace_id, db_path=db_path)


def clear_workspace_feedback(user_id: str, workspace_id: str, db_path: str | None = None) -> int:
    return _delete_table("user_feedback", user_id, workspace_id, db_path=db_path)


def clear_workspace_actions(user_id: str, workspace_id: str, db_path: str | None = None) -> int:
    return _delete_table("action_memory", user_id, workspace_id, db_path=db_path)


def clear_workspace_turns_traces_reports(user_id: str, workspace_id: str, db_path: str | None = None) -> dict:
    return {
        "agent_turns_deleted": _delete_table("agent_turns", user_id, workspace_id, db_path=db_path),
        "agent_traces_deleted": _delete_table("agent_traces", user_id, workspace_id, db_path=db_path),
        "reports_deleted": _delete_table("reports", user_id, workspace_id, db_path=db_path),
    }


def clear_current_workspace_all_data(user_id: str, workspace_id: str, db_path: str | None = None) -> dict:
    turn_related = clear_workspace_turns_traces_reports(user_id, workspace_id, db_path=db_path)
    return {
        "business_memory_deleted": clear_workspace_business_memory(user_id, workspace_id, db_path=db_path),
        "user_feedback_deleted": clear_workspace_feedback(user_id, workspace_id, db_path=db_path),
        "action_memory_deleted": clear_workspace_actions(user_id, workspace_id, db_path=db_path),
        **turn_related,
    }

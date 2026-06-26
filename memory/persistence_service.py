from memory.action_memory_service import persist_action_items
from memory.report_service import persist_report
from memory.trace_service import persist_agent_trace
from memory.turn_service import persist_agent_turn


def persist_full_agent_turn(
    user_id: str,
    workspace_id: str,
    turn_result: dict,
    db_path: str | None = None,
) -> dict:
    result = {"turn": None, "trace": None, "report": None, "actions": [], "errors": []}
    turn_result = turn_result or {}
    try:
        result["turn"] = persist_agent_turn(user_id, workspace_id, turn_result, db_path=db_path)
        turn_id = result["turn"]["turn_id"]
    except Exception as exc:
        result["errors"].append(f"persist_agent_turn failed: {exc}")
        turn_id = turn_result.get("turn_id")

    if turn_id:
        try:
            result["trace"] = persist_agent_trace(
                user_id=user_id,
                workspace_id=workspace_id,
                turn_id=turn_id,
                trace=turn_result.get("trace"),
                trace_markdown=turn_result.get("trace_markdown", ""),
                db_path=db_path,
            )
        except Exception as exc:
            result["errors"].append(f"persist_agent_trace failed: {exc}")
        try:
            result["report"] = persist_report(
                user_id=user_id,
                workspace_id=workspace_id,
                turn_id=turn_id,
                report_markdown=turn_result.get("report_markdown", ""),
                db_path=db_path,
            )
        except Exception as exc:
            result["errors"].append(f"persist_report failed: {exc}")
        try:
            result["actions"] = persist_action_items(
                user_id=user_id,
                workspace_id=workspace_id,
                action_items=turn_result.get("chat_action_items", []),
                related_turn_id=turn_id,
                db_path=db_path,
            )
        except Exception as exc:
            result["errors"].append(f"persist_action_items failed: {exc}")
    return result

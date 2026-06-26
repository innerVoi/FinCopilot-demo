from agent_api.action_sync import sync_turn_result_to_action_items
from agent_api.manager_agent import call_manager_agent_api
from agent_api.memory_orchestrator import prepare_memory_for_agent_turn
from agent_api.multi_agent_report import build_multi_agent_report
from agent_api.response_composer import compose_agent_trace_summary, compose_final_answer
from agent_api.safety_guardrails import get_agent_safety_note, validate_agent_output
from agent_api.specialist_agents import call_selected_specialist_agents
from agent_api.tool_router import build_tool_call_trace, execute_tool_calls
from agent_api.trace_builder import build_multi_agent_trace, trace_to_markdown
from memory.persistence_service import persist_full_agent_turn


def infer_overall_mode(manager_result: dict | None, specialist_outputs: dict | None) -> str:
    """
    Infer api_agent / fallback / mixed from all Agent modes.
    """
    modes = []
    if manager_result:
        modes.append(manager_result.get("mode", "fallback"))
    for payload in (specialist_outputs or {}).values():
        modes.append(payload.get("mode", "fallback"))
    if modes and all(mode == "api_agent" for mode in modes):
        return "api_agent"
    if not modes or all(mode == "fallback" for mode in modes):
        return "fallback"
    return "mixed"


def _dedupe(items):
    result = []
    seen = set()
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def collect_clarifying_questions(manager_plan: dict | None, specialist_outputs: dict | None) -> list[str]:
    """
    Collect and dedupe clarifying questions.
    """
    questions = list((manager_plan or {}).get("clarifying_questions", []))
    for payload in (specialist_outputs or {}).values():
        result = payload.get("result", {}) if isinstance(payload, dict) else {}
        questions.extend(result.get("questions", []))
    return _dedupe([str(item) for item in questions])


def collect_suggested_actions(specialist_outputs: dict | None) -> list[str]:
    """
    Collect and dedupe recommended actions.
    """
    actions = []
    for payload in (specialist_outputs or {}).values():
        result = payload.get("result", {}) if isinstance(payload, dict) else {}
        actions.extend(result.get("recommended_actions", []))
    return _dedupe([str(item) for item in actions])


def build_orchestrator_error_response(
    user_query: str,
    error: Exception | str,
    memory_context: dict | None = None,
    memory_trace: dict | None = None,
) -> dict:
    """
    Build a safe error response that can be returned to UI.
    """
    error_text = str(error)
    assistant_reply = (
        "The multi-agent call encountered an issue and switched to safe fallback."
        f"\n\n{get_agent_safety_note()}"
    )
    safety_result = validate_agent_output({"final_answer": assistant_reply})
    safe_reply = safety_result["sanitized_output"].get("final_answer", assistant_reply)
    result = {
        "mode": "fallback",
        "user_query": user_query or "",
        "assistant_reply": safe_reply,
        "manager_result": {},
        "manager_plan": {},
        "tool_results": [],
        "tool_trace": {},
        "specialist_outputs": {},
        "agent_trace_summary": {},
        "safety_result": safety_result,
        "suggested_actions": [],
        "clarifying_questions": [],
        "chat_action_items": [],
        "report_markdown": "",
        "trace_markdown": "",
        "memory_context": memory_context or {"memory_count": 0, "used_memory_ids": [], "memory_notes": "No historical business memory yet. This analysis is mainly based on the uploaded data."},
        "memory_trace": memory_trace or {},
        "memory_augmented": bool((memory_context or {}).get("memory_count")),
        "used_memory_ids": list((memory_context or {}).get("used_memory_ids") or []),
        "errors": [error_text],
    }
    result["trace"] = build_multi_agent_trace(result)
    result["chat_action_items"] = sync_turn_result_to_action_items(result)
    result["report_markdown"] = build_multi_agent_report(result)
    result["trace_markdown"] = trace_to_markdown(result["trace"])
    return result


def run_multi_agent_turn(
    user_query: str,
    agent_context_summary: dict | None = None,
    chat_state: dict | None = None,
    user_id: str | None = None,
    workspace_id: str | None = None,
    memory_db_path: str | None = None,
) -> dict:
    """
    Unified multi-agent chat entry point.
    """
    errors = []
    memory_payload = {
        "agent_context_summary": agent_context_summary or {},
        "memory_context": {"memory_count": 0, "used_memory_ids": [], "memory_notes": "No historical business memory yet. This analysis is mainly based on the uploaded data."},
        "memory_trace": {},
        "task_type": "general_finance_summary",
    }
    try:
        memory_payload = prepare_memory_for_agent_turn(
            user_id=user_id,
            workspace_id=workspace_id,
            user_query=user_query,
            agent_context_summary=agent_context_summary,
            db_path=memory_db_path,
        )
        augmented_context_summary = memory_payload["agent_context_summary"]
        memory_context = memory_payload["memory_context"]
        memory_trace = memory_payload["memory_trace"]
        manager_result = call_manager_agent_api(
            user_query=user_query,
            context_summary=augmented_context_summary,
        )
        errors.extend(manager_result.get("errors", []))
        manager_plan = manager_result.get("manager_plan", {})
        tool_results = execute_tool_calls(
            manager_plan.get("tool_plan", []),
            augmented_context_summary or {},
        )
        tool_trace = build_tool_call_trace(tool_results)
        errors.extend(
            result.get("error")
            for result in tool_results
            if result.get("status") == "failed" and result.get("error")
        )
        specialist_outputs = call_selected_specialist_agents(
            user_query=user_query,
            manager_plan=manager_plan,
            context_summary=augmented_context_summary,
            tool_results=tool_results,
        )
        for payload in specialist_outputs.values():
            errors.extend(payload.get("errors", []))
        assistant_reply = compose_final_answer(
            user_query=user_query,
            manager_plan=manager_plan,
            specialist_outputs=specialist_outputs,
            tool_results=tool_results,
            memory_context=memory_context,
        )
        safety_result = validate_agent_output({"final_answer": assistant_reply})
        safe_reply = safety_result["sanitized_output"].get("final_answer", assistant_reply)
        errors.extend(safety_result.get("risks", []))
        agent_trace_summary = compose_agent_trace_summary(
            manager_result=manager_result,
            specialist_outputs=specialist_outputs,
            tool_results=tool_results,
        )
        mode = infer_overall_mode(manager_result, specialist_outputs)
        turn_result = {
            "mode": mode,
            "user_query": user_query or "",
            "assistant_reply": safe_reply,
            "manager_result": manager_result,
            "manager_plan": manager_plan,
            "tool_results": tool_results,
            "tool_trace": tool_trace,
            "specialist_outputs": specialist_outputs,
            "agent_trace_summary": agent_trace_summary,
            "safety_result": safety_result,
            "suggested_actions": collect_suggested_actions(specialist_outputs),
            "clarifying_questions": collect_clarifying_questions(manager_plan, specialist_outputs),
            "report_markdown": "",
            "trace_markdown": "",
            "memory_context": memory_context,
            "memory_trace": memory_trace,
            "memory_augmented": bool(memory_context.get("memory_count")),
            "used_memory_ids": list(memory_context.get("used_memory_ids") or []),
            "chat_action_items": [],
            "errors": [item for item in errors if item],
        }
        turn_result["trace"] = build_multi_agent_trace(turn_result)
        turn_result["chat_action_items"] = sync_turn_result_to_action_items(turn_result)
        turn_result["report_markdown"] = build_multi_agent_report(turn_result)
        turn_result["trace_markdown"] = trace_to_markdown(turn_result["trace"])
        persistence_result = persist_full_agent_turn(
            user_id=user_id or "demo_user",
            workspace_id=workspace_id or "demo_workspace",
            turn_result=turn_result,
            db_path=memory_db_path,
        )
        turn_result["persistence_result"] = persistence_result
        turn_result["persisted"] = not persistence_result.get("errors")
        turn_result["persistence_errors"] = persistence_result.get("errors", [])
        if persistence_result.get("turn", {}).get("turn_id"):
            turn_result["turn_id"] = persistence_result["turn"]["turn_id"]
        return turn_result
    except Exception as error:
        return build_orchestrator_error_response(
            user_query,
            error,
            memory_context=memory_payload.get("memory_context"),
            memory_trace=memory_payload.get("memory_trace"),
        )

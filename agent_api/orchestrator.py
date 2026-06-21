from agent_api.action_sync import sync_turn_result_to_action_items
from agent_api.manager_agent import call_manager_agent_api
from agent_api.multi_agent_report import build_multi_agent_report
from agent_api.response_composer import compose_agent_trace_summary, compose_final_answer
from agent_api.safety_guardrails import get_agent_safety_note, validate_agent_output
from agent_api.specialist_agents import call_selected_specialist_agents
from agent_api.tool_router import build_tool_call_trace, execute_tool_calls
from agent_api.trace_builder import build_multi_agent_trace, trace_to_markdown


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


def build_orchestrator_error_response(user_query: str, error: Exception | str) -> dict:
    """
    Build a safe error response that can be returned to UI.
    """
    error_text = str(error)
    assistant_reply = (
        "当前多 Agent 调用出现问题，已切换为安全 fallback。"
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
) -> dict:
    """
    Unified multi-agent chat entry point.
    """
    errors = []
    try:
        manager_result = call_manager_agent_api(
            user_query=user_query,
            context_summary=agent_context_summary,
        )
        errors.extend(manager_result.get("errors", []))
        manager_plan = manager_result.get("manager_plan", {})
        tool_results = execute_tool_calls(
            manager_plan.get("tool_plan", []),
            agent_context_summary or {},
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
            context_summary=agent_context_summary,
            tool_results=tool_results,
        )
        for payload in specialist_outputs.values():
            errors.extend(payload.get("errors", []))
        assistant_reply = compose_final_answer(
            user_query=user_query,
            manager_plan=manager_plan,
            specialist_outputs=specialist_outputs,
            tool_results=tool_results,
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
            "chat_action_items": [],
            "errors": [item for item in errors if item],
        }
        turn_result["trace"] = build_multi_agent_trace(turn_result)
        turn_result["chat_action_items"] = sync_turn_result_to_action_items(turn_result)
        turn_result["report_markdown"] = build_multi_agent_report(turn_result)
        turn_result["trace_markdown"] = trace_to_markdown(turn_result["trace"])
        return turn_result
    except Exception as error:
        return build_orchestrator_error_response(user_query, error)

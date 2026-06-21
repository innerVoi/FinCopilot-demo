from uuid import uuid4


def build_trace_id(prefix: str = "trace") -> str:
    """
    Build a short trace id.
    """
    return f"{prefix}_{uuid4().hex[:10]}"


def build_multi_agent_trace(turn_result: dict) -> dict:
    """
    Build a unified trace from a multi-agent turn result.
    """
    turn_result = turn_result or {}
    manager_result = turn_result.get("manager_result", {}) or {}
    manager_plan = turn_result.get("manager_plan", {}) or manager_result.get("manager_plan", {}) or {}
    tool_trace = turn_result.get("tool_trace", {}) or {}
    specialist_outputs = turn_result.get("specialist_outputs", {}) or {}
    safety_result = turn_result.get("safety_result", {}) or {}
    specialist_errors = []
    api_agent_count = 0
    fallback_count = 0
    for payload in specialist_outputs.values():
        if payload.get("mode") == "api_agent":
            api_agent_count += 1
        else:
            fallback_count += 1
        specialist_errors.extend(payload.get("errors", []))
    return {
        "trace_id": build_trace_id(),
        "user_query": turn_result.get("user_query", ""),
        "mode": turn_result.get("mode", "fallback"),
        "manager": {
            "mode": manager_result.get("mode", "fallback"),
            "intent": manager_plan.get("intent", "unknown"),
            "selected_agents": manager_plan.get("selected_agents", []),
            "tool_plan": manager_plan.get("tool_plan", []),
        },
        "tools": {
            "total": tool_trace.get("total", 0),
            "success": tool_trace.get("success", 0),
            "failed": tool_trace.get("failed", 0),
            "tools_called": tool_trace.get("tools_called", []),
        },
        "specialists": {
            "agents_called": list(specialist_outputs.keys()),
            "api_agent_count": api_agent_count,
            "fallback_count": fallback_count,
            "errors": specialist_errors,
        },
        "safety": {
            "safe": safety_result.get("safe", True),
            "risks": safety_result.get("risks", []),
        },
    }


def trace_to_markdown(trace: dict | None) -> str:
    """
    Convert a trace dict to Markdown.
    """
    trace = trace or {}
    manager = trace.get("manager", {})
    tools = trace.get("tools", {})
    specialists = trace.get("specialists", {})
    safety = trace.get("safety", {})
    return (
        f"# Multi-Agent Trace\n\n"
        f"- Trace ID: {trace.get('trace_id', '')}\n"
        f"- Mode: {trace.get('mode', 'fallback')}\n"
        f"- User Query: {trace.get('user_query', '')}\n\n"
        "## Manager\n"
        f"- Mode: {manager.get('mode', 'fallback')}\n"
        f"- Intent: {manager.get('intent', 'unknown')}\n"
        f"- Selected Agents: {', '.join(manager.get('selected_agents', []))}\n"
        f"- Tool Plan: {', '.join(manager.get('tool_plan', []))}\n\n"
        "## Tools\n"
        f"- Total: {tools.get('total', 0)}\n"
        f"- Success: {tools.get('success', 0)}\n"
        f"- Failed: {tools.get('failed', 0)}\n"
        f"- Tools Called: {', '.join(tools.get('tools_called', []))}\n\n"
        "## Specialists\n"
        f"- Agents Called: {', '.join(specialists.get('agents_called', []))}\n"
        f"- API Agent Count: {specialists.get('api_agent_count', 0)}\n"
        f"- Fallback Count: {specialists.get('fallback_count', 0)}\n"
        f"- Errors: {specialists.get('errors', [])}\n\n"
        "## Safety\n"
        f"- Safe: {safety.get('safe', True)}\n"
        f"- Risks: {safety.get('risks', [])}\n"
    )

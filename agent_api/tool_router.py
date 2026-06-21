from agent_api.tool_schemas import validate_tool_name


TOOL_TO_CONTEXT_KEY = {
    "get_business_snapshot": "business_snapshot",
    "get_budget_summary": "budget_summary",
    "get_invoice_summary": "invoice_summary",
    "get_cashflow_summary": "cashflow_summary",
    "get_anomaly_summary": "anomaly_summary",
    "get_goal_summary": "goal_summary",
    "get_action_summary": "action_summary",
    "get_progress_summary": "progress_summary",
    "get_workflow_report_summary": "report_summary",
    "get_full_context_summary": "__full__",
}


def normalize_tool_call(tool_call) -> dict:
    """
    Normalize a string or dict into a tool call dict.
    """
    if isinstance(tool_call, str):
        return {"tool_name": tool_call, "arguments": {}}
    if isinstance(tool_call, dict):
        return {
            "tool_name": tool_call.get("tool_name") or tool_call.get("name") or "",
            "arguments": tool_call.get("arguments") or {},
        }
    return {"tool_name": "", "arguments": {}}


def route_tool_call(tool_name: str, context_summary: dict, arguments: dict | None = None) -> dict:
    """
    Route a tool call to the corresponding context summary key.
    """
    if not validate_tool_name(tool_name):
        return {
            "tool_name": tool_name,
            "status": "failed",
            "result": None,
            "error": "Unknown tool name",
        }
    context_summary = context_summary or {}
    context_key = TOOL_TO_CONTEXT_KEY.get(tool_name)
    if context_key == "__full__":
        return {
            "tool_name": tool_name,
            "status": "success",
            "result": context_summary,
            "error": None,
        }
    if context_key not in context_summary:
        return {
            "tool_name": tool_name,
            "status": "failed",
            "result": None,
            "error": "Context key not available",
        }
    return {
        "tool_name": tool_name,
        "status": "success",
        "result": context_summary.get(context_key),
        "error": None,
    }


def execute_tool_calls(tool_calls: list, context_summary: dict) -> list[dict]:
    """
    Execute multiple local read-only tool calls.
    """
    results = []
    for raw_call in tool_calls or []:
        tool_call = normalize_tool_call(raw_call)
        results.append(
            route_tool_call(
                tool_call["tool_name"],
                context_summary,
                arguments=tool_call.get("arguments"),
            )
        )
    return results


def build_tool_call_trace(tool_results: list[dict]) -> dict:
    """
    Build a compact tool call trace.
    """
    tool_results = tool_results or []
    success_count = sum(1 for result in tool_results if result.get("status") == "success")
    failed_count = sum(1 for result in tool_results if result.get("status") == "failed")
    return {
        "total": len(tool_results),
        "success": success_count,
        "failed": failed_count,
        "tools_called": [result.get("tool_name") for result in tool_results],
    }

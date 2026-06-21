from agent_api.tool_router import (
    build_tool_call_trace,
    execute_tool_calls,
    normalize_tool_call,
    route_tool_call,
)


def test_normalize_tool_call_handles_string():
    assert normalize_tool_call("get_cashflow_summary") == {
        "tool_name": "get_cashflow_summary",
        "arguments": {},
    }


def test_normalize_tool_call_handles_dict():
    assert normalize_tool_call({"name": "get_budget_summary", "arguments": {"x": 1}}) == {
        "tool_name": "get_budget_summary",
        "arguments": {"x": 1},
    }


def test_route_tool_call_returns_success_for_cashflow_summary():
    context_summary = {"cashflow_summary": {"risk_level": "medium"}}
    result = route_tool_call("get_cashflow_summary", context_summary)
    assert result == {
        "tool_name": "get_cashflow_summary",
        "status": "success",
        "result": {"risk_level": "medium"},
        "error": None,
    }


def test_route_tool_call_unknown_tool_returns_failed():
    result = route_tool_call("missing_tool", {})
    assert result["status"] == "failed"
    assert result["error"] == "Unknown tool name"


def test_route_tool_call_missing_context_key_returns_failed():
    result = route_tool_call("get_cashflow_summary", {})
    assert result["status"] == "failed"
    assert result["error"] == "Context key not available"


def test_execute_tool_calls_returns_list():
    results = execute_tool_calls(
        ["get_cashflow_summary"],
        {"cashflow_summary": {"risk_level": "low"}},
    )
    assert isinstance(results, list)
    assert results[0]["status"] == "success"


def test_build_tool_call_trace_returns_summary():
    results = [
        {"tool_name": "get_cashflow_summary", "status": "success"},
        {"tool_name": "missing_tool", "status": "failed"},
    ]
    trace = build_tool_call_trace(results)
    assert trace == {
        "total": 2,
        "success": 1,
        "failed": 1,
        "tools_called": ["get_cashflow_summary", "missing_tool"],
    }

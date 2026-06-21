from agent_api.trace_builder import build_multi_agent_trace, build_trace_id, trace_to_markdown


def test_build_trace_id_returns_string():
    assert build_trace_id().startswith("trace_")


def test_build_multi_agent_trace_handles_full_result():
    trace = build_multi_agent_trace(
        {
            "user_query": "q",
            "mode": "fallback",
            "manager_result": {"mode": "fallback"},
            "manager_plan": {
                "intent": "cashflow_check",
                "selected_agents": ["cashflow_agent"],
                "tool_plan": ["get_cashflow_summary"],
            },
            "tool_trace": {"total": 1, "success": 1, "failed": 0, "tools_called": ["get_cashflow_summary"]},
            "specialist_outputs": {"cashflow_agent": {"mode": "fallback", "errors": []}},
            "safety_result": {"safe": True, "risks": []},
        }
    )
    assert trace["manager"]["intent"] == "cashflow_check"
    assert trace["tools"]["success"] == 1


def test_build_multi_agent_trace_handles_empty_dict():
    trace = build_multi_agent_trace({})
    assert trace["mode"] == "fallback"
    assert "trace_id" in trace


def test_trace_to_markdown_contains_sections():
    markdown = trace_to_markdown(build_multi_agent_trace({}))
    assert "Manager" in markdown
    assert "Tools" in markdown
    assert "Specialists" in markdown
    assert "Safety" in markdown

import pytest

from agent.tool_registry import (
    get_tool_registry,
    get_tool_spec,
    list_available_tools,
    validate_tool_plan,
)


def test_tool_registry_contains_core_tools():
    registry = get_tool_registry()

    assert "analyze_budget" in registry
    assert "analyze_cashflow" in registry
    assert "detect_lof_anomalies" in registry


def test_each_tool_spec_has_required_metadata():
    registry = get_tool_registry()

    for spec in registry.values():
        assert spec["tool_name"]
        assert spec["description"]
        assert isinstance(spec["input_keys"], list)
        assert spec["output_key"]


def test_list_available_tools_returns_specs():
    tools = list_available_tools()

    assert isinstance(tools, list)
    assert any(tool["tool_name"] == "analyze_budget" for tool in tools)


def test_get_tool_spec_returns_one_tool():
    spec = get_tool_spec("analyze_budget")

    assert spec["tool_name"] == "analyze_budget"
    assert spec["output_key"] == "budget_result"


def test_get_tool_spec_rejects_unknown_tool():
    with pytest.raises(ValueError):
        get_tool_spec("missing_tool")


def test_validate_tool_plan_reports_missing_tools():
    result = validate_tool_plan(["analyze_budget", "missing_tool"])

    assert result["valid"] is False
    assert result["available_tools"] == ["analyze_budget"]
    assert result["missing_tools"] == ["missing_tool"]

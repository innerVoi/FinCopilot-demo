from agent.workflow_report import (
    build_action_items_section,
    build_agent_workflow_report,
    build_tool_execution_section,
    filter_non_empty_context,
    markdown_dict,
    markdown_list,
    safe_format_value,
)


def test_safe_format_value_handles_common_values():
    assert safe_format_value(None) == "无"
    assert "a" in safe_format_value({"a": 1})
    assert "x" in safe_format_value(["x", "y"])


def test_filter_non_empty_context_filters_empty_values():
    result = filter_non_empty_context(
        {"a": None, "b": "", "c": 0, "d": 10, "e": "note"}
    )

    assert result == {"d": 10, "e": "note"}


def test_markdown_helpers_return_markdown_strings():
    assert markdown_list(["a"]).startswith("- ")
    assert "**a**" in markdown_dict({"a": 1})


def test_build_action_items_section_handles_empty_items():
    assert "无行动项" in build_action_items_section([])


def test_build_tool_execution_section_handles_empty_execution():
    assert "无工具执行记录" in build_tool_execution_section({})


def test_build_agent_workflow_report_returns_markdown_with_safety_boundary():
    workspace = {
        "task": {
            "task_name": "检查未来 30 天现金流是否安全",
            "task_goal": "判断现金流风险。",
            "workflow_steps": ["检查数据", "生成报告"],
        },
        "data_check": {"status": "partial"},
        "task_plan": {"plan_status": "needs_clarification", "tool_steps": []},
        "ranked_action_items": [],
        "progress_summary": {},
    }

    report = build_agent_workflow_report(workspace)

    assert isinstance(report, str)
    assert "Agent 工作流报告" in report
    assert "安全边界" in report or "免责声明" in report
    assert "检查未来 30 天现金流是否安全" in report


def test_build_agent_workflow_report_handles_empty_workspace():
    report = build_agent_workflow_report({})

    assert "Agent 工作流报告" in report
    assert "安全边界" in report

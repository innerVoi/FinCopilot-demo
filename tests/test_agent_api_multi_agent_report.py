from agent_api.multi_agent_report import (
    build_manager_section,
    build_multi_agent_report,
    build_specialist_outputs_section,
    build_tool_results_section,
    markdown_bullets,
    safe_markdown_value,
)


def test_safe_markdown_value_handles_none_dict_list():
    assert safe_markdown_value(None) == "无"
    assert "```json" in safe_markdown_value({"a": 1})
    assert "```json" in safe_markdown_value(["a"])


def test_markdown_bullets_handles_empty_list():
    assert markdown_bullets([]) == "- 无"


def test_build_manager_section_handles_empty_plan():
    section = build_manager_section(None)
    assert "Manager Agent 任务理解" in section
    assert "unknown" in section


def test_build_tool_results_section_handles_empty_results():
    section = build_tool_results_section(None)
    assert "工具摘要调用" in section
    assert "无工具摘要调用" in section


def test_build_specialist_outputs_section_handles_empty_outputs():
    section = build_specialist_outputs_section(None)
    assert "Specialist Agents 输出" in section
    assert "无 Specialist Agent 输出" in section


def test_build_multi_agent_report_returns_markdown():
    markdown = build_multi_agent_report(
        {
            "user_query": "未来 30 天现金流安全吗？",
            "manager_plan": {"intent": "cashflow_check"},
            "assistant_reply": "需要关注现金流。",
            "suggested_actions": ["确认余额"],
            "clarifying_questions": ["当前真实余额是多少？"],
            "trace": {"mode": "fallback"},
        }
    )
    assert "# FinCopilot Multi-Agent 对话报告" in markdown
    assert "安全边界与免责声明" in markdown
    assert "不构成投资、税务、法律、债务处置或专业财务建议" in markdown


def test_build_multi_agent_report_handles_empty_turn_result():
    markdown = build_multi_agent_report(None)
    assert "FinCopilot Multi-Agent 对话报告" in markdown
    assert "安全边界与免责声明" in markdown

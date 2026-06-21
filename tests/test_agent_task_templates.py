import pytest

from agent.task_templates import (
    get_supported_agent_tasks,
    get_task_options_for_ui,
    get_task_template,
)


def test_get_supported_agent_tasks_returns_three_tasks():
    tasks = get_supported_agent_tasks()

    assert isinstance(tasks, list)
    assert len(tasks) >= 3
    for task in tasks:
        assert {"task_id", "task_name", "task_goal", "workflow_steps", "required_tools"}.issubset(task.keys())
        assert task["workflow_steps"]
        assert task["required_tools"]


def test_get_task_options_for_ui_returns_mapping():
    options = get_task_options_for_ui()

    assert isinstance(options, dict)
    assert "检查未来 30 天现金流是否安全" in options
    assert options["检查未来 30 天现金流是否安全"] == "cashflow_safety_check"


def test_get_task_template_returns_task_by_id():
    task = get_task_template("suspicious_expense_review")

    assert task["task_id"] == "suspicious_expense_review"
    assert task["task_name"] == "处理本月最可疑的异常支出"


def test_get_task_template_invalid_id_is_clear():
    with pytest.raises(ValueError, match="Unsupported agent task_id"):
        get_task_template("not_a_task")

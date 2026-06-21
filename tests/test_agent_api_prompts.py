from agent_api.prompts import (
    build_manager_prompt_with_context,
    build_specialist_prompt_with_context,
    get_agent_prompt,
    get_all_agent_prompts,
)


def test_get_agent_prompt_returns_manager_prompt():
    prompt = get_agent_prompt("manager_agent")
    assert "Manager Agent" in prompt
    assert "不能编造财务数字" in prompt


def test_get_agent_prompt_returns_cashflow_prompt():
    prompt = get_agent_prompt("cashflow_agent")
    assert "Cashflow Agent" in prompt


def test_get_all_agent_prompts_returns_dict():
    prompts = get_all_agent_prompts()
    assert isinstance(prompts, dict)
    assert "safety_agent" in prompts


def test_build_manager_prompt_with_context_returns_string():
    prompt = build_manager_prompt_with_context("现金流安全吗", {"risk": "medium"})
    assert isinstance(prompt, str)
    assert "摘要上下文" in prompt


def test_build_specialist_prompt_with_context_returns_string():
    prompt = build_specialist_prompt_with_context(
        "anomaly_agent",
        "哪些支出可疑",
        {"intent": "expense_anomaly_review"},
        {"count": 2},
    )
    assert isinstance(prompt, str)
    assert "Manager Plan" in prompt


def test_prompts_include_safety_boundary():
    prompt = get_agent_prompt("planning_agent")
    assert "不能提供投资、税务、法律、债务处置或专业财务建议" in prompt

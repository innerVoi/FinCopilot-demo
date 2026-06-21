from agent.progress_summary import (
    action_items_to_status_markdown,
    build_agent_progress_conclusion,
    build_progress_summary_text,
)
from agent.progress_tracker import summarize_progress


def make_actions():
    return [
        {
            "action_id": "A001",
            "title": "优先核查未来 30 天现金流缺口",
            "priority": "high",
            "source": "cashflow",
            "status": "pending",
            "reason": "现金流风险较高。",
            "suggested_deadline": "今天",
            "recommended_steps": ["确认当前余额。"],
        },
        {
            "action_id": "A002",
            "title": "处理逾期发票",
            "priority": "high",
            "source": "invoice",
            "status": "done",
            "reason": "存在逾期发票。",
            "suggested_deadline": "今天",
            "recommended_steps": ["查看发票列表。"],
        },
    ]


def test_build_progress_summary_text_returns_text_with_counts():
    actions = make_actions()
    text = build_progress_summary_text(actions, summarize_progress(actions))

    assert isinstance(text, str)
    assert "2 个行动项" in text


def test_build_agent_progress_conclusion_returns_for_three_tasks():
    actions = make_actions()

    assert build_agent_progress_conclusion("cashflow_safety_check", actions)
    assert build_agent_progress_conclusion("suspicious_expense_review", actions)
    assert build_agent_progress_conclusion("goal_action_plan", actions)


def test_action_items_to_status_markdown_contains_status_and_title():
    markdown = action_items_to_status_markdown(make_actions())

    assert "# FinCopilot 行动项进展" in markdown
    assert "[high][pending]" in markdown
    assert "优先核查未来 30 天现金流缺口" in markdown

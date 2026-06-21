import inspect

import ui.copilot_main as copilot_main
from ui.copilot_main import RECOMMENDED_QUESTIONS, render_copilot_main


def test_recommended_questions_not_empty():
    assert RECOMMENDED_QUESTIONS


def test_recommended_questions_include_cashflow_anomaly_and_action_list():
    joined = "\n".join(RECOMMENDED_QUESTIONS)
    assert "现金流" in joined
    assert "支出" in joined or "可疑" in joined
    assert "行动清单" in joined


def test_render_copilot_main_accepts_latest_agent_turn():
    signature = inspect.signature(render_copilot_main)
    assert "latest_agent_turn" in signature.parameters


def test_copilot_main_imports_answer_presentation_helpers():
    assert copilot_main.build_answer_presentation
    assert copilot_main.render_answer_presentation


def test_copilot_main_imports_detail_preview_helpers():
    assert copilot_main.build_detail_preview
    assert copilot_main.render_inline_detail_preview


def test_copilot_main_imports_onboarding_and_task_helpers():
    assert copilot_main.render_onboarding_panel
    assert copilot_main.build_recommended_tasks
    assert copilot_main.render_recommended_task_cards


def test_copilot_main_does_not_restore_agent_api_switch():
    source = inspect.getsource(copilot_main)
    assert "ENABLE_AGENT_API" not in source
    assert "checkbox" not in source
    assert "toggle" not in source

from agent_api.orchestrator import (
    build_orchestrator_error_response,
    collect_clarifying_questions,
    collect_suggested_actions,
    infer_overall_mode,
    run_multi_agent_turn,
)


def test_infer_overall_mode_all_fallback():
    assert infer_overall_mode({"mode": "fallback"}, {"a": {"mode": "fallback"}}) == "fallback"


def test_infer_overall_mode_mixed():
    assert infer_overall_mode({"mode": "api_agent"}, {"a": {"mode": "fallback"}}) == "mixed"


def test_collect_clarifying_questions_dedupes():
    questions = collect_clarifying_questions(
        {"clarifying_questions": ["q1"]},
        {"a": {"result": {"questions": ["q1", "q2"]}}},
    )
    assert questions == ["q1", "q2"]


def test_collect_suggested_actions_dedupes():
    actions = collect_suggested_actions(
        {"a": {"result": {"recommended_actions": ["a1", "a1", "a2"]}}}
    )
    assert actions == ["a1", "a2"]


def test_build_orchestrator_error_response_returns_safe_structure():
    response = build_orchestrator_error_response("hello", "boom")
    assert response["mode"] == "fallback"
    assert response["assistant_reply"]
    assert response["errors"] == ["boom"]
    assert "trace" in response
    assert "chat_action_items" in response
    assert "report_markdown" in response
    assert "trace_markdown" in response


def test_run_multi_agent_turn_fallback_returns_complete_result(monkeypatch):
    monkeypatch.setenv("ENABLE_AGENT_API", "false")
    result = run_multi_agent_turn(
        "未来 30 天现金流安全吗？",
        agent_context_summary={"cashflow_summary": {"risk_level": "medium"}},
    )
    assert result["mode"] == "fallback"
    assert result["assistant_reply"]
    assert result["manager_result"]
    assert result["specialist_outputs"]
    assert result["trace"]
    assert isinstance(result["chat_action_items"], list)
    assert result["report_markdown"]
    assert result["trace_markdown"]
    assert isinstance(result["errors"], list)

from agent_api.fallback import (
    build_fallback_specialist_result,
    build_fallback_agent_response,
    build_fallback_manager_plan,
    infer_intent_from_query,
)


def test_infer_intent_cashflow():
    assert infer_intent_from_query("未来 30 天现金流安全吗？") == "cashflow_check"


def test_infer_intent_anomaly():
    assert infer_intent_from_query("这个月哪些支出最可疑？") == "expense_anomaly_review"


def test_infer_intent_promotion_or_budget():
    assert infer_intent_from_query("我能不能花 5000 做促销？") == "promotion_or_purchase_planning"


def test_build_fallback_manager_plan_returns_plan():
    plan = build_fallback_manager_plan("现金流安全吗")
    assert plan["intent"] == "cashflow_check"
    assert plan["selected_agents"]


def test_build_fallback_agent_response_returns_final_schema():
    response = build_fallback_agent_response("现金流安全吗")
    assert response["mode"] == "fallback"
    assert response["manager_plan"]["intent"] == "cashflow_check"
    assert "final_answer" in response


def test_fallback_response_contains_safety_note():
    response = build_fallback_agent_response("哪些支出可疑")
    assert "financial organization" in response["safety_note"]


def test_empty_query_does_not_crash():
    response = build_fallback_agent_response(None)
    assert response["manager_plan"]["intent"] == "unknown"


def test_fallback_specialist_result_is_complete():
    result = build_fallback_specialist_result("现金流安全吗？", "cashflow_agent")
    assert result["agent_name"] == "cashflow_agent"
    assert result["findings"]
    assert result["risks"]
    assert result["recommended_actions"]
    assert result["questions"]

from agent_api.schemas import (
    ensure_list,
    get_default_agent_response,
    get_default_manager_plan,
    get_default_specialist_result,
    merge_specialist_outputs,
    normalize_confidence,
    normalize_intent,
    validate_manager_plan,
    validate_specialist_result,
)


def test_default_manager_plan_returns_dict():
    assert isinstance(get_default_manager_plan("hello"), dict)


def test_default_specialist_result_returns_dict():
    assert isinstance(get_default_specialist_result("cashflow_agent"), dict)


def test_default_agent_response_returns_dict():
    assert isinstance(get_default_agent_response("hello"), dict)


def test_normalize_intent_invalid_returns_unknown():
    assert normalize_intent("bad_intent") == "unknown"


def test_ensure_list_handles_common_values():
    assert ensure_list(None) == []
    assert ensure_list("x") == ["x"]
    assert ensure_list(["x"]) == ["x"]


def test_validate_manager_plan_completes_missing_fields():
    plan = validate_manager_plan({"intent": "cashflow_check"})
    assert plan["intent"] == "cashflow_check"
    assert "selected_agents" in plan


def test_validate_specialist_result_completes_missing_fields():
    result = validate_specialist_result({"summary": "ok"}, agent_name="cashflow_agent")
    assert result["agent_name"] == "cashflow_agent"
    assert "recommended_actions" in result


def test_normalize_confidence_invalid_returns_medium():
    assert normalize_confidence("bad") == "medium"
    assert normalize_confidence("high") == "high"


def test_merge_specialist_outputs_combines_fields():
    merged = merge_specialist_outputs(
        {
            "cashflow_agent": {
                "result": {
                    "summary": "s",
                    "findings": ["f"],
                    "risks": ["r"],
                    "recommended_actions": ["a"],
                    "questions": ["q"],
                    "needs_user_input": True,
                }
            }
        }
    )
    assert merged["summaries"] == ["s"]
    assert merged["needs_user_input"] is True

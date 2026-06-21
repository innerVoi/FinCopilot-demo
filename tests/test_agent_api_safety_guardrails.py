from agent_api.safety_guardrails import (
    build_safe_error_response,
    detect_policy_risks,
    get_agent_safety_note,
    sanitize_agent_text,
    validate_agent_output,
    validate_specialist_result_safety,
)


def test_get_agent_safety_note_returns_string():
    assert "不构成投资" in get_agent_safety_note()


def test_detect_policy_risks_detects_fraud_claim():
    risks = detect_policy_risks("这是欺诈")
    assert "这是欺诈" in risks


def test_sanitize_agent_text_appends_disclaimer():
    text = sanitize_agent_text("这是欺诈")
    assert "可能存在风险，建议核查" in text
    assert "本分析仅用于财务整理" in text


def test_validate_agent_output_returns_expected_shape():
    result = validate_agent_output({"final_answer": "这是诈骗", "safety_note": ""})
    assert set(result) == {"safe", "risks", "sanitized_output"}
    assert result["safe"] is False


def test_build_safe_error_response_returns_final_schema():
    response = build_safe_error_response("hello", "boom")
    assert response["mode"] == "fallback"
    assert response["errors"] == ["boom"]
    assert "本分析仅用于财务整理" in response["final_answer"]


def test_validate_specialist_result_safety_sanitizes_risky_text():
    result = validate_specialist_result_safety(
        {"agent_name": "anomaly_agent", "summary": "这是欺诈"}
    )
    assert result["safe"] is False
    assert "可能存在风险，建议核查" in result["sanitized_result"]["summary"]

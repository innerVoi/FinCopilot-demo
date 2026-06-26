from agent_api.answer_presenter import (
    build_action_cards,
    build_answer_presentation,
    build_clarification_cards,
    build_detail_sections,
    build_headline,
    build_metric_cards,
    build_memory_cards,
    build_report_card,
    build_risk_cards,
    build_status_badge,
    build_summary,
    ensure_list,
    infer_status_type,
    safe_get,
)


def make_turn_result():
    return {
        "mode": "fallback",
        "assistant_reply": "Cash flow has some pressure. Confirm the balance first.",
        "manager_plan": {"intent": "cashflow_check"},
        "tool_results": [{"tool_name": "get_cashflow_summary"}],
        "specialist_outputs": {
            "cashflow_agent": {
                "result": {
                    "summary": "Cash-flow safety analysis is complete",
                    "risks": ["Upcoming collection information is incomplete"],
                }
            }
        },
        "suggested_actions": ["Confirm the real account balance"],
        "chat_action_items": [
            {
                "title": "Confirm the real account balance",
                "priority": "medium",
                "description": "This information affects cash-flow judgment.",
                "suggested_deadline": "within 3 days",
                "status": "pending",
            }
        ],
        "clarifying_questions": ["What is the current available business cash balance?"],
        "report_markdown": "# report",
    }


def test_safe_get_handles_none():
    assert safe_get(None, "x", "fallback") == "fallback"


def test_ensure_list_handles_common_values():
    assert ensure_list(None) == []
    assert ensure_list("x") == ["x"]
    assert ensure_list(["x"]) == ["x"]


def test_infer_status_type_handles_values():
    assert infer_status_type("high") == "danger"
    assert infer_status_type("medium") == "warning"
    assert infer_status_type("low") == "success"
    assert infer_status_type("fallback") == "danger"


def test_build_headline_cashflow():
    assert "Cash-flow" in build_headline({"manager_plan": {"intent": "cashflow_check"}})


def test_build_summary_empty_turn_result_does_not_crash():
    assert build_summary(None)


def test_build_status_badge_returns_dict():
    badge = build_status_badge(make_turn_result())
    assert badge["label"] == "Agent Mode"


def test_build_metric_cards_returns_list():
    cards = build_metric_cards(make_turn_result())
    assert len(cards) >= 6


def test_build_risk_cards_extracts_specialist_risks():
    cards = build_risk_cards(make_turn_result())
    assert cards[0]["source"] == "cashflow_agent"
    assert "collection" in cards[0]["description"]


def test_build_action_cards_uses_chat_action_items():
    cards = build_action_cards(make_turn_result())
    assert cards[0]["title"] == "Confirm the real account balance"
    assert cards[0]["deadline"] == "within 3 days"


def test_build_clarification_cards_extracts_questions():
    cards = build_clarification_cards(make_turn_result())
    assert "available" in cards[0]["question"]


def test_build_detail_sections_by_intent():
    sections = build_detail_sections(make_turn_result())
    assert sections[0]["target_page"] == "Copilot Home"
    assert any(section["target_page"] == "Analysis Details" for section in sections)


def test_build_detail_sections_do_not_return_legacy_pages():
    legacy_pages = {"财务分析", "Agent 工作台", "行动中心", "报告中心", "数据管理"}
    sections = build_detail_sections(make_turn_result())
    assert not legacy_pages.intersection({section["target_page"] for section in sections})


def test_build_report_card_detects_report():
    report = build_report_card(make_turn_result())
    assert report["available"] is True
    assert "summary" in report
    assert len(report["title"]) < 40


def test_build_memory_cards_extracts_memory_context():
    turn_result = make_turn_result()
    turn_result["memory_context"] = {
        "memory_count": 1,
        "used_memory_ids": ["mem_1"],
        "cash_context": ["Current cash balance is 12000."],
    }
    cards = build_memory_cards(turn_result)
    assert cards[0]["title"] == "Business Memory Used"
    assert "12000" in cards[0]["items"][0]


def test_build_answer_presentation_returns_complete_structure():
    presentation = build_answer_presentation(make_turn_result())
    assert {
        "headline",
        "summary",
        "status_badge",
        "metric_cards",
        "memory_cards",
        "risk_cards",
        "action_cards",
        "clarification_cards",
        "detail_sections",
        "report",
        "debug_available",
        "safety_note",
    }.issubset(presentation)

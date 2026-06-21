from agent_api.answer_presenter import (
    build_action_cards,
    build_answer_presentation,
    build_clarification_cards,
    build_detail_sections,
    build_headline,
    build_metric_cards,
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
        "assistant_reply": "现金流存在一定压力。建议先确认余额。",
        "manager_plan": {"intent": "cashflow_check"},
        "tool_results": [{"tool_name": "get_cashflow_summary"}],
        "specialist_outputs": {
            "cashflow_agent": {
                "result": {
                    "summary": "现金流安全性分析已完成",
                    "risks": ["未来回款信息不完整"],
                }
            }
        },
        "suggested_actions": ["确认当前真实账户余额"],
        "chat_action_items": [
            {
                "title": "确认当前真实账户余额",
                "priority": "medium",
                "description": "该信息会影响现金流判断。",
                "suggested_deadline": "3 天内",
                "status": "pending",
            }
        ],
        "clarifying_questions": ["当前企业账户真实可用余额是多少？"],
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
    assert "现金流" in build_headline({"manager_plan": {"intent": "cashflow_check"}})


def test_build_summary_empty_turn_result_does_not_crash():
    assert build_summary(None)


def test_build_status_badge_returns_dict():
    badge = build_status_badge(make_turn_result())
    assert badge["label"] == "Agent 模式"


def test_build_metric_cards_returns_list():
    cards = build_metric_cards(make_turn_result())
    assert len(cards) >= 6


def test_build_risk_cards_extracts_specialist_risks():
    cards = build_risk_cards(make_turn_result())
    assert cards[0]["source"] == "cashflow_agent"
    assert "回款" in cards[0]["description"]


def test_build_action_cards_uses_chat_action_items():
    cards = build_action_cards(make_turn_result())
    assert cards[0]["title"] == "确认当前真实账户余额"
    assert cards[0]["deadline"] == "3 天内"


def test_build_clarification_cards_extracts_questions():
    cards = build_clarification_cards(make_turn_result())
    assert "真实可用余额" in cards[0]["question"]


def test_build_detail_sections_by_intent():
    sections = build_detail_sections(make_turn_result())
    assert sections[0]["target_page"] == "Copilot 主界面"
    assert any(section["target_page"] == "分析详情" for section in sections)


def test_build_detail_sections_do_not_return_legacy_pages():
    legacy_pages = {"财务分析", "Agent 工作台", "行动中心", "报告中心", "数据管理"}
    sections = build_detail_sections(make_turn_result())
    assert not legacy_pages.intersection({section["target_page"] for section in sections})


def test_build_report_card_detects_report():
    report = build_report_card(make_turn_result())
    assert report["available"] is True


def test_build_answer_presentation_returns_complete_structure():
    presentation = build_answer_presentation(make_turn_result())
    assert {
        "headline",
        "summary",
        "status_badge",
        "metric_cards",
        "risk_cards",
        "action_cards",
        "clarification_cards",
        "detail_sections",
        "report",
        "debug_available",
        "safety_note",
    }.issubset(presentation)

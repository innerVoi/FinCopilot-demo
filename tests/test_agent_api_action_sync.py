from agent_api.action_sync import (
    build_chat_action_item,
    infer_action_deadline,
    infer_action_priority,
    merge_chat_action_items,
    normalize_chat_action_text,
    summarize_chat_action_items,
    sync_turn_result_to_action_items,
)


def test_normalize_chat_action_text_handles_str():
    assert normalize_chat_action_text(" 确认余额 ") == "确认余额"


def test_normalize_chat_action_text_handles_dict():
    assert normalize_chat_action_text({"title": "核查发票"}) == "核查发票"


def test_infer_action_priority_high():
    assert infer_action_priority("今天优先处理逾期发票") == "high"


def test_infer_action_priority_medium():
    assert infer_action_priority("确认当前真实账户余额") == "medium"


def test_infer_action_deadline_by_priority():
    assert infer_action_deadline("high") == "今天"
    assert infer_action_deadline("medium") == "3 天内"
    assert infer_action_deadline("low") == "本周内"


def test_build_chat_action_item_returns_standard_item():
    item = build_chat_action_item(
        "确认当前真实账户余额",
        1,
        {"user_query": "未来 30 天现金流安全吗？", "manager_plan": {"intent": "cashflow_check"}},
    )
    assert item["action_id"] == "C001"
    assert item["source"] == "agent_chat"
    assert item["status"] == "pending"
    assert item["related_record"]["intent"] == "cashflow_check"


def test_sync_turn_result_to_action_items_generates_items():
    items = sync_turn_result_to_action_items(
        {
            "user_query": "q",
            "manager_plan": {"intent": "cashflow_check"},
            "suggested_actions": ["确认当前真实账户余额", "优先核查高风险支出"],
        }
    )
    assert [item["action_id"] for item in items] == ["C001", "C002"]
    assert items[0]["title"] == "确认当前真实账户余额"


def test_merge_chat_action_items_dedupes_by_title():
    existing = [build_chat_action_item("确认余额", 1)]
    new = [build_chat_action_item("确认余额", 1), build_chat_action_item("核查发票", 2)]
    merged = merge_chat_action_items(existing, new)
    assert len(merged) == 2
    assert [item["action_id"] for item in merged] == ["C001", "C002"]


def test_merge_chat_action_items_preserves_existing_status():
    existing = [dict(build_chat_action_item("确认余额", 1), status="done")]
    new = [build_chat_action_item("确认余额", 1)]
    merged = merge_chat_action_items(existing, new)
    assert merged[0]["status"] == "done"


def test_summarize_chat_action_items_returns_counts():
    items = [
        dict(build_chat_action_item("优先处理逾期发票", 1), status="pending"),
        dict(build_chat_action_item("生成报告", 2), status="done"),
    ]
    summary = summarize_chat_action_items(items)
    assert summary["total"] == 2
    assert summary["high"] == 1
    assert summary["low"] == 1
    assert summary["pending"] == 1
    assert summary["done"] == 1

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
    assert normalize_chat_action_text(" Confirm balance ") == "Confirm balance"


def test_normalize_chat_action_text_handles_dict():
    assert normalize_chat_action_text({"title": "Review invoices"}) == "Review invoices"


def test_infer_action_priority_high():
    assert infer_action_priority("Prioritize overdue invoices today") == "high"


def test_infer_action_priority_medium():
    assert infer_action_priority("Confirm the current real account balance") == "medium"


def test_infer_action_deadline_by_priority():
    assert infer_action_deadline("high") == "today"
    assert infer_action_deadline("medium") == "within 3 days"
    assert infer_action_deadline("low") == "this week"


def test_build_chat_action_item_returns_standard_item():
    item = build_chat_action_item(
        "Confirm the current real account balance",
        1,
        {"user_query": "Is cash flow safe for the next 30 days?", "manager_plan": {"intent": "cashflow_check"}},
    )
    assert item["action_id"].startswith("C_")
    assert item["source"] == "agent_chat"
    assert item["status"] == "pending"
    assert item["related_record"]["intent"] == "cashflow_check"


def test_sync_turn_result_to_action_items_generates_items():
    items = sync_turn_result_to_action_items(
        {
            "user_query": "q",
            "manager_plan": {"intent": "cashflow_check"},
            "suggested_actions": ["Confirm the current real account balance", "Prioritize high-risk expense review"],
        }
    )
    assert all(item["action_id"].startswith("C_") for item in items)
    assert len({item["action_id"] for item in items}) == 2
    assert items[0]["title"] == "Confirm the current real account balance"


def test_merge_chat_action_items_dedupes_by_title():
    existing = [build_chat_action_item("Confirm balance", 1)]
    new = [build_chat_action_item("Confirm balance", 1), build_chat_action_item("Review invoices", 2)]
    merged = merge_chat_action_items(existing, new)
    assert len(merged) == 2
    assert all(item["action_id"].startswith("C_") for item in merged)


def test_merge_chat_action_items_preserves_existing_status():
    existing = [dict(build_chat_action_item("Confirm balance", 1), status="done")]
    new = [build_chat_action_item("Confirm balance", 1)]
    merged = merge_chat_action_items(existing, new)
    assert merged[0]["status"] == "done"


def test_summarize_chat_action_items_returns_counts():
    items = [
        dict(build_chat_action_item("Prioritize overdue invoices", 1), status="pending"),
        dict(build_chat_action_item("Generate report", 2), status="done"),
    ]
    summary = summarize_chat_action_items(items)
    assert summary["total"] == 2
    assert summary["high"] == 1
    assert summary["low"] == 1
    assert summary["pending"] == 1
    assert summary["done"] == 1

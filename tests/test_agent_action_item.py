from agent.action_item import (
    action_item_to_display_dict,
    generate_action_id,
    make_action_item,
    normalize_priority,
    normalize_source,
)


def test_make_action_item_returns_required_fields():
    item = make_action_item(
        action_id="A001",
        title="处理逾期发票",
        description="存在逾期发票。",
        source="invoice",
        priority="high",
        reason="逾期发票会影响现金流安排。",
        suggested_deadline="今天",
        recommended_steps=["查看发票列表。"],
    )

    assert item["action_id"] == "A001"
    assert item["title"]
    assert item["source"] == "invoice"
    assert item["priority"] == "high"
    assert item["status"] == "pending"
    assert item["recommended_steps"]


def test_normalize_priority_handles_invalid_values():
    assert normalize_priority("high") == "high"
    assert normalize_priority("urgent") == "medium"
    assert normalize_priority(None) == "medium"


def test_normalize_source_handles_invalid_values():
    assert normalize_source("cashflow") == "cashflow"
    assert normalize_source("unknown") == "summary"


def test_generate_action_id_formats_index():
    assert generate_action_id(1) == "A001"


def test_action_item_to_display_dict_is_flat():
    item = make_action_item(
        "A001",
        "核查交易",
        "说明",
        "rule_anomaly",
        "medium",
        "原因",
        "7 天内",
        ["步骤"],
    )

    display = action_item_to_display_dict(item)

    assert display["action_id"] == "A001"
    assert "related_record" not in display

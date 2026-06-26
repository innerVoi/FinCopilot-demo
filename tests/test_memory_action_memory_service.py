import pytest

from memory.action_memory_service import (
    ACTION_FEEDBACK_TO_STATUS,
    count_handled_actions,
    count_pending_actions,
    get_action_item,
    is_action_feedback_allowed,
    list_handled_action_items,
    list_pending_action_items,
    mark_action_feedback_recorded,
    normalize_action_item,
    persist_action_items,
    upsert_action_item,
)


def test_normalize_action_item_generates_action_id():
    item = normalize_action_item({"title": "联系客户", "priority": "high"})
    assert item["action_id"]
    assert item["status"] == "pending"


def test_upsert_and_list_action_items_scoped(tmp_path):
    db_path = str(tmp_path / "memory.db")
    upsert_action_item("user_a", "shop_1", {"action_id": "A001", "title": "联系客户"}, db_path=db_path)
    upsert_action_item("user_b", "shop_1", {"action_id": "A001", "title": "另一个用户"}, db_path=db_path)
    rows = list_pending_action_items("user_a", "shop_1", db_path=db_path)
    assert len(rows) == 1
    assert rows[0]["title"] == "联系客户"
    assert count_pending_actions("user_a", "shop_1", db_path=db_path) == 1


def test_mark_action_feedback_recorded_updates_status_and_metadata(tmp_path):
    db_path = str(tmp_path / "memory.db")
    upsert_action_item("user_a", "shop_1", {"action_id": "A001", "title": "联系客户"}, db_path=db_path)
    result = mark_action_feedback_recorded(
        "user_a",
        "shop_1",
        "A001",
        "ignore_action",
        "客户已确认下周付款。",
        feedback_id="fb_1",
        db_path=db_path,
    )
    assert result["updated"] is True
    action = get_action_item("user_a", "shop_1", "A001", db_path=db_path)
    assert action["status"] == ACTION_FEEDBACK_TO_STATUS["ignore_action"]
    assert action["metadata"]["feedback"]["feedback_reason"] == "客户已确认下周付款。"
    assert is_action_feedback_allowed("user_a", "shop_1", "A001", db_path=db_path) is False
    assert count_handled_actions("user_a", "shop_1", db_path=db_path) == 1


def test_duplicate_action_feedback_is_rejected(tmp_path):
    db_path = str(tmp_path / "memory.db")
    upsert_action_item("user_a", "shop_1", {"action_id": "A001", "title": "联系客户"}, db_path=db_path)
    mark_action_feedback_recorded("user_a", "shop_1", "A001", "complete_action", "已完成", db_path=db_path)
    result = mark_action_feedback_recorded("user_a", "shop_1", "A001", "ignore_action", "重复", db_path=db_path)
    assert result["duplicate_feedback"] is True
    assert get_action_item("user_a", "shop_1", "A001", db_path=db_path)["status"] == "done"


def test_upsert_does_not_overwrite_handled_status(tmp_path):
    db_path = str(tmp_path / "memory.db")
    upsert_action_item("user_a", "shop_1", {"action_id": "A001", "title": "联系客户"}, db_path=db_path)
    mark_action_feedback_recorded("user_a", "shop_1", "A001", "complete_action", "已完成", db_path=db_path)
    upsert_action_item("user_a", "shop_1", {"action_id": "A001", "title": "新标题", "status": "pending"}, db_path=db_path)
    action = get_action_item("user_a", "shop_1", "A001", db_path=db_path)
    assert action["status"] == "done"
    assert action["title"] == "联系客户"


def test_persist_action_items_batch(tmp_path):
    db_path = str(tmp_path / "memory.db")
    rows = persist_action_items(
        "user_a",
        "shop_1",
        [{"action_id": "A001", "title": "联系客户"}, {"action_id": "A002", "title": "核查发票"}],
        related_turn_id="turn_1",
        db_path=db_path,
    )
    assert len(rows) == 2
    assert len(list_pending_action_items("user_a", "shop_1", db_path=db_path)) == 2

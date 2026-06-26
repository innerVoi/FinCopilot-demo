from memory.action_memory_service import get_action_item, upsert_action_item
from memory.feedback_service import list_action_item_feedback, submit_feedback


def test_submit_feedback_rejects_duplicate_action_feedback(tmp_path):
    db_path = str(tmp_path / "memory.db")
    upsert_action_item("user_a", "shop_1", {"action_id": "A001", "title": "联系客户"}, db_path=db_path)
    first = submit_feedback(
        "user_a",
        "shop_1",
        "complete_action",
        "已联系客户，对方确认明天付款。",
        target_type="action_item",
        target_id="A001",
        create_memory=False,
        db_path=db_path,
    )
    second = submit_feedback(
        "user_a",
        "shop_1",
        "ignore_action",
        "重复反馈。",
        target_type="action_item",
        target_id="A001",
        create_memory=False,
        db_path=db_path,
    )
    assert first["action_updated"] is True
    assert second["duplicate_feedback"] is True
    assert second["feedback"] is None
    assert len(list_action_item_feedback("user_a", "shop_1", action_id="A001", db_path=db_path)) == 1
    assert get_action_item("user_a", "shop_1", "A001", db_path=db_path)["status"] == "done"

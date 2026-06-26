import ui.action_feedback_panel as action_feedback_panel

from memory.feedback_service import list_action_item_feedback, submit_feedback
from memory.memory_service import list_business_memory


def test_action_item_feedback_reason_written_to_user_feedback(tmp_path):
    db_path = str(tmp_path / "memory.db")
    result = submit_feedback(
        user_id="user_a",
        workspace_id="shop_1",
        feedback_type="ignore_action",
        feedback_text="客户已经确认下周付款，暂时不需要再次催促。",
        target_type="action_item",
        target_id="A001",
        target_metadata={"action_id": "A001", "title": "联系客户确认回款"},
        create_memory=False,
        db_path=db_path,
    )
    assert result["memory_created"] is False
    rows = list_action_item_feedback("user_a", "shop_1", action_id="A001", db_path=db_path)
    assert len(rows) == 1
    assert rows[0]["target_type"] == "action_item"
    assert rows[0]["target_id"] == "A001"
    assert rows[0]["feedback_text"] == "客户已经确认下周付款，暂时不需要再次催促。"
    assert list_business_memory("user_a", "shop_1", db_path=db_path) == []


def test_action_feedback_types_do_not_create_business_memory(tmp_path):
    db_path = str(tmp_path / "memory.db")
    for feedback_type in ["complete_action", "ignore_action", "reject_suggestion", "needs_follow_up"]:
        submit_feedback(
            user_id="user_a",
            workspace_id="shop_1",
            feedback_type=feedback_type,
            feedback_text=f"{feedback_type} reason",
            target_type="action_item",
            target_id=feedback_type,
            create_memory=False,
            db_path=db_path,
        )
    assert len(list_action_item_feedback("user_a", "shop_1", db_path=db_path)) == 4
    assert list_business_memory("user_a", "shop_1", db_path=db_path) == []


def test_render_action_feedback_form_requires_reason(monkeypatch):
    class SubmitDummy:
        session_state = {}

        def __init__(self):
            self.messages = []

        def selectbox(self, label, options, **kwargs):
            return "complete_action"

        def text_area(self, *args, **kwargs):
            return ""

        def button(self, *args, **kwargs):
            return True

        def warning(self, *args, **kwargs):
            self.messages.append(("warning", args, kwargs))

        def __getattr__(self, name):
            return lambda *args, **kwargs: None

    dummy = SubmitDummy()
    monkeypatch.setattr(action_feedback_panel, "st", dummy)
    action_feedback_panel.render_action_feedback_form(
        "user_a",
        "shop_1",
        {"action_id": "A001", "title": "联系客户"},
    )
    assert any("请填写反馈原因" in call[1][0] for call in dummy.messages)

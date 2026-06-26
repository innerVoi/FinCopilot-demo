import ui.action_feedback_panel as action_feedback_panel


class DummyContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def __getattr__(self, _name):
        return lambda *args, **kwargs: None


class DummyStreamlit:
    session_state = {}

    def __init__(self):
        self.messages = []

    def __getattr__(self, name):
        def recorder(*args, **kwargs):
            self.messages.append((name, args, kwargs))
            return None

        return recorder

    def expander(self, *args, **kwargs):
        return DummyContext()

    def selectbox(self, label, options, **kwargs):
        return options[0] if options else None

    def text_area(self, *args, **kwargs):
        return ""

    def button(self, *args, **kwargs):
        return False


def patch_streamlit(monkeypatch):
    dummy = DummyStreamlit()
    monkeypatch.setattr(action_feedback_panel, "st", dummy)
    return dummy


def test_extract_action_id_uses_existing_id():
    assert action_feedback_panel.extract_action_id({"action_id": "A001"}) == "A001"


def test_extract_action_id_generates_stable_fallback():
    item = {"title": "联系客户", "priority": "high"}
    assert action_feedback_panel.extract_action_id(item) == action_feedback_panel.extract_action_id(item)


def test_build_action_target_metadata_contains_action_fields():
    metadata = action_feedback_panel.build_action_target_metadata(
        {"action_id": "A001", "title": "联系客户", "priority": "high"}
    )
    assert metadata["action_id"] == "A001"
    assert metadata["title"] == "联系客户"


def test_render_action_feedback_form_supports_empty_reason(monkeypatch):
    patch_streamlit(monkeypatch)
    monkeypatch.setattr(action_feedback_panel, "get_action_item", lambda *args, **kwargs: None)
    action_feedback_panel.render_action_feedback_form(
        "demo_user",
        "demo_workspace",
        {"action_id": "A001", "title": "联系客户"},
    )


def test_render_action_feedback_list_supports_none(monkeypatch):
    dummy = patch_streamlit(monkeypatch)
    action_feedback_panel.render_action_feedback_list("demo_user", "demo_workspace", None)
    assert any(call[0] == "info" for call in dummy.messages)


def test_render_action_feedback_form_hides_handled_action(monkeypatch):
    dummy = patch_streamlit(monkeypatch)
    monkeypatch.setattr(
        action_feedback_panel,
        "get_action_item",
        lambda *args, **kwargs: {
            "status": "done",
            "metadata": {"feedback": {"feedback_reason": "已联系客户。"}},
        },
    )
    action_feedback_panel.render_action_feedback_form(
        "demo_user",
        "demo_workspace",
        {"action_id": "A001", "title": "联系客户"},
    )
    assert any(call[0] == "info" for call in dummy.messages)

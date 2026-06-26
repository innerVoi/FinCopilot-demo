import ui.memory_feedback_panel as memory_feedback_panel


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

    def columns(self, count):
        return [DummyContext() for _ in range(count)]

    def expander(self, *args, **kwargs):
        return DummyContext()

    def button(self, *args, **kwargs):
        return False

    def selectbox(self, label, options, **kwargs):
        return options[0] if options else None


def patch_streamlit(monkeypatch):
    dummy = DummyStreamlit()
    monkeypatch.setattr(memory_feedback_panel, "st", dummy)
    return dummy


def test_memory_feedback_panel_imports():
    assert memory_feedback_panel.render_feedback_panel
    assert memory_feedback_panel.render_general_feedback_form
    assert memory_feedback_panel.render_transaction_feedback_buttons
    assert memory_feedback_panel.render_action_feedback_buttons
    assert memory_feedback_panel.render_feedback_history


def test_render_general_feedback_form_supports_demo_identity(monkeypatch):
    patch_streamlit(monkeypatch)
    memory_feedback_panel.render_general_feedback_form("demo_user", "demo_workspace")


def test_render_transaction_feedback_buttons_supports_transaction(monkeypatch):
    patch_streamlit(monkeypatch)
    memory_feedback_panel.render_transaction_feedback_buttons(
        "demo_user",
        "demo_workspace",
        {"merchant": "Acme", "amount": 800, "date": "2026-06-22"},
    )


def test_render_action_feedback_buttons_supports_action_item(monkeypatch):
    patch_streamlit(monkeypatch)
    memory_feedback_panel.render_action_feedback_buttons(
        "demo_user",
        "demo_workspace",
        {"title": "联系客户确认回款"},
    )


def test_render_feedback_history_empty_state(monkeypatch):
    dummy = patch_streamlit(monkeypatch)
    monkeypatch.setattr(memory_feedback_panel, "list_user_feedback", lambda *args, **kwargs: [])
    memory_feedback_panel.render_feedback_history("demo_user", "demo_workspace")
    assert any(call[0] == "info" for call in dummy.messages)


def test_render_feedback_panel_supports_latest_turn_none(monkeypatch):
    patch_streamlit(monkeypatch)
    memory_feedback_panel.render_feedback_panel("demo_user", "demo_workspace", latest_turn_result=None)

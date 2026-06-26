import ui.memory_management_page as memory_management_page


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

    def selectbox(self, label, options, **kwargs):
        return options[0] if options else None

    def button(self, *args, **kwargs):
        return False

    def text_input(self, *args, **kwargs):
        return ""


def patch_streamlit(monkeypatch):
    dummy = DummyStreamlit()
    monkeypatch.setattr(memory_management_page, "st", dummy)
    return dummy


def patch_services(monkeypatch):
    monkeypatch.setattr(memory_management_page, "get_workspace", lambda *args, **kwargs: None)
    monkeypatch.setattr(memory_management_page, "list_workspaces", lambda *args, **kwargs: [])
    monkeypatch.setattr(memory_management_page, "get_workspace_memory_stats", lambda *args, **kwargs: {})
    monkeypatch.setattr(memory_management_page, "list_business_memory", lambda *args, **kwargs: [])
    monkeypatch.setattr(memory_management_page, "list_user_feedback", lambda *args, **kwargs: [])
    monkeypatch.setattr(memory_management_page, "list_pending_action_items", lambda *args, **kwargs: [])
    monkeypatch.setattr(memory_management_page, "list_handled_action_items", lambda *args, **kwargs: [])
    monkeypatch.setattr(memory_management_page, "list_agent_turns", lambda *args, **kwargs: [])
    monkeypatch.setattr(memory_management_page, "list_agent_traces", lambda *args, **kwargs: [])
    monkeypatch.setattr(memory_management_page, "list_reports", lambda *args, **kwargs: [])


def test_memory_management_page_imports():
    assert memory_management_page.render_memory_management_page


def test_memory_management_sections_callable(monkeypatch):
    patch_streamlit(monkeypatch)
    patch_services(monkeypatch)
    memory_management_page.render_current_identity_card("demo_user", "demo_workspace")
    memory_management_page.render_workspace_switcher("demo_user")
    memory_management_page.render_workspace_stats("demo_user", "demo_workspace")
    memory_management_page.render_business_memory_section("demo_user", "demo_workspace")
    memory_management_page.render_feedback_section("demo_user", "demo_workspace")
    memory_management_page.render_action_memory_section("demo_user", "demo_workspace")
    memory_management_page.render_turns_section("demo_user", "demo_workspace")
    memory_management_page.render_reports_section("demo_user", "demo_workspace")
    memory_management_page.render_workspace_clear_panel("demo_user", "demo_workspace")
    memory_management_page.render_memory_management_page("demo_user", "demo_workspace")

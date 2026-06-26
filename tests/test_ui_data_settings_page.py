import inspect

import ui.data_settings_page as data_settings_page


class DummyContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def __getattr__(self, _name):
        return lambda *args, **kwargs: None


class DummyStreamlit:
    session_state = {}

    def __getattr__(self, _name):
        return lambda *args, **kwargs: None

    def columns(self, count):
        return [DummyContext() for _ in range(count)]

    def expander(self, *args, **kwargs):
        return DummyContext()

    def tabs(self, labels):
        return [DummyContext() for _ in labels]


def patch_streamlit(monkeypatch):
    dummy = DummyStreamlit()
    monkeypatch.setattr(data_settings_page, "st", dummy)
    monkeypatch.setattr(data_settings_page, "render_data_status_card", lambda *args, **kwargs: None)
    monkeypatch.setattr(data_settings_page, "render_quick_upload_panel", lambda *args, **kwargs: None)
    monkeypatch.setattr(data_settings_page, "render_upload_help", lambda *args, **kwargs: None)
    monkeypatch.setattr(data_settings_page, "render_memory_management_page", lambda *args, **kwargs: None)


def test_data_settings_page_imports():
    assert data_settings_page.render_data_settings_page


def test_render_data_upload_tab_supports_none(monkeypatch):
    patch_streamlit(monkeypatch)
    data_settings_page.render_data_upload_tab()


def test_render_data_preview_tab_supports_none(monkeypatch):
    patch_streamlit(monkeypatch)
    data_settings_page.render_data_preview_tab()


def test_render_field_guide_tab_callable(monkeypatch):
    patch_streamlit(monkeypatch)
    data_settings_page.render_field_guide_tab()


def test_render_agent_model_tab_callable(monkeypatch):
    patch_streamlit(monkeypatch)
    data_settings_page.render_agent_model_tab()


def test_render_memory_workspace_tab_supports_none(monkeypatch):
    patch_streamlit(monkeypatch)
    data_settings_page.render_memory_workspace_tab()


def test_render_safety_boundary_tab_callable(monkeypatch):
    patch_streamlit(monkeypatch)
    data_settings_page.render_safety_boundary_tab()


def test_render_data_settings_page_supports_none(monkeypatch):
    patch_streamlit(monkeypatch)
    data_settings_page.render_data_settings_page()


def test_data_settings_page_imports_memory_management_page():
    assert data_settings_page.render_memory_management_page


def test_data_settings_page_does_not_render_agent_api_switch():
    source = inspect.getsource(data_settings_page)
    assert "ENABLE_AGENT_API" not in source
    assert "checkbox" not in source
    assert "toggle" not in source

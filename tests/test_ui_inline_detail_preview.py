import ui.inline_detail_preview as inline_detail_preview


class DummyContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def __getattr__(self, _name):
        return lambda *args, **kwargs: None


class DummyStreamlit:
    def __getattr__(self, _name):
        return lambda *args, **kwargs: None

    def columns(self, count):
        return [DummyContext() for _ in range(count)]

    def container(self, *args, **kwargs):
        return DummyContext()

    def expander(self, *args, **kwargs):
        return DummyContext()


def patch_streamlit(monkeypatch):
    monkeypatch.setattr(inline_detail_preview, "st", DummyStreamlit())


def test_inline_detail_preview_imports():
    assert inline_detail_preview.render_inline_detail_preview


def test_render_inline_detail_preview_supports_none(monkeypatch):
    patch_streamlit(monkeypatch)
    inline_detail_preview.render_inline_detail_preview(None, turn_result=None)


def test_render_data_overview_preview_supports_empty_dict(monkeypatch):
    patch_streamlit(monkeypatch)
    inline_detail_preview.render_data_overview_preview({})


def test_render_cashflow_invoice_preview_supports_empty_dict(monkeypatch):
    patch_streamlit(monkeypatch)
    inline_detail_preview.render_cashflow_invoice_preview({}, {})


def test_render_anomaly_preview_supports_empty_dict(monkeypatch):
    patch_streamlit(monkeypatch)
    inline_detail_preview.render_anomaly_preview({})


def test_render_goal_preview_supports_empty_dict(monkeypatch):
    patch_streamlit(monkeypatch)
    inline_detail_preview.render_goal_preview({})


def test_render_action_preview_supports_empty_dict(monkeypatch):
    patch_streamlit(monkeypatch)
    inline_detail_preview.render_action_preview({})


def test_render_report_preview_supports_empty_dict(monkeypatch):
    patch_streamlit(monkeypatch)
    inline_detail_preview.render_report_preview({}, turn_result={})


def test_render_agent_execution_preview_supports_empty_dict(monkeypatch):
    patch_streamlit(monkeypatch)
    inline_detail_preview.render_agent_execution_preview({}, {}, {})


def test_render_detail_navigation_supports_empty_list(monkeypatch):
    patch_streamlit(monkeypatch)
    inline_detail_preview.render_detail_navigation([])

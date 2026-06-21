import ui.action_report_page as action_report_page


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

    def expander(self, *args, **kwargs):
        return DummyContext()

    def tabs(self, labels):
        return [DummyContext() for _ in labels]


def patch_streamlit(monkeypatch):
    monkeypatch.setattr(action_report_page, "st", DummyStreamlit())


def test_action_report_page_imports():
    assert action_report_page.render_action_report_page


def test_render_action_items_tab_supports_none(monkeypatch):
    patch_streamlit(monkeypatch)
    action_report_page.render_action_items_tab()


def test_render_reports_tab_supports_none(monkeypatch):
    patch_streamlit(monkeypatch)
    action_report_page.render_reports_tab()


def test_render_trace_tab_supports_none(monkeypatch):
    patch_streamlit(monkeypatch)
    action_report_page.render_trace_tab()


def test_render_action_report_page_supports_none(monkeypatch):
    patch_streamlit(monkeypatch)
    action_report_page.render_action_report_page()

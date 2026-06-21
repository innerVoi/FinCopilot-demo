import ui.analysis_detail_page as analysis_detail_page


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
    monkeypatch.setattr(analysis_detail_page, "st", DummyStreamlit())


def test_analysis_detail_page_imports():
    assert analysis_detail_page.render_analysis_detail_page


def test_render_budget_detail_tab_supports_none(monkeypatch):
    patch_streamlit(monkeypatch)
    analysis_detail_page.render_budget_detail_tab()


def test_render_invoice_cashflow_detail_tab_supports_none(monkeypatch):
    patch_streamlit(monkeypatch)
    analysis_detail_page.render_invoice_cashflow_detail_tab()


def test_render_anomaly_detail_tab_supports_none(monkeypatch):
    patch_streamlit(monkeypatch)
    analysis_detail_page.render_anomaly_detail_tab()


def test_render_goal_detail_tab_supports_none(monkeypatch):
    patch_streamlit(monkeypatch)
    analysis_detail_page.render_goal_detail_tab()


def test_render_agent_trace_detail_tab_supports_none(monkeypatch):
    patch_streamlit(monkeypatch)
    analysis_detail_page.render_agent_trace_detail_tab()


def test_render_analysis_detail_page_supports_none(monkeypatch):
    patch_streamlit(monkeypatch)
    analysis_detail_page.render_analysis_detail_page()

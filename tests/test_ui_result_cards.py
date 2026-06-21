import ui.result_cards as result_cards


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

    def tabs(self, labels):
        return [DummyContext() for _ in labels]


def patch_streamlit(monkeypatch):
    monkeypatch.setattr(result_cards, "st", DummyStreamlit())


def test_result_cards_imports():
    assert result_cards.render_answer_presentation


def test_render_answer_presentation_supports_none(monkeypatch):
    patch_streamlit(monkeypatch)
    result_cards.render_answer_presentation(None, turn_result=None)


def test_render_metric_cards_supports_empty_list(monkeypatch):
    patch_streamlit(monkeypatch)
    result_cards.render_metric_cards([])


def test_render_risk_cards_supports_empty_list(monkeypatch):
    patch_streamlit(monkeypatch)
    result_cards.render_risk_cards([])


def test_render_action_cards_supports_empty_list(monkeypatch):
    patch_streamlit(monkeypatch)
    result_cards.render_action_cards([])


def test_render_clarification_cards_supports_empty_list(monkeypatch):
    patch_streamlit(monkeypatch)
    result_cards.render_clarification_cards([])


def test_render_detail_sections_supports_empty_list(monkeypatch):
    patch_streamlit(monkeypatch)
    result_cards.render_detail_sections([])


def test_render_report_card_supports_empty_report(monkeypatch):
    patch_streamlit(monkeypatch)
    result_cards.render_report_card(None)
